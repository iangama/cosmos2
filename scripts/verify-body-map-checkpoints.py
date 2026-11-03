"""Persist map cell indices and frozen provider data atomically, including masked refusals."""
from pathlib import Path
import copy
import hashlib
import json
import shutil
import sys
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is3-body-maps-product/app'
sys.path.insert(0,str(APP))
from session import Session
from body_registry import digest
import body_field_maps as maps
import body_field_view as view

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
phase=lambda s:(s.sim.t,[(p.m,p.x,p.y,p.z,p.vx,p.vy,p.vz) for p in s.sim.particles])
guard=lambda p:{k:p[k] for k in ['system_id','edit_token','revision']}|{'frame':p['contract']['frame'],'expected_time':p['time']}


def main():
    folder=ROOT/'output/is3-map-checkpoints-20261024a';receipt=ROOT/'evidence/is3-map-checkpoints-20261024a.json'
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve map checkpoint evidence.')
    folder.mkdir()
    paths=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [Path(__file__).resolve(),ROOT/'IS-3-MAPAS-NATIVOS-CONTRATO.md']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths};owner=sha(ROOT/'user/sessions/latest.json')
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for p in paths:archive.write(p,p.relative_to(ROOT).as_posix())
    old=ROOT/'output/is3-body-view-topology-product/gravity-sessions'
    manifest=json.loads((old/'latest.json').read_text(encoding='utf-8'));initial=manifest['atlas_initial']
    report={'schema':1,'accepted':False,'completed':False,'source_sha256':hashes,'cases':[]}
    try:
        for model in ['IGRF14','JRM33']:
            for representation in ['shell','cut']:
                for visible in [False,True]:
                    storage=folder/(model+'-'+representation+'-'+str(visible));session=Session(storage);session.import_atlas(initial)
                    p=session.state();body=next(b for b in p['bodies'] if b['reference_id']==('sol:naif:399' if model=='IGRF14' else 'sol:naif:599'))
                    parameters={'latitude_deg':-23.55,'longitude_deg':-46.63,'altitude_m':1000.} if model=='IGRF14' else {'radius_m':1.5*71492000.,'latitude_deg':0.,'east_longitude_deg':0.,'degree':13}
                    reading=getattr(session,'earth_field' if model=='IGRF14' else 'jupiter_field')({**guard(p),'body_id':body['id'],**parameters})
                    data=maps.build(reading);row,column=(9,9) if representation=='shell' else (32,61 if model=='IGRF14' else 48)
                    assert data[representation]['samples'][row][column] is not None
                    session.sim.integrate(3600./p['physical_scale']['time_unit_s']);p=session.state()
                    config={'selected_body_id':body['id'],'representation':representation,'earth':[-23.55,-46.63,1000.],
                            'jupiter':[1.5*71492000.,0.,0.,13]}
                    metadata=view.capture(p,config,{'reading':reading,'representation':representation,'visible':visible,'map_probe':{'row':row,'column':column}})
                    before=phase(session);session.save(renderer_view=metadata);assert phase(session)==before
                    restored=Session(storage);restored.load();assert phase(restored)==before and restored.body_field_view==metadata
                    rebuilt=maps.build(restored.body_field_view['layer']['reading'])
                    assert rebuilt[representation]['samples'][row][column]==data[representation]['samples'][row][column]
                    branch=restored.create_branch({**guard(restored.state()),'name':'map-cell','renderer_view':metadata})
                    restored.load_branch({**guard(restored.state()),'branch_id':branch['id']})
                    assert phase(restored)==before and restored.body_field_view==metadata
                    report['cases'].append({'model':model,'representation':representation,'visible':visible,'cell':[row,column],
                                            'checkpoint_branch_phase_and_stored_SI_sample_exact':True})
        saved_hashes={p.name:sha(p) for p in storage.iterdir() if p.is_file()};refusals=0
        for cell in [{'row':True,'column':0},{'row':65,'column':0},{'row':0,'column':-1},
                     {'row':32,'column':32},{'row':32,'column':48,'native_id':'unknown'}]:
            bad=copy.deepcopy(metadata);bad['layer']['map_probe']=cell
            try:session.save(renderer_view=bad)
            except ValueError:refusals+=1
            else:raise AssertionError('Invalid saved map cell accepted.')
            assert phase(session)==before and {p.name:sha(p) for p in storage.iterdir() if p.is_file()}==saved_hashes
            broken=json.loads((storage/'latest.json').read_text(encoding='utf-8'));broken['body_field_view']=bad
            broken['manifest_sha256']=digest({k:v for k,v in broken.items() if k!='manifest_sha256'})
            isolated=folder/('invalid-cell-'+str(refusals));isolated.mkdir()
            shutil.copy2(storage/broken['binary'],isolated/broken['binary'])
            (isolated/'latest.json').write_text(json.dumps(broken)+'\n',encoding='utf-8')
            active=Session(isolated);active_before=phase(active)
            try:active.load()
            except ValueError:refusals+=1
            else:raise AssertionError('Invalid restored map cell accepted.')
            assert phase(active)==active_before
        copied=folder/'older-0.6.1';copied.mkdir()
        for name in ['latest.json',manifest['binary']]:shutil.copy2(old/name,copied/name)
        previous=Session(copied);previous.load();assert previous.state()['restoration']['status']=='changed_generation'
        assert all(sha(ROOT/name)==value for name,value in hashes.items()) and sha(ROOT/'user/sessions/latest.json')==owner
        report.update(accepted=True,completed=True,transactional_cell_refusals=refusals,older_checkpoint_readable=True,
                      scope='Atomic map-cell configuration/reading/checkpoint/branch validation and SI sample reproduction; actual native probe/CEF/restart/performance separate.')
    except Exception:report['failure']=traceback.format_exc()
    receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'accepted':report['accepted'],'cases':len(report['cases']),'refusals':report.get('transactional_cell_refusals'),'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
