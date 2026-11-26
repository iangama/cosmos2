"""Four sealed C2-14 CEF animation windows with continuous native process gauges."""
import argparse
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
import c214_profile_contract as c
import collect_c214_orbits_residency_v3 as collector
from windows_shared_json_v2 import read_json

ROOT = Path(__file__).resolve().parents[1]
h = SourceFileLoader('c214_profile_native', str(ROOT/'scripts/benchmark-body-points-native.py')).load_module()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: dt.datetime.now(dt.timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--plan-label', required=True)
    args = parser.parse_args()
    for label in [args.label, args.plan_label]:
        c.require(label and len(label) <= 20 and all(ch in 'abcdefghijklmnopqrstuvwxyz0123456789-' for ch in label), 'Invalid label')
    plan_path = ROOT/f'evidence/c214-orbits-profile-plan-{args.plan_label}.json'
    plan = json.loads(plan_path.read_text())
    c.require(plan['accepted'] and plan['windows'] == c.WINDOWS and plan['limits'] == c.LIMITS, 'Unsealed profile plan')
    sources = plan['source_sha256'] | {plan_path.relative_to(ROOT).as_posix(): sha(plan_path)}
    c.require(all(sha(ROOT/name) == seal for name, seal in sources.items()), 'Profile sources changed')
    folder = ROOT/f'output/c214-orbits-profile-{args.label}'
    out = ROOT/f'evidence/c214-orbits-profile-{args.label}.json'
    c.require(not folder.exists() and not out.exists(), 'Preserve previous profile')
    session = json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    c.require(Path(session['serverScript']).resolve() == ROOT/'output/c214-orbits-product0.28.2/app/server.py', 'Wrong candidate')
    c.require(sha(Path(session['runtime'])/'bin/OpenSpace.exe') == plan['engine_sha256'], 'Engine differs')
    folder.mkdir()
    archive_path = folder/'executed-sources.zip'
    with zipfile.ZipFile(archive_path, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name in sources:
            if name.startswith(('scripts/', 'output/c214-orbits-product0.28.2/app/', 'output/c214-orbits-product0.28.2/data/')) or name.startswith('C2-14-ORBITAS-PERFIL') or name == plan_path.relative_to(ROOT).as_posix():
                archive.write(ROOT/name, name)
    result = dict(completed=False, session=session, source_sha256=sources, engine_sha256=plan['engine_sha256'],
                  source_archive_sha256=sha(archive_path), source_archive_scope='Own candidate app/data and Python helpers; inherited lineage inputs referenced by SHA-256 and prior archives', plan=plan_path.relative_to(ROOT).as_posix(),
                  started_utc=now(), runs=[], page_errors=[])
    job = None
    tracing = False
    serial = 0

    def persist():
        collector.atomic(out, result)

    def status():
        c.require(job.poll() is None, 'Collector exited early')
        path = folder/'collector-status.json'
        if not path.exists():
            return {}
        value = read_json(path)
        c.require(value['valid'], value.get('failure', 'Collector invalid'))
        return value

    def wait_samples(control, count):
        deadline = time.monotonic()+count+20
        while True:
            value = status()
            if value.get('acknowledged_id') == control['id'] and value['phase_samples'] >= count:
                return value
            c.require(time.monotonic() < deadline, 'Collector acknowledgement deadline')
            time.sleep(.05)

    def control(kind, recipe=None, expected=None):
        nonlocal serial
        serial += 1
        value = dict(schema=1, id=f'{serial:03d}-{kind}', kind=kind,
                     window=recipe['name'] if recipe else None, recipe=recipe, expected_scenario=expected)
        collector.atomic(folder/'control.json', value)
        if job is not None:
            wait_samples(value, 1)
        return value

    def begin():
        nonlocal tracing
        h.native('openspace.cosmos2BeginStageTrace();openspace.cosmos2BeginFrameCapture(120000);return {ready=true}')
        tracing = True
        return dict(capture_start_utc=now(), began=time.perf_counter())

    def end(row):
        nonlocal tracing
        native = h.native('return {trace=openspace.cosmos2EndStageTrace(),capture=openspace.cosmos2EndFrameCapture()}')
        row.update(capture_end_utc=now(), wall_interval_s=time.perf_counter()-row.pop('began'), **native)
        tracing = False

    def until(deadline):
        while time.perf_counter() < deadline:
            status()
            time.sleep(min(.1, max(0, deadline-time.perf_counter())))

    persist()
    try:
        with Page() as page:
            page.on('pageerror', lambda error: result['page_errors'].append(error))
            page.goto('http://127.0.0.1:4700/')
            page.wait_for_function('appState?.mode==="atlas"&&!pending', timeout=60000)
            page.evaluate('(async()=>{await navigate("clock",{paused:true,rate:1});await navigate("viewpoint",{target:"Earth",preset:"overview"});selectTarget("Earth",true);})()')
            page.wait_for_function('!pending&&navigationState?.navigation?.Anchor==="Earth"', timeout=30000)
            page.goto('http://127.0.0.1:4700/forces.html#timelike-orbits')
            page.wait_for_function('!pending&&response?.result.timelike', timeout=30000)
            for recipe in c.WINDOWS:
                if job is not None:
                    control('transition')
                cfg = dict(scenario='timelike-orbits', parameters=c.PARAMETERS | dict(orbit_kind=recipe['orbit_kind']),
                           controls=dict(gravity=dict(acting=True, visible=True,
                              effects=dict(orbital_acceleration=recipe['orbit'], proper_clock_rate=True))))
                page.evaluate('(async()=>{config='+json.dumps(cfg)+';buildControls();buildParameters();await calculate();})()')
                page.wait_for_function('!pending&&response?.result.timelike&&!byId("force-status").classList.contains("error")')
                page.locator('#timelike-view').select_option(recipe['view'])
                page.evaluate('document.body.style.zoom=1;window.scrollTo(0,0);document.querySelector("article").scrollTop=0;document.body.inert=true')
                if not page.evaluate('Boolean(window.__c214Profile)'):
                    page.evaluate(c.ANIMATION_EXPRESSION)
                    page.wait_for_function('window.__c214Profile.advances>2')
                reference, worker = collector.http_object(folder)
                expected = c.service(worker, reference['sha256'])
                c.admit_service(expected, recipe)
                c.admit_ui(page.evaluate(c.UI_EXPRESSION), expected, recipe, worker['result']['result'])
                if job is None:
                    preparation = control('prepare', recipe, expected)
                    with (folder/'collector.log').open('xb') as stream:
                        job = subprocess.Popen([sys.executable, '-u', '-Xutf8', str(ROOT/'scripts/collect_c214_orbits_residency_v3.py'),
                                                '--label', args.label, '--folder', str(folder), '--max-samples', '900'],
                                               cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT)
                    wait_samples(preparation, 2)
                warm_control = control('warmup', recipe, expected)
                warmup = dict(control=warm_control, **begin())
                print(json.dumps(dict(stage='warmup', window=recipe['name'])), flush=True)
                until(warmup['began']+30)
                end(warmup)
                stable = control('stable', recipe, expected)
                wait_samples(stable, 3)
                run = dict(recipe=recipe, warmup=warmup, stable_control=stable, samples=[], **begin())
                result['pending_run'] = run
                persist()
                print(json.dumps(dict(stage='capture', window=recipe['name'])), flush=True)
                for part in range(4):
                    until(run['began']+20*part)
                    native = h.native('return {camera=openspace.navigation.getNavigationState(),memory=openspace.cosmos2MemoryMetrics()}')
                    witness = dict(offset_s=time.perf_counter()-run['began'], native=native, ui=page.evaluate(c.UI_EXPRESSION))
                    c.admit_ui(witness['ui'], expected, recipe, worker['result']['result'])
                    run['samples'].append(witness)
                end(run)
                wait_samples(stable, 66)
                result['runs'].append(run)
                result.pop('pending_run')
                persist()
            control('cleanup')
            page.evaluate('window.__c214Profile.enabled=false;animating=false;document.body.inert=false')
            collector.atomic(folder/'stop.json', dict(reason='c214_windows_complete'))
            result['collector_exit'] = job.wait(timeout=30)
            c.require(job.returncode == 0, 'Collector refused C2-14')
            job = None
            result['completed'] = True
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        if tracing:
            try:
                result['interrupted_capture'] = dict(began=time.perf_counter(), capture_start_utc=now())
                end(result['interrupted_capture'])
            except Exception:
                result['interrupted_capture_failure'] = traceback.format_exc()
        if job is not None:
            try:
                collector.atomic(folder/'stop.json', dict(reason='executor_failure'))
                result['collector_exit'] = job.wait(timeout=30)
            except Exception:
                result['collector_stop_failure'] = traceback.format_exc()
        try:
            with Page() as page:
                page.evaluate('if(window.__c214Profile)window.__c214Profile.enabled=false;document.body.inert=false')
            c.require(all(sha(ROOT/name) == seal for name, seal in sources.items()), 'Profile sources/protected changed')
        except Exception:
            result['cleanup_failure'] = traceback.format_exc()
            result['completed'] = False
        result['finished_utc'] = now()
        persist()
    print(json.dumps(dict(completed=result['completed'], failure=result.get('failure'), cleanup_failure=result.get('cleanup_failure'))), flush=True)
    return 0 if result['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
