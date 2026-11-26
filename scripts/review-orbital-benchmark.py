"""Audit persisted formal frame/GPU evidence without rerunning native routes."""
from pathlib import Path
from datetime import datetime
import argparse
import hashlib
import json
import math
import statistics
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('label',nargs='?',default='g0bulk')
parser.add_argument('--source-archive',type=Path)
parser.add_argument('--engine-file',type=Path)
args=parser.parse_args();label=args.label
if not all(c.isalnum() or c in '_-' for c in label):raise ValueError('Invalid benchmark label')
archive=tarfile.open(args.source_archive,'r:gz') if args.source_archive else None
def source_bytes(path):
    if archive is None:return (ROOT/path).read_bytes()
    stream=archive.extractfile(path)
    if stream is None:raise ValueError('Source archive is missing '+path)
    return stream.read()
source = ROOT/f'evidence/native-benchmark-{label}.json'
r = json.loads(source.read_text())
assert r['completed'] and r['warmup_s']==30 and r['route_duration_s']==60
p128=r.get('profile','').startswith('C2-06 P128')
fields=r.get('profile','').startswith('C2-11 fields')
history=r.get('profile','').startswith('C2-11 orbital')
massive_profile=p128 or fields or history
assert len(r['runs'])==(3 if massive_profile else 9)
expected = {(name,run) for name in (('history128',) if history else ('fields128',) if fields else ('p128',) if p128 else ('atlas','atlas_p32','p32')) for run in (1,2,3)}
assert {(x['scenario'],x['run']) for x in r['runs']}==expected
configuration_hashes={p.replace('\\','/'):digest for p,digest in r['configuration_sha256'].items()}
for path,digest in configuration_hashes.items():
    assert hashlib.sha256(source_bytes(path)).hexdigest()==digest, path
engine = r['runtime_receipt']['built_files']['OpenSpace.exe']
engine_file=args.engine_file or ROOT/'.runtime-built/bin/OpenSpace.exe'
assert hashlib.sha256(engine_file.read_bytes()).hexdigest()==engine
ram, gpu, budgets, summaries = [], [], [], []
def percentile(values,q):
    ordered=sorted(values);index=(len(ordered)-1)*q;lo=math.floor(index);hi=math.ceil(index)
    return ordered[lo]+(ordered[hi]-ordered[lo])*(index-lo)
def check_physics(p):
    assert len(p['bodies'])==128 and all(b['mass']>0 for b in p['bodies']) and not p['paused']
    assert p['population_contract']['active_mass_count']==128 and p['population_contract']['all_active_masses_gravitate']
    assert p['requested_rate']==1 and p['energy_error']<1e-8
    assert p['conservation']['momentum_error_normalized']<1e-8 and p['conservation']['angular_momentum_error_normalized']<1e-8
    for path,digest in p['scientific_generation']['code_sha256'].items():assert configuration_hashes[path]==digest,path
    for path,digest in p['scientific_generation']['data_sha256'].items():assert hashlib.sha256(source_bytes(path)).hexdigest()==digest,path
for run in r['runs']:
    assert run['capture']['width']==1920 and run['capture']['height']==1080
    assert not run['capture']['capacity_reached'] and run['capture']['invalid_samples']==0
    values = run['frame_times_s']
    assert all(0<x<1 for x in values)
    assert abs(sum(values)-60)<.5 and abs(run['wall_interval_s']-60)<.5
    s=run['statistics']
    assert s['frames']==len(values) and s['median_fps']>=30
    assert s['p95_ms']<=25 and s['p99_ms']<=50 and s['over_100ms']==0
    if massive_profile:
        assert s['median_ms']<=16.7 and math.isclose(s['median_ms'],statistics.median(values)*1000,abs_tol=1e-10)
        for field,q in [('p95_ms',.95),('p99_ms',.99)]:assert math.isclose(s[field],percentile(values,q)*1000,abs_tol=1e-10)
        assert s['over_100ms']==sum(v>.1 for v in values)
        for part in run['route_parts']:
            segment=values[part['first_frame']:part['end_frame']]
            assert segment and part['median_ms']<=16.7 and part['p95_ms']<=25 and part['p99_ms']<=50 and part['over_100ms']==0
            assert math.isclose(part['median_ms'],statistics.median(segment)*1000,abs_tol=1e-10)
        p=run['physics'];check_physics(p['initial']);check_physics(p['final'])
        rate=(p['final']['time']-p['initial']['time'])/run['wall_interval_s']
        assert rate>=.9 and math.isclose(rate,p['measured_model_units_per_wall_s'],abs_tol=1e-12)
    product=run['product_gpu'];assert product['samples']==66 and product['covers_frame_window']
    path=ROOT/product['report'].replace('\\','/')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==product['sha256']
    g=json.loads(path.read_text(encoding='utf-8-sig'))
    assert not g.get('counter_errors',[]), 'GPU query reported invalid counter data'
    assert g['engine_sha256']==engine
    assert g['collector_sha256']==configuration_hashes['scripts/collect-gpu-memory.ps1']
    assert len(g['samples'])==66 and g['session']['app']==r['session']['app']
    start,end=map(datetime.fromisoformat,(run['capture_start_utc'],run['capture_end_utc']))
    assert datetime.fromisoformat(g['samples'][0]['utc'].replace('Z','+00:00'))<=start
    assert datetime.fromisoformat(g['samples'][-1]['utc'].replace('Z','+00:00'))>=end
    mode='atlas' if run['scenario']=='atlas' else 'experiment'
    assert all(not sample['invalid_samples'] and sample['scenario']['mode']==mode for sample in g['samples'])
    if mode=='experiment':assert all(not sample['scenario']['paused'] for sample in g['samples'])
    peak=max(sample['product_dedicated_sum_bytes'] for sample in g['samples'])
    assert peak==product['product_dedicated_sum_max_bytes'] and peak<=5.5*2**30
    for item in run['memory']:
        if massive_profile:check_physics(item['physics'])
        log=item['engine_gpu'].get('script_log')
        if log is not None:
            assert log['initialized'] and not log['failed'] and log['dropped']==0
            assert 0<=log['queued_bytes']<=8*1024*1024 and 0<=log['written']<=log['accepted']
        resident=item['ram']['sum_working_set_bytes'];assert resident<=8*2**30
        ram.append(resident)
        adapters=list(item['engine_gpu']['adapters'].values())
        physical=[a for a in adapters if a['vendor_id']==4098 and a['status']=='ok']
        assert physical and all(peak<a['budget_bytes'] for a in physical)
        budgets.extend(a['budget_bytes'] for a in physical)
    gpu.append(peak)
    summaries.append({'scenario':run['scenario'],'run':run['run'],**s,'product_gpu_sum_GiB':peak/2**30})
report={'benchmark':str(source.relative_to(ROOT)), 'benchmark_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'engine_sha256':engine,('three_history128_routes_verified' if history else 'three_field128_routes_verified' if fields else 'three_P128_routes_verified' if p128 else 'nine_routes_verified'):True,'gpu_windows_covered':True,
        'median_fps_min':min(x['median_fps'] for x in summaries),
        'p95_ms_max':max(x['p95_ms'] for x in summaries),'p99_ms_max':max(x['p99_ms'] for x in summaries),
        'over_100ms_total':sum(x['over_100ms'] for x in summaries),
        'resident_sum_max_GiB':max(ram)/2**30,'product_gpu_dedicated_sum_max_GiB':max(gpu)/2**30,
        'engine_dxgi_budget_min_GiB':min(budgets)/2**30,
        'memory_method':'WDDM per-process dedicated sums, including cross-process shared allocations; conservative product tally, not unique VRAM. DXGI budget belongs to engine process. Resident sums may repeat shared pages. Other apps excluded from product, adapter totals not used.',
        'counter_limit':'Windows10 KB4490156 acknowledged; no false-growth defect established on this Windows11 run. This audit does not independently validate WDDM hardware accounting.',
        'scope':'Formal small-profile routes on this machine/build; startup, offline and visual review have separate receipts.',
        'runs':summaries}
if archive:
    archive.close()
    report['frozen_source_archive']={'path':str(args.source_archive),'sha256':hashlib.sha256(args.source_archive.read_bytes()).hexdigest()}
    report['source_scope']='Historical frozen source; this audit does not assert that the current workspace matches it.'
if massive_profile:
    assert r['all128_active_confirmed'] and len(r['pause_latency_samples'])==20
    assert all(0<s['wall_ms']<=250 and 0<=s['worker_elapsed_ms']<=s['wall_ms'] for s in r['pause_latency_samples'])
    report.update(profile='C2-11 live history with128 active masses; separate from historical C2-06/G0' if history else 'C2-11 fields with128 active masses; separate from historical C2-06/G0' if fields else 'C2-06 P128; separate from historical G0',
        requested_model_units_per_wall_s=1,
        measured_rate_min=min(x['physics']['measured_model_units_per_wall_s'] for x in r['runs']),
        pause_API_wall_max_ms=max(x['wall_ms'] for x in r['pause_latency_samples']),
        camera_API_wall_max_ms=max(r['camera_command_latency_ms']),
        energy_relative_error_max=max(x['physics']['final']['energy_error'] for x in r['runs']),
        momentum_normalized_error_max=max(x['physics']['final']['conservation']['momentum_error_normalized'] for x in r['runs']),
        angular_momentum_normalized_error_max=max(x['physics']['final']['conservation']['angular_momentum_error_normalized'] for x in r['runs']),
        scientific_generation=r['fixture_initial_state']['scientific_generation'])
if history:
    for run in r['runs']:
        for p in (run['physics']['initial'],run['physics']['final']):
            c=p['orbital_instruments'];assert c['recording'] and c['cadence_wall_s']==.25 and c['sample_count']<=128
            assert c['definition']['j']==2 and c['latest']['available']
        a,b=run['physics']['initial']['orbital_instruments'],run['physics']['final']['orbital_instruments']
        assert b['sample_count']==128 and b['next_sequence']>a['next_sequence'] and b['next_sequence']==b['dropped']+128
    report['orbital_capture']={'maximum_records':128,'cadence_wall_s':.25,'live_graph':'native visible finite wrapped angles','scope':'No automatic resonance classification or256/10k acceptance'}
    for run in r['runs']:
        initial,final=run['physics']['initial'],run['physics']['final']
        for p in (initial,final):
            assert len(p['instruments']['probes'])==16 and p['instrument_history']['recording']
            assert p['instrument_history']['cadence_wall_s']==.25 and p['instrument_history']['sample_count']<=128
        assert final['instrument_history']['sample_count']==128 and final['instrument_history']['next_sequence']>initial['instrument_history']['next_sequence']
        assert final['instrument_history']['next_sequence']==final['instrument_history']['dropped']+128
    report.update(history_maximum_records=128,recorded_probe_count=16,history_wall_cadence_s=.25,
        history_policy='Live confirmed readings,2-probe CEF graph and16 frozen native marks; no256/10k acceptance')
if fields:
    assert r['field_map']['sample_count']==569 and len(r['field_map']['source_ids'])==128
    assert r['field_map']['shell']['sample_count']==128 and r['field_map']['cut']['sample_count']==441
    assert len(r['field_resampling_latency_ms'])==5 and all(0<x['evaluation_ms']<=x['worker_elapsed_ms']<=x['wall_ms']<2000 for x in r['field_resampling_latency_ms'])
    report.update(field_sample_count=569,field_resampling_wall_max_ms=max(x['wall_ms'] for x in r['field_resampling_latency_ms']),
        field_evaluation_max_ms=max(x['evaluation_ms'] for x in r['field_resampling_latency_ms']),
        field_policy='Frozen confirmed overlay with live128-mass evolution; resampling timed separately; no256/10k acceptance')
(ROOT/f'evidence/native-benchmark-{label}-review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='runs'},indent=2))
