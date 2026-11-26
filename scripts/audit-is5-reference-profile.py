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
    source=ROOT/('evidence/is5-reference-profile-'+args.label+'.json')
    out=ROOT/('evidence/is5-reference-profile-audit-'+label+'.json')
    if out.exists():
        raise FileExistsError('Preserve audit')
    r=json.loads(source.read_text())
    result=dict(accepted=False,profile=source.relative_to(ROOT).as_posix(),profile_sha256=sha(source),
                auditor_sha256=sha(Path(__file__)),runs=[])
    try:
        assert r['completed'] and not r.get('failure') and not r.get('cleanup_failure')
        assert not r.get('page_errors')
        assert r['warmup_s']==30 and r['window_s']==60 and r['requested_radial_queries_per_s']==2
        assert [(x['zone_active'],x['reference_open']) for x in r['runs']]==[(False,True),(False,False),(True,True),(True,False)]
        archive=ROOT/('output/is5-reference-profile-'+args.label+'/executed-sources.zip')
        assert sha(archive)==r['archive_sha256']
        with zipfile.ZipFile(archive) as z:
            assert set(z.namelist())==set(r['source_sha256'])
            assert all(hashlib.sha256(z.read(n)).hexdigest()==v for n,v in r['source_sha256'].items())
        assert all(sha(ROOT/n)==v for n,v in r['source_sha256'].items())
        runtime=Path(r['session']['runtime'].replace('\\','/')).name
        assert runtime=='.runtime-is4-stream' and sha(ROOT/runtime/'bin/OpenSpace.exe')==r['engine_sha256']
        assert r['session'].get('is5ReferenceCandidate') is True
        assert r['session']['serverScript'].replace('\\','/').endswith('/output/is5-reference-product0.16.0/app/server.py')
        limits=r['limits_before_execution']
        assert limits==dict(median_ms=16.7,p95_ms=25.,p99_ms=50.,over_100ms=0,measured_rate_min=.9,RAM_bytes=8*2**30,GPU_bytes=5.5*2**30)
        original=phase(r['runs'][0]['samples'][0]['source'])
        ram_peak=gpu_peak=0
        states_checked=0
        data=json.loads((ROOT/'output/is5-reference-product0.16.0/app/references/GS98.json').read_text())
        by_index={x['index']:x for x in json.loads((ROOT/'output/is5-reference-product0.16.0/app/references/GS98-ideal-EOS-Age1.json').read_text())}
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
            first,last=row['initial'],row['final']
            states=[first,last,*[dict(zone=x['zone'],reference=x['reference']) for x in row['samples']]]
            assert len(row['samples'])==4 and all(abs(x['offset_s']-20*i)<.5 for i,x in enumerate(row['samples']))
            baseline=first['zone']['worker']
            for state in states:
                ui,z=state['reference'],state['zone']
                assert ui['open']==row['reference_open'] and ui['scale']=='1'
                assert 0<=ui['applied']<=ui['completed']<=ui['requested'] and ui['errors']==0
                sample=ui['sample'];i=sample['index']
                assert sample['model']=='GS98' and type(i) is int and 0<=i<=2000
                assert sample['structure']==data['derived'][i] and sample['quality_flags']==data['flags'][i]
                assert sample['r_over_Rsun']==data['raw_values'][i][0] and sample['interpolation'] is False
                assert sample['abundances']==dict(zip(data['columns'][18:],data['raw_values'][i][18:]))
                assert sample['ideal_comparison']==by_index.get(i)
                assert sample['provenance']['doi']=='10.5281/zenodo.10822316' and sample['provenance']['version']=='B23v1.2'
                assert z['active']==row['zone_active'] and not z['playing'] and not z['busy'] and not z['error']
                if row['zone_active']:
                    w=z['worker']
                    assert all(w[k]==baseline[k] for k in ['worker_id','artifact_id','artifact_sha256','edit_token','revision','source','configuration','view'])
                    c=w['configuration']
                    assert c['mode']=='isochoric' and c['include_coulomb'] is True and c['include_screening'] is True
                    assert c['parameters']==dict(temperature_K=15e6,density_kg_m3=1.5e5,hydrogen_fraction=.34,catalyst_fraction=.01,catalyst_seed='n14',duration_s=315576000000.,volume_m3=1.)
                    assert c['acting']==dict(strong=True,weak=True,electromagnetic=True) and all(c['channel_switches'].values())
                    assert w['view']['selected_index']==0 and w['sample']['actual']['Coulomb_internal_energy_J_m3']<0
                    assert z['scene']['confirmed'] and z['scene']['source_binding_sha256']==w['source']['binding_sha256']
                else:assert z['worker'] is None and z['scene'] is None
                states_checked+=1
            changes={field:last['reference'][field]-first['reference'][field] for field in ['requested','completed','applied']}
            if row['reference_open']:
                ratios={field:count/row['wall_interval_s']/2 for field,count in changes.items()}
                assert all(.9<=value<=1.05 for value in ratios.values()),ratios
            else:
                assert set(changes.values())=={0},changes
                ratios=None
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
                memory=sample['ram']
                assert sum(p['working_set_bytes'] for p in memory['processes'])==memory['sum_working_set_bytes']
                assert {p['pid'] for p in memory['processes']}==set(gpu['owned_processes'])
                assert memory['sum_working_set_bytes']<=limits['RAM_bytes']
                ram_peak=max(ram_peak,memory['sum_working_set_bytes'])
                adapters=[a for a in sample['engine_gpu']['adapters'].values() if a['vendor_id']==4098 and a['status']=='ok']
                assert adapters and all(peak<a['budget_bytes'] for a in adapters)
            result['runs'].append(dict(run=row['run'],zone_active=row['zone_active'],reference_open=row['reference_open'],
                **metrics,radial_query_rate_ratios=ratios,frame_interval_s=math.fsum(values),GPU_peak_GiB=peak/2**30))
        assert sha(ROOT/'user/sessions/latest.json')==r['owner_sha256']
        assert states_checked==24,states_checked
        result.update(accepted=True,reference_states_checked=states_checked,RAM_peak_GiB=ram_peak/2**30,GPU_peak_GiB=gpu_peak/2**30,
            scope='Four read-only B23 radial-query windows with absent/paused Coulomb zone only; no stellar evolution or new EOS.')
    except Exception:
        result['failure']=traceback.format_exc()
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False),flush=True)
    return 0 if result['accepted'] else 1


if __name__=='__main__':
    raise SystemExit(main())
