"""Preserve failed gates, exact frame offsets and DXGI context without a rerun."""
from pathlib import Path
from datetime import datetime, timedelta
import argparse
import hashlib
import json
import math
import re

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('label')
args = parser.parse_args()
if not re.fullmatch(r'[a-z0-9_-]{1,18}', args.label):
    raise ValueError('Invalid evidence label')
path = ROOT / f'evidence/native-benchmark-{args.label}.json'
destination = ROOT / f'evidence/native-benchmark-{args.label}-failure.json'
if destination.exists():
    raise RuntimeError('Preserve existing failure evidence')
r = json.loads(path.read_text())
results = []
for run in r['runs']:
    elapsed, slow = 0., []
    start = datetime.fromisoformat(run['capture_start_utc'])
    for value in run['frame_times_s']:
        if value > .1:
            slow.append({'offset_s': elapsed, 'duration_ms': value * 1000,
                         'utc': (start + timedelta(seconds=elapsed)).isoformat()})
        elapsed += value
    statistics = run['statistics']
    violations = []
    for key, limit in [('p95_ms', 25), ('p99_ms', 50), ('over_100ms', 0)]:
        if statistics[key] > limit:
            violations.append({'field': key, 'measured': statistics[key], 'maximum': limit})
    if statistics['median_fps'] < 30:
        violations.append({'field': 'median_fps', 'measured': statistics['median_fps'], 'minimum': 30})
    budgets, log = [], []
    for memory in run['memory']:
        metrics = memory['engine_gpu']
        for adapter in metrics['adapters'].values():
            if adapter['vendor_id'] == 4098 and adapter['status'] == 'ok':
                budgets.append({'offset_s': memory['offset_s'], 'budget_bytes': adapter['budget_bytes'],
                                'engine_local_usage_bytes': adapter['process_local_usage_bytes']})
        log.append({'offset_s': memory['offset_s'], **metrics.get('script_log', {})})
    results.append({'scenario': run['scenario'], 'run': run['run'], 'statistics': statistics,
                    'violations': violations, 'over100ms': slow, 'DXGI_context': budgets,
                    'script_log': log, 'product_gpu': run['product_gpu']})
assert any(row['violations'] for row in results), 'No frame gate failure to summarize'
report = {'benchmark': str(path.relative_to(ROOT)),
          'benchmark_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
          'engine_sha256': r['runtime_receipt']['built_files']['OpenSpace.exe'],
          'capture_completed': bool(r.get('completed')), 'runs': results,
          'over100ms_total': sum(len(row['over100ms']) for row in results),
          'minimum_DXGI_budget_GiB': min(v['budget_bytes'] for row in results for v in row['DXGI_context']) / 2**30,
          'scope': 'Failure/context record, not an acceptance. DXGI budget changes can accompany competing allocations; they do not by themselves prove which application or stage caused a frame hitch.'}
destination.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'runs'}, indent=2))
