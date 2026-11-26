"""Independent audit of raw spatial frames, exact probes and process resources."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import math
import re
import statistics
import sys
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'output/is6-spatial-product0.18.2/app'))
from is6_product_scene import artifact
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def percentile(values,q):
    a=sorted(values);i=(len(a)-1)*q;lo,hi=math.floor(i),math.ceil(i)
    return a[lo]+(a[hi]-a[lo])*(i-lo)


def phase(p):return {k:p[k] for k in ['system_id','edit_token','revision','time','bodies','atlas_initial','interventions']}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);parser.add_argument('--audit-label');args=parser.parse_args()
    for label in [args.label,args.audit_label or args.label]:
        if not label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):parser.error('Invalid label')
    source=ROOT/('evidence/is6-spatial-profile-'+args.label+'.json');out=ROOT/('evidence/is6-spatial-profile-audit-'+(args.audit_label or args.label)+'.json')
    if out.exists():raise FileExistsError('Preserve audit')
    r=json.loads(source.read_text());result=dict(accepted=False,profile=source.relative_to(ROOT).as_posix(),profile_sha256=sha(source),auditor_sha256=sha(Path(__file__)),runs=[])
    try:
        assert r['completed'] and not r.get('failure') and not r.get('cleanup_failure') and not r['page_errors']
        assert r['warmup_s']==30 and r['window_s']==60
        limits=dict(median_ms=16.7,p95_ms=25.,p99_ms=50.,over_100ms=0,RAM_bytes=8*2**30,GPU_bytes=5.5*2**30,command_rate_min=.9,command_p95_s=.5,command_max_s=1.)
        assert r['limits_before_execution']==limits
        assert [(v['kind'],v['radial_count']) for v in r['runs']]==[('static-default',65),('static-maximum',257),('probe-maximum',257),('visibility-maximum',257)]
        assert len(r['inputs_before_execution'])==4
        assert r['session']['is6SpatialCandidate'] and r['session']['serverScript'].replace('\\','/').endswith('/output/is6-spatial-product0.18.2/app/server.py')
        archive=ROOT/('output/is6-spatial-profile-'+args.label+'/executed-sources.zip');assert sha(archive)==r['archive_sha256']
        expected=dict(r['source_sha256'])
        for row in r['runs']:
            for key in ['artifact','recipe']:expected[row[key]]=row[key+'_sha256']
        with zipfile.ZipFile(archive) as z:
            assert len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(expected)
            assert all(hashlib.sha256(z.read(n)).hexdigest()==v for n,v in expected.items())
        assert all(sha(ROOT/n)==v for n,v in expected.items())
        assert sha(ROOT/'.runtime-is4-stream/bin/OpenSpace.exe')==r['engine_sha256']
        ram_peak=gpu_peak=exact_samples=0
        for row,inputs in zip(r['runs'],r['inputs_before_execution']):
            assert all(inputs[k]==row[k] for k in ['run','artifact','artifact_sha256','recipe','recipe_sha256'])
            payload=json.loads((ROOT/row['artifact']).read_text());run=artifact.Run.restore(payload)
            recipe=json.loads((ROOT/row['recipe']).read_text());digest=artifact.digest(payload)
            assert payload['configuration']=={**artifact.DEFAULT_CONFIGURATION,'radial_count':row['radial_count']}
            assert payload['binding']['body_reference_id']=='sol:naif:10'
            capture=row['capture'];assert capture['width']==1920 and capture['height']==1080 and not capture['capacity_reached'] and capture['invalid_samples']==0
            raw=capture['samples_s'];raw=raw if isinstance(raw,list) else [raw[str(i)] for i in range(1,len(raw)+1)]
            assert all(type(v) in (float,int) and math.isfinite(v) and 0<v<1 for v in raw)
            values=raw[1:];assert len(values)>1000 and abs(math.fsum(values)-60)<.5 and abs(row['wall_interval_s']-60)<.5
            metrics=dict(frames=len(values),median_ms=statistics.median(values)*1000,p95_ms=percentile(values,.95)*1000,p99_ms=percentile(values,.99)*1000,over_100ms=sum(v>.1 for v in values))
            for k in ['median_ms','p95_ms','p99_ms','over_100ms']:assert metrics[k]<=limits[k],(row['kind'],k,metrics[k])
            assert not row['producer_errors']
            commands=row['commands'];active=row['kind'] in ['probe-maximum','visibility-maximum']
            assert len(recipe)==(120 if active else 0) and len(commands)==len(recipe)
            if active:
                rate=sum(c['finished_offset_s']<=60 for c in commands)/120
                times=[c['elapsed_s'] for c in commands]
                assert rate>=limits['command_rate_min'] and percentile(times,.95)<=limits['command_p95_s'] and max(times)<=limits['command_max_s'],(row['kind'],rate,max(times),percentile(times,.95))
                metrics.update(command_completion_ratio=rate,command_p95_s=percentile(times,.95),command_max_s=max(times))
                for c,item in zip(commands,recipe):
                    assert c['tick']==item['tick'] and c['artifact_sha256']==digest and c['view']==item['view']
                    assert c['sample']==item['sample']==run.sample(item['view'])
                    assert abs(c['started_offset_s']-item['offset_s'])<.5
                    exact_samples+=1
            assert len(row['samples'])==4
            for index,s in enumerate(row['samples']):
                assert abs(s['offset_s']-20*index)<.5
                assert phase(s['source'])==r['source_phase'] and s['source']['paused']
                for snapshot in [s['spatial'],s['following_spatial']]:
                    assert snapshot['active'] and not snapshot['busy'] and not snapshot['error']
                    assert snapshot['artifact']['id']==run.id and snapshot['artifact']['sha256']==digest
                    assert snapshot['artifact']['sample']==run.sample(snapshot['artifact']['view'])
                    exact_samples+=1
                assert s['spatial']['guard']==s['following_spatial']['guard']
                assert s['native']['draw'] is s['spatial']['artifact']['view']['visible']
                ram=s['ram'];assert ram['sum_working_set_bytes']==sum(p['working_set_bytes'] for p in ram['processes'])
                assert ram['sum_working_set_bytes']<=limits['RAM_bytes'];ram_peak=max(ram_peak,ram['sum_working_set_bytes'])
            initial,final=row['initial'],row['final']
            assert initial['artifact']['sha256']==final['artifact']['sha256']==digest
            if active:assert final['artifact']['view']==recipe[-1]['view']
            else:assert initial['artifact']==final['artifact']
            gpu_path=ROOT/row['gpu_report'];assert sha(gpu_path)==row['gpu_sha256']
            gpu=json.loads(gpu_path.read_text(encoding='utf-8-sig'))
            assert gpu['schema']==3 and gpu['valid'] and gpu['failure'] is None and gpu['expected_mode']=='experiment' and gpu['expected_worker']=='paused' and not gpu['counter_errors']
            assert gpu['session']['app']==r['session']['app'] and gpu['engine_sha256']==r['engine_sha256'] and len(gpu['samples'])==66
            selected=set(gpu['configured_counter_paths'])
            assert selected==set(gpu['counter_paths_after']) and len(selected)==len(gpu['configured_counter_paths'])
            owned=set(gpu['owned_processes']);exposed=set()
            for path in selected:
                match=re.fullmatch(r'\\gpu process memory\(pid_(\d+)_[^)]+\)\\(dedicated usage|shared usage)',path)
                if match:
                    assert int(match[1]) in owned;exposed.add(int(match[1]))
                else:assert re.fullmatch(r'\\gpu adapter memory\([^)]+\)\\dedicated usage',path),path
            assert exposed==set(gpu['owned_gpu_processes']) and owned-exposed==set(gpu['owned_without_exposed_gpu_counter'])
            for inventory in [gpu['inventory_before'],gpu['inventory_after']]:
                assert owned <= {p['ProcessId'] for p in inventory}
            stamps=[dt.datetime.fromisoformat(s['utc'].replace('Z','+00:00')) for s in gpu['samples']]
            assert stamps[0]<=dt.datetime.fromisoformat(row['capture_start_utc']) and stamps[-1]>=dt.datetime.fromisoformat(row['capture_end_utc'])
            peak=0
            for s in gpu['samples']:
                raw=s['raw_counter_samples'];by_path={v['path']:v for v in raw}
                assert set(by_path)==selected and len(raw)==len(selected)
                assert all(v['status']==0 and type(v['cooked_value']) in [int,float] and math.isfinite(v['cooked_value']) and v['cooked_value']>=0 for v in raw)
                product_keys=set()
                for p in s['product']:
                    key='\\gpu process memory('+p['instance'].lower()+')\\'+p['counter']
                    assert p['pid'] in owned and key in by_path and by_path[key]['cooked_value']==p['bytes']
                    product_keys.add(key)
                assert product_keys=={key for key in selected if key.startswith('\\gpu process memory(')}
                assert {p['pid'] for p in s['product']}==exposed
                adapter_keys=set()
                for adapter in s['adapters_all_applications']:
                    key='\\gpu adapter memory('+adapter['instance'].lower()+')\\dedicated usage'
                    assert key in by_path and by_path[key]['cooked_value']==adapter['bytes'];adapter_keys.add(key)
                assert adapter_keys=={key for key in selected if key.startswith('\\gpu adapter memory(')}
                assert not s['invalid_samples'] and s['scenario']['mode']=='experiment' and s['scenario']['paused'] and s['scenario']['renderer_confirmed']
                assert s['scenario']['physical_time']==0 and s['scenario']['revision']==0
                assert all(p['counter'] in ['dedicated usage','shared usage'] and p['bytes']>=0 for p in s['product'])
                dedicated=sum(p['bytes'] for p in s['product'] if p['counter']=='dedicated usage')
                total=sum(p['bytes'] for p in s['product'])
                assert dedicated==s['product_dedicated_sum_bytes'] and total<=limits['GPU_bytes']
                assert any(p['pid']==r['session']['app'] and p['counter']=='dedicated usage' for p in s['product'])
                peak=max(peak,total);gpu_peak=max(gpu_peak,total)
            for sample in row['samples']:
                assert {p['pid'] for p in sample['ram']['processes']}==set(gpu['owned_processes'])
            result['runs'].append(dict(run=row['run'],kind=row['kind'],**metrics,frame_interval_s=math.fsum(values),GPU_peak_GiB=peak/2**30))
        assert sha(ROOT/'user/sessions/latest.json')==r['owner_sha256'] and exact_samples==272
        result.update(accepted=True,exact_samples=exact_samples,RAM_peak_GiB=ram_peak/2**30,GPU_peak_GiB=gpu_peak/2**30,
                      scope='Four spatial mesh/probe/visibility windows only; no dynamical GR integration, simultaneous force layers, arbitrary workload or promotion acceptance.')
    except Exception:result['failure']=traceback.format_exc()
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=False),flush=True)
    return 0 if result['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
