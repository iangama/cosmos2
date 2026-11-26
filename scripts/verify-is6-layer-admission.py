"""Audit real independent magnetic/spatial references before any native coupling."""
from pathlib import Path
import copy
import hashlib
import itertools
import json
import sys
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is6-spatial-product0.18.5/app'
sys.path[:0]=[str(ROOT/'output/is6-layer-coordination-staging'),str(APP)]
import is6_layer_contract as contract

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    receipt=ROOT/'evidence/is6-layer-admission-20261102a.json'
    folder=ROOT/'output/is6-layer-admission-20261102a'
    if receipt.exists() or folder.exists():raise FileExistsError('Preserve evidence')
    manifest=APP.parent/'build-manifest.json';m=json.loads(manifest.read_text())
    sources=dict(m['source_sha256'])
    sources.update({(APP/n).relative_to(ROOT).as_posix():v for n,v in m['files_sha256'].items()})
    seed=ROOT/'output/is6-spatial-profile-20261102c/artifact-1.json'
    anchor=ROOT/'evidence/is6-spatial-profile-audit-20261102c.json'
    assert json.loads(anchor.read_text())['accepted']
    for p in [Path(__file__),Path(contract.__file__),manifest,seed,anchor,ROOT/'IS-6-COEXISTENCIA-CONTRATO-PREVIO.md']:
        sources[p.relative_to(ROOT).as_posix()]=sha(p)
    assert all(sha(ROOT/n)==v for n,v in sources.items())
    folder.mkdir()
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in sources:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=sources,cases=[],refusals=[],
           owner_sha256=sha(ROOT/'user/sessions/latest.json'),native_coexistence_confirmed=False,
           scope='K0 CPU admission and independent model recomputation only. No native, UI, migration, composite restore or performance acceptance.')
    def persist():receipt.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    def refuse(name,phase,payload,reading,visibility):
        before=contract.digest([phase,payload,reading,visibility])
        try:contract.compose(phase,payload,reading,visibility)
        except ValueError as error:r['refusals'].append(dict(case=name,error=str(error)))
        else:raise AssertionError('Accepted incompatible references: '+name)
        assert contract.digest([phase,payload,reading,visibility])==before,'Refusal mutated input'
    persist()
    try:
        seed_payload=json.loads(seed.read_text());phase=seed_payload['phase']
        for target in ['399','599']:
            body=next(b for b in phase['bodies'] if b['reference_id']=='sol:naif:'+target)
            run=contract.artifact.Run.create(phase,dict(body_id=body['id'],source_guard=contract.artifact.body.guard(phase)),contract.artifact.DEFAULT_CONFIGURATION)
            reading=(contract.earth_magnetism.read(phase,body['id'],-23.55,-46.63,1000.) if target=='399' else contract.jupiter_magnetism.read(phase,body['id'],1.5*71492000.,0.,0.,13))
            payload=run.payload;frozen=contract.digest([phase,payload,reading]);plans=[]
            for spatial,magnetic in itertools.product([False,True],repeat=2):
                plan=contract.compose(phase,payload,reading,dict(spatial=spatial,magnetic=magnetic))
                assert [x['visible'] for x in plan['layers']]==[spatial,magnetic]
                assert plan['layers'][1]['uncertainty'] is None and not plan['physical_coupling'] and not plan['native_coexistence_confirmed']
                assert contract.digest([phase,payload,reading])==frozen
                plans.append(plan)
            assert len({tuple(x['solution_sha256'] for x in p['layers']) for p in plans})==1
            assert len({p['plan_sha256'] for p in plans})==4
            (folder/(target+'-plans.json')).write_text(json.dumps(plans,indent=2)+'\n',encoding='utf8')
            visible=dict(spatial=True,magnetic=True)
            bad=copy.deepcopy(phase);bad['time']+=1;refuse(target+'_different_orbital_phase',bad,payload,reading,visible)
            bad=copy.deepcopy(payload);bad['mesh']['display_vertices_relative_m'][0][0]+=1.;refuse(target+'_modified_mesh',phase,bad,reading,visible)
            bad=copy.deepcopy(payload);bad['generation']['version']='future';refuse(target+'_future_generation',phase,bad,reading,visible)
            mutations=[('body_id','foreign'),('body_reference_id','sol:naif:301'),('frame','GALACTIC'),('time',1.),('revision',99),('uncertainty',0.),('field_norm_T',0.)]
            for key,value in mutations:
                bad=copy.deepcopy(reading);bad[key]=value;refuse(target+'_reading_'+key,phase,payload,bad,visible)
            for key in ['et_tdb_s','utc']:
                bad=copy.deepcopy(reading);bad['epoch'][key]=0 if key=='et_tdb_s' else '2000-01-01T00:00:00Z';refuse(target+'_epoch_'+key,phase,payload,bad,visible)
            bad=copy.deepcopy(reading);bad['field_render_T'][0]+=1e-6;refuse(target+'_field_vector',phase,payload,bad,visible)
            bad=copy.deepcopy(reading);bad['J2000_to_render'][0][0]+=.01;refuse(target+'_rotation',phase,payload,bad,visible)
            bad=copy.deepcopy(reading);bad['provenance']['PCK_sha256']='0'*64;refuse(target+'_PCK_source',phase,payload,bad,visible)
            bad=copy.deepcopy(reading);bad['unsupported_electric_field_T']=[0.,0.,0.];refuse(target+'_invented_capability',phase,payload,bad,visible)
            for i,v in enumerate([dict(spatial=1,magnetic=True),dict(spatial=True),dict(spatial=True,magnetic=True,strong=True)]):
                refuse(target+'_visibility_'+str(i),phase,payload,reading,v)
            r['cases'].append(dict(body=target,model=reading['provenance']['model'],visibility_combinations=4,
                                   source_phase_sha256=contract.digest(phase),spatial_sha256=contract.artifact.digest(payload),magnetic_sha256=contract.digest(reading)))
            persist()
        assert sha(ROOT/'user/sessions/latest.json')==r['owner_sha256']
        assert all(sha(ROOT/n)==v for n,v in sources.items())
        r.update(accepted=True,completed=True)
    except Exception:r['failure']=traceback.format_exc()
    persist();print(json.dumps(dict(accepted=r['accepted'],cases=len(r['cases']),refusals=len(r['refusals']),failure=r.get('failure','').splitlines()[-1:]),ensure_ascii=False))
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
