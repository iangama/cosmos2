"""Seal or execute one bounded nine-destination Atlas profile on the visible app."""
import argparse
from contextlib import contextmanager
import datetime as dt
import hashlib
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
import zipfile

from cef_page_v2 import Page
from native_product_memory_v2 import product_memory
from owned_process_preparation import stabilize
from owned_process_snapshot import snapshot
from gpu_pdh_audit_v3 import audit
from windows_gpu_pdh_v2 import generation

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is6-planet-navigation-product0.24.0/app'
h = SourceFileLoader('navigation_profile_helpers', str(ROOT / 'scripts/benchmark-body-points-native.py')).load_module()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
utc = lambda: dt.datetime.now(dt.timezone.utc).isoformat()
TARGETS = ['Mercury', 'Venus', 'Earth', 'Moon', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune']
LIMITS = dict(median_ms=16.7, p95_ms=25., p99_ms=50., over_100ms=0,
              RAM_bytes=8*2**30, GPU_bytes=5.5*2**30)


def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    temp.replace(path)


def prepare(label):
    out = ROOT / f'evidence/is6-planet-navigation-profile-plan-{label}.json'
    folder = ROOT / f'output/is6-planet-navigation-profile-plan-{label}'
    if out.exists() or folder.exists(): raise FileExistsError('Preserve profile plan')
    manifest = read(APP.parent / 'build-manifest.json')
    assert manifest['candidate'] == '0.24.0' and not manifest['promoted']
    native = ROOT / 'evidence/is6-planet-navigation-native-20261111d.json'
    visual = ROOT / 'evidence/is6-planet-navigation-visual-20261111a.json'
    assert read(native)['functional_accepted'] and read(visual)['accepted']
    sources = dict(manifest['source_sha256'])
    for name, seal in manifest['files_sha256'].items():
        sources[(APP / name).relative_to(ROOT).as_posix()] = seal
    files = [Path(__file__), native, visual, APP.parent / 'build-manifest.json',
             ROOT / 'IS-6-NAVEGACAO-PERFIL-CONTRATO.md',
             *[ROOT / 'scripts' / name for name in ['audit-is6-planet-navigation-profile.py',
               'cef_page_v2.py', 'benchmark-body-points-native.py', 'native_product_memory_v2.py',
               'owned_process_preparation.py', 'owned_process_snapshot.py',
               'collect_gpu_pdh_v3.py', 'gpu_pdh_audit_v3.py', 'gpu_pdh_audit_v2.py',
               'windows_gpu_pdh_v2.py', 'is6_pair_profile_support.py']]]
    for p in files: sources[p.relative_to(ROOT).as_posix()] = sha(p)
    assert all(sha(ROOT / name) == seal for name, seal in sources.items())
    folder.mkdir()
    archive = folder / 'sealed-sources.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in sorted(sources): z.write(ROOT / name, name)
    plan = dict(prepared=True, candidate='0.24.0', label=label, performance_accepted=False,
                source_sha256=sources, source_archive=archive.relative_to(ROOT).as_posix(),
                source_archive_sha256=sha(archive), engine_sha256=sha(ROOT / '.runtime-is4-stream/bin/OpenSpace.exe'),
                targets=TARGETS, utc='2026-10-11T12:00:00Z', exposure=3.7, stars=True, paused=True,
                viewpoint='overview', resolution=[1920,1080], ui_scale='1', warmup_s=30,
                window_s=60, GPU_samples=66, preflight_samples=3, limits_before_execution=LIMITS,
                scope='One cached static overview per destination; attached app remains open. Own profile only, no cold startup, K5 transfer, promotion or complete IS6 acceptance.')
    write(out, plan)
    print(json.dumps(dict(prepared=True, targets=len(TARGETS), sources=len(sources), plan=out.name)), flush=True)


@contextmanager
def gpu_collection(label, folder, session, samples):
    out = ROOT / f'evidence/gpu-pdh-{label}.json'
    ready = ROOT / f'output/gpu-memory-ready-{label}.json'
    if out.exists() or ready.exists(): raise FileExistsError('Preserve PDH window')
    with (folder / (label + '.log')).open('xb') as log:
        with subprocess.Popen([sys.executable, '-Xutf8', str(ROOT / 'scripts/collect_gpu_pdh_v3.py'),
                '--label', label, '--samples', str(samples), '--expected-mode', 'atlas',
                '--expected-worker', 'any', '--signal-ready'], stdout=log, stderr=subprocess.STDOUT) as process:
            try:
                deadline = time.monotonic() + 30
                while not ready.exists():
                    if process.poll() is not None: raise RuntimeError('PDH preflight did not start: ' + label)
                    if time.monotonic() >= deadline: raise TimeoutError('PDH readiness')
                    time.sleep(.05)
                signal = read(ready)
                assert signal['engine_pid'] == session['app'] and signal['label'] == label
                yield out
                if process.wait(timeout=30) != 0: raise RuntimeError('PDH collection refused: ' + label)
            finally:
                if process.poll() is None: process.terminate(); process.wait(timeout=10)


def execute(label):
    plan_path = ROOT / f'evidence/is6-planet-navigation-profile-plan-{label}.json'
    plan = read(plan_path)
    assert plan['prepared'] and plan['targets'] == TARGETS and plan['limits_before_execution'] == LIMITS
    assert all(sha(ROOT / name) == seal for name, seal in plan['source_sha256'].items())
    folder = ROOT / f'output/is6-planet-navigation-profile-{label}'
    out = ROOT / f'evidence/is6-planet-navigation-profile-{label}.json'
    if folder.exists() or out.exists(): raise FileExistsError('Preserve executed profile')
    folder.mkdir()
    session = read(ROOT / 'output/session.json')
    assert Path(session['serverScript']).resolve() == APP / 'server.py'
    assert h.get('/api/state')['mode'] == 'atlas'
    protected = {name:sha(ROOT / name) for name in ['user/sessions/latest.json', 'Iniciar-Cosmos2.cmd']}
    report = dict(completed=False, collection_completed=False, accepted=False, runs=[], page_errors=[],
                  started_utc=utc(), session=session, plan_path=plan_path.relative_to(ROOT).as_posix(),
                  plan_sha256=sha(plan_path), engine_sha256=plan['engine_sha256'], protected_sha256=protected,
                  scope=plan['scope'])
    original_id = None
    previous_scale = '1'
    persist = lambda: write(out, report)
    nav = lambda action, **payload: h.post('/api/navigation/' + action, payload)['navigation']
    persist()
    try:
        report['original_navigation'] = h.get('/api/navigation/state')
        before = h.get('/api/navigation/favorites')['views']
        saved = nav('save', name='Perfil temporário · vista inicial')['views']
        original_id = next(r['id'] for r in saved if r['id'] not in {b['id'] for b in before})
        observations = []
        report['preparation'] = stabilize(lambda: snapshot(session)['owned'], observations.append)
        report['preparation']['observations'] = observations
        with Page() as page:
            page.on('pageerror', report['page_errors'].append)
            page.goto('http://127.0.0.1:4700/')
            page.wait_for_function('appState?.mode==="atlas"&&atlasState&&navigationState&&!pending')
            previous_scale = page.evaluate('$("ui-scale").value')
            page.locator('#ui-scale').select_option('1')
            h.post('/api/atlas/epoch', {'utc':plan['utc']})
            nav('display', exposure=plan['exposure'], stars=plan['stars'])
            page.evaluate('document.body.inert=true')
            with gpu_collection('is6nav-' + label + '-pre', folder, session, 3) as pre:
                pass
            report['preflight'] = dict(path=pre.relative_to(ROOT).as_posix(), sha256=sha(pre),
                audit=audit(read(pre), expected_samples=3, expected_session=session,
                            engine_sha256=plan['engine_sha256'], generation=generation()))
            persist()
            for index, target in enumerate(plan['targets'],1):
                initial = nav('viewpoint', target=target, preset=plan['viewpoint'])
                page.evaluate('selectTarget(' + json.dumps(target) + ',true);$("atlas-details").scrollTop=0;$("atlas-panel").scrollTop=0')
                row = dict(index=index, target=target, initial_navigation=initial, checks=[], warmup_start_utc=utc())
                report['runs'].append(row); persist()
                print(json.dumps(dict(stage='warmup', index=index, target=target, seconds=30)), flush=True)
                time.sleep(plan['warmup_s'])
                with gpu_collection('is6nav-' + label + '-' + str(index), folder, session, 66) as gpu:
                    h.native('openspace.cosmos2BeginStageTrace();openspace.cosmos2BeginFrameCapture(12000);return {ready=true}')
                    row['capture_start_utc'] = utc(); began = time.perf_counter()
                    print(json.dumps(dict(stage='capture', index=index, target=target, seconds=60)), flush=True)
                    for offset in [0,20,40,60]:
                        time.sleep(max(0,began+offset-time.perf_counter()))
                        state = h.get('/api/navigation/state')
                        assert state['paused'] and state['et'] == initial['et'] and state['navigation']['Anchor'] == target and not state['flying']
                        display = h.get('/api/navigation/display')
                        assert abs(display['exposure']-plan['exposure'])<1e-6 and display['stars'] is True
                        ui = page.evaluate('({scale:$("ui-scale").value,target:selectedTarget,mode:appState.mode,visible:document.visibilityState,inert:document.body.inert})')
                        assert ui == dict(scale='1',target=target,mode='atlas',visible='visible',inert=True), ui
                        row['checks'].append(dict(offset_s=time.perf_counter()-began, navigation=state,
                                                  ui=ui, display=display, ram=product_memory(session),
                                                  engine=h.native('return openspace.cosmos2MemoryMetrics()')))
                        print(json.dumps(dict(stage='sample', index=index, target=target, offset=offset)), flush=True)
                    row.update(h.native('local trace=openspace.cosmos2EndStageTrace();return {trace=trace,capture=openspace.cosmos2EndFrameCapture()}'))
                    row['capture_end_utc'] = utc(); row['wall_interval_s'] = time.perf_counter()-began
                    persist()
                row['gpu'] = dict(path=gpu.relative_to(ROOT).as_posix(), sha256=sha(gpu))
                row['gpu']['audit'] = audit(read(gpu), expected_samples=66, expected_session=session,
                    engine_sha256=plan['engine_sha256'], generation=generation(),
                    coverage=[row['capture_start_utc'],row['capture_end_utc']])
                persist()
                print(json.dumps(dict(stage='window_saved', index=index, target=target)), flush=True)
            assert not report['page_errors'], report['page_errors']
            report['collection_completed'] = True
        report['completed'] = True
    except Exception:
        report['failure'] = traceback.format_exc()
    finally:
        try:
            h.native('openspace.cosmos2EndStageTrace();openspace.cosmos2EndFrameCapture();return {stopped=true}')
            if original_id:
                restored = nav('restore', id=original_id); nav('delete', id=original_id)
                report['restored_owner_view'] = restored
            with Page() as page:
                page.evaluate('document.body.inert=false')
                page.locator('#ui-scale').select_option(previous_scale)
                if original_id: page.evaluate('selectTarget(' + json.dumps(restored['target']) + ',true)')
            report['protected_unchanged'] = {name:sha(ROOT/name) == seal for name,seal in protected.items()}
            assert all(report['protected_unchanged'].values())
            report['owner_app_kept_open'] = h.get('/api/state')['mode'] == 'atlas'
        except Exception:
            report['cleanup_failure'] = traceback.format_exc(); report['completed'] = False
        persist()
    print(json.dumps(dict(completed=report['completed'], windows=len(report['runs']),
                          failure=report.get('failure'), cleanup_failure=report.get('cleanup_failure'))), flush=True)
    return 0 if report['completed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label',required=True)
    parser.add_argument('--prepare',action='store_true')
    args = parser.parse_args()
    if not args.label or len(args.label)>20 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label): parser.error('Invalid label')
    if args.prepare: prepare(args.label)
    else: raise SystemExit(execute(args.label))
