"""Independent imported-mesh frames, probes, provenance and native GPU audit."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import traceback
import zipfile
from is6_pair_profile_support import LIMITS,frame_statistics,percentile
import gpu_pdh_audit_v2 as gpu_audit
import windows_gpu_pdh_v2 as pdh

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT/'output/is6-spatial-import-product0.22.1/app'
sys.path.insert(0,str(APP))
import is6_spatial_import_store as storage
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def same_context(first,second):
    assert first['flags']==second['flags'] and first['camera'].keys()==second['camera'].keys()
    for key,value in first['camera'].items():
        if key=='Up':
            assert all(abs(a-b)<=1e-12 for a,b in zip(value,second['camera'][key],strict=True))
        else:
            assert value==second['camera'][key]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--label',required=True)
    parser.add_argument('--plan-label',default='20261105p1')
    args=parser.parse_args()
    for label in [args.label,args.plan_label]:
        if not label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
            parser.error('Invalid label')
    source=ROOT/('evidence/is6-spatial-import-profile-'+args.label+'.json')
    out=ROOT/('evidence/is6-spatial-import-profile-audit-'+args.label+'.json')
    if out.exists():
        raise FileExistsError('Preserve independent profile audit')
    r=json.loads(source.read_text())
    result=dict(accepted=False,completed=False,profile=source.relative_to(ROOT).as_posix(),
                profile_sha256=sha(source),auditor_sha256=sha(Path(__file__)),runs=[])
    try:
        assert r['completed'] and not r.get('failure') and not r.get('cleanup_failure') and not r['page_errors']
        assert r['candidate']=='0.22.1' and r['limits_before_execution']==LIMITS and r['warmup_s']==30 and r['window_s']==60
        assert all(r['processes'][key]==0 for key in ['engine_exit','server_exit','launcher_exit','launcher_wrapper_exit'])
        plan_path=ROOT/('evidence/is6-spatial-import-profile-plan-'+args.plan_label+'.json')
        plan=json.loads(plan_path.read_text())
        assert plan['accepted'] and plan['limits_before_execution']==LIMITS
        assert r['records_before']==r['records_after'] and r['records_before']
        assert [(row['run'],row['kind']) for row in r['runs']]==[(w['run'],w['kind']) for w in plan['windows']]
        assert len(r['inputs_before_execution'])==4
        expected=dict(r['source_sha256'])
        expected.update(r['persisted_archives'])
        pre=r['paused_GPU_preflight']
        expected[pre['path']]=pre['sha256']
        expected[pre['validation']]=pre['validation_sha256']
        assert json.loads((ROOT/pre['validation']).read_text())['accepted']
        preflight=json.loads((ROOT/pre['path']).read_text())
        assert preflight['expected_mode']=='experiment' and preflight['expected_worker']=='paused'
        gpu_audit.audit(preflight,expected_samples=3,expected_session=r['session'],engine_sha256=r['engine_sha256'],generation=pdh.generation())
        for item in r['inputs_before_execution']:
            expected.update(item['scene_files'])
        archive=ROOT/('output/is6-spatial-import-profile-'+args.label+'/executed-sources-inputs.zip')
        assert sha(archive)==r['archive_sha256']
        with zipfile.ZipFile(archive) as package:
            assert len(package.namelist())==len(set(package.namelist())) and set(package.namelist())==set(expected)
            assert all(hashlib.sha256(package.read(name)).hexdigest()==seal for name,seal in expected.items())
        assert all(sha(ROOT/name)==seal for name,seal in expected.items())
        assert sha(ROOT/'.runtime-is4-stream/bin/OpenSpace.exe')==r['engine_sha256']
        reference=storage.decode((ROOT/plan['reference_path']).read_bytes())
        run=storage.artifact.Run.restore(reference.payload)
        digest=storage.artifact.digest(reference.payload)
        assert digest==plan['artifact_sha256'] and reference.origin['source_sha256']==plan['source_sha256_original']
        assert reference.payload['configuration']==storage.artifact.DEFAULT_CONFIGURATION
        assert reference.payload['binding']['body_reference_id']=='sol:naif:10'
        commands=ram_peak=gpu_peak=0
        for index,(row,item) in enumerate(zip(r['runs'],plan['windows'],strict=True),1):
            recipe=json.loads((ROOT/item['path']).read_text())
            assert row['run']==index and row['kind']==recipe['kind'] and row['input']==r['inputs_before_execution'][index-1]
            assert row['input']['recipe']==item and row['input']['scene_files']
            metrics=frame_statistics(row['capture'],row['wall_interval_s'])
            initial,final=row['initial'],row['final']
            assert initial['artifact']['sha256']==final['artifact']['sha256']==digest
            assert initial['artifact']['view']==recipe['initial_view']
            assert initial['artifact']['sample']==recipe['initial_sample']==run.sample(recipe['initial_view'])
            assert initial['artifact']['origin']==final['artifact']['origin']
            assert initial['artifact']['origin']['original_view']==plan['original_view']
            assert initial['artifact']['origin']['source_sha256']==plan['source_sha256_original']
            assert initial['artifact']['archived'] is True and final['artifact']['archived'] is True
            assert len(row['commands'])==len(recipe['recipe']) and not row['producer_errors']
            guard=initial['guard']
            for actual,scheduled in zip(row['commands'],recipe['recipe'],strict=True):
                assert actual['tick']==scheduled['tick'] and abs(actual['started_offset_s']-scheduled['offset_s'])<.5
                assert actual['artifact_sha256']==digest and actual['view']==scheduled['view']
                assert actual['sample']==scheduled['sample']==run.sample(actual['view'])
                assert actual['guard']['session_id']==guard['session_id'] and actual['guard']['artifact_id']==guard['artifact_id']
                assert actual['guard']['revision']==guard['revision']+1
                guard=actual['guard']
            assert final['guard']==guard
            if recipe['recipe']:
                ratio=sum(command['finished_offset_s']<=60 for command in row['commands'])/120
                times=[command['elapsed_s'] for command in row['commands']]
                assert ratio>=LIMITS['command_rate_min'] and percentile(times,.95)<=LIMITS['command_p95_s'] and max(times)<=LIMITS['command_max_s']
                assert final['artifact']['view']==recipe['recipe'][-1]['view']
                metrics.update(command_completion_ratio=ratio,command_p95_s=percentile(times,.95),command_max_s=max(times))
                commands+=len(times)
            else:
                assert initial['artifact']==final['artifact']
            assert len(row['samples'])==4
            for part,sample in enumerate(row['samples']):
                assert abs(sample['offset_s']-part*20)<.5 and sample['paused'] is True and sample['source_phase']==r['source_phase']
                before,after=sample['spatial'],sample['following_spatial']
                assert before['guard']==after['guard'] and not before['busy'] and not after['busy']
                for snapshot in [before,after]:
                    assert snapshot['active'] and not snapshot['error'] and snapshot['artifact']['sha256']==digest
                    assert snapshot['artifact']['origin']==initial['artifact']['origin']
                    assert snapshot['artifact']['sample']==run.sample(snapshot['artifact']['view'])
                assert sample['native']['draw'] is before['artifact']['view']['visible']
                same_context(row['context'],sample['context'])
                ui=sample['ui']
                assert ui['url']=='http://127.0.0.1:4700/' and ui['scale']=='1' and ui['active'] and not ui['error']
                assert ui['guard']['session_id']==guard['session_id'] and ui['guard']['artifact_id']==guard['artifact_id']
                assert initial['guard']['revision']<=ui['guard']['revision']<=after['guard']['revision']
                memory=sample['ram']
                assert memory['sum_working_set_bytes']==sum(p['working_set_bytes'] for p in memory['processes'])
                assert memory['sum_working_set_bytes']<=LIMITS['RAM_bytes']
                ram_peak=max(ram_peak,memory['sum_working_set_bytes'])
            path=ROOT/row['gpu_report']
            assert sha(path)==row['gpu_sha256']
            gpu=json.loads(path.read_text())
            peak=gpu_audit.audit(gpu,expected_samples=66,expected_session=r['session'],engine_sha256=r['engine_sha256'],
                generation=pdh.generation(),coverage=[row['capture_start_utc'],row['capture_end_utc']])['peak_dedicated_plus_shared_bytes']
            assert peak<=LIMITS['GPU_bytes']
            for sample in row['samples']:
                assert {p['pid'] for p in sample['ram']['processes']}==set(gpu['owned_processes'])
            gpu_peak=max(gpu_peak,peak)
            result['runs'].append(dict(run=index,kind=row['kind'],**metrics,GPU_peak_GiB=peak/2**30))
        assert commands==240 and sha(ROOT/'user/sessions/latest.json')==r['owner_sha256']
        result.update(accepted=True,completed=True,commands=commands,RAM_peak_GiB=ram_peak/2**30,GPU_peak_GiB=gpu_peak/2**30,
            scope='Four imported solar65x96 rendering/view windows only; records remain unchanged. No import/save/startup throughput, larger derived mesh, coupled GR, promotion or full IS6/v1 acceptance.')
    except Exception:
        result['failure']=traceback.format_exc()
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(dict(accepted=result['accepted'],runs=len(result['runs']),failure=result.get('failure'))))
    return 0 if result['accepted'] else 1


if __name__=='__main__':
    raise SystemExit(main())
