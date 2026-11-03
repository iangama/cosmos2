"""Verify JRM33 worker dispatch, exact phase guards and preserved checkpoint lineage."""
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
helpers=SourceFileLoader('jupiter_worker_helpers',str(ROOT/'scripts/verify-solar-tide-worker.py')).load_module()
Worker,guard,physical=helpers.Worker,helpers.guard,helpers.physical
APP=helpers.APP
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    folder=ROOT/('output/is3-jupiter-worker-'+args.label);receipt=ROOT/('evidence/is3-jupiter-worker-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve evidence.')
    folder.mkdir();storage=folder/'sessions';storage.mkdir()
    paths=sorted(p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths += [Path(__file__).resolve(),ROOT/'scripts/verify-solar-tide-worker.py',ROOT/'IS-3-JRM33-ORIENTACAO-CONTRATO.md']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
    owner=ROOT/'user/sessions/latest.json';owner_before=sha(owner)
    base=json.loads((ROOT/'evidence/is3-tides-candidate-prepared-20261023.json').read_text(encoding='utf-8'))
    report={'schema':1,'source_sha256':hashes,'checks':{},'completed':False,'accepted':False,
        'scope':'Actual worker JRM33 binding/guards/persistence; numerical orientation evidence is separate. No native UI acceptance.'}
    def persist():receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    persist();worker=None
    try:
        worker=Worker(storage)
        initial=helpers.prepare(helpers.states('2026-10-11T12:00:00Z'));worker.call('import_atlas',initial_state=initial)
        first=copy.deepcopy(worker.latest);jupiter=next(b for b in first['bodies'] if b['reference_id']=='sol:naif:599')
        earth=next(b for b in first['bodies'] if b['reference_id']=='sol:naif:399')
        request={**guard(first),'body_id':jupiter['id'],'radius_m':1.5*71492000.,'latitude_deg':0.,'east_longitude_deg':0.,'degree':13}
        reading=worker.call('jupiter_field',**request)['result']
        assert physical(worker.latest)==physical(first)
        assert reading['scientific_generation']==first['scientific_generation']
        assert reading['epoch']['et_tdb_s']==initial['source']['epoch']['et_tdb_s']
        assert reading['body_reference_id']=='sol:naif:599' and reading['orientation']['frame']=='IAU_JUPITER'
        assert reading['jupiter_center_inertial_m']==[v*first['physical_scale']['length_unit_m'] for v in jupiter['position']]
        generation=reading['scientific_generation'];assert generation['candidate_extension']['id']=='is3-body-fields'
        assert generation['candidate_extension']['code_sha256']['jrm33.py']==sha(APP/'jrm33.py')
        assert generation['data_sha256']['output/is3-tides-product/app/jrm33-coefficients.json']==sha(APP/'jrm33-coefficients.json')
        assert 'evidence/is3-jupiter-orientation-acquisition-20261023b.json' in generation['data_sha256']
        report['checks']['read_only_field_with_current_center_epoch_and_generation']=reading
        variants=[]
        for key in request:
            bad=copy.deepcopy(request);del bad[key];variants.append(('missing_'+key,bad))
        for key,value in [('year',2026),('revision',1),('revision',True),('edit_token','stale'),('system_id','stale'),
            ('expected_time',1),('expected_time',True),('frame','SSB'),('body_id',earth['id']),
            ('radius_m',True),('radius_m',71492000.-1),('radius_m',21*71492000.),
            ('latitude_deg',91),('latitude_deg',float('nan')),('east_longitude_deg',-1),
            ('east_longitude_deg',361),('east_longitude_deg',float('inf')),('degree',30),('degree',True)]:
            bad=copy.deepcopy(request);bad[key]=value;variants.append((key+'_'+str(value),bad))
        for label,payload in variants:
            before=physical(worker.latest);worker.call('jupiter_field',expect_error=True,**payload);worker.call('snapshot')
            assert physical(worker.latest)==before,label
        report['checks']['transactional_refusals']=[label for label,_ in variants]
        for degree in [1,18]:
            value=worker.call('jupiter_field',**{**request,'degree':degree})['result']
            assert value['degree']==degree and value['field_J2000_T']!=reading['field_J2000_T']
        old_earth=worker.call('earth_field',**{**guard(first),'body_id':earth['id'],'latitude_deg':0.,'longitude_deg':0.,'altitude_m':0.})['result']
        assert old_earth['body_reference_id']=='sol:naif:399' and old_earth['orientation']['frame']=='ITRF93'
        tide=worker.call('solar_tide',**{**guard(first),'body_id':earth['id'],'offset_m':[0,0,0]})['result']
        assert tide['exact_m_s2']==[0.,0.,0.] and len(tide['sources'])==3
        worker.call('save');saved=copy.deepcopy(worker.latest)
        worker.call('resume');time.sleep(.1);worker.call('pause');evolved=copy.deepcopy(worker.latest);assert evolved['time']>0
        worker.call('jupiter_field',expect_error=True,**request);worker.call('snapshot')
        assert physical(worker.latest)==physical(evolved)
        current=worker.call('jupiter_field',**{**request,**guard(evolved)})['result']
        assert current['epoch']['et_tdb_s']==initial['source']['epoch']['et_tdb_s']+evolved['time']*evolved['physical_scale']['time_unit_s']
        assert current['field_SystemIII_T']==reading['field_SystemIII_T'] and current['field_J2000_T']!=reading['field_J2000_T']
        worker.call('load');loaded=copy.deepcopy(worker.latest)
        assert loaded['bodies']==saved['bodies'] and loaded['atlas_initial']==saved['atlas_initial']
        assert loaded['restoration']['status']=='same_generation' and loaded['edit_token']!=saved['edit_token']
        worker.call('jupiter_field',expect_error=True,**request)
        fresh=worker.call('jupiter_field',**{**request,**guard(loaded)})['result']
        assert fresh['field_J2000_T']==reading['field_J2000_T'] and fresh['point_inertial_m']==reading['point_inertial_m']
        report['checks']['degrees_Earth_tide_regression_evolution_exact_restore_and_stale_refusals']=True
        worker.close();worker=None
        older=ROOT/'output/is3-tides-product/gravity-sessions';copied=folder/'older-Earth-checkpoint';copied.mkdir()
        manifest=json.loads((older/'latest.json').read_text(encoding='utf-8'));old_hash=sha(older/'latest.json')
        for name in ['latest.json',manifest['binary']]:shutil.copy2(older/name,copied/name)
        worker=Worker(copied);worker.call('load');p=copy.deepcopy(worker.latest)
        assert p['restoration']['status']=='changed_generation' and p['atlas_initial']==manifest['atlas_initial']
        identifier=next(b['id'] for b in p['bodies'] if b['reference_id']=='sol:naif:599')
        worker.call('jupiter_field',**{**request,**guard(p),'body_id':identifier})
        assert sha(older/'latest.json')==old_hash
        report['checks']['older_Earth_checkpoint_copied_and_source_preserved']=True
        assert sha(owner)==owner_before==base['owner_pointer_sha256']
        assert all(sha(ROOT/name)==digest for name,digest in base['base_source_sha256'].items())
        assert all(sha(ROOT/name)==digest for name,digest in hashes.items())
        report['checks']['IS12_and_owner_preserved']=True
        report['completed']=report['accepted']=True
    except Exception:report['failure']=traceback.format_exc()
    finally:
        if worker is not None:worker.close()
        persist()
    print(json.dumps({'receipt':receipt.relative_to(ROOT).as_posix(),'accepted':report['accepted'],'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
