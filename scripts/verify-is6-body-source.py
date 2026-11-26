"""Check frozen spherical-reference binding against two independently archived phases."""
from pathlib import Path
from decimal import Decimal
import argparse
import copy
import hashlib
import json
import math
import sys
import traceback
import zipfile
import mpmath as mp
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/is6-body-binding-staging'
FIXTURE=ROOT/'output/is6-body-fixtures-20261101a/fixtures-before-execution.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/f'output/is6-body-source-{args.label}';receipt=ROOT/f'evidence/is6-body-source-{args.label}.json'
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve body-source evidence')
    science_path=ROOT/'evidence/is6-spatial-20261101c.json';science=json.loads(science_path.read_text());assert science['accepted']
    files=[Path(__file__),FIXTURE,STAGE/'is6_body_source.py',STAGE/'body-reference-radii.json',
           ROOT/'scripts/prepare-is6-body-radii.py',ROOT/'scripts/prepare-is6-body-fixtures.py',
           ROOT/'IS-6-FONTE-CORPOS-CONTRATO-PREVIO.md',science_path]
    hashes=dict(science['source_sha256']);hashes.update({p.relative_to(ROOT).as_posix():sha(p) for p in files})
    app=ROOT/'output/is5-compression-product0.17.2/app'
    for p in [p for p in app.rglob('*') if p.is_file() and '__pycache__' not in p.parts]:hashes[p.relative_to(ROOT).as_posix()]=sha(p)
    folder.mkdir();archive=folder/'executed-sources.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name in hashes:z.write(ROOT/name,name)
    r=dict(accepted=False,completed=False,source_sha256=hashes,archive_sha256=sha(archive),groups=[],bindings=[],refusals=[],
           limits_before_execution=dict(center_absolute_m=.001,probe_relative=3e-13),
           scope='Headless body/source/PCK/epoch binding only; no mesh artifact, HTTP, CEF, native view, visual or profile acceptance.')
    def persist():receipt.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def passed(name):r['groups'].append(name);persist();print(json.dumps(dict(group=name,passed=True)),flush=True)
    persist()
    try:
        sys.path.insert(0,str(STAGE));import is6_body_source as source
        generation=source.generation();r['generation']=generation;mp.mp.dps=80
        fixture=json.loads(FIXTURE.read_text());before=copy.deepcopy(fixture)
        descriptors=[];maximum_center=0.;maximum_probe=0.
        for index,phase in enumerate(fixture['phases']):
            for body in phase['bodies']:
                request=dict(body_id=body['id'],source_guard=source.guard(phase))
                descriptor=source.bind(phase,request);descriptors.append((phase,descriptor))
                reference=fixture['independent_radii_m'][body['reference_id']]
                # Literal SI fixtures recover the exact original decimal km
                # inputs, then independently repeat their binary64 SI conversion.
                expected_km=[float(Decimal(str(x))/1000) for x in reference]
                expected_m=[x*1000 for x in expected_km]
                assert descriptor['boundary']['raw_radii_km']==expected_km
                assert descriptor['boundary']['reference_semiaxes_m']==expected_m
                assert descriptor['source_configuration']['material_radius_m']==max(expected_m)
                unit=phase['physical_scale']['nominal_GM_unit_m3_s2'];length=phase['physical_scale']['length_unit_m']
                assert descriptor['source_configuration']['GM_m3_s2']==body['mass']*unit
                center=np.array(body['position'])*length
                expected=np.array(descriptor['J2000_to_render'])@center
                error=float(max(abs(expected-np.array(descriptor['center_render_m']))));maximum_center=max(maximum_center,error)
                assert error<=.001
                assert descriptor['center_inertial_m']==center.tolist()
                assert descriptor['velocity_inertial_m_s']==[v*phase['physical_scale']['velocity_unit_m_s'] for v in body['velocity']]
                epoch=phase['atlas_initial']['source']['epoch']['et_tdb_s']+phase['time']*phase['physical_scale']['time_unit_s']
                assert descriptor['epoch']['et_tdb_s']==epoch and not descriptor['source_feedback']
                for factor in [1.,2.]:
                    radius=factor*max(expected_m);sample=source.evaluate(phase,descriptor,radius)
                    gm=mp.mpf(body['mass']*unit);rs=2*gm/mp.mpf(299792458)**2;rr=mp.mpf(radius)
                    for key,expected_value in dict(static_clock_ratio=mp.sqrt(1-rs/rr),metric_rr=1/(1-rs/rr),Kretschmann_m_inverse4=12*rs**2/rr**6).items():
                        error=float(abs(mp.mpf(sample[key])-expected_value)/abs(expected_value));maximum_probe=max(maximum_probe,error)
                        assert error<=3e-13,(key,error)
                    if factor==1:
                        try:source.evaluate(phase,descriptor,math.nextafter(radius,0.))
                        except ValueError:r['refusals'].append('material_boundary_next_float_inside:'+body['reference_id']+':'+str(index))
                        else:raise AssertionError('Interior accepted')
                assert source.validate(phase,descriptor)==descriptor
                r['bindings'].append(dict(phase=index,reference_id=body['reference_id'],descriptor=descriptor))
        assert fixture==before
        r.update(maximum_center_error_m=maximum_center,maximum_probe_relative_error=maximum_probe)
        passed('Four_bodies_two_actual_epochs_PCK_boundaries_GM_centers_rotation_static_metric_and_exterior_guard')
        phase,descriptor=descriptors[0];held=copy.deepcopy(descriptor)
        returned=source.bind(phase,dict(body_id=descriptor['body_id'],source_guard=source.guard(phase)))
        returned['boundary']['reference_semiaxes_m'][0]=1;returned['center_render_m'][0]=123
        assert source.bind(phase,dict(body_id=descriptor['body_id'],source_guard=source.guard(phase)))==held
        def refuse(name,payload,request=None,record=None):
            original=copy.deepcopy(payload)
            try:
                if record is not None:source.validate(payload,record)
                else:source.bind(payload,request)
            except (ValueError,KeyError):pass
            else:raise AssertionError('Invalid source accepted:'+name)
            assert payload==original
            r['refusals'].append(name)
        good=dict(body_id=descriptor['body_id'],source_guard=source.guard(phase))
        for key,value in [('revision',True),('time',True),('revision',phase['revision']+1),('time',phase['time']+1),('frame','SSB'),('system_id','0'*32)]:
            request=copy.deepcopy(good);request['source_guard'][key]=value
            refuse('guard:'+key+':'+str(value),phase,request=request)
        for key,value in [('paused',False),('revision',True),('time',True),('edit_token','wrong')]:
            bad=copy.deepcopy(phase);bad[key]=value;refuse('phase:'+key,bad,request=good)
        bad=copy.deepcopy(phase);bad['bodies'][1]['reference_id']='sol:naif:5';refuse('barycenter5_not599',bad,request=good)
        bad=copy.deepcopy(phase);bad['physical_scale']['length_unit_m']*=2;refuse('scale',bad,request=good)
        bad=copy.deepcopy(phase);bad['atlas_initial']['source']['epoch']['utc']='2020-01-01T00:00:00Z';refuse('epoch',bad,request=good)
        bad=copy.deepcopy(phase);bad['bodies'][1]['id']=bad['bodies'][0]['id'];refuse('duplicate_identity',bad,request=good)
        refuse('body_not_in_phase',phase,request={**good,'body_id':'missing'})
        refuse('body_bool',phase,request={**good,'body_id':True})
        refuse('extra_request_field',phase,request={**good,'extra':1})
        for field in ['binding_sha256','center_render_m','source_configuration','boundary','boundary_provenance','scientific_generation']:
            bad=copy.deepcopy(descriptor)
            if field=='binding_sha256':bad[field]='0'*64
            elif field=='center_render_m':bad[field][0]+=1
            elif field=='source_configuration':bad[field]['GM_m3_s2']*=2
            elif field=='boundary':bad[field]['exterior_boundary_m']=1
            elif field=='boundary_provenance':bad[field]['sha256']='0'*64
            else:bad[field]['version']='wrong'
            refuse('descriptor:'+field,phase,record=bad)
        assert source.generation()==generation and fixture==before and all(sha(ROOT/n)==v for n,v in hashes.items())
        passed('Strict_guards_phase_epoch_scale_body_identity_descriptor_seal_and_independent_copies')
        r.update(accepted=True,completed=True)
    except Exception:r['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps(dict(accepted=r['accepted'],completed=r['completed'],bindings=len(r['bindings']),refusals=len(r['refusals']),maximum_center_error_m=r.get('maximum_center_error_m'),maximum_probe_relative_error=r.get('maximum_probe_relative_error'),failure=r.get('failure'))),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
