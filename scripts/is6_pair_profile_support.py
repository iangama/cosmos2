"""Fixed K2 thresholds and independent raw Windows GPU verification."""
import datetime as dt
import math
import re
import statistics

LIMITS = dict(median_ms=16.7, p95_ms=25., p99_ms=50., over_100ms=0,
              RAM_bytes=8*2**30, GPU_bytes=5.5*2**30,
              command_rate_min=.9, command_p95_s=.5, command_max_s=1.)
WINDOWS = [('399', 'static'), ('599', 'static'), ('399', 'visibility'), ('599', 'visibility')]
COMBINATIONS = [dict(spatial=s, magnetic=m) for s in [False, True] for m in [False, True]]


def percentile(values, q):
    values = sorted(values)
    i = (len(values)-1)*q
    a, b = math.floor(i), math.ceil(i)
    return values[a] + (values[b]-values[a])*(i-a)


def frame_statistics(capture, wall_s):
    assert capture['width'] == 1920 and capture['height'] == 1080
    assert not capture['capacity_reached'] and capture['invalid_samples'] == 0
    raw = capture['samples_s']
    raw = raw if isinstance(raw, list) else [raw[str(i)] for i in range(1, len(raw)+1)]
    assert all(type(v) in (float, int) and math.isfinite(v) and 0 < v < 1 for v in raw)
    values = raw[1:]
    assert len(values) > 1000 and abs(math.fsum(values)-60) < .5 and abs(wall_s-60) < .5
    result = dict(frames=len(values), median_ms=statistics.median(values)*1000,
                  p95_ms=percentile(values, .95)*1000, p99_ms=percentile(values, .99)*1000,
                  over_100ms=sum(v > .1 for v in values), interval_s=math.fsum(values))
    assert all(result[k] <= LIMITS[k] for k in ['median_ms', 'p95_ms', 'p99_ms', 'over_100ms']), result
    return result


def audit_gpu(gpu, session, engine_sha, row):
    assert gpu['schema'] == 3 and gpu['valid'] and gpu['failure'] is None and not gpu['counter_errors']
    assert gpu['expected_mode'] == 'experiment' and gpu['expected_worker'] == 'paused'
    assert gpu['session']['app'] == session['app'] and gpu['session']['server'] == session['server']
    assert gpu['engine_sha256'] == engine_sha and len(gpu['samples']) == 66
    selected = set(gpu['configured_counter_paths'])
    assert selected == set(gpu['counter_paths_after']) and len(selected) == len(gpu['configured_counter_paths'])
    owned, exposed = set(gpu['owned_processes']), set()
    for path in selected:
        match = re.fullmatch(r'\\gpu process memory\(pid_(\d+)_[^)]+\)\\(dedicated usage|shared usage)', path)
        if match:
            assert int(match[1]) in owned
            exposed.add(int(match[1]))
        else:
            assert re.fullmatch(r'\\gpu adapter memory\([^)]+\)\\dedicated usage', path), path
    assert exposed == set(gpu['owned_gpu_processes'])
    assert owned-exposed == set(gpu['owned_without_exposed_gpu_counter'])
    for inventory in [gpu['inventory_before'], gpu['inventory_after']]:
        assert owned <= {p['ProcessId'] for p in inventory}
    stamps = [dt.datetime.fromisoformat(s['utc'].replace('Z', '+00:00')) for s in gpu['samples']]
    assert stamps[0] <= dt.datetime.fromisoformat(row['capture_start_utc'])
    assert stamps[-1] >= dt.datetime.fromisoformat(row['capture_end_utc'])
    peak = 0
    for s in gpu['samples']:
        raw = s['raw_counter_samples']
        by_path = {v['path']: v for v in raw}
        assert set(by_path) == selected and len(raw) == len(selected)
        assert all(v['status'] == 0 and type(v['cooked_value']) in (int, float)
                   and math.isfinite(v['cooked_value']) and v['cooked_value'] >= 0 for v in raw)
        product_keys = set()
        for p in s['product']:
            key = '\\gpu process memory(' + p['instance'].lower() + ')\\' + p['counter']
            assert p['pid'] in owned and key in by_path and by_path[key]['cooked_value'] == p['bytes']
            product_keys.add(key)
        assert product_keys == {key for key in selected if key.startswith('\\gpu process memory(')}
        assert {p['pid'] for p in s['product']} == exposed
        adapter_keys = set()
        for adapter in s['adapters_all_applications']:
            key = '\\gpu adapter memory(' + adapter['instance'].lower() + ')\\dedicated usage'
            assert key in by_path and by_path[key]['cooked_value'] == adapter['bytes']
            adapter_keys.add(key)
        assert adapter_keys == {key for key in selected if key.startswith('\\gpu adapter memory(')}
        scenario = s['scenario']
        assert not s['invalid_samples'] and scenario['mode'] == 'experiment' and scenario['paused'] and scenario['renderer_confirmed']
        assert scenario['physical_time'] == 0 and scenario['revision'] == 0
        dedicated = sum(p['bytes'] for p in s['product'] if p['counter'] == 'dedicated usage')
        total = sum(p['bytes'] for p in s['product'])
        assert dedicated == s['product_dedicated_sum_bytes'] and total <= LIMITS['GPU_bytes']
        assert any(p['pid'] == session['app'] and p['counter'] == 'dedicated usage' for p in s['product'])
        peak = max(peak, total)
    for sample in row['samples']:
        assert {p['pid'] for p in sample['ram']['processes']} == owned
    return peak
