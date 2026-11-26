"""One continuous, sealed, ten-window native residence journey of candidate0.27.0."""
import argparse
import copy
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
import collect_expanded_residency_v2 as collector
import expanded_residency_contract_v2 as c
import expanded_residency_audit as audit

ROOT = Path(__file__).resolve().parents[1]
base = SourceFileLoader('expanded_residency_native_base', str(ROOT / 'scripts/verify-native-is6-expanded-journey.py')).load_module()
h = base.h
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
now = lambda: dt.datetime.now(dt.timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--plan-label', required=True)
    args = parser.parse_args()
    for label in [args.label, args.plan_label]:
        c.require(label and len(label) <= 20 and all(ch in 'abcdefghijklmnopqrstuvwxyz0123456789-' for ch in label), 'Invalid profile label')
    folder = ROOT / f'output/is6-expanded-residency-{args.label}'
    out = ROOT / f'evidence/is6-expanded-residency-{args.label}.json'
    c.require(not folder.exists() and not out.exists(), 'Preserve original profile')
    plan_path = ROOT / f'evidence/is6-expanded-residency-plan-{args.plan_label}.json'
    plan = json.loads(plan_path.read_text())
    c.require(plan['accepted'] and plan['windows'] == c.WINDOWS and plan['limits'] == c.LIMITS, 'Sealed plan differs')
    sources = plan['source_sha256'] | {plan_path.relative_to(ROOT).as_posix(): sha(plan_path)}
    c.require(all(sha(ROOT / name) == seal for name, seal in (sources | plan['protected_sha256']).items()), 'Plan/inputs changed')
    seed = json.loads((ROOT / plan['seed']).read_text())
    service = json.loads((ROOT / plan['service']).read_text())
    session = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
    c.require(Path(session['serverScript']).resolve() == base.APP / 'server.py' and session['is6ExpandedJourneyCandidate'], 'Own candidate required')
    c.require(sha(Path(session['runtime']) / 'bin/OpenSpace.exe') == plan['engine_sha256'], 'Engine executable differs')
    folder.mkdir()
    with zipfile.ZipFile(folder / 'executed-sources.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for name in sources:
            archive.write(ROOT / name, name)
    result = dict(completed=False, session=session, plan=plan_path.relative_to(ROOT).as_posix(), source_sha256=sources,
                  source_archive_sha256=sha(folder / 'executed-sources.zip'), protected_sha256=plan['protected_sha256'],
                  engine_sha256=plan['engine_sha256'], started_utc=now(), runs=[], transitions=[], cleanups=[], page_errors=[])
    job, page, active_context, live4, tracing = None, None, None, None, False
    serial = 0

    def persist():
        collector.atomic(out, result)

    def command(name, **fields):
        return h.post('/api/command', dict(command=name, **fields))

    def module(name):
        return h.get('/api/' + name + '/state')

    def phase():
        return h.get('/api/state')['physics']

    def status():
        if job.poll() is not None:
            raise RuntimeError('Continuous memory collector exited: ' + str(job.returncode))
        path = folder / 'collector-status.json'
        if not path.exists():
            return {}
        value = json.loads(path.read_text())
        c.require(value['valid'] is True, value.get('failure', 'Collector invalid'))
        return value

    def wait_samples(control, count):
        deadline = time.monotonic() + max(15, count + 8)
        while True:
            value = status()
            if value.get('acknowledged_id') == control['id'] and value['phase_samples'] >= count:
                return value
            if time.monotonic() > deadline:
                raise TimeoutError('Collector phase acknowledgement: ' + control['id'])
            time.sleep(.03)

    def control(kind, recipe=None, expected=None):
        nonlocal serial
        serial += 1
        value = dict(schema=1, id=f'{serial:03d}-{kind}', kind=kind, window=recipe['name'] if recipe else None,
                     recipe=recipe, expected_scenario=expected)
        collector.atomic(folder / 'control.json', value)
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
        row.update(capture_end_utc=now(), wall_interval_s=time.perf_counter() - row.pop('began'), **native)
        tracing = False
        return row

    def wait_ui(recipe):
        page.wait_for_function('appState?.mode===' + json.dumps(recipe['mode']) + '&&!pending', timeout=70000)
        if recipe['mode'] == 'experiment':
            page.wait_for_function('appState?.physics?.edit_token===' + json.dumps(phase()['edit_token']), timeout=15000)
        if recipe['instrument'] == 'particles':
            page.wait_for_function('particleState.active&&!particlePending&&particleState.worker.paused&&!particleState.view.pending_sequence&&particleState.worker.experiment.phase.time_s===particleState.view.confirmed_phase.time_s', timeout=30000)
        elif recipe['instrument'] == 'solar-zone':
            page.wait_for_function('solarZoneState.active&&!solarZonePending&&!solarZoneState.busy&&!solarZoneCurvePending&&solarZoneCurveId===solarZoneState.worker.artifact_id', timeout=750000)

    def present(recipe):
        for name in ['spatial', 'layers']:
            page.evaluate('document.getElementById(' + json.dumps(name + '-panel') + ').hidden=true')
        instrument = recipe['instrument']
        focus = {'spatial': 'spatial-title', 'layers': 'layers-spatial-reading', 'particles': 'particle-title', 'solar-zone': 'zone-probe'}.get(instrument, 'solar-body')
        if instrument in ['spatial', 'layers']:
            page.evaluate('document.getElementById(' + json.dumps('open-' + instrument) + ').click()')
        if recipe['mode'] == 'atlas':
            page.evaluate('selectTarget("Earth",true)')
        else:
            page.evaluate('(()=>{const e=document.getElementById(' + json.dumps(focus) + ');if(e.closest("#lab-panel")&&getComputedStyle($("lab-panel")).display==="none"&&document.body.classList.contains("details-open"))$("panel-toggle").click();for(let p=e.parentElement;p;p=p.parentElement)if(p.tagName==="DETAILS")p.open=true;e.scrollIntoView({block:"start"});})()')
        page.locator('#ui-scale').select_option('1')
        page.evaluate('document.body.inert=true')

    def leave():
        nonlocal active_context
        for name in ['spatial', 'layers', 'particles', 'solar-zone']:
            value = module(name)
            if not value['active']:
                continue
            if name == 'spatial':
                nodes = [value['scene'][key] for key in ['frame', 'wire', 'focus']]
                request = dict(command='leave', guard=value['guard'])
            elif name == 'layers':
                scene = value['scene']
                nodes = [scene['spatial_frame'], scene['spatial_wire'], scene['spatial_frame'].replace('SpatialFrame_', 'SpatialFocus_'),
                         scene['magnetic_frame'], *scene['magnetic_nodes'], *[scene['magnetic_frame'] + suffix for suffix in ['_basis', '_probe', '_display_probe']]]
                request = dict(command='leave', guard=value['guard'])
            elif name == 'particles':
                nodes = list(value['view']['native_nodes'].values())
                request = dict(command='leave')
            else:
                nodes = [value['scene'][key] for key in ['node', 'label_node']]
                request = dict(command='leave', guard=base.SolarClient.guard(value['worker']))
            base.post('/api/' + name + '/command', request)
            exists = h.native('local r={};for _,n in ipairs(' + base.lua(list(dict.fromkeys(nodes))) + ') do r[n]=openspace.hasSceneGraphNode(n) end;return r')
            c.require(exists and not any(exists.values()), 'Old instrument scene survived')
            c.require(c.physical(phase()) == result['common4'], 'Instrument mutated live4')
            after = base.context(live4)
            base.same_context(active_context, after)
            result['cleanups'].append(dict(instrument=name, nodes=exists, before=active_context, after=after))
            active_context = None

    def enter(recipe):
        nonlocal live4, active_context
        leave()
        name = recipe['name']
        if name == 'atlas_earth':
            h.post('/api/atlas/epoch', dict(utc=service['recipe_before_execution']['utc']))
            h.post('/api/navigation/viewpoint', dict(target='Earth', preset='overview'))
        elif name == 'sixteen_system':
            h.post('/api/dynamics16/experiment', dict(utc=service['recipe_before_execution']['utc']))
            command('load')
            wait_ui(recipe)
            page.evaluate('$("lab-home").click()')
            page.wait_for_function('!pending', timeout=70000)
            result['geometry16'] = base.geometry(phase())
        elif name == 'sixteen_titan_restored':
            command('load')
            wait_ui(recipe)
            titan = next(body for body in phase()['bodies'] if body['reference_id'] == 'sol:naif:606')
            page.locator('#solar-body').select_option(titan['id'])
            page.evaluate('$("solar-view-body").click();$("solar-sample").click()')
            page.wait_for_function('!pending&&solarReading?.sources.length===15', timeout=70000)
            result['final_reading16'] = page.evaluate('solarReading')
            result['final_geometry16'] = base.geometry(phase())
        else:
            if live4 is None:
                command('load_branch', **base.guard(phase()), branch_id=seed['four_branch'])
                live4 = copy.deepcopy(phase())
                result['common4'] = c.physical(live4)
                audit.phase_equal(result['common4'], seed['common_source_phase4'])
                result['geometry4'] = base.geometry(live4)
            active_context = base.context(live4)
            instrument = recipe['instrument']
            body = next((body for body in live4['bodies'] if body['reference_id'] == 'sol:naif:' + recipe.get('body', '')), None)
            source_guard = base.contract.artifact.body.guard(live4)
            if instrument == 'spatial':
                h.post('/api/spatial/command', dict(command='create', guard=module('spatial')['guard'], source_guard=source_guard,
                       body_id=body['id'], configuration=service['recipe_before_execution']['spatial_configuration']))
                actual = h.post('/api/spatial/command', dict(command='get_artifact', guard=module('spatial')['guard']))['result']
                c.require(actual['configuration'] == service['recipe_before_execution']['spatial_configuration'], 'Simple mesh recipe differs')
            elif instrument == 'layers':
                h.post('/api/layers/command', dict(command='load_saved', guard=module('layers')['guard'], source_guard=source_guard))
                h.post('/api/layers/command', dict(command='branch_load', guard=module('layers')['guard'], branch_id=seed['instrument_checkpoints'][recipe['body']]['layer_branch']))
                scientific = h.post('/api/layers/command', dict(command='get_artifact', guard=module('layers')['guard']))['result']['scientific']
                c.require(scientific == seed['instrument_checkpoints'][recipe['body']]['layer_scientific'], 'Archived layer science changed')
            elif instrument == 'particles':
                h.post('/api/particles/command', dict(command='load_saved'))
                h.post('/api/particles/command', dict(command='load_branch', guard=base.ParticleClient.guard(module('particles')['worker']),
                       branch_id=seed['instrument_checkpoints'][recipe['body']]['particle_branch']))
            else:
                base.post('/api/solar-zone/command', dict(command='load_saved'))
        wait_ui(recipe)
        present(recipe)
        value = collector.scenario()
        audit.provenance(value, recipe, seed, result.get('common4'), service)
        return value

    persist()
    try:
        c.require(h.get('/api/state')['mode'] == 'atlas', 'Atlas initial state required')
        with Page() as page:
            page.on('pageerror', lambda error: result['page_errors'].append(error))
            page.wait_for_function('appState?.mode==="atlas"&&!pending')
            page.locator('#ui-scale').select_option('1')
            collector.atomic(folder / 'control.json', dict(schema=1, id='000-prepare', kind='prepare', window=None, recipe=None, expected_scenario=None))
            with (folder / 'collector.log').open('xb') as stream:
                job = subprocess.Popen([sys.executable, '-u', '-Xutf8', str(ROOT / 'scripts/collect_expanded_residency_v2.py'),
                                        '--label', args.label, '--folder', str(folder), '--max-samples', '3600'], cwd=ROOT,
                                       stdout=stream, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
            wait_samples(dict(id='000-prepare'), 3)
            for recipe in plan['windows']:
                ctrl = control('transition', recipe)
                row = dict(name=recipe['name'], control=ctrl, budget_s=750 if recipe['instrument'] == 'solar-zone' else 70,
                           before=collector.scenario(), **begin())
                result['pending_transition'] = row
                persist()
                value = enter(recipe)
                row['after'] = value
                result['transitions'].append(end(row))
                result.pop('pending_transition')
                persist()
                warm_control = control('warmup', recipe, value)
                warmup = dict(control=warm_control, **begin())
                print(json.dumps(dict(stage='warmup', window=recipe['name'])), flush=True)
                while time.perf_counter() - warmup['began'] < 30:
                    status()
                    time.sleep(min(.2, max(0, 30 - (time.perf_counter() - warmup['began']))))
                end(warmup)
                stable = control('stable', recipe, value)
                wait_samples(stable, 3)
                run = dict(recipe=recipe, warmup=warmup, stable_control=stable, samples=[], **begin())
                run['expected_anchor'] = h.native('return openspace.navigation.getNavigationState()')['Anchor']
                result['pending_run'] = run
                persist()
                print(json.dumps(dict(stage='capture', window=recipe['name'])), flush=True)
                for part in range(4):
                    deadline = run['began'] + 20 * part
                    while time.perf_counter() < deadline:
                        status()
                        time.sleep(min(.2, deadline - time.perf_counter()) if deadline > time.perf_counter() else 0)
                    native = h.native('return {camera=openspace.navigation.getNavigationState(),memory=openspace.cosmos2MemoryMetrics()}')
                    sample = dict(offset_s=time.perf_counter() - run['began'], native=native, scenario=collector.scenario(),
                                  ui=page.evaluate('({scale:$("ui-scale").value,mode:appState.mode,width:innerWidth,height:innerHeight})'))
                    c.admit_scenario(sample['scenario'], recipe, value)
                    run['samples'].append(sample)
                end(run)
                wait_samples(stable, 66)
                result['runs'].append(run)
                result.pop('pending_run')
                persist()
            ctrl = control('cleanup')
            cleanup = dict(name='return_atlas', control=ctrl, budget_s=70, before=collector.scenario(), **begin())
            leave()
            command('atlas')
            page.wait_for_function('appState?.mode==="atlas"&&!pending', timeout=70000)
            page.evaluate('document.body.inert=false')
            cleanup['after'] = collector.scenario()
            result['transitions'].append(end(cleanup))
            wait_samples(ctrl, 5)
            collector.atomic(folder / 'stop.json', dict(reason='ten_windows_complete'))
            result['collector_exit'] = job.wait(timeout=30)
            c.require(job.returncode == 0, 'Collector rejected the residence journey')
            job = None
            result['completed'] = True
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        if tracing:
            try:
                result['interrupted_native_capture'] = end(dict(began=time.perf_counter(), capture_start_utc=now()))
            except Exception:
                result['interrupted_capture_failure'] = traceback.format_exc()
        if job:
            try:
                collector.atomic(folder / 'stop.json', dict(reason='executor_failure'))
                result['collector_exit'] = job.wait(timeout=30)
            except Exception:
                result['collector_stop_failure'] = traceback.format_exc()
        try:
            if not result['completed']:
                leave()
                if h.get('/api/state')['mode'] == 'experiment':
                    command('atlas')
            with Page() as cleanup_page:
                cleanup_page.evaluate('document.body.inert=false')
            c.require(all(sha(ROOT / name) == seal for name, seal in (sources | plan['protected_sha256']).items()), 'Source/protected input changed')
        except Exception:
            result['cleanup_failure'] = traceback.format_exc()
            result['completed'] = False
        path = ROOT / f'evidence/is6-expanded-residency-collector-{args.label}.json'
        result.update(collector_receipt=path.relative_to(ROOT).as_posix(), collector_sha256=sha(path) if path.exists() else None,
                      finished_utc=now())
        persist()
    print(json.dumps(dict(completed=result['completed'], windows=len(result['runs']), failure=result.get('failure'), cleanup_failure=result.get('cleanup_failure'))), flush=True)
    return 0 if result['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
