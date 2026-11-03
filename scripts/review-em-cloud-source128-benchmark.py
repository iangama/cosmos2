"""Independent frames/resources/static energy audit and adaptive ODE endpoint reference for128sources."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import math
import statistics
import struct
import sys
import tarfile
import numpy as np
import scipy
from scipy.integrate import solve_ivp
from scipy.integrate._ivp import rk, ivp, dop853_coefficients
import inspect

ROOT = Path(__file__).resolve().parents[1]
label = sys.argv[1]
assert 1 <= len(label) <= 18 and all(c.isalnum() or c in '_-' for c in label)
source = ROOT/f'evidence/native-emcloud-{label}.json'
r = json.loads(source.read_bytes())
failures, summaries, ram, gpu, budgets, science = [], [], [], [], [], []
result = {'benchmark': str(source.relative_to(ROOT)), 'benchmark_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'audit_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'accepted': False, 'scope': 'Only the declared10k/128weak charged-dipolar shell fixture,97E+97B arrows and three routes. '
                                      'No strong/arbitrary128-source, potential, mutualEM128/new-runtime regression, wholeC2-12 or installation approval.'}


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
    assert s['model'] == r['declared_source_model'] and len(s['model']['sources']) == 128
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


def field_scalar(x,model):
    es=[[],[],[]];bs=[[],[],[]];escale=bscale=0.
    for source in model['sources']:
        d=[a-b for a,b in zip(x,source['position_m'])];radius=math.hypot(*d)
        assert radius>source['exclusion_radius_m']
        moment=source['magnetic_moment_A_m2'];along=math.fsum(a*b for a,b in zip(d,moment))
        electric=[ke*source['charge_C']*a/radius**3 for a in d]
        magnetic=[mu4pi*(3*a*along/radius**5-m/radius**3) for a,m in zip(d,moment)]
        escale+=math.hypot(*electric);bscale+=math.hypot(*magnetic)
        for k in range(3):es[k].append(electric[k]);bs[k].append(magnetic[k])
    e=[math.fsum(a)+b for a,b in zip(es,model['uniform_E_V_m'])]
    b=[math.fsum(a)+b for a,b in zip(bs,model['uniform_B_T'])]
    return e,b,max(escale+math.hypot(*model['uniform_E_V_m']),1e-300),max(bscale+math.hypot(*model['uniform_B_T']),1e-300)


def mechanical(xs,vs,model):
    kinetic=math.fsum(.5*math.fsum(c*c for c in v) for v in vs)
    potential=math.fsum(math.fsum(ke*s['charge_C']/math.dist(x,s['position_m']) for s in model['sources']) for x in xs)
    return kinetic+potential,kinetic+abs(potential)


def ode_reference(xs,vs,finish,model):
    assert scipy.__version__=='1.18.1'
    indices=[0,1234,9999];x=np.array([xs[k] for k in indices]);v=np.array([vs[k] for k in indices])
    sx=np.array([s['position_m'] for s in model['sources']]);sq=np.array([s['charge_C'] for s in model['sources']]);sm=np.array([s['magnetic_moment_A_m2'] for s in model['sources']])
    def rhs(_t,y):
        x,v=y.reshape(2,3,3);d=x[:,None,:]-sx;r=np.sqrt(np.sum(d*d,axis=2));assert np.all(r>.02)
        e=np.sum((ke*sq/r**3)[:,:,None]*d,axis=1)+model['uniform_E_V_m']
        b=mu4pi*np.sum(3*d*np.sum(d*sm,axis=2)[:,:,None]/r[:,:,None]**5-sm/r[:,:,None]**3,axis=1)+model['uniform_B_T']
        return np.array([v,e+np.cross(v,b)]).reshape(-1)
    references=[]
    for tol in (1e-12,2.5e-14):
        solved=solve_ivp(rhs,(0.,finish),np.array([x,v]).reshape(-1),method='DOP853',rtol=tol,atol=tol*.1,max_step=.05)
        assert solved.success and solved.t[-1]==finish
        references.append(solved.y[:,-1].reshape(2,3,3))
    return references[-1],float(np.max(abs(references[0]-references[1])))


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
        prefix = r.get('candidate_source_prefix', 'output/c212-em-cloud-native-product/em-cloud/')
        assert prefix in ('output/c212-em-cloud-native-product/em-cloud/','output/c212-em-time-product/em-cloud/','output/c212-em-integration-product/em-cloud/','output/c212-em-cloud-editor-product/em-cloud/','output/c212-em-framing-product/em-cloud/','output/c212-em-viewport-product/em-cloud/')
        assert bool(r.get('integration_profile'))==(prefix in ('output/c212-em-integration-product/em-cloud/','output/c212-em-cloud-editor-product/em-cloud/','output/c212-em-framing-product/em-cloud/','output/c212-em-viewport-product/em-cloud/'))
        assert bool(r.get('cloud_editor_profile'))==(prefix in ('output/c212-em-cloud-editor-product/em-cloud/','output/c212-em-framing-product/em-cloud/','output/c212-em-viewport-product/em-cloud/'))
        if r.get('cloud_editor_profile'):
            assert r['session']['emCloudEditorCandidate'] and r['cloud_editor_UI']=={'interface_scale':1,'active_panel':'layers'}
        assert bool(r.get('framing_profile'))==(prefix in ('output/c212-em-framing-product/em-cloud/','output/c212-em-viewport-product/em-cloud/'))
        assert bool(r.get('viewport_profile'))==(prefix=='output/c212-em-viewport-product/em-cloud/')
        if r.get('viewport_profile'):assert r['session']['emViewportCandidate']
        if r.get('framing_profile'):
            assert r['session']['emFramingCandidate']
            if r.get('viewport_profile'):
                from em_viewport_profile_audit import audit_dependencies
            else:
                from em_framing_profile_audit import audit_dependencies
            result['framing_static_dependencies']=audit_dependencies(r,frozen)
        if r.get('integration_profile'):assert r['session']['emIntegrationCandidate']
        for path, digest in r['scientific_generation']['files_sha256'].items():
            assert r['configuration_sha256'][prefix+path] == digest
        for name, digest in r['parent_sources_sha256'].items():
            assert r['configuration_sha256'][prefix.rsplit('/em-cloud/',1)[0]+'/app/'+name] == digest
        variant = r.get('runtime_variant', 'em-cloud')
        assert variant in ('em-cloud', 'topic-cleanup')
        runtime = json.loads(frozen('evidence/built-runtime-'+variant+'.json'))
        assert runtime['engine_sha256'] == r['engine_sha256']
        assert r['configuration_sha256']['.runtime-'+variant+'/bin/OpenSpace.exe'] == r['engine_sha256']
        assert r['configuration_sha256'][runtime['patch'].replace('\\', '/')] == runtime['patch_sha256']
        if variant == 'topic-cleanup':
            assert hashlib.sha256(frozen('evidence/built-runtime-em-cloud.json')).hexdigest() == runtime['base_receipt_sha256']
            for name, digest in runtime['changed_source_sha256'].items():
                assert hashlib.sha256(frozen('.upstream/openspace/'+name)).hexdigest() == digest
            for filename, key in (('scripts/build-topic-cleanup-runtime.ps1', 'builder_sha256'), ('scripts/stage-topic-cleanup-runtime.py', 'stager_sha256')):
                assert hashlib.sha256(frozen(filename)).hexdigest() == runtime[key]
        assert hashlib.sha256(frozen(r['fixture_checkpoint'])).hexdigest() == r['fixture_sha256']
        seed = checkpoint(frozen(r['fixture_checkpoint']))
        x0, v0 = vectors(seed['phase']['position_f64le_hex']), vectors(seed['phase']['velocity_f64le_hex'])
        assert seed['phase']['time_s'] == 0 and seed['model'] == r['declared_source_model']
        model = seed['model']
        assert model['uniform_E_V_m'] == [0.,0.,0.] and model['uniform_B_T'] == [0.,0.,1.]
        assert len(model['sources']) == 128 and len({s['id'] for s in model['sources']}) == 128
        for j,s in enumerate(model['sources']):
            assert s['charge_C'] == (-1)**j*1e-12 and s['magnetic_moment_A_m2'] == [1e4,-2e4,3e4]
            assert s['exclusion_radius_m'] == .02 and math.isclose(math.hypot(*s['position_m']),8.,abs_tol=1e-14)
        constants = json.loads(frozen(prefix+'constants.json'))
        ke = 1/(4*math.pi*constants['vacuum_electric_permittivity_F_m']['value'])
        mu4pi = constants['vacuum_magnetic_permeability_N_A2']['value']/(4*math.pi)
        build = json.loads(frozen(prefix+'build-receipt.json').decode('utf-8-sig'))
        assert build['abi'] == 1
        for name,key in (('cloud_kernel.cpp','cpp_sha256'),('CMakeLists.txt','cmake_sha256'),('cosmos2_em_cloud.dll','dll_sha256')):
            assert r['configuration_sha256'][prefix+name] == build[key]
        assert r['configuration_sha256']['scripts/build-em-cloud-kernel.ps1'] == build['builder_sha256']
        masses = struct.unpack('<10000d', bytes.fromhex(seed['particles']['mass_f64le_hex']))
        charges = struct.unpack('<10000d', bytes.fromhex(seed['particles']['charge_f64le_hex']))
        assert all(m == q == 1 for m, q in zip(masses, charges))
        assert all(v[2] == 0 for v in v0)
        energy0, energy_scale0 = mechanical(x0, v0, model)
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
            assert len(field['render']['meshes']) == 2
            assert {m['quantity'] for m in field['render']['meshes']} == {'electric','magnetic'}
            for mesh in field['render']['meshes']:
                assert mesh['arrow_count'] == 97
                assert hashlib.sha256(frozen(str(Path(mesh['file']).relative_to(ROOT)).replace('\\', '/'))).hexdigest() == mesh['file_sha256']
            assert field['source_model'] == model and field['scientific_generation'] == r['scientific_generation']
            for sample in field['measurement']['samples']:
                assert sample['valid']
                reference = field_scalar(sample['position_m'], model)
                assert math.dist(sample['electric_field_V_m'], reference[0]) <= 1e-10*reference[2]
                assert math.dist(sample['magnetic_field_T'], reference[1]) <= 1e-10*reference[3]
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
            reference, reference_change = ode_reference(x0,v0,time_s,model)
            criterion(reference_change < 1e-8, 'independent DOP853 reference refinement <1e-8', reference_change)
            position_error = velocity_error = 0.
            for k,index in enumerate((0,1234,9999)):
                speed = math.hypot(*v0[index])
                position_error = max(position_error, math.dist(xs[index],reference[0,k])/speed)
                velocity_error = max(velocity_error, math.dist(vs[index],reference[1,k])/speed)
            energy, _ = mechanical(xs,vs,model)
            energy_error = abs(energy-energy0)/energy_scale0
            criterion(position_error <= 1e-3 and velocity_error <= 1e-3, 'run'+str(number)+' independent general128source ODE trajectory <=1e-3', [position_error, velocity_error])
            criterion(energy_error <= 1e-6, 'run'+str(number)+' relative static mechanical energy drift <=1e-6', energy_error)
            print(json.dumps({'audited_run':number,'ODE_position_error':position_error,'ODE_velocity_error':velocity_error,'static_energy_error':energy_error}),flush=True)
            endpoint = run['paused_endpoint']
            assert endpoint['state']['paused'] and endpoint['state']['time_s'] == time_s
            assert endpoint['native']['confirmation']['metadata']['time_s'] == time_s
            assert endpoint['native']['confirmation']['metadata']['payload_sha256'] == hashlib.sha256(bytes.fromhex(p['phase']['position_f64le_hex'])).hexdigest()
            science.append({'run': number, 'time_s': time_s, 'position_error_over_initial_uniform_B_Larmor_scale': position_error,
                            'velocity_error_over_initial_speed': velocity_error, 'mechanical_energy_relative_error': energy_error, 'reference_refinement_max_component_change':reference_change})
            summaries.append({'run': number, 'rate': rate, **summary})
    pauses = r['pause_latency_samples']
    assert len(pauses) == 20 and all(0 <= p['worker_elapsed_ms'] <= p['wall_ms'] for p in pauses)
    criterion(max(p['wall_ms'] for p in pauses) <= 250, '20 confirmed native pauses <=250ms', max(p['wall_ms'] for p in pauses))
    result.update(scipy_version=scipy.__version__, reference_sources_sha256={str(Path(inspect.getfile(m)).relative_to(ROOT)):hashlib.sha256(Path(inspect.getfile(m)).read_bytes()).hexdigest() for m in (rk,ivp,dop853_coefficients)}, accepted=not failures, criteria_failures=failures, three_EM10000_routes_measured_and_integrity_verified=True,
                  frozen_source_archive=r['frozen_source_archive'], runs=summaries, independent_general128source_ODE=science,
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
