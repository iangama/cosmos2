"""Real CEF/actor/native acceptance for the isolated solar-zone instrument."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import argparse
import copy
import hashlib
import json
import subprocess
import time
import traceback
import zipfile
import psutil
from PIL import Image
from cef_page import Page

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is5-pp2-zone-product0.12.1/app'
h = SourceFileLoader('is5_native_helpers', str(ROOT / 'scripts/verify-native-solar-integration.py')).load_module()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    path = ROOT / ('evidence/is5-native-pp2-121-' + args.label + '.json')
    archive = ROOT / ('output/is5-native-pp2-121-' + args.label + '.zip')
    if path.exists() or archive.exists():
        raise FileExistsError('Preserve prior evidence')
    files = [p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [* (ROOT/'output/is5-thermal-staging').glob('*.py'),Path(__file__), ROOT / 'IS-5-PP-II-PRODUTO-CONTRATO.md', ROOT / 'scripts/launch-is5-pp2-121-candidate.py']
    files += [p for p in (ROOT/'output/is5-pp2-staging').rglob('*') if p.is_file() and p.suffix in ('.py','.json','.txt','.pdf') and '__pycache__' not in p.parts]
    data=json.loads((ROOT/'output/is5-pp2-staging/pp2-data.json').read_text())
    files += [ROOT/e['raw_file'] for e in data['rates'].values() if 'raw_file' in e]
    files += [ROOT/'data/science/ame2020-mass-original.txt',ROOT/'app/nuclei.py']
    hashes = {f.relative_to(ROOT).as_posix(): sha(f) for f in files}
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in hashes:
            z.write(ROOT / name, name)
    r = dict(accepted=False, completed=False, source_sha256=hashes, archive_sha256=sha(archive),
             session=h.get('/health'), checks=[], refusals=0, captures=[], page_errors=[])
    def persist():
        path.write_text(json.dumps(r, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    def zone():
        return h.get('/api/solar-zone/state')
    def guard(state):
        return {k: state['worker'][k] for k in ('worker_id', 'artifact_id', 'edit_token', 'revision')}
    def command(action, **extra):
        request = dict(command=action, **extra)
        if action not in ('create', 'load_saved'):
            request['guard'] = guard(zone())
        return h.post('/api/solar-zone/command', request)
    def capture(page, name, scale='1'):
        page.locator('#ui-scale').select_option(scale)
        page.evaluate('document.getElementById("zone-panel").scrollTop=0;document.getElementById("zone-charts").scrollTop=0')
        time.sleep(.3)
        filename = 'cosmos2-is5-pp2-121-' + args.label + '-' + name + '.png'
        subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                        str(ROOT / 'scripts/capture-window.ps1'), '-Name', filename], check=True, capture_output=True)
        pixels=Image.open(ROOT/'evidence'/filename).convert('RGB').crop((700,460,1200,650))
        marker_pixels=sum(red>225 and 140<green<210 and 50<blue<130 for red,green,blue in pixels.getdata())
        r['captures'].append(dict(path='evidence/' + filename, sha256=sha(ROOT / 'evidence' / filename),marker_pixels=marker_pixels))
        assert marker_pixels>12000,('Native marker absent from captured image',filename,marker_pixels)
    persist()
    try:
        with Page() as page:
            page.on('pageerror', lambda e: r['page_errors'].append(e))
            page.goto(h.BASE + '/')
            page.wait_for_function('solarZoneState!==null&&!pending&&!solarZonePending')
            if zone()['active']:
                command('leave')
            if h.get('/api/state')['mode'] == 'experiment':
                h.post('/api/command', {'command': 'atlas'})
            page.wait_for_function('appState?.mode==="atlas"&&!pending')
            h.click(page, '#copy-solar')
            page.wait_for_function('!pending&&appState?.physics?.paused&&appState?.physics?.bodies.length===4', timeout=70000)
            orbital = h.phase(h.get('/api/state')['physics'])
            page.evaluate('document.getElementById("zone-setup").open=true')
            page.wait_for_function('!document.getElementById("zone-create").disabled')
            page.locator('#zone-create').click()
            page.wait_for_function('!solarZonePending&&solarZoneState?.active&&solarZoneCurveId===solarZoneState.worker.artifact_id', timeout=70000)
            initial = zone()
            run = command('get_result')['result']
            assert run['actual'] == run['reference']
            assert initial['scene']['confirmed'] and 'arquivado' in initial['scene']['label']
            assert initial['scene']['source_binding_sha256'] == initial['worker']['source']['binding_sha256']
            assert h.phase(h.get('/api/state')['physics']) == orbital
            r['checks'].append('Real CEF creation, complete reference, archived native source and untouched orbital phase')
            original_guard = guard(initial)
            page.evaluate('document.getElementById("zone-index").value=240;document.getElementById("zone-index").dispatchEvent(new Event("change",{bubbles:true}))')
            page.wait_for_function('!solarZonePending&&solarZoneState.worker.view.selected_index===240')
            w = zone()['worker']
            assert w['sample']['actual']['time_s'] == w['configuration']['parameters']['duration_s']
            assert w['sample']['actual']['energy_available_J_m3'] > 0
            assert w['sample']['actual']['temperature_K']>w['configuration']['parameters']['temperature_K']
            assert w['sample']['actual']['internal_energy_J_m3']>run['actual']['internal_energy_J_m3'][0]
            assert w['sample']['actual']['captured_electrons_m3']>0 and w['sample']['actual']['mass_fractions']['be7']>0
            assert 'Elétrons capturados:' in page.evaluate('document.getElementById("zone-probe").textContent')
            assert 'Temperatura:' in page.evaluate('document.getElementById("zone-probe").textContent')
            capture(page, 'all-on-100')
            capture(page, 'all-on-150', '1.5')
            page.locator('#ui-scale').select_option('1')
            page.evaluate('document.getElementById("zone-config-form").parentElement.open=true')
            page.locator('#zone-weak').set_checked(False)
            page.locator('#zone-recompute').click()
            page.wait_for_function('!solarZonePending&&!solarZoneState.worker.configuration.acting.weak&&solarZoneCurveId===solarZoneState.worker.artifact_id', timeout=70000)
            command('sample', index=240)
            changed = command('get_result')['result']
            assert changed['configuration']['parameters'] == run['configuration']['parameters']
            assert changed['source'] == run['source'] and changed['reference'] == run['reference']
            assert 0 < changed['actual']['energy_available_J_m3'][-1] < changed['reference']['energy_available_J_m3'][-1]
            assert changed['actual']['neutrino_count_m3'][-1] == 0
            assert not any(changed['actual']['active_channels'][k] for k in ('pp','n13beta','o15beta'))
            assert changed['actual']['active_channels']['n14pg']
            r['checks'].append('Weak operator disabled through CEF; remaining radiative capture preserved, neutrinos zero and full reference unchanged')
            for bad in [original_guard, {**guard(zone()), 'revision': True}]:
                before = zone()
                h.post('/api/solar-zone/command', dict(command='sample', index=1, guard=bad), expected=400)
                assert zone()['worker']['artifact_id'] == before['worker']['artifact_id']
                assert zone()['scene'] == before['scene']
                r['refusals'] += 1
            config = copy.deepcopy(changed['configuration'])
            config['parameters']['temperature_K'] = True
            before = zone()
            h.post('/api/solar-zone/command', dict(command='configure', configuration=config, guard=guard(before)), expected=400)
            assert zone()['worker']['artifact_id'] == before['worker']['artifact_id'] and zone()['scene'] == before['scene']
            r['refusals'] += 1
            config['parameters']['temperature_K']=16e6
            h.post('/api/solar-zone/command',dict(command='configure',configuration=config,guard=guard(zone())),expected=400)
            assert zone()['worker']['artifact_id']==before['worker']['artifact_id'] and zone()['scene']==before['scene']
            r['refusals'] += 1
            config=copy.deepcopy(changed['configuration']);config['mode']='prescribed'
            h.post('/api/solar-zone/command',dict(command='configure',configuration=config,guard=guard(zone())),expected=400)
            assert zone()['worker']['artifact_id']==before['worker']['artifact_id'] and zone()['scene']==before['scene']
            r['refusals'] += 1
            for route, request in [('/api/command', dict(command='resume')), ('/api/solar/experiment', dict(utc='2026-10-12T12:00:00')),
                                   ('/api/atlas/experiment', dict(utc='2026-10-12T12:00:00')), ('/api/particles/command', dict(command='load_saved')),
                                   ('/api/navigation/visit', dict(target='Earth'))]:
                h.post(route, request, expected=400)
                r['refusals'] += 1
            assert h.phase(h.get('/api/state')['physics']) == orbital
            page.wait_for_function('solarZoneState?.worker?.sample?.index===240')
            probe=page.evaluate('document.getElementById("zone-probe").textContent')
            assert 'resíduo' in probe and 'Taxa Be-7 + e⁻: -0' not in probe,probe
            command('sample', index=0)
            command('play')
            time.sleep(.6)
            command('pause')
            assert 0 < zone()['worker']['view']['selected_index'] < 240
            command('sample', index=120)
            command('set_view', view=dict(selected_index=120, visible=dict(composition=True, energy=True, neutrinos=False, reference=True)))
            command('save')
            saved_state = zone()
            a = command('branch_create', name='Referência sem fraca')['result']['branch']['id']
            config = copy.deepcopy(changed['configuration'])
            config['acting']['weak'] = True
            config['channel_switches']['pp'] = False
            command('configure', configuration=config)
            b = command('branch_create', name='Canal pp desligado')['result']['branch']['id']
            assert next(row for row in zone()['worker']['branches'] if row['id'] == b)['parent'] == a
            command('branch_load', branch_id=a)
            assert command('get_result')['result'] == changed
            assert zone()['worker']['view'] == saved_state['worker']['view']
            oldworker = zone()['worker']['worker_id']
            command('new_worker')
            assert zone()['worker']['worker_id'] != oldworker
            assert command('get_result')['result'] == changed
            assert zone()['worker']['view'] == saved_state['worker']['view']
            command('restart')
            assert zone()['worker']['artifact_id'] != changed['id'] and zone()['worker']['view']['selected_index'] == 0
            command('load')
            export = command('export')['result']
            exported = json.loads(Path(export['path']).read_text())
            assert exported['run'] == changed and exported['record_sha256'] == export['record_sha256']
            r['checks'].append('Playback, indexed probe, visibility, save/load, two parented branches, new subprocess, restart and sealed export')
            saved = APP.parent / 'solar-zone-checkpoints/saved.json'
            raw = saved.read_bytes()
            broken = json.loads(raw)
            broken['record_sha256'] = '0' * 64
            before = zone()
            try:
                saved.write_text(json.dumps(broken))
                h.post('/api/solar-zone/command', dict(command='load', guard=guard(before)), expected=400)
                assert zone()['worker']['artifact_id'] == before['worker']['artifact_id']
                assert zone()['worker']['worker_id'] == before['worker']['worker_id'] and zone()['scene'] == before['scene']
                r['refusals'] += 1
            finally:
                saved.write_bytes(raw)
            page.wait_for_function('!solarZonePending&&solarZoneState.worker.view.selected_index===120')
            capture(page, 'no-weak-100')
            archived = zone()['worker']['source']
            oldnode = zone()['scene']['node']
            command('leave')
            assert not h.native('return {exists=openspace.hasSceneGraphNode(' + json.dumps(oldnode) + ')}')['exists']
            assert h.phase(h.get('/api/state')['physics']) == orbital
            h.post('/api/command', dict(command='resume'))
            time.sleep(.35)
            h.post('/api/command', dict(command='pause'))
            moved = h.phase(h.get('/api/state')['physics'])
            assert moved['time'] > orbital['time']
            command('load_saved')
            assert zone()['worker']['source'] == archived
            assert zone()['scene']['source_binding_sha256'] == archived['binding_sha256']
            assert zone()['scene']['center_render_m'] == archived['center_render_m']
            assert h.phase(h.get('/api/state')['physics']) == moved
            page.wait_for_function('solarZoneState?.active&&solarZoneCurveId===solarZoneState.worker.artifact_id')
            capture(page, 'archived-source-150', '1.5')
            r['checks'].append('Corrupt reload preserves actor/scene; archived source restores despite later orbital phase; closing removes native nodes')
            assert not r['page_errors'], r['page_errors']
            assert all(sha(ROOT / n) == value for n, value in hashes.items())
            r.update(accepted=True, completed=True)
    except Exception:
        r['failure'] = traceback.format_exc()
    finally:
        try:
            if zone()['active']:
                command('leave')
            with Page() as page:
                page.locator('#ui-scale').select_option('1')
            if h.get('/api/state')['mode'] == 'experiment':
                h.post('/api/command', dict(command='atlas'))
            leftovers = [p.info for p in psutil.process_iter(['pid','cmdline']) if p.info['cmdline'] and any(str(APP / 'is5_worker.py').lower() in arg.lower() for arg in p.info['cmdline'])]
            assert not leftovers, leftovers
        except Exception:
            r['cleanup_failure'] = traceback.format_exc()
            r['accepted'] = False
        persist()
    print(json.dumps(dict(accepted=r['accepted'], checks=len(r['checks']), refusals=r['refusals'], failure=r.get('failure'), cleanup_failure=r.get('cleanup_failure'))), flush=True)
    return 0 if r['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
