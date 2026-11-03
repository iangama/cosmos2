"""Recompute solar playback frame, rate, source, process and GPU profile metrics."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import math
import statistics
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def percentile(values, q):
    a=sorted(values);i=(len(a)-1)*q;lo,hi=math.floor(i),math.ceil(i)
    return a[lo]+(a[hi]-a[lo])*(i-lo)


def phase(p):
    return {k:p[k] for k in ('system_id','edit_token','revision','time','bodies','interventions','atlas_initial')}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);parser.add_argument('--audit-label')
    args=parser.parse_args();label=args.audit_label or args.label
    for value in (args.label,label):
        if not value or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in value):
            parser.error('Invalid label')
    source=ROOT/('evidence/is5-zone-profile-'+args.label+'.json')
    out=ROOT/('evidence/is5-zone-profile-audit-'+label+'.json')
    if out.exists():
        raise FileExistsError('Preserve audit')
    r=json.loads(source.read_text())
    result=dict(accepted=False,profile=source.relative_to(ROOT).as_posix(),profile_sha256=sha(source),
                auditor_sha256=sha(Path(__file__)),runs=[])
    try:
        assert r['completed'] and not r.get('failure') and not r.get('cleanup_failure')
        assert r['warmup_s']==30 and r['window_s']==60 and r['requested_knots_per_s']==2
        assert [(x['weak'],x['charts_visible']) for x in r['runs']]==[(True,True),(True,False),(False,True),(False,False)]
        archive=ROOT/('output/is5-zone-profile-'+args.label+'/executed-sources.zip')
        assert sha(archive)==r['archive_sha256']
        with zipfile.ZipFile(archive) as z:
            assert set(z.namelist())==set(r['source_sha256'])
            assert all(hashlib.sha256(z.read(n)).hexdigest()==v for n,v in r['source_sha256'].items())
        assert all(sha(ROOT/n)==v for n,v in r['source_sha256'].items())
        runtime=Path(r['session']['runtime'].replace('\\','/')).name
        assert runtime=='.runtime-is4-stream' and sha(ROOT/runtime/'bin/OpenSpace.exe')==r['engine_sha256']
        limits=r['limits_before_execution']
        assert limits==dict(median_ms=16.7,p95_ms=25.,p99_ms=50.,over_100ms=0,measured_rate_min=.9,RAM_bytes=8*2**30,GPU_bytes=5.5*2**30)
        original=phase(r['runs'][0]['samples'][0]['source'])
        ram_peak=gpu_peak=0
        for row in r['runs']:
            capture=row['capture']
            assert capture['width']==1920 and capture['height']==1080
            assert not capture['capacity_reached'] and capture['invalid_samples']==0
            raw=capture['samples_s']
            raw=raw if isinstance(raw,list) else [raw[str(i)] for i in range(1,len(raw)+1)]
            assert all(type(v) in (int,float) and math.isfinite(v) and 0<v<1 for v in raw)
            values=raw[1:]
            assert len(values)>1000 and abs(math.fsum(values)-60)<.5 and abs(row['wall_interval_s']-60)<.5
            metrics=dict(frames=len(values),median_ms=statistics.median(values)*1000,p95_ms=percentile(values,.95)*1000,
                         p99_ms=percentile(values,.99)*1000,over_100ms=sum(v>.1 for v in values))
            for key in ('median_ms','p95_ms','p99_ms','over_100ms'):
                assert metrics[key]<=limits[key],(row['run'],key,metrics[key])
            first,last=row['initial']['worker'],row['final']['worker']
            rate=(last['view']['selected_index']-first['view']['selected_index'])/row['wall_interval_s']/2
            assert .9<=rate<=1.05,rate
            assert len(row['samples'])==4 and all(abs(s['offset_s']-20*i)<.5 for i,s in enumerate(row['samples']))
            for state in [row['initial'],row['final'],*[s['zone'] for s in row['samples']]]:
                w=state['worker']
                assert state['active'] and state['playing'] and not state['busy'] and not state['error']
                assert state['samples_per_wall_s']==2
                assert all(w[k]==first[k] for k in ('worker_id','artifact_id','artifact_sha256','edit_token','revision','source','configuration'))
                assert w['configuration']['acting']==dict(strong=True,weak=row['weak'],electromagnetic=True)
                assert all(w['configuration']['channel_switches'].values()) and w['configuration']['decay_basis']=='nubase2020'
                assert w['configuration']['parameters']==dict(temperature_K=15e6,density_kg_m3=1.5e5,hydrogen_fraction=.34,
                    catalyst_fraction=.01,catalyst_seed='n14',duration_s=31557600000000.,volume_m3=1.)
                assert w['view']['visible']=={k:row['charts_visible'] for k in ('composition','energy','neutrinos','reference')}
                i=w['view']['selected_index'];assert 0<i<240 and w['sample']['index']==i
                assert math.isclose(w['sample']['actual']['time_s'],w['configuration']['parameters']['duration_s']*i/240,rel_tol=2e-15)
                if not row['weak']:
                    assert w['sample']['actual']['neutrino_count_m3']==0
                scene=state['scene'];assert scene['confirmed'] and scene['source_binding_sha256']==w['source']['binding_sha256']
                assert scene['center_render_m']==w['source']['center_render_m'] and 'arquivado' in scene['label']
            gpu_path=ROOT/row['gpu_report'];assert sha(gpu_path)==row['gpu_sha256']
            gpu=json.loads(gpu_path.read_text(encoding='utf-8-sig'))
            assert gpu['engine_sha256']==r['engine_sha256'] and gpu['session']['app']==r['session']['app'] and not gpu['counter_errors']
            assert gpu['collector_sha256']==r['source_sha256']['scripts/collect-gpu-memory-diagnostic.ps1']
            assert gpu['expected_mode']=='experiment' and gpu['expected_worker']=='paused' and len(gpu['samples'])==66
            stamps=[dt.datetime.fromisoformat(s['utc'].replace('Z','+00:00')) for s in gpu['samples']]
            assert stamps[0]<=dt.datetime.fromisoformat(row['capture_start_utc']) and stamps[-1]>=dt.datetime.fromisoformat(row['capture_end_utc'])
            assert all(b>a for a,b in zip(stamps,stamps[1:]))
            peak=0
            for s in gpu['samples']:
                assert not s['invalid_samples'] and s['scenario']['mode']=='experiment' and s['scenario']['paused']
                assert s['scenario']['physical_time']==0 and s['scenario']['revision']==0 and s['scenario']['renderer_confirmed']
                total=sum(p['bytes'] for p in s['product'] if p['counter']=='dedicated usage')
                assert total==s['product_dedicated_sum_bytes'] and total<=limits['GPU_bytes']
                assert any(p['pid']==r['session']['app'] and p['counter']=='dedicated usage' for p in s['product'])
                peak=max(peak,total);gpu_peak=max(gpu_peak,total)
            for sample in row['samples']:
                p=sample['source'];assert p['paused'] and phase(p)==original
                scene=sample['zone']['scene'];n=sample['native_source']
                assert n==dict(marker=True,label=True,text=scene['label'],position=scene['center_render_m'])
                memory=sample['ram']
                assert sum(p['working_set_bytes'] for p in memory['processes'])==memory['sum_working_set_bytes']
                assert {p['pid'] for p in memory['processes']}==set(gpu['owned_processes'])
                assert memory['sum_working_set_bytes']<=limits['RAM_bytes']
                ram_peak=max(ram_peak,memory['sum_working_set_bytes'])
                adapters=[a for a in sample['engine_gpu']['adapters'].values() if a['vendor_id']==4098 and a['status']=='ok']
                assert adapters and all(peak<a['budget_bytes'] for a in adapters)
            result['runs'].append(dict(run=row['run'],weak=row['weak'],charts_visible=row['charts_visible'],
                **metrics,measured_knots_rate_ratio=rate,frame_interval_s=math.fsum(values),GPU_peak_GiB=peak/2**30))
        assert sha(ROOT/'user/sessions/latest.json')==r['owner_sha256']
        result.update(accepted=True,RAM_peak_GiB=ram_peak/2**30,GPU_peak_GiB=gpu_peak/2**30,
            scope='Four native solar-instrument playback windows only; no integration throughput, thermal evolution, spatial emission or full IS5 acceptance.')
    except Exception:
        result['failure']=traceback.format_exc()
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False),flush=True)
    return 0 if result['accepted'] else 1


if __name__=='__main__':
    raise SystemExit(main())
