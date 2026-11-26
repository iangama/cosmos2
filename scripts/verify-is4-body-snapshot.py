"""Bind frozen body fields and four-center gravity to one paused scientific phase."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import sys
import traceback
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is3-body-points-product/app';STAGE=ROOT/'output/is4-body-particle-staging'
sys.path[:0]=[str(STAGE),str(APP)]
from session import Session
from body_field_lines import Model
import geomagnetism as igrf
from is4_body_snapshot import Snapshot
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
guard=lambda p:{k:p[k] for k in ['system_id','edit_token','revision']}|{'frame':p['contract']['frame'],'expected_time':p['time']}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    folder=ROOT/('output/is4-body-snapshot-'+args.label);receipt=ROOT/('evidence/is4-body-snapshot-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve snapshot evidence.')
    folder.mkdir();owner=sha(ROOT/'user/sessions/latest.json')
    old=ROOT/'output/is3-body-points-product/gravity-sessions/latest.json'
    initial=json.loads(old.read_text(encoding='utf-8'))['atlas_initial']
    session=Session(folder/'session');session.import_atlas(initial);phase={**session.state(),'paused':True}
    before=copy.deepcopy(phase);fixtures=[]
    for kind,degree in [('IGRF14',13),('JRM33',1),('JRM33',13),('JRM33',18)]:
        body=next(b for b in phase['bodies'] if b['reference_id']==('sol:naif:399' if kind=='IGRF14' else 'sol:naif:599'))
        request={**guard(phase),'body_id':body['id']}
        reading=session.earth_field({**request,'latitude_deg':-23.55,'longitude_deg':-46.63,'altitude_m':1000.}) if kind=='IGRF14' else session.jupiter_field({**request,'radius_m':1.5*71492000.,'latitude_deg':30.,'east_longitude_deg':90.,'degree':degree})
        path=folder/(kind+'-'+str(degree)+'.json');path.write_text(json.dumps({'phase':phase,'reading':reading},indent=2)+'\n',encoding='utf-8');fixtures.append((kind,degree,path))
    files=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [*STAGE.glob('*.py'),Path(__file__),ROOT/'IS-4-PARTICULAS-CONTRATO-PREVIO.md',*[p for _,_,p in fixtures]]
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(folder/'executed-sources-and-fixtures.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    report={'schema':1,'accepted':False,'completed':False,'source_sha256':hashes,'models':[]}
    try:
        refusals=0
        for kind,degree,path in fixtures:
            fixture=json.loads(path.read_text(encoding='utf-8'));p,r=fixture['phase'],fixture['reading']
            frozen=Snapshot(p,r);trusted=Model(r)
            rotation=np.array(r['ITRF93_to_J2000' if kind=='IGRF14' else 'SystemIII_to_J2000'])
            selected=next(b for b in p['bodies'] if b['id']==r['body_id'])
            length=p['physical_scale']['length_unit_m'];gm_unit=p['physical_scale']['nominal_GM_unit_m3_s2']
            source_offsets=[(np.array(b['position'])-selected['position'])*length for b in p['bodies']]
            gms=[b['mass']*gm_unit for b in p['bodies']]
            points=[]
            for lat in [-80.,-23.55,0.,45.,90.]:
                for lon in [-135.,0.,90.]:
                    if kind=='IGRF14':
                        points.extend(igrf.field_at(r['epoch']['decimal_UTC_year'],lat,lon,h)['position_ecef_m'] for h in [1.,1000.,500000.,999999.])
                    else:
                        a,l=math.radians(lat),math.radians(lon)
                        points.extend([radius*math.cos(a)*math.cos(l),radius*math.cos(a)*math.sin(l),radius*math.sin(a)] for radius in [1.00001*71492000.,2*71492000.,19.99*71492000.])
            max_b=max_g=max_potential=0.
            for point in points:
                actual=frozen.evaluate(point);field=trusted.field(point)
                assert max(abs(a-b) for a,b in zip(actual['magnetic_field_T'],field))<=2e-18
                # Independent gravity in J2000, then rotate back. Do not use
                # the adapter's transformed Source objects or evaluate kernel.
                inertial=rotation@point;deltas=[inertial-center for center in source_offsets]
                radii=[np.linalg.norm(delta) for delta in deltas]
                reference=rotation.T@sum((-gm*delta/radius**3 for gm,delta,radius in zip(gms,deltas,radii)),np.zeros(3))
                expected_potential=-sum(gm/radius for gm,radius in zip(gms,radii))
                assert np.allclose(actual['gravity_m_s2'],reference,rtol=2e-13,atol=1e-12)
                assert math.isclose(actual['gravity_potential_J_kg'],expected_potential,rel_tol=1e-12)
                max_b=max(max_b,max(abs(a-b) for a,b in zip(actual['magnetic_field_T'],field)))
                max_g=max(max_g,float(np.max(np.abs(reference-actual['gravity_m_s2']))))
                max_potential=max(max_potential,abs(actual['gravity_potential_J_kg']-expected_potential))
                assert actual['electric_field_V_m']==[0.,0.,0.]
            radius=igrf.WGS_A if kind=='IGRF14' else 71492000.
            outer=radius+1e6 if kind=='IGRF14' else 20*radius
            calls=frozen.magnetic_evaluations
            for bad in [[0.,0.,0.],[radius-1.,0.,0.],[outer+1.,0.,0.]]:
                assert not frozen.segment_in_domain(bad,bad)
                try:frozen.evaluate(bad)
                except ValueError:refusals+=1
                else:raise AssertionError('Unavailable field queried.')
                assert frozen.magnetic_evaluations==calls
            chord=radius+1000. if kind=='IGRF14' else 2*radius
            assert not frozen.segment_in_domain([-chord,0.,0.],[chord,0.,0.])
            assert frozen.magnetic_evaluations==calls
            original=frozen.evaluate(frozen.seed_m);descriptor=frozen.descriptor
            p['bodies'][0]['mass']*=2;r['epoch']['utc']='mutated';descriptor['sources'][0]['GM_m3_s2']=0.
            assert frozen.evaluate(frozen.seed_m)==original and frozen.descriptor['reading']['epoch']['utc']!='mutated'
            report['models'].append({'model':kind,'degree':degree,'points':len(points),'B_max_error_T':max_b,'gravity_max_error_m_s2':max_g,
                'potential_max_error_J_kg':max_potential,'invalid_domain_no_provider_calls':True,'input_and_export_mutations_isolated':True,'fixture':path.relative_to(ROOT).as_posix()})
        fixture=json.loads(fixtures[0][2].read_text(encoding='utf-8'))
        for target,key,value in [('phase','paused',False),('phase','revision',True),('phase','time',True),('reading','time',1.),
            ('reading','frame','rotating'),('reading','field_norm_T',1.),('reading','ITRF93_to_J2000',[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])]:
            bad=copy.deepcopy(fixture);bad[target][key]=value
            try:Snapshot(bad['phase'],bad['reading'])
            except ValueError:refusals+=1
            else:raise AssertionError((target,key))
        for edit in ['units','source_mass','source_duplicate','source_position','generation','extra_gravity','fixture_hash']:
            bad=copy.deepcopy(fixture)
            if edit=='units':bad['phase']['physical_scale']['length_unit_m']*=2
            if edit=='source_mass':bad['phase']['bodies'][0]['mass']=True
            if edit=='source_duplicate':bad['phase']['bodies'][0]['id']=bad['phase']['bodies'][1]['id']
            if edit=='source_position':bad['phase']['bodies'][1]['position'][0]+=1.
            if edit=='generation':bad['reading']['scientific_generation']['schema']=99
            if edit=='extra_gravity':bad['phase']['gravity_effects']={'J2':True}
            if edit=='fixture_hash':bad['phase']['fixture_sha256']='bad'
            try:Snapshot(bad['phase'],bad['reading'])
            except ValueError:refusals+=1
            else:raise AssertionError(edit)
        assert {**session.state(),'paused':True}==before and sha(ROOT/'user/sessions/latest.json')==owner
        assert all(sha(ROOT/name)==value for name,value in hashes.items())
        report.update(accepted=True,completed=True,refusals=refusals,session_phase_unchanged=True,owner_pointer_unchanged=True,
            scope='Coherent paused static body-field/four-monopole snapshot, same SI providers, independent rotated gravity and potential, inner/outer/segment domain gates and mutation/refusal guards. Body trajectories/DOP853, live environment, worker, native and performance separate.')
    except Exception:report['failure']=traceback.format_exc()
    receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'accepted':report['accepted'],'models':len(report['models']),'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
