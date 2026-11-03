"""Independent recalculation of particle/native/GPU profile evidence."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import math
import statistics
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def percentile(values,q):
    a=sorted(values);i=(len(a)-1)*q;lo,hi=math.floor(i),math.ceil(i)
    return a[lo]+(a[hi]-a[lo])*(i-lo)

def source_phase(s):
    return {k:s[k] for k in ['system_id','edit_token','revision','time','bodies','interventions','atlas_initial']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--audit-label');args=p.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):p.error('Invalid label')
    audit_label=args.audit_label or args.label
    if any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in audit_label):p.error('Invalid audit label')
    source=ROOT/('evidence/is4-wind-profile-'+args.label+'.json');out=ROOT/('evidence/is4-wind-profile-audit-'+audit_label+'.json')
    if out.exists():raise FileExistsError('Preserve audit')
    r=json.loads(source.read_text(encoding='utf-8'));result=dict(schema=1,accepted=False,profile=source.relative_to(ROOT).as_posix(),profile_sha256=sha(source),auditor_sha256=sha(Path(__file__)),runs=[])
    try:
        assert r['completed'] and not r.get('failure') and not r.get('cleanup_failure')
        assert len(r['runs'])==4 and r['warmup_s']==30 and r['window_s']==60 and r['requested_steps_per_s']==200
        assert [(x['target'],x['visible']) for x in r['runs']]==[('proton-north',True),('proton-north',False),('electron-south',True),('electron-south',False)]
        archive=ROOT/('output/is4-wind-profile-'+args.label+'/executed-sources.zip');assert sha(archive)==r['archive_sha256']
        with zipfile.ZipFile(archive) as z:
            assert set(z.namelist())==set(r['source_sha256'])
            assert all(hashlib.sha256(z.read(n)).hexdigest()==v for n,v in r['source_sha256'].items())
        assert all(sha(ROOT/n)==v for n,v in r['source_sha256'].items())
        runtime_name=Path(r['session']['runtime'].replace('\\','/')).name
        assert runtime_name=='.runtime-is4-stream' and sha(ROOT/runtime_name/'bin/OpenSpace.exe')==r['engine_sha256']
        limits=r['limits_before_execution']
        assert limits==dict(median_ms=16.7,p95_ms=25.,p99_ms=50.,over_100ms=0,measured_rate_min=.9,RAM_bytes=8*2**30,GPU_bytes=5.5*2**30)
        original=source_phase(r['runs'][0]['samples'][0]['source']);bindings=set();ram_peak=gpu_peak=lag_peak=0
        for row in r['runs']:
            capture=row['capture'];assert capture['width']==1920 and capture['height']==1080 and not capture['capacity_reached'] and capture['invalid_samples']==0
            raw=capture['samples_s'];raw=raw if isinstance(raw,list) else [raw[str(i)] for i in range(1,len(raw)+1)]
            assert all(type(v) in (int,float) and math.isfinite(v) and 0<v<1 for v in raw)
            values=raw[1:];assert len(values)>1000 and abs(math.fsum(values)-60)<.5 and abs(row['wall_interval_s']-60)<.5
            metrics=dict(frames=len(values),median_ms=statistics.median(values)*1000,p95_ms=percentile(values,.95)*1000,p99_ms=percentile(values,.99)*1000,over_100ms=sum(v>.1 for v in values))
            for k in ['median_ms','p95_ms','p99_ms','over_100ms']:assert metrics[k]<=limits[k],(row['run'],k,metrics[k])
            first,last=row['initial']['worker'],row['final']['worker'];e=first['experiment'];delta=last['experiment']['step_index']-e['step_index'];rate=delta/row['wall_interval_s']/200
            assert rate>=limits['measured_rate_min'] and rate<=1.05
            assert e['degree'] is None and e['model']=='Parker prescrito, duas polaridades'
            assert e['parameters']['charge_C']>0 if row['target']=='proton-north' else e['parameters']['charge_C']<0
            assert len(row['samples'])==4 and all(abs(s['offset_s']-20*i)<.5 for i,s in enumerate(row['samples']))
            binding=row['initial']['view']['binding_sha256'];assert binding not in bindings;bindings.add(binding)
            for state in [row['initial'],row['final'],*[s['particle'] for s in row['samples']]]:
                w=state['worker'];x=w['experiment'];v=state['view'];assert state['active'] and not state['error'] and not w['paused'] and not w['notice'] and not x['termination']
                assert w['worker_id']==first['worker_id'] and x['id']==e['id'] and x['edit_token']==e['edit_token'] and x['revision']==0
                assert x['controls']==dict(electric=True,magnetic=True,gravity=True) and x['snapshot_configuration_sha256']==e['snapshot_configuration_sha256'] and x['snapshot_epoch']==e['snapshot_epoch']
                assert x['scene_time']==0 and x['clock']=='independent_particle_seconds; source epoch/orientation/centers frozen'
                assert math.isclose(w['requested_particle_s_per_wall_s'],200*x['parameters']['dt_s'],rel_tol=1e-14)
                assert v['visible']==row['visible'] and v['binding_sha256']==binding and v['source_epoch']==e['snapshot_epoch']
                confirmed=v['confirmed_phase'];lag=(x['phase']['time_s']-confirmed['time_s'])/w['requested_particle_s_per_wall_s']
                assert -1e-9<=lag<=2.;lag_peak=max(lag_peak,lag)
                metadata=v['confirmed_metadata'];assert metadata['time_s']==confirmed['time_s'] and 1<=metadata['count']<=129
                assert v['native']['state']=='accepted' and v['native']['gpu_buffer_uploaded'] and v['native']['metadata']==metadata
                assert v['native']['draw_submitted_sequence']<=metadata['sequence']
            gpu_path=ROOT/row['gpu_report'];assert sha(gpu_path)==row['gpu_sha256'];gpu=json.loads(gpu_path.read_text(encoding='utf-8-sig'))
            assert gpu['engine_sha256']==r['engine_sha256'] and gpu['session']['app']==r['session']['app'] and not gpu['counter_errors']
            assert gpu['collector_sha256']==r['source_sha256']['scripts/collect-gpu-memory-diagnostic.ps1']
            assert gpu['expected_worker']=='paused' and gpu['expected_mode']=='experiment' and len(gpu['samples'])==66
            stamps=[dt.datetime.fromisoformat(s['utc'].replace('Z','+00:00')) for s in gpu['samples']]
            assert stamps[0]<=dt.datetime.fromisoformat(row['capture_start_utc']) and stamps[-1]>=dt.datetime.fromisoformat(row['capture_end_utc'])
            assert all(b>a for a,b in zip(stamps,stamps[1:]))
            for s in gpu['samples']:
                assert not s['invalid_samples'] and s['scenario']['mode']=='experiment' and s['scenario']['paused'] and s['scenario']['physical_time']==0 and s['scenario']['revision']==0 and s['scenario']['renderer_confirmed']
                assert any(p['pid']==r['session']['app'] and p['counter']=='dedicated usage' for p in s['product'])
                total=sum(p['bytes'] for p in s['product'] if p['counter']=='dedicated usage')
                assert total==s['product_dedicated_sum_bytes'] and total<=limits['GPU_bytes'];gpu_peak=max(gpu_peak,total)
            peak=max(s['product_dedicated_sum_bytes'] for s in gpu['samples'])
            for sample in row['samples']:
                s=sample['source'];assert s['paused'] and source_phase(s)==original and [b['reference_id'] for b in s['bodies']]==['sol:naif:10','sol:naif:399','sol:naif:301','sol:naif:599']
                assert sample['native_visibility']==dict(draw=row['visible'],enabled=True)
                memory=sample['ram'];assert sum(p['working_set_bytes'] for p in memory['processes'])==memory['sum_working_set_bytes']
                assert {p['pid'] for p in memory['processes']}==set(gpu['owned_processes'])
                assert memory['sum_working_set_bytes']<=limits['RAM_bytes'];ram_peak=max(ram_peak,memory['sum_working_set_bytes'])
                physical=[a for a in sample['engine_gpu']['adapters'].values() if a['vendor_id']==4098 and a['status']=='ok']
                assert physical and all(peak<a['budget_bytes'] for a in physical)
            result['runs'].append(dict(run=row['run'],target=row['target'],visible=row['visible'],**metrics,measured_steps_rate_ratio=rate,frame_interval_s=math.fsum(values),GPU_peak_GiB=peak/2**30))
        assert sha(ROOT/'user/sessions/latest.json')==r['owner_sha256']
        result.update(accepted=True,RAM_peak_GiB=ram_peak/2**30,GPU_peak_GiB=gpu_peak/2**30,sampled_confirmation_lag_max_wall_s=lag_peak,scope='Four paired visible/hidden prescribed Parker single-particle windows only, 200steps/wall second. CEF real; source orbital paused. No arbitrary workload, plasma/MHD, live solar observations or full IS4 acceptance.')
    except Exception:result['failure']=traceback.format_exc()
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
    return 0 if result['accepted'] else 1

if __name__=='__main__':raise SystemExit(main())
