"""Independent K3 API/UI profile audit of inputs, native flags and raw resources."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is6-layers-product0.19.1/app';sys.path.insert(0,str(APP))
import is6_layer_contract as contract
import is6_layers_profile_support as support
from is6_pair_profile_support import frame_statistics,percentile,audit_gpu
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def same_context(a,b):
    assert a['flags']==b['flags'] and a['camera'].keys()==b['camera'].keys()
    for key,value in a['camera'].items():
        if key=='Up':assert all(abs(x-y)<=1e-12 for x,y in zip(value,b['camera'][key],strict=True))
        else:assert value==b['camera'][key],key


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    source=ROOT/('evidence/is6-layers-profile-'+args.label+'.json');out=ROOT/('evidence/is6-layers-profile-audit-'+args.label+'.json')
    if out.exists():raise FileExistsError('Preserve audit')
    r=json.loads(source.read_text());result=dict(accepted=False,profile=source.relative_to(ROOT).as_posix(),profile_sha256=sha(source),auditor_sha256=sha(Path(__file__)),runs=[])
    try:
        assert r['completed'] and not r.get('failure') and not r.get('cleanup_failure') and not r['page_errors']
        assert r['warmup_s']==30 and r['window_s']==60 and r['limits_before_execution']==support.LIMITS
        assert [(v['body'],v['kind']) for v in r['runs']]==support.WINDOWS
        assert len(r['inputs_before_execution'])==len(r['scene_files_before_execution'])==4
        assert r['session']['is6LayersCandidate'] and r['session']['serverScript'].replace('\\','/').endswith('/output/is6-layers-product0.19.1/app/server.py')
        archive=ROOT/('output/is6-layers-profile-'+args.label+'/executed-sources-and-inputs.zip');assert sha(archive)==r['archive_sha256']
        expected=dict(r['source_sha256'])
        for item in r['inputs_before_execution']:expected[item['path']]=item['sha256']
        for item in r['scene_files_before_execution']:expected.update(item['sha256'])
        with zipfile.ZipFile(archive) as z:
            assert len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(expected)
            assert all(hashlib.sha256(z.read(p)).hexdigest()==seal for p,seal in expected.items())
        assert all(sha(ROOT/p)==seal for p,seal in expected.items())
        assert sha(ROOT/'.runtime-is4-stream/bin/OpenSpace.exe')==r['engine_sha256']
        commands=ram_peak=gpu_peak=0
        for index,(row,item) in enumerate(zip(r['runs'],r['inputs_before_execution'],strict=True),1):
            assert row['run']==item['run']==index and row['input']==item
            data=json.loads((ROOT/item['path']).read_text());reference='sol:naif:'+row['body'];science=data['scientific'];phase=science['spatial']['phase']
            assert support.phase_fields(phase)==r['source_phase'] and (data['body'],data['kind'])==support.WINDOWS[index-1]
            digest=support.verify_scientific(contract,science,phase,reference)
            assert data['settings']==support.settings(phase,reference) and data['recipe']==support.recipe(row['kind'])
            recipe=data['recipe'];metrics=frame_statistics(row['capture'],row['wall_interval_s'])
            first=row['initial'];artifact_id=first['artifact']['id'];scene=first['scene'];support.confirm_response(first,artifact_id,digest,dict(spatial=True,magnetic=True))
            assert len(row['commands'])==len(recipe) and not row['producer_errors']
            guard=first['guard']
            for c,scheduled in zip(row['commands'],recipe,strict=True):
                assert c['tick']==scheduled['tick'] and c['visible']==scheduled['visible'] and c['guard_before']==guard
                assert abs(c['started_offset_s']-scheduled['offset_s'])<.5
                support.confirm_response(c['response'],artifact_id,digest,scheduled['visible'])
                assert c['response']['guard']['revision']==guard['revision']+1 and c['response']['guard']['session_id']==guard['session_id']
                assert c['response']['artifact']['magnetic']==science['magnetic'] and c['response']['artifact']['admission']==science['admission']
                guard=c['response']['guard']
            if recipe:
                times=[c['elapsed_s'] for c in row['commands']];ratio=sum(c['finished_offset_s']<=60 for c in row['commands'])/120
                assert ratio>=support.LIMITS['command_rate_min'] and percentile(times,.95)<=support.LIMITS['command_p95_s'] and max(times)<=support.LIMITS['command_max_s']
                metrics.update(command_completion_ratio=ratio,command_p95_s=percentile(times,.95),command_max_s=max(times));commands+=len(recipe)
            support.confirm_response(row['final'],artifact_id,digest,dict(spatial=True,magnetic=True));assert row['final']['guard']==guard
            assert len(row['samples'])==4
            for part,s in enumerate(row['samples']):
                assert abs(s['offset_s']-part*20)<.5 and s['paused'] and s['source_phase']==r['source_phase']
                before,after=s['layers'],s['following_layers'];visible=before['artifact']['visible']
                assert visible in support.COMBINATIONS and before['guard']==after['guard']
                if row['kind']=='static':assert visible==dict(spatial=True,magnetic=True)
                for value in [before,after]:support.confirm_response(value,artifact_id,digest,visible)
                support.verify_flags(s['native'],scene,visible);same_context(row['context'],s['context'])
                ui=s['ui'];assert ui['url']=='http://127.0.0.1:4700/' and ui['scale']=='1' and not ui['panelHidden'] and ui['active'] and not ui['error']
                assert ui['guard']['session_id']==guard['session_id'] and ui['guard']['artifact_id']==artifact_id and 0<=ui['guard']['revision']<=after['guard']['revision']
                assert 'Déficit do relógio:' in ui['reading']
                ram=s['ram'];assert ram['sum_working_set_bytes']==sum(p['working_set_bytes'] for p in ram['processes']) and ram['sum_working_set_bytes']<=support.LIMITS['RAM_bytes']
                ram_peak=max(ram_peak,ram['sum_working_set_bytes'])
            assert not any(row['nodes_after_cleanup'].values());same_context(r['base_context'],row['context_after_cleanup'])
            gpu_path=ROOT/row['gpu_report'];assert sha(gpu_path)==row['gpu_sha256']
            peak=audit_gpu(json.loads(gpu_path.read_text(encoding='utf-8-sig')),r['session'],r['engine_sha256'],row);gpu_peak=max(gpu_peak,peak)
            result['runs'].append(dict(run=index,body=row['body'],kind=row['kind'],GPU_peak_GiB=peak/2**30,**metrics))
        assert commands==240 and sha(ROOT/'user/sessions/latest.json')==r['owner_sha256']
        result.update(accepted=True,commands=commands,RAM_peak_GiB=ram_peak/2**30,GPU_peak_GiB=gpu_peak/2**30,scope=r['scope'])
    except Exception:result['failure']=traceback.format_exc()
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(result,ensure_ascii=False),flush=True)
    return 0 if result['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
