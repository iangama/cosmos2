"""Independent stdlib audit: frozen files, frame limits, resources and analytic B motion."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import math
import statistics
import struct
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
label = sys.argv[1]
assert 1 <= len(label) <= 18 and all(c.isalnum() or c in '_-' for c in label)
source = ROOT/f'evidence/native-emcloud-{label}.json'
r = json.loads(source.read_bytes())
failures, summaries, ram, gpu, budgets, science = [], [], [], [], [], []
result = {'benchmark': str(source.relative_to(ROOT)), 'benchmark_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'audit_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'accepted': False, 'scope': 'Only the declared10k prescribed uniform-B/SI fixture,97 frozen B arrows and three visibility routes. '
                                      'No128-source, potential, EM128/new-runtime regression, whole C2-12 or installation approval.'}


def criterion(condition, name, detail=None):
    if not condition:
        failures.append({'criterion': name, 'observed': detail})


def percentile(values, fraction):
    values = sorted(values)
    index = (len(values)-1)*fraction
    a, b = math.floor(index), math.ceil(index)
    return values[a]+(values[b]-values[a])*(index-a)


def frames(values, context):
    assert values and all(math.isfinite(x) and x > 0 for x in values)
    record = {'frames': len(values), 'median_ms': statistics.median(values)*1000,
              'p95_ms': percentile(values, .95)*1000, 'p99_ms': percentile(values, .99)*1000,
              'over100ms': sum(x > .1 for x in values)}
    for key, limit in (('median_ms', 16.7), ('p95_ms', 25), ('p99_ms', 50), ('over100ms', 0)):
        criterion(record[key] <= limit, context+' '+key+' <= '+str(limit), record[key])
    return record


def state(value):
    s, n = value['state'], value['native']
    assert not s['paused'] and s['notice'] is None and s['count'] == 10000 and s['dt_s'] == .002
    assert s['requested_model_s_per_wall_s'] == 1 and s['controls'] == {'electric_acting': True, 'magnetic_acting': True}
    assert s['model'] == {'sources': [], 'uniform_E_V_m': [0., 0., 0.], 'uniform_B_T': [0., 0., 1.]}
    assert s['scientific_generation'] == r['scientific_generation']
    assert n['active'] and n['error'] is None and n['confirmation']['state'] == 'accepted'
    m = n['confirmation']['metadata']
    for key in ('system_id', 'edit_token', 'cloud_id', 'source_id', 'count'):
        assert m[key] == s[key]
    assert m['model'] == 'SI_prescribed_EM_test_cloud_boris_v2' and m['time_unit_s'] == m['length_unit_m'] == 1
    assert 0 <= s['time_s']-m['time_s'] <= 1
    assert len(value['field_map']['measurement']['samples']) == 97
    return s


def checkpoint(raw):
    value = json.loads(raw)
    seal = value.pop('sha256')
    assert hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()).hexdigest() == seal
    assert value['schema'] == 1 and value['count'] == 10000 and value['dt_s'] == .002
    assert value['generation'] == r['scientific_generation']
    return value


def vectors(value):
    raw = bytes.fromhex(value)
    assert len(raw) == 10000*24
    return list(struct.iter_unpack('<ddd', raw))


try:
    assert r['completed'] and len(r['runs']) == 3 and r['warmup_s'] == 30 and r['route_duration_s'] == 60
    assert r['count'] == 10000 and r['dt_s'] == .002 and r['requested_model_s_per_wall_s'] == 1
    assert r['owner_pointer_preserved'] and r['installed_product_files_preserved'] == 82
    assert [x['run'] for x in r['runs']] == [1, 2, 3]
    assert [(x['expected_cloud_visible'], x['expected_magnetic_visible']) for x in r['runs']] == [(True, True), (False, True), (True, False)]
    archive = ROOT/r['frozen_source_archive']['path']
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == r['frozen_source_archive']['sha256']
    with tarfile.open(archive, 'r:gz') as tar:
        def frozen(path):
            return tar.extractfile(str(path).replace('\\', '/')).read()
        for path, digest in r['configuration_sha256'].items():
            assert hashlib.sha256(frozen(path)).hexdigest() == digest, path
        prefix = 'output/c212-em-cloud-product/em-cloud/'
        for path, digest in r['scientific_generation']['files_sha256'].items():
            assert r['configuration_sha256'][prefix+path] == digest
        for name, digest in r['parent_sources_sha256'].items():
            assert r['configuration_sha256']['output/c212-em-cloud-product/app/'+name] == digest
        runtime = json.loads(frozen('evidence/built-runtime-em-cloud.json'))
        assert runtime['engine_sha256'] == r['engine_sha256']
        assert r['configuration_sha256']['.runtime-em-cloud/bin/OpenSpace.exe'] == r['engine_sha256']
        assert r['configuration_sha256'][runtime['patch'].replace('\\', '/')] == runtime['patch_sha256']
        assert hashlib.sha256(frozen(r['fixture_checkpoint'])).hexdigest() == r['fixture_sha256']
        seed = checkpoint(frozen(r['fixture_checkpoint']))
        x0, v0 = vectors(seed['phase']['position_f64le_hex']), vectors(seed['phase']['velocity_f64le_hex'])
        assert seed['phase']['time_s'] == 0 and seed['model'] == {'sources': [], 'uniform_E_V_m': [0., 0., 0.], 'uniform_B_T': [0., 0., 1.]}
        masses = struct.unpack('<10000d', bytes.fromhex(seed['particles']['mass_f64le_hex']))
        charges = struct.unpack('<10000d', bytes.fromhex(seed['particles']['charge_f64le_hex']))
        assert all(m == q == 1 for m, q in zip(masses, charges))
        assert all(v[2] == 0 for v in v0)
        energy0 = math.fsum(.5*math.fsum(c*c for c in v) for v in v0)
        for run in r['runs']:
            number = run['run']
            capture = run['capture']
            assert capture['width'] == 1920 and capture['height'] == 1080 and not capture['capacity_reached'] and capture['invalid_samples'] == 0
            values = run['frame_times_s']
            assert run['raw_capture_samples_s'][1:] == values
            assert abs(math.fsum(values)-60) < .5 and abs(run['wall_interval_s']-60) < .5
            summary = frames(values, 'run'+str(number))
            for key, value in summary.items():
                assert math.isclose(value, run['statistics'][key], abs_tol=1e-9)
            initial, final = state(run['initial']), state(run['final'])
            assert initial['system_id'] == final['system_id']
            rate = (final['time_s']-initial['time_s'])/run['wall_interval_s']
            assert math.isclose(rate, run['observed_model_s_per_wall_s'], abs_tol=1e-12)
            criterion(rate >= .9, 'run'+str(number)+' model rate >=.9 for1 requested', rate)
            for index, mark in enumerate(run['memory']):
                finish = run['memory'][index+1]['first_frame'] if index < 2 else len(values)
                frames(values[mark['first_frame']:finish], 'run'+str(number)+' camera'+str(index+1))
                s = state(mark['state'])
                assert s['system_id'] == initial['system_id']
                memory = mark['ram']
                resident = sum(p['working_set_bytes'] for p in memory['processes'])
                assert resident == memory['sum_working_set_bytes']
                criterion(resident <= 8*2**30, 'RAM product sum <=8GiB', resident)
                assert {r['session']['app'], r['session']['server'], r['em_worker_pid']} <= {p['pid'] for p in memory['processes']}
                ram.append(resident)
                adapters = mark['engine_gpu']['adapters']
                adapters = adapters.values() if isinstance(adapters, dict) else adapters
                physical = [a for a in adapters if a['vendor_id'] == 4098 and a['status'] == 'ok']
                assert physical
                budgets.extend(a['budget_bytes'] for a in physical)
                log = mark['engine_gpu'].get('script_log')
                if log is not None:
                    assert log['initialized'] and not log['failed'] and log['dropped'] == 0
                visibility = mark['independent_native_visibility']
                assert visibility['receiver_enabled'] and visibility['opacity'] == (1 if run['expected_cloud_visible'] else 0)
                assert visibility['selection_visible'] is run['expected_cloud_visible']
                assert mark['state']['visual']['cloud_visible'] is run['expected_cloud_visible']
                assert mark['state']['visual']['magnetic_visible'] is run['expected_magnetic_visible']
            field = run['frozen_field_map']
            assert len(field['measurement']['samples']) == 97 and field['measurement']['time_s'] == 0
            assert field['measurement']['system_id'] == initial['system_id']
            assert len(field['render']['meshes']) == 1
            mesh = field['render']['meshes'][0]
            assert mesh['quantity'] == 'magnetic' and mesh['arrow_count'] == 97
            assert hashlib.sha256(frozen(str(Path(mesh['file']).relative_to(ROOT)).replace('\\', '/'))).hexdigest() == mesh['file_sha256']
            for sample in field['measurement']['samples']:
                assert sample['valid'] and sample['electric_field_V_m'] == [0., 0., 0.] and sample['magnetic_field_T'] == [0., 0., 1.]
            gpu_path = ROOT/run['gpu_report']
            assert hashlib.sha256(gpu_path.read_bytes()).hexdigest() == run['gpu_sha256']
            g = json.loads(gpu_path.read_text(encoding='utf-8-sig'))
            assert len(g['samples']) == 66 and not g['counter_errors']
            assert g['engine_sha256'] == r['engine_sha256'] and g['session']['app'] == r['session']['app']
            assert g['collector_sha256'] == r['configuration_sha256']['scripts/collect-em-cloud-gpu-memory.ps1']
            assert {r['session']['app'], r['session']['server'], r['em_worker_pid']} <= set(g['owned_processes'])
            start, end = datetime.fromisoformat(run['capture_start_utc']), datetime.fromisoformat(run['capture_end_utc'])
            assert datetime.fromisoformat(g['samples'][0]['utc'].replace('Z', '+00:00')) <= start
            assert datetime.fromisoformat(g['samples'][-1]['utc'].replace('Z', '+00:00')) >= end
            for sample in g['samples']:
                scenario = sample['scenario']
                assert not sample['invalid_samples'] and scenario['mode'] == 'emcloud' and not scenario['paused']
                assert scenario['renderer_confirmed'] and scenario['fixture_count'] == 10000 and scenario['requested_rate'] == 1.
                assert scenario['system_id'] == initial['system_id'] and scenario['source_id'] == initial['source_id']
                assert scenario['dt_s'] == .002 and scenario['field_samples'] == 97
                assert scenario['cloud_visible'] is run['expected_cloud_visible'] and scenario['magnetic_visible'] is run['expected_magnetic_visible']
                assert abs(scenario['physical_time']-scenario['native_time']) <= 1
                total = sum(p['bytes'] for p in sample['product'] if p['counter'] == 'dedicated usage')
                assert total == sample['product_dedicated_sum_bytes']
            peak = max(s['product_dedicated_sum_bytes'] for s in g['samples'])
            criterion(peak <= 5.5*2**30 and peak < min(budgets), 'WDDM product sum <=5.5GiB and below engine budget', peak)
            gpu.append(peak)
            endpoint_raw = frozen(run['endpoint_checkpoint'])
            assert hashlib.sha256(endpoint_raw).hexdigest() == run['endpoint_sha256']
            p = checkpoint(endpoint_raw)
            assert p['model'] == seed['model'] and p['controls'] == seed['controls'] and p['particles'] == seed['particles']
            xs, vs = vectors(p['phase']['position_f64le_hex']), vectors(p['phase']['velocity_f64le_hex'])
            time_s = p['phase']['time_s']
            sine, cosine = math.sin(time_s), math.cos(time_s)
            position_error = velocity_error = 0.
            for x, v, xstart, vstart in zip(xs, vs, x0, v0):
                speed = math.hypot(*vstart)
                reference_x = (xstart[0]+vstart[0]*sine+vstart[1]*(1-cosine),
                               xstart[1]+vstart[1]*sine-vstart[0]*(1-cosine), xstart[2])
                reference_v = (vstart[0]*cosine+vstart[1]*sine, vstart[1]*cosine-vstart[0]*sine, 0.)
                position_error = max(position_error, math.dist(x, reference_x)/speed)
                velocity_error = max(velocity_error, math.dist(v, reference_v)/speed)
            energy = math.fsum(.5*math.fsum(c*c for c in v) for v in vs)
            energy_error = abs(energy-energy0)/energy0
            criterion(position_error <= 1e-3 and velocity_error <= 1e-3, 'run'+str(number)+' independent uniform-B analytic trajectory <=1e-3', [position_error, velocity_error])
            criterion(energy_error <= 1e-10, 'run'+str(number)+' relative kinetic energy drift <=1e-10', energy_error)
            endpoint = run['paused_endpoint']
            assert endpoint['state']['paused'] and endpoint['state']['time_s'] == time_s
            assert endpoint['native']['confirmation']['metadata']['time_s'] == time_s
            assert endpoint['native']['confirmation']['metadata']['payload_sha256'] == hashlib.sha256(bytes.fromhex(p['phase']['position_f64le_hex'])).hexdigest()
            science.append({'run': number, 'time_s': time_s, 'position_error_over_Larmor_radius': position_error,
                            'velocity_error_over_initial_speed': velocity_error, 'energy_relative_error': energy_error})
            summaries.append({'run': number, 'rate': rate, **summary})
    pauses = r['pause_latency_samples']
    assert len(pauses) == 20 and all(0 <= p['worker_elapsed_ms'] <= p['wall_ms'] for p in pauses)
    criterion(max(p['wall_ms'] for p in pauses) <= 250, '20 confirmed native pauses <=250ms', max(p['wall_ms'] for p in pauses))
    result.update(accepted=not failures, criteria_failures=failures, three_EM10000_routes_measured_and_integrity_verified=True,
                  frozen_source_archive=r['frozen_source_archive'], runs=summaries, independent_analytic_B=science,
                  observed_rate_min=min(s['rate'] for s in summaries), p95_ms_max=max(s['p95_ms'] for s in summaries),
                  p99_ms_max=max(s['p99_ms'] for s in summaries), pause_wall_max_ms=max(p['wall_ms'] for p in pauses),
                  resident_sum_max_GiB=max(ram)/2**30, WDDM_dedicated_sum_max_GiB=max(gpu)/2**30,
                  engine_DXGI_budget_min_GiB=min(budgets)/2**30,
                  memory_method='WDDM/RAM process sums may duplicate shared allocations. DXGI budget belongs to engine; other applications excluded from product tally.')
except BaseException as error:
    result['integrity_failure'] = type(error).__name__+': '+str(error)
    raise
finally:
    (ROOT/f'evidence/native-emcloud-{label}-review.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
if not result['accepted']:
    raise SystemExit(1)
