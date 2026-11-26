"""Bounded K5 diagnostic with native stage and CEF timings."""
import argparse
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
import hashlib
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

from is6_owned_profile_host import Host

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts'
CANDIDATE = 'output/is6-layers-product0.21.1'
LAUNCHER = 'scripts/launch-is6-layers-import-candidate-v3.py'
OBSERVE_CEF = """(() => {
    const rows = [];
    let dropped = 0;
    if (!PerformanceObserver.supportedEntryTypes.includes('longtask')) return false;
    function collect(entries) {
        for (const entry of entries) {
            if (rows.length === 512) {
                dropped += 1;
                continue;
            }
            rows.push({
                utc_ms: performance.timeOrigin + entry.startTime,
                duration_ms: entry.duration
            });
        }
    }
    const observer = new PerformanceObserver(list => collect(list.getEntries()));
    observer.observe({type: 'longtask'});
    window.cosmos2HitchTasks = () => {
        collect(observer.takeRecords());
        const result = {rows: rows.splice(0), dropped};
        dropped = 0;
        return result;
    };
    return true;
})()"""


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def utc():
    return datetime.now(timezone.utc).isoformat()


def checkpoint_records():
    folder = ROOT / CANDIDATE / 'layer-checkpoints'
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(folder.rglob('*.json'))}


def write(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n',
                    encoding='utf8')
    temp.replace(path)


@contextmanager
def collect_gpu(label, folder, session, *, samples=66):
    report = ROOT / 'evidence' / f'gpu-pdh-{label}.json'
    ready = ROOT / 'output' / f'gpu-memory-ready-{label}.json'
    if report.exists() or ready.exists():
        raise FileExistsError(label)
    with (folder / f'{label}.log').open('xb') as log:
        with subprocess.Popen(
            [sys.executable, '-Xutf8', str(SCRIPT / 'collect_gpu_pdh_v3.py'), '--label',
             label, '--samples', str(samples), '--expected-mode', 'experiment',
             '--expected-worker', 'paused', '--signal-ready'],
            stdout=log, stderr=subprocess.STDOUT
        ) as process:
            try:
                deadline = time.monotonic() + 30
                while not ready.is_file():
                    if process.poll() is not None:
                        raise RuntimeError(f'PDH exited before readiness: {label}')
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f'PDH readiness: {label}')
                    time.sleep(.05)
                signal = read(ready)
                if signal['engine_pid'] != session['app'] or signal['label'] != label:
                    raise ValueError('Unexpected collector readiness identity')
                yield report
                if process.wait(timeout=30) != 0:
                    raise RuntimeError(f'PDH collection failed: {label}')
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=10)


def layer_requests(events):
    """Use CDP clock pairs, keeping only timing data for the layer state route."""
    requests = {}
    for event in events:
        method = event.get('method')
        params = event.get('params', {})
        request_id = params.get('requestId')
        if method == 'Network.requestWillBeSent':
            if params['request']['url'] == 'http://127.0.0.1:4700/api/layers/state':
                requests[request_id] = {
                    'utc_ms': params['wallTime'] * 1000, 'request_timestamp': params['timestamp']
                }
        elif method in ('Network.loadingFinished', 'Network.loadingFailed') and request_id in requests:
            row = requests[request_id]
            row['duration_ms'] = (params['timestamp'] - row['request_timestamp']) * 1000
            row['finished'] = method == 'Network.loadingFinished'
    return [{k: v for k, v in row.items() if k != 'request_timestamp'} for row in requests.values()]


def capture(k5, page, row, initial, phase, session, seconds):
    h, support = k5.h, k5.support
    get_state = lambda: h.get('/api/layers/state')
    page.evaluate('window.cosmos2HitchTasks()')
    event_start = len(page.events)
    row['begin_request_utc'] = utc()
    h.native('openspace.cosmos2BeginStageTrace();'
             'openspace.cosmos2BeginFrameCapture(12000);return {ready=true}')
    row['capture_start_utc'] = utc()
    began = time.perf_counter()
    for offset in range(0, seconds + 1, 20):
        time.sleep(max(0, began + offset - time.perf_counter()))
        state = get_state()
        flags = h.native(support.flag_script(k5.lua, initial['scene']))
        following = get_state()
        for snapshot in (state, following):
            support.confirm_response(snapshot, initial['artifact']['id'], initial['artifact']['sha256'],
                                     {'spatial': True, 'magnetic': True})
            assert snapshot['guard'] == initial['guard']
        support.verify_flags(flags, initial['scene'], {'spatial': True, 'magnetic': True})
        physics = h.get('/api/state')['physics']
        assert physics['paused'] and support.phase_fields(physics) == support.phase_fields(phase)
        ui = page.evaluate("""({
            guard: layerInstrument.snapshot.guard, error: layerInstrument.error,
            visible: document.visibilityState, scale: document.getElementById('ui-scale').value,
            panel: !document.getElementById('layers-panel').hidden
        })""")
        assert ui['guard'] == initial['guard'] and ui['scale'] == '1' and ui['panel'] and not ui['error']
        view = k5.context(phase)
        ram = k5.product_memory(session)
        engine = h.native('return openspace.cosmos2MemoryMetrics()')
        row['checks'].append(dict(offset_s=time.perf_counter()-began, view=view, flags=flags, ui=ui,
                                  ram_bytes=ram['sum_working_set_bytes'], engine=engine))
    row['end_request_utc'] = utc()
    row.update(h.native('local trace=openspace.cosmos2EndStageTrace();'
                        'return {trace=trace,capture=openspace.cosmos2EndFrameCapture()}'))
    row['capture_end_utc'] = utc()
    row['wall_interval_s'] = time.perf_counter() - began
    row['cef_longtasks'] = page.evaluate('window.cosmos2HitchTasks()')
    row['cef_layer_state_requests'] = layer_requests(page.events[event_start:])
    raw = row['capture']
    assert (raw['width'], raw['height']) == (1920, 1080)
    assert not raw['invalid_samples'] and not raw['capacity_reached'] and raw['samples_s']
    assert not row['trace']['truncated'] and not row['cef_longtasks']['dropped']


def exercise(k5, plan, result, report, folder):
    from gpu_pdh_audit_v3 import audit
    from windows_gpu_pdh_v2 import generation

    h, support = k5.h, k5.support
    session = result['session']
    with k5.Page() as page:
        page.on('pageerror', result['page_errors'].append)
        page.goto(h.test.BASE + '/')
        page.wait_for_function('appState&&atlasState&&layerInstrument.snapshot&&!pending')
        k5.click(page, '#open-layers')
        k5.click(page, '#layers-copy')
        page.wait_for_function('appState.physics?.bodies.length===4&&!pending', timeout=70000)
        page.locator('#ui-scale').select_option('1')
        assert page.evaluate(OBSERVE_CEF)
        phase = h.get('/api/state')['physics']
        observations = []
        result['preparation'] = k5.stabilize(lambda: k5.gpu_collector.inventory(session),
                                              observations.append)
        result['preparation']['observations'] = observations
        with collect_gpu(f'is6k5diag-{plan["label"]}-pre', folder, session, samples=3) as preflight:
            pass
        result['paused_GPU_preflight'] = dict(
            path=preflight.relative_to(ROOT).as_posix(), sha256=sha(preflight),
            audit=audit(read(preflight), expected_samples=3, expected_session=session,
                        engine_sha256=plan['engine_sha256'], generation=generation())
        )
        initial = None
        for spec in plan['windows']:
            reference = 'sol:naif:' + spec['body']
            if initial is None or initial['artifact']['source']['body_reference_id'] != reference:
                if initial is not None:
                    page.evaluate('document.body.inert=false')
                    k5.click(page, '#layers-leave')
                settings = support.settings(phase, reference)
                page.locator('#layers-body').select_option(settings['body_id'])
                k5.click(page, '#layers-create')
                initial = h.get('/api/layers/state')
                assert initial['checkpoint_available'] and len(initial['branches']) == 5
                assert sum(b['valid'] and b.get('origin') is not None for b in initial['branches']) >= 1
                data = h.post('/api/layers/command', dict(command='get_artifact', guard=initial['guard']))
                digest = support.verify_scientific(k5.contract, data['result']['scientific'], phase, reference)
                support.confirm_response(initial, initial['artifact']['id'], digest,
                                         {'spatial': True, 'magnetic': True})
            page.evaluate('document.getElementById("layers-panel").scrollTop=0;document.body.inert=true')
            row = dict(spec, guard=initial['guard'], scene=initial['scene'], checks=[])
            result['runs'].append(row)
            write(report, result)
            print(json.dumps(dict(stage='warmup', **spec)), flush=True)
            time.sleep(plan['warmup_s'])
            label = f'is6k5diag-{plan["label"]}-{spec["id"]}'
            collector = collect_gpu(label, folder, session) if spec['pdh'] else nullcontext()
            with collector as gpu:
                print(json.dumps(dict(stage='capture', **spec)), flush=True)
                capture(k5, page, row, initial, phase, session, plan['window_s'])
            if gpu:
                row['gpu'] = dict(path=gpu.relative_to(ROOT).as_posix(), sha256=sha(gpu))
                row['gpu']['audit'] = audit(
                    read(gpu), expected_samples=66, expected_session=session,
                    engine_sha256=plan['engine_sha256'], generation=generation(),
                    coverage=[row['capture_start_utc'], row['capture_end_utc']]
                )
            write(report, result)
        page.evaluate('document.body.inert=false')
        k5.click(page, '#layers-leave')
        assert not result['page_errors']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or len(args.label) > 20 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    label = args.label
    plan_path = ROOT / 'evidence' / f'is6-k5-hitch-plan-{label}.json'
    report = ROOT / 'evidence' / f'is6-k5-hitch-native-{label}.json'
    folder = ROOT / 'output' / f'is6-k5-hitch-native-{label}'
    if folder.exists() or report.exists():
        raise FileExistsError('Preserve diagnostic evidence')
    plan = read(plan_path)
    assert plan['label'] == label and plan['warmup_s'] == 30 and plan['window_s'] == 60
    assert [(w['body'], w['pdh']) for w in plan['windows']] == [('399', True), ('599', True), ('599', False)]
    before = checkpoint_records()
    engine = ROOT / '.runtime-is4-stream/bin/OpenSpace.exe'
    source_paths = plan['source_sha256']
    assert before == plan['checkpoints'] and sha(engine) == plan['engine_sha256']
    assert all(sha(ROOT / name) == seal for name, seal in source_paths.items())
    owner, shortcut = ROOT / 'user/sessions/latest.json', ROOT / 'Iniciar-Cosmos2.cmd'
    assert sha(owner) == plan['owner_sha256'] and sha(shortcut) == plan['shortcut_sha256']
    protected = {p: sha(p) for p in (owner, shortcut)}
    folder.mkdir()
    k5 = SourceFileLoader('k5_hitch_reference', str(SCRIPT / 'benchmark-is6-layers-import-native-v4.py')).load_module()
    result = dict(plan=plan_path.relative_to(ROOT).as_posix(), plan_sha256=sha(plan_path),
                  completed=False, runs=[], page_errors=[], scope='instrumented diagnostic')
    host = Host(folder, k5.h, candidate=CANDIDATE, launcher=LAUNCHER)
    try:
        result['session'] = host.start()
        exercise(k5, plan, result, report, folder)
        result['completed'] = True
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        try:
            result['processes'] = host.close()
            assert set(result['processes'].values()) == {0} and len(result['processes']) == 4
            result['checkpoints_unchanged'] = checkpoint_records() == before
            result['protected_unchanged'] = all(sha(p) == seal for p, seal in protected.items())
            assert result['checkpoints_unchanged'] and result['protected_unchanged']
            assert sha(engine) == plan['engine_sha256']
            assert all(sha(ROOT / name) == seal for name, seal in source_paths.items())
        except Exception:
            result['cleanup_failure'] = traceback.format_exc()
            result['completed'] = False
        write(report, result)
    print(json.dumps(dict(completed=result['completed'], runs=len(result['runs']),
                          failure=result.get('failure'), cleanup_failure=result.get('cleanup_failure'))),
          flush=True)
    return 0 if result['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
