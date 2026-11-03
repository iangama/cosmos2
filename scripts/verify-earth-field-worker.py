"""Verify the scene Earth-field command, stale guards and checkpoint provenance."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import shutil
import time
import traceback
import zipfile
from importlib.machinery import SourceFileLoader

ROOT=Path(__file__).resolve().parents[1]
helpers=SourceFileLoader('tide_worker_helpers',str(ROOT/'scripts/verify-solar-tide-worker.py')).load_module()
Worker,guard,physical=helpers.Worker,helpers.guard,helpers.physical
APP=helpers.APP
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    folder=ROOT/('output/is3-earth-worker-'+args.label);receipt=ROOT/('evidence/is3-earth-worker-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve worker evidence.')
    folder.mkdir();storage=folder/'sessions';storage.mkdir()
    paths=sorted(p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths += [Path(__file__).resolve(),ROOT/'scripts/verify-solar-tide-worker.py',ROOT/'IS-3-IGRF-CONTRATO.md']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
    owner=ROOT/'user/sessions/latest.json';owner_before=sha(owner)
    base=json.loads((ROOT/'evidence/is3-tides-candidate-prepared-20261023.json').read_text(encoding='utf-8'))
    report={'schema':1,'source_sha256':hashes,'checks':{},'accepted':False,
        'scope':'Actual worker command/guards/persistence integration; staged numerical field checks have separate evidence. No native UI acceptance.'}
    def persist():receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    persist();worker=None
    try:
        worker=Worker(storage)
        initial=helpers.prepare(helpers.states('2026-10-11T12:00:00Z'));worker.call('import_atlas',initial_state=initial)
        first=copy.deepcopy(worker.latest);earth=next(b for b in first['bodies'] if b['reference_id']=='sol:naif:399')
        request={**guard(first),'body_id':earth['id'],'latitude_deg':-23.55,'longitude_deg':-46.63,'altitude_m':1000}
        reading=worker.call('earth_field',**request)['result']
        assert physical(worker.latest)==physical(first)
        assert reading['scientific_generation']==first['scientific_generation']
        assert reading['epoch']['et_tdb_s']==initial['source']['epoch']['et_tdb_s']
        assert reading['orientation']['status']=='EOP_supported_region'
        assert reading['body_reference_id']=='sol:naif:399'
        assert reading['earth_center_inertial_m']==[v*first['physical_scale']['length_unit_m'] for v in earth['position']]
        generation=reading['scientific_generation']
        assert generation['candidate_extension']['id']=='is3-earth-field'
        assert 'earth_magnetism.py' in generation['candidate_extension']['code_sha256']
        assert 'output/is3-earth-orientation-staging/earth_000101_270118_261022.bpc' in generation['data_sha256']
        report['checks']['actual_read_only_field_with_epoch_body_and_generation']=True
        variants=[]
        for key in request:
            bad=copy.deepcopy(request);del bad[key];variants.append(('missing_'+key,bad))
        for key,value in [('year',2026),('revision',1),('revision',True),('edit_token','stale'),('system_id','stale'),
            ('expected_time',1),('expected_time',True),('frame','SSB'),('body_id',first['bodies'][2]['id']),
            ('latitude_deg',True),('latitude_deg',91),('longitude_deg',float('nan')),('longitude_deg',181),
            ('altitude_m',-1),('altitude_m',1000001),('altitude_m',float('inf'))]:
            bad=copy.deepcopy(request);bad[key]=value;variants.append((key+'_'+str(value),bad))
        for label,payload in variants:
            before=physical(worker.latest);worker.call('earth_field',expect_error=True,**payload);worker.call('snapshot')
            assert physical(worker.latest)==before,label
        report['checks']['transactional_refusals']=[label for label,_ in variants]
        # Existing tide command continues through the modified worker dispatcher.
        tide=worker.call('solar_tide',**{**guard(worker.latest),'body_id':earth['id'],'offset_m':[0,0,0]})['result']
        assert tide['exact_m_s2']==[0.,0.,0.] and len(tide['sources'])==3
        worker.call('save');saved=copy.deepcopy(worker.latest)
        worker.call('resume');time.sleep(.1);worker.call('pause');evolved=copy.deepcopy(worker.latest)
        assert evolved['time']>0
        worker.call('earth_field',expect_error=True,**request)
        worker.call('snapshot');assert physical(worker.latest)==physical(evolved)
        current=worker.call('earth_field',**{**guard(evolved),'body_id':earth['id'],'latitude_deg':-23.55,'longitude_deg':-46.63,'altitude_m':1000})['result']
        assert current['epoch']['et_tdb_s']==initial['source']['epoch']['et_tdb_s']+evolved['time']*evolved['physical_scale']['time_unit_s']
        assert current['point_inertial_m']!=reading['point_inertial_m']
        worker.call('load');loaded=copy.deepcopy(worker.latest)
        assert loaded['bodies']==saved['bodies'] and loaded['atlas_initial']==saved['atlas_initial']
        assert loaded['restoration']['status']=='same_generation' and loaded['edit_token']!=saved['edit_token']
        worker.call('earth_field',expect_error=True,**request)
        fresh=worker.call('earth_field',**{**guard(loaded),'body_id':earth['id'],'latitude_deg':-23.55,'longitude_deg':-46.63,'altitude_m':1000})['result']
        assert fresh['field_J2000_T']==reading['field_J2000_T'] and fresh['point_inertial_m']==reading['point_inertial_m']
        report['checks']['tide_regression_evolution_exact_restore_and_token_refusals']=True
        worker.close();worker=None
        older=ROOT/'output/is3-tides-product/gravity-sessions';copy_folder=folder/'older-tide-checkpoint';copy_folder.mkdir()
        old_manifest=json.loads((older/'latest.json').read_text(encoding='utf-8'));old_hash=sha(older/'latest.json')
        for name in ['latest.json',old_manifest['binary']]:shutil.copy2(older/name,copy_folder/name)
        worker=Worker(copy_folder);worker.call('load');p=copy.deepcopy(worker.latest)
        assert p['restoration']['status']=='changed_generation' and p['atlas_initial']==old_manifest['atlas_initial']
        identifier=next(b['id'] for b in p['bodies'] if b['reference_id']=='sol:naif:399')
        worker.call('earth_field',**{**guard(p),'body_id':identifier,'latitude_deg':0,'longitude_deg':0,'altitude_m':0})
        assert sha(older/'latest.json')==old_hash
        report['checks']['older_tide_checkpoint_copied_source_preserved']=True
        assert sha(owner)==owner_before==base['owner_pointer_sha256']
        assert all(sha(ROOT/name)==digest for name,digest in base['base_source_sha256'].items())
        assert all(sha(ROOT/name)==digest for name,digest in hashes.items())
        report['checks']['IS12_and_owner_preserved']=True
        report['accepted']=True
    except Exception:report['failure']=traceback.format_exc()
    finally:
        if worker is not None:worker.close()
        persist()
    print(json.dumps({'receipt':receipt.relative_to(ROOT).as_posix(),'accepted':report['accepted'],'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1

if __name__=='__main__':raise SystemExit(main())
