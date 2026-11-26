"""Real CEF journey for the separate prescribed-field EM cloud candidate."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--topic-cleanup', action='store_true')
args = parser.parse_args()
variant = 'topic-cleanup' if args.topic_cleanup else 'em-cloud'
destination = ROOT/('evidence/em-cloud-helper-topic-cleanup-ui-check.json' if args.topic_cleanup else 'evidence/em-cloud-helper-native-ui-check.json')
if args.topic_cleanup: assert not destination.exists()
runtime_receipt = json.loads((ROOT/('evidence/built-runtime-'+variant+'.json')).read_bytes())
session = json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert Path(session['runtime']).resolve() == (ROOT/('.runtime-'+variant)).resolve()
assert hashlib.sha256((ROOT/('.runtime-'+variant)/'bin/OpenSpace.exe').read_bytes()).hexdigest() == runtime_receipt['engine_sha256']
CANDIDATE = ROOT/'output/c212-em-cloud-native-product'
sys.path.insert(0, str(CANDIDATE/'em-cloud'))
from cloud_presets import create
import cloud_transport as wire
from cef_page import Page

owner = ROOT/'user/sessions/latest.json'
original = owner.read_bytes()
app_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (ROOT/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
errors, combos, pauses = [], [], []


def idle(page):
    page.wait_for_function('state && !pending && native?.confirmation && !native.error && native.confirmation.metadata.system_id===state.system_id && (state.paused ? native.confirmation.metadata.time_s===state.time_s : state.time_s-native.confirmation.metadata.time_s<=1)', timeout=25000)


def state(page):
    return page.evaluate('JSON.parse(JSON.stringify(state))')


def click(page, element):
    page.locator('#'+element).click()
    idle(page)


def fill(page, values):
    page.evaluate('Object.entries('+json.dumps(values)+').forEach(([k,v])=>document.getElementById(k).value=v)')


def checked(page, element, value):
    page.locator('#'+element).set_checked(value)
    idle(page)


def load(page, count=10000, preset='crossed'):
    page.locator('#count').select_option(str(count))
    page.locator('#preset').select_option(preset)
    click(page, 'load-preset')
    page.wait_for_function('state.count==='+str(count)+' && state.time_s===0 && state.paused')


try:
    with Page() as page:
        page.on('pageerror', lambda value: errors.append(value))
        page.goto('http://127.0.0.1:4700/')
        page.wait_for_function('document.querySelector("#em-cloud-lab")')
        page.locator('#em-cloud-lab').click()
        page.wait_for_function('location.pathname==="/em-cloud.html"')
        idle(page)
        load(page)
        initial = state(page)
        assert initial['count'] == 10000 and initial['paused']
        fill(page, {'index': 9999})
        click(page, 'select')
        assert state(page)['selected_particle']['index'] == 9999
        click(page, 'focus')
        click(page, 'frame')
        click(page, 'measure')
        assert page.evaluate('fieldMap.measurement.samples.length') == 97
        assert page.evaluate('fieldMap.render.meshes.map(m=>m.arrow_count)') == [97, 97]
        fill(page, {'px': 3, 'py': 2, 'pz': 1})
        page.evaluate('document.getElementById("probe-form").requestSubmit()')
        idle(page)
        assert page.evaluate('lastProbe.electric_field_V_m') == [.2, 0., 0.]
        assert page.evaluate('lastProbe.magnetic_field_T') == [0., 0., 1.]
        for _ in range(5):
            start = state(page)['time_s']
            click(page, 'play')
            page.wait_for_function('!state.paused && state.time_s>'+repr(start+.02))
            began = time.perf_counter()
            click(page, 'play')
            pauses.append((time.perf_counter()-began)*1000)
            assert state(page)['paused']
        assert 'CONGELADO' in page.locator('#map-state').inner_text()
        assert 'CONGELADA' in page.locator('#probe-reading').inner_text()
        page.locator('#rate').select_option('0.5')
        idle(page)
        assert state(page)['requested_model_s_per_wall_s'] == .5
        for acting in (False, True):
            for visible in (False, True):
                load(page, count=128)
                checked(page, 'acting-e', acting)
                before = state(page)
                checked(page, 'visible-e', visible)
                assert state(page)['phase_sha256'] == before['phase_sha256']
                assert state(page)['controls'] == before['controls']
                assert state(page)['revision'] == before['revision']
                controls = state(page)['controls']
                system, phase, dt, _ = create('crossed', 128)
                phase, _ = system.step(phase, dt, **controls)
                click(page, 'step')
                assert state(page)['phase_sha256'] == hashlib.sha256(phase._x+phase._v).hexdigest()
                combos.append({'electric_acting': acting, 'electric_visible': visible, 'one_full_step_exact': True})
        for acting in (False, True):
            for visible in (False, True):
                load(page, count=128)
                checked(page, 'acting-b', acting)
                before = state(page)
                checked(page, 'visible-b', visible)
                assert state(page)['phase_sha256'] == before['phase_sha256']
                assert state(page)['controls'] == before['controls']
                system, phase, dt, _ = create('crossed', 128)
                phase, _ = system.step(phase, dt, **state(page)['controls'])
                click(page, 'step')
                assert state(page)['phase_sha256'] == hashlib.sha256(phase._x+phase._v).hexdigest()
                combos.append({'magnetic_acting': acting, 'magnetic_visible': visible, 'one_full_step_exact': True})
        load(page)
        checked(page, 'visible-cloud', False)
        start = state(page)['time_s']
        click(page, 'play')
        page.wait_for_function('state.time_s>'+repr(start+.02))
        click(page, 'play')
        checked(page, 'visible-cloud', True)
        checked(page, 'visible-e', True)
        checked(page, 'visible-b', True)
        fill(page, {'index': 9999})
        click(page, 'select')
        fill(page, {'dt': .001})
        page.evaluate('document.getElementById("timestep-form").requestSubmit()')
        idle(page)
        assert state(page)['dt_s'] == .001
        fill(page, {'ex': .15, 'ey': -.1, 'ez': 0, 'bx': 0, 'by': 0, 'bz': .5})
        page.evaluate('document.getElementById("background-form").requestSubmit()')
        idle(page)
        assert state(page)['model']['uniform_E_V_m'] == [.15, -.1, 0.]
        assert state(page)['model']['uniform_B_T'] == [0., 0., .5]
        click(page, 'frame')
        click(page, 'save')
        saved = state(page)
        saved_visual = page.evaluate('JSON.parse(JSON.stringify(visual))')
        click(page, 'step')
        assert state(page)['time_s'] > saved['time_s']
        click(page, 'restore')
        restored = state(page)
        for key in ('time_s', 'phase_sha256', 'model', 'controls', 'dt_s', 'selected_particle', 'requested_model_s_per_wall_s'):
            assert saved[key] == restored[key], key
        assert page.evaluate('visual') == saved_visual and restored['paused']
        click(page, 'export')
        artifact = page.evaluate('lastArtifact')
        raw = urllib.request.urlopen('http://127.0.0.1:4700'+artifact['url'], timeout=10).read()
        assert len(raw) == artifact['bytes'] and hashlib.sha256(raw).hexdigest() == artifact['sha256']
        exported = json.loads(raw)
        _, xyz = wire.decode(wire.read_packet(CANDIDATE/'native-cloud/positions.bin'),
                             *[restored[k] for k in ('system_id', 'edit_token', 'cloud_id', 'source_id')], 10000)
        assert exported['positions_m'] == xyz.tolist()
        assert exported['metadata']['time_s'] == restored['time_s']
        # A resealed stale browser edit is refused without altering the phase.
        response = page.evaluate('''(async()=>{const r=await fetch('/api/em-cloud/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:'advance',...guard(),edit_token:'stale',steps:1})});return {status:r.status,body:await r.json()};})()''')
        assert response['status'] == 400 and 'Stale' in response['body']['error']
        page.evaluate('refresh(true)')
        assert state(page)['phase_sha256'] == restored['phase_sha256']
        click(page, 'measure')
        page.evaluate('document.querySelectorAll("aside").forEach(e=>e.scrollTop=0)')
        subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                        str(ROOT/'scripts/capture-window.ps1'), '-Name', 'cosmos2-em-cloud-helper-topic-cleanup-ui.png' if args.topic_cleanup else 'cosmos2-em-cloud-helper-native-ui.png'],
                       check=True, capture_output=True)
        # Both EM modes return through the real navigation flow and clear their nodes.
        page.locator('#small-em').click()
        page.wait_for_function('location.pathname==="/em.html" && state?.experiment && nativeState?.active && !pending', timeout=25000)
        page.locator('#native-return').click()
        page.wait_for_function('location.pathname==="/"')
        for _ in range(3):
            page.locator('#em-cloud-lab').click()
            page.wait_for_function('location.pathname==="/em-cloud.html"')
            idle(page)
            page.locator('#return').click()
            page.wait_for_function('location.pathname==="/"')
        assert not errors, errors
    assert owner.read_bytes() == original
    assert app_hashes == {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in (ROOT/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    report = {'status': 'candidate_EM_cloud_real_CEF_controls_SI_export_and_transitions_verified',
              'engine_sha256': runtime_receipt['engine_sha256'], 'runtime_variant': variant,
              'count': 10000, 'five_live_pause_UI_wall_ms': pauses, 'acting_visibility_combinations': combos,
              'field_map_97_samples_and_194_native_arrows': True, 'frozen_map_and_probe_labels': True,
              'hidden_cloud_keeps_evolving': True, 'timestep_background_rate_and_selection_edited': True,
              'save_restore_science_and_aux_preferences_exact': True,
              'export_bytes': len(raw), 'export_sha256': artifact['sha256'], 'all_export_SI_positions_exact': True,
              'stale_browser_guard_refused_without_mutation': True, 'EM_to_cloud_and_three_Atlas_round_trips': True,
              'JS_errors': errors, 'installed_app_files_preserved': len(app_hashes), 'owner_pointer_preserved': True,
              'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (*CANDIDATE.glob('app/em_cloud*.py'), CANDIDATE/'app/server.py',
                                          *CANDIDATE.glob('app/ui/em/cloud.*'), CANDIDATE/'app/ui/em-cloud.html', Path(__file__))},
              'scope': 'Real CEF functional journey. Screenshot awaits visual review; no formal native performance or128-source throughput acceptance.'}
    destination.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'status': report['status'], 'export_bytes': len(raw), 'JS_errors': errors}, indent=2))
except Exception as error:
    (ROOT/'evidence'/('em-cloud-ui-failure-'+uuid.uuid4().hex+'.json')).write_text(json.dumps({
        'error': str(error), 'combos_completed': combos, 'JS_errors': errors,
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, indent=2)+'\n')
    raise
finally:
    assert owner.read_bytes() == original
