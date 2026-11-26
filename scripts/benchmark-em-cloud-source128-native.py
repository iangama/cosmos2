"""Three formal EM10k routes with unchanged fixed fixture and complete resource windows."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import io
import json
import math
import subprocess
import sys
import tarfile
import time
import urllib.request
import uuid
import numpy as np
import psutil
from websockets.sync.client import connect
from cef_page import Page
import native_product_memory as ram

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--label', required=True)
parser.add_argument('--topic-cleanup', action='store_true')
parser.add_argument('--time-controls', action='store_true')
parser.add_argument('--integration', action='store_true')
parser.add_argument('--cloud-editor', action='store_true')
parser.add_argument('--framing',action='store_true')
parser.add_argument('--viewport',action='store_true')
args = parser.parse_args()
assert not args.time_controls or args.topic_cleanup
assert not args.integration or args.time_controls
assert not args.cloud_editor or args.integration
assert not args.framing or args.cloud_editor
assert not args.viewport or args.framing
CANDIDATE = ROOT/('output/c212-em-time-product' if args.time_controls else 'output/c212-em-cloud-native-product')
if args.integration:CANDIDATE=ROOT/'output/c212-em-integration-product'
if args.cloud_editor:CANDIDATE=ROOT/'output/c212-em-cloud-editor-product'
if args.framing:CANDIDATE=ROOT/'output/c212-em-framing-product'
if args.viewport:CANDIDATE=ROOT/'output/c212-em-viewport-product'
sys.path.insert(0, str(CANDIDATE/'em-cloud'))
from cloud_core import System, Phase
from cloud_checkpoint import save, load, generation
from em_fields import Model, Source
from em_cloud_source_fixture import source_model

RUNTIME = ROOT/('.runtime-topic-cleanup' if args.topic_cleanup else '.runtime-em-cloud')
RUNTIME_RECEIPT = ROOT/('evidence/built-runtime-topic-cleanup.json' if args.topic_cleanup else 'evidence/built-runtime-em-cloud.json')
LAUNCHER = ROOT/('scripts/start-c212-topic-cleanup-candidate.ps1' if args.topic_cleanup else 'scripts/start-c212-em-cloud-native-candidate.ps1')
if args.time_controls: LAUNCHER=ROOT/'scripts/start-c212-em-time-candidate.ps1'
if args.integration: LAUNCHER=ROOT/'scripts/start-c212-em-integration-candidate.ps1'
if args.cloud_editor:LAUNCHER=ROOT/'scripts/start-c212-em-cloud-editor-candidate.ps1'
if args.framing:LAUNCHER=ROOT/'scripts/start-c212-em-framing-candidate.ps1'
if args.viewport:LAUNCHER=ROOT/'scripts/start-c212-em-viewport-candidate.ps1'
assert 1 <= len(args.label) <= 18 and all(c.isalnum() or c in '_-' for c in args.label)
destination = ROOT/f'evidence/native-emcloud-{args.label}.json'
assert not destination.exists()
session = json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
ram.session = session
assert session['emCloudCandidate'] and Path(session['serverScript']).resolve() == (CANDIDATE/'app/server.py').resolve()
assert Path(session['runtime']).resolve() == RUNTIME.resolve()
if args.framing:assert session['emFramingCandidate']
if args.viewport:assert session['emViewportCandidate']
owner = ROOT/'user/sessions/latest.json'
original = owner.read_bytes()
app_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (ROOT/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
storage = CANDIDATE/'c212-em-cloud-worker/product'
storage.mkdir(parents=True, exist_ok=True)
name = 'profile-'+uuid.uuid4().hex[:20]
i = np.arange(10000)
theta = i*(math.pi*(3-math.sqrt(5)))
x = np.column_stack((.4*np.cos(theta), .4*np.sin(theta), .4*(i+.5)/10000-.2))
v = np.column_stack((np.ones(10000), .1*np.sin(theta), np.zeros(10000)))
specification = source_model()
system = System.uniform(Model(tuple(Source(**s) for s in specification['sources']), specification['uniform_E_V_m'], specification['uniform_B_T']), 10000, 1., 1.)
phase = Phase(x, v)
acting = {'electric_acting': True, 'magnetic_acting': True}
save(storage/(name+'.json'), system, phase, .002, acting)
fixture = storage/(name+'.json')
configuration = [Path(__file__), ROOT/'scripts/native_product_memory.py', ROOT/'scripts/collect-em-cloud-gpu-memory.ps1',
                 LAUNCHER, RUNTIME_RECEIPT,
                 ROOT/'config/cosmos2.cfg', ROOT/'config/window-1080.json', RUNTIME/'openspace.cfg',
                 ROOT/'user/data/profiles/cosmos2.profile', fixture,
                 ROOT/'scripts/em_cloud_source_fixture.py', ROOT/'scripts/build-em-cloud-kernel.ps1',
                 CANDIDATE/'em-cloud/CMakeLists.txt',
                 ROOT/'patches/em-cloud-position-binding.patch',
                 ROOT/'.upstream/openspace/modules/base/rendering/pointcloud/renderablepointcloud.cpp',
                 ROOT/'.upstream/openspace/modules/base/rendering/pointcloud/renderablepointcloud.h',
                 RUNTIME/'bin/OpenSpace.exe',
                 *sorted((ROOT/'user/data/assets/cosmos2').glob('*.asset'))]
if args.topic_cleanup:
    runtime_receipt = json.loads(RUNTIME_RECEIPT.read_bytes())
    configuration += [ROOT/'scripts/build-topic-cleanup-runtime.ps1', ROOT/'scripts/stage-topic-cleanup-runtime.py',
                      ROOT/runtime_receipt['patch'], ROOT/'evidence/built-runtime-em-cloud.json']
    configuration += [ROOT/'.upstream/openspace'/name for name in runtime_receipt['changed_source_sha256']]
configuration += [ROOT/'scripts/cef_page.py']
configuration += [p for folder in ('em', 'em-cloud', 'app') for p in (CANDIDATE/folder).rglob('*')
                  if p.is_file() and p.suffix in ('.py', '.json', '.html', '.js', '.css', '.cpp', '.dll') and '__pycache__' not in p.parts]
if args.framing:
    configuration += [ROOT/'scripts/em_framing_profile_audit.py',ROOT/'evidence/em-framing-static-sampler-release2-check.json']
if args.viewport:
    configuration += [ROOT/'scripts/em_viewport_profile_audit.py']
report = {'schema': 1, 'profile': 'C2-12 EM10000 plus128nonzero charged/dipolar prescribed sources, native helperE Borisv2',
          'session': session, 'warmup_s': 30, 'route_duration_s': 60, 'requested_model_s_per_wall_s': 1.,
          'dt_s': .002, 'scientific_generation': generation(), 'candidate_source_prefix': str(CANDIDATE.relative_to(ROOT)).replace('\\','/')+'/em-cloud/', 'count': 10000, 'declared_source_model': specification,
          'fixture_checkpoint': str(fixture.relative_to(ROOT)), 'fixture_sha256': hashlib.sha256(fixture.read_bytes()).hexdigest(),
          'runtime_variant': 'topic-cleanup' if args.topic_cleanup else 'em-cloud',
          'integration_profile': args.integration,
          'cloud_editor_profile':args.cloud_editor,
        'framing_profile':args.framing,
        'viewport_profile':args.viewport,
          'engine_sha256': hashlib.sha256((RUNTIME/'bin/OpenSpace.exe').read_bytes()).hexdigest(),
          'configuration_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in configuration},
          'runs': [], 'completed': False,
          'scope': 'Each route starts from the same10k q=m=1 SI checkpoint, 128static sources q=+-1e-12C/moments(1e4,-2e4,3e4)A.m2 at8m, uniformB1T,dt.002/rate1. '
                   '97 frozen E plus97B arrows from128nonzero charged/dipolar sources on8m shell, plus uniformB1T. All layers, hidden particles with live confirmations, and hidden B are measured separately. '
                   'Only this declared128-source shell fixture; no potential, mutualEM128/new-runtime, arbitrary-source geometry or wholeC2-12 performance acceptance. '
                   'Graphic scale1e9; hidden particles keep the receiver updating at zero opacity. WDDM/RAM sums may duplicate shared allocations.'}


def persist():
    temp = destination.with_suffix('.tmp')
    temp.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    temp.replace(destination)


def state():
    return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/em-cloud/state', timeout=10))


def command(name, **values):
    guard = {}
    if name not in ('pause', 'snapshot'):
        s = state()['state']
        guard = {k: s[k] for k in ('system_id', 'edit_token', 'revision', 'frame')} | {'expected_time_s': s['time_s']}
    request = urllib.request.Request('http://127.0.0.1:4700/api/em-cloud/command',
                                     data=json.dumps({'command': name, **guard, **values}).encode(),
                                     headers={'Content-Type': 'application/json'})
    response = json.load(urllib.request.urlopen(request, timeout=20))
    assert not response.get('display'), response
    return response


socket = connect('ws://127.0.0.1:4682', open_timeout=5, close_timeout=.2, ping_interval=None, max_size=4*1024*1024)
socket.send(json.dumps({'type': 'apiHandshake', 'apiVersion': {'major': 1, 'minor': 0, 'patch': 0}}))
topic = 0


def native(code):
    global topic
    topic += 1
    socket.send(json.dumps({'topic': topic, 'type': 'luascript', 'payload': {'script': code, 'return': True}}))
    reply = json.loads(socket.recv(timeout=15))
    assert reply.get('topic') == topic, reply
    def normalize(value):
        if isinstance(value, dict):
            if value and set(value) == {str(i) for i in range(1, len(value)+1)}:
                return [normalize(value[str(i)]) for i in range(1, len(value)+1)]
            return {key: normalize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [normalize(item) for item in value]
        return value
    return normalize(reply['payload']['1'])


routes = ((0, -8e9, 5e9), (8e9, 0, 5e9), (0, -6e9, 7e9))


def navigate(position):
    native('openspace.navigation.setNavigationState({Anchor="C2EMCamera",ReferenceFrame="C2EMRoot",Position={'+','.join(map(str, position))+'},Up={0,0,1}});return {queued=true}')


def check_state(value):
    s, n = value['state'], value['native']
    assert not s['paused'] and s['notice'] is None and s['requested_model_s_per_wall_s'] == 1.
    assert s['count'] == 10000 and s['dt_s'] == .002 and s['controls'] == acting
    assert s['model'] == specification and len(s['model']['sources']) == 128
    assert s['scientific_generation'] == report['scientific_generation']
    assert n['active'] and n['error'] is None and n['confirmation']['metadata']['system_id'] == s['system_id']
    assert 0 <= s['time_s']-n['confirmation']['metadata']['time_s'] <= 1.
    assert len(value['field_map']['measurement']['samples']) == 97


def host_observation():
    # Additional raw observations for diagnosing scheduling pressure. They do
    # not replace or alter any formal frame, rate or resource criterion.
    parent=psutil.Process(session['server'])
    owned={p.pid:p for p in [parent,psutil.Process(session['app']),*parent.children(recursive=True)]}
    return {'utc':datetime.now(timezone.utc).isoformat(),'monotonic_s':time.perf_counter(),
            'logical_processors':psutil.cpu_count(),
            'system_CPU_times_per_processor':[dict(t._asdict()) for t in psutil.cpu_times(percpu=True)],
            'available_RAM_bytes':psutil.virtual_memory().available,
            'product_processes':[{'pid':p.pid,'CPU_times':dict(p.cpu_times()._asdict()),
                                  'threads':p.num_threads()} for p in owned.values() if p.is_running()]}


def start_gpu(run):
    label = f'{args.label}-emcloud-{run}'
    path = ROOT/f'evidence/gpu-memory-{label}.json'
    ready = ROOT/f'output/gpu-memory-ready-{label}.json'
    assert not path.exists() and not ready.exists()
    job = subprocess.Popen(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                             str(ROOT/'scripts/collect-em-cloud-gpu-memory.ps1'), '-Label', label,
                             '-Samples', '66', '-ExpectedMode', 'emcloud', '-ExpectedWorker', 'running', '-SignalReady'],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
    deadline = time.monotonic()+15
    try:
        while time.monotonic() < deadline:
            if job.poll() is not None:
                raise RuntimeError(job.communicate()[0])
            if ready.exists():
                try:
                    signal = json.loads(ready.read_text(encoding='utf-8-sig'))
                except (PermissionError, json.JSONDecodeError):
                    # Set-Content exposes the pathname before closing its Windows
                    # handle. Readiness requires a complete, readable signal.
                    time.sleep(.05)
                    continue
                assert signal['engine_pid'] == session['app']
                return job, path
            time.sleep(.05)
        raise TimeoutError('GPU resource collector startup unconfirmed')
    except BaseException:
        if job.poll() is None:
            job.terminate()
        job.communicate(timeout=5)
        raise


gpu_job = None
persist()
try:
    with Page() as page:
        page.goto('http://127.0.0.1:4700/em-cloud.html')
        if args.cloud_editor:
            page.wait_for_function('state&&!pending&&typeof cloudPanel!=="undefined"',timeout=30000)
            page.locator('#interface-scale').select_option('1')
            if page.evaluate('cloudPanel')!='layers':page.locator('[data-cloud-panel="layers"]').click()
            report['cloud_editor_UI']={'interface_scale':1,'active_panel':'layers'}
        page.wait_for_function('state && native?.active && !pending', timeout=30000)
        command('pause')
        report['em_worker_pid'] = state()['worker_pid']
        report['parent_sources_sha256'] = state()['parent_sources_sha256']
        for key, digest in report['parent_sources_sha256'].items():
            assert hashlib.sha256((CANDIDATE/'app'/key).read_bytes()).hexdigest() == digest
        for run, (cloud_visible, magnetic_visible) in enumerate(((True, True), (False, True), (True, False)), 1):
            if run > 1:
                command('pause')
            command('load', file=name)
            command('set_rate', value=1.)
            command('set_visual', changes={'cloud_visible': cloud_visible, 'electric_visible': True, 'magnetic_visible': magnetic_visible})
            points = []
            for k in range(48):
                z = 1-2*(k+.5)/48
                a = k*math.pi*(3-math.sqrt(5))
                rad = math.sqrt(1-z*z)
                points.append([3*rad*math.cos(a), 3*rad*math.sin(a), 3*z])
            points += [[a, b, 0] for a in range(-3, 4) for b in range(-3, 4)]
            command('field_map', points_m=points)
            frozen = state()['field_map']
            assert frozen['measurement']['time_s'] == 0
            for mesh in frozen['render']['meshes']:
                for key in ('file', 'names_file'):
                    path = Path(mesh[key])
                    report['configuration_sha256'][str(path.relative_to(ROOT)).replace('\\', '/')] = hashlib.sha256(path.read_bytes()).hexdigest()
                path = Path(mesh['file']).with_name('receipt.json')
                report['configuration_sha256'][str(path.relative_to(ROOT)).replace('\\', '/')] = hashlib.sha256(path.read_bytes()).hexdigest()
            command('resume')
            navigate(routes[0])
            print(json.dumps({'phase': 'warmup', 'run': run, 'seconds': 30}), flush=True)
            time.sleep(30)
            gpu_job, gpu_path = start_gpu(run)
            native('openspace.cosmos2BeginFrameCapture(12000);return {started=true}')
            began, capture_start = time.perf_counter(), datetime.now(timezone.utc)
            initial = state()
            check_state(initial)
            host_initial = host_observation()
            marks = []
            for part, position in enumerate(routes):
                if part:
                    navigate(position)
                metrics = native('local m=openspace.cosmos2MemoryMetrics();if openspace.cosmos2ScriptLogStatus then m.script_log=openspace.cosmos2ScriptLogStatus() end;return m')
                value = state()
                check_state(value)
                visible = native('return {opacity=openspace.propertyValue("Scene.C2EMCloudStream.Renderable.Opacity"),receiver_enabled=openspace.propertyValue("Scene.C2EMCloudStream.Renderable.Enabled"),selection_visible=openspace.propertyValue("Scene.C2EMCloudSelection.Renderable.Enabled")}')
                marks.append({'offset_s': time.perf_counter()-began, 'ram': ram.product_memory(), 'engine_gpu': metrics,
                              'state': value, 'independent_native_visibility': visible,
                              'host_observation': host_observation(),
                              'first_frame': max(0, int(metrics['capture_samples'])-1) if part else 0})
                remaining = began+(part+1)*20-time.perf_counter()
                if remaining > 0:
                    time.sleep(remaining)
            captured = native('return openspace.cosmos2EndFrameCapture()')
            capture_end, wall = datetime.now(timezone.utc), time.perf_counter()-began
            final = state()
            check_state(final)
            host_final = host_observation()
            record = {'run': run, 'capture_start_utc': capture_start.isoformat(), 'capture_end_utc': capture_end.isoformat(),
                      'wall_interval_s': wall, 'capture': captured, 'initial': initial, 'final': final, 'memory': marks,
                      'host_initial':host_initial,'host_final':host_final,
                      'expected_cloud_visible': cloud_visible, 'expected_magnetic_visible': magnetic_visible,
                      'gpu_report': str(gpu_path.relative_to(ROOT)), 'frozen_field_map': frozen}
            report['pending_collection'] = record
            persist()
            # Counter sampling and final process inventory run independently of
            # the60s frame window. Keep all samples; bound and expose finalization.
            deadline = time.monotonic()+90
            while True:
                try:
                    output = gpu_job.communicate(timeout=5)[0]
                    break
                except subprocess.TimeoutExpired:
                    print(json.dumps({'phase': 'resource_finalization', 'run': run,
                                      'collector_pid': gpu_job.pid}), flush=True)
                    if time.monotonic() >= deadline:
                        raise TimeoutError('GPU collector finalization exceeded90s; raw journal preserved')
            assert gpu_job.returncode == 0, output
            gpu_job = None
            gpu = json.loads(gpu_path.read_text(encoding='utf-8-sig'))
            stamps = [datetime.fromisoformat(s['utc'].replace('Z', '+00:00')) for s in gpu['samples']]
            assert len(stamps) == 66 and stamps[0] <= capture_start and stamps[-1] >= capture_end
            record['raw_capture_samples_s'] = captured['samples_s']
            values = np.array(captured['samples_s'][1:])
            assert captured['width'] == 1920 and captured['height'] == 1080 and not captured['capacity_reached'] and captured['invalid_samples'] == 0
            assert abs(float(values.sum())-60) < .5 and abs(wall-60) < .5
            command('pause')
            endpoint_name = name+'-'+str(run)
            command('save', file=endpoint_name)
            endpoint = storage/(endpoint_name+'.json')
            s, p, d, a = load(endpoint)
            paused = state()
            assert paused['native']['confirmation']['metadata']['payload_sha256'] == hashlib.sha256(p._x).hexdigest()
            record.update(frame_times_s=values.tolist(), observed_model_s_per_wall_s=(final['state']['time_s']-initial['state']['time_s'])/wall,
                          statistics={'frames': len(values), 'median_ms': float(np.median(values)*1000),
                                      'p95_ms': float(np.quantile(values, .95)*1000), 'p99_ms': float(np.quantile(values, .99)*1000),
                                      'over100ms': int(np.sum(values > .1))},
                          gpu_sha256=hashlib.sha256(gpu_path.read_bytes()).hexdigest(), resource_window_covered=True,
                          endpoint_checkpoint=str(endpoint.relative_to(ROOT)), endpoint_sha256=hashlib.sha256(endpoint.read_bytes()).hexdigest(),
                          paused_endpoint=paused)
            captured.pop('samples_s')
            configuration.append(endpoint)
            report['configuration_sha256'][str(endpoint.relative_to(ROOT)).replace('\\', '/')] = record['endpoint_sha256']
            report['runs'].append(record)
            report.pop('pending_collection')
            persist()
            print(json.dumps({'run': run, 'rate': record['observed_model_s_per_wall_s'], **record['statistics']}), flush=True)
        report['pause_latency_samples'] = []
        for _ in range(20):
            command('resume')
            time.sleep(.12)
            began = time.perf_counter()
            response = command('pause')
            elapsed = (time.perf_counter()-began)*1000
            current = state()
            assert current['state']['time_s'] == current['native']['confirmation']['metadata']['time_s']
            report['pause_latency_samples'].append({'wall_ms': elapsed, 'worker_elapsed_ms': response['elapsed_ms']})
        assert owner.read_bytes() == original
        assert app_hashes == {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (ROOT/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        archive = ROOT/f'evidence/native-emcloud-{args.label}-source.tar.gz'
        assert not archive.exists()
        with tarfile.open(archive, 'w:gz') as tar:
            for path, digest in sorted(report['configuration_sha256'].items()):
                data = (ROOT/path).read_bytes()
                assert hashlib.sha256(data).hexdigest() == digest, path
                member = tarfile.TarInfo(path)
                member.size = len(data)
                tar.addfile(member, io.BytesIO(data))
        report.update(completed=True, owner_pointer_preserved=True, installed_product_files_preserved=len(app_hashes),
                      frozen_source_archive={'path': str(archive.relative_to(ROOT)), 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()})
        persist()
except BaseException as error:
    report['error'] = type(error).__name__+': '+str(error)
    persist()
    raise
finally:
    if gpu_job is not None:
        if gpu_job.poll() is None:
            gpu_job.terminate()
        gpu_job.communicate(timeout=5)
    try:
        command('pause')
        with Page() as page:
            page.goto('http://127.0.0.1:4700/')
    finally:
        socket.close()
print(json.dumps({'report': str(destination), 'completed': report['completed']}), flush=True)
