"""Native saved/followed probes: SI marks, stale readings, export and restoration.

Requires the C2-11 probe candidate to have been promoted and the backend
restarted. Never run against a3.4 backend or concurrently with a benchmark.
"""
from pathlib import Path
import copy
import json
import subprocess
import time
import urllib.request

from cef_page import Page
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:4700'
latest = ROOT / 'user/sessions/latest.json'
original_latest = latest.read_bytes() if latest.exists() else None
errors, cases = [], []


def get(path):
    return json.load(urllib.request.urlopen(BASE + path, timeout=20))


def post(body):
    request = urllib.request.Request(BASE + '/api/command', data=json.dumps(body).encode(),
                                     headers={'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(request, timeout=20))


def guard(p):
    return {'system_id': p['system_id'], 'edit_token': p['edit_token'], 'revision': p['revision'],
            'expected_time': p['time'], 'frame': p['contract']['frame'],
            'instruments_revision': p['instruments']['revision']}


def physical(p):
    return {k: copy.deepcopy(p[k]) for k in ('bodies', 'time', 'revision', 'conservation',
                                            'system_id', 'edit_token', 'scientific_generation')}


def settled(page):
    page.wait_for_function('appState?.physics?.instruments!==undefined&&!pending')
    time.sleep(.1)


def fill(page, identifier, value):
    page.evaluate('document.getElementById(' + json.dumps(identifier) + ').value=' + json.dumps(str(value)))


def capture(label):
    subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                    str(ROOT / 'scripts/capture-window.ps1'), '-Name', 'cosmos2-instruments-' + label + '.png'],
                   check=True, capture_output=True)


socket = connect('ws://127.0.0.1:4682', open_timeout=5, close_timeout=.2, ping_interval=None)
socket.send(json.dumps({'type': 'apiHandshake', 'apiVersion': {'major': 1, 'minor': 0, 'patch': 0}}))
serial = 0


def lua(code):
    global serial
    serial += 1
    socket.send(json.dumps({'topic': serial, 'type': 'luascript', 'payload': {'script': code, 'return': True}}))
    reply = json.loads(socket.recv(timeout=15))
    assert reply['topic'] == serial
    payload = reply.get('payload', {})
    if '1' not in payload:
        raise RuntimeError('Lua did not return a confirmed value: ' + json.dumps(reply))
    return payload['1']


atlas_before = get('/api/atlas/state')
try:
    with Page() as page:
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(BASE + '/')
        page.wait_for_function('appState!==null')
        page.locator('#ui-scale').select_option('1')
        for atlas_copy in (False, True):
            post({'command': 'atlas'})
            if atlas_copy:
                request = urllib.request.Request(BASE + '/api/atlas/experiment',
                    data=json.dumps({'utc': atlas_before['epoch']['utc']}).encode(),
                    headers={'Content-Type': 'application/json'})
                assert json.load(urllib.request.urlopen(request, timeout=20))['ok']
            else:
                post({'command': 'enter'})
                post({'command': 'reset', 'count': 32})
            page.evaluate('updateState()')
            settled(page)
            p = get('/api/state')['physics']
            assert p['scientific_generation']['model_version'] in ('3.5.0','3.6.0','3.7.0','3.8.0')
            original = physical(p)
            if not page.evaluate('document.getElementById("gravity-instruments").open'):
                page.locator('#gravity-instruments summary').click()
            page.locator('#prepare-instrument').click()
            settled(page)
            fill(page, 'instrument-name', 'Sonda "órbita" \\ salva')
            for k, value in enumerate((1.7e10, -9e9, 3e9)):
                fill(page, 'instrument-coordinate-' + str(k), value)
            page.locator('#apply-instrument').click()
            page.wait_for_function('appState.physics.instruments.probes.length===1&&!pending')
            assert physical(get('/api/state')['physics']) == original
            fixed_id = get('/api/state')['physics']['instruments']['probes'][0]['id']
            page.locator('#instrument-selection').select_option('')
            page.locator('#prepare-instrument').click()
            settled(page)
            page.locator('#instrument-mode').select_option('follow')
            followed_id = p['bodies'][-1]['id']
            page.locator('#instrument-body').select_option(followed_id)
            page.locator('#instrument-exclude').set_checked(True)
            fill(page, 'instrument-name', 'Seguir fonte original')
            for k, value in enumerate((1e5, -2e5, 3e5)):
                fill(page, 'instrument-coordinate-' + str(k), value)
            page.locator('#apply-instrument').click()
            page.wait_for_function('appState.physics.instruments.probes.length===2&&!pending')
            page.locator('#measure-instruments').click()
            page.wait_for_function('appState.instruments_preview?.readings.length===2&&!pending')
            state = get('/api/state')
            assert physical(state['physics']) == original
            preview = state['instruments_preview']
            assert all(r['available'] for r in preview['readings'])
            error = 0.
            for reading in preview['render']['readings']:
                position = lua('return openspace.propertyValue(' + json.dumps('Scene.' + reading['scene_node'] + '.Translation.Position') + ')')
                position = position if isinstance(position, list) else [position[str(i)] for i in (1, 2, 3)]
                error = max(error, max(abs(a - b) for a, b in zip(position, reading['position_render_m'])))
            assert error < .01
            page.locator('#instrument-selection').select_option(fixed_id)
            page.locator('#view-instrument').click()
            target = next(r for r in preview['render']['readings'] if r['id'] == fixed_id)['scene_node']
            deadline = time.monotonic() + 3
            while lua('return openspace.navigation.getNavigationState()')['Anchor'] != target:
                assert time.monotonic() < deadline, 'Camera did not confirm the requested probe anchor'
                time.sleep(.05)
            page.evaluate('document.getElementById("instruments-status").scrollIntoView({block:"start"})')
            time.sleep(.5)
            capture('atlas' if atlas_copy else 'p32')
            page.locator('#save').click()
            settled(page)
            manifest = json.loads(latest.read_text())
            definitions = copy.deepcopy(manifest['instruments'])
            page.locator('#export-instruments').click()
            settled(page)
            page.wait_for_function('document.getElementById("notice").textContent.startsWith("Exportado:")')
            export_path = Path(page.locator('#notice').inner_text().removeprefix('Exportado: '))
            exported = json.loads(export_path.read_text(encoding='utf8'))
            assert exported['reading']['source_snapshot_si'] == preview['source_snapshot_si']
            assert not exported['reading_is_stale']
            post({'command': 'resume'})
            time.sleep(.2)
            post({'command': 'pause'})
            page.evaluate('updateState()')
            settled(page)
            page.wait_for_function('document.getElementById("instruments-status").textContent.includes("CONGELADA")')
            # Re-measure while anchored to an old mark: replacement must retain
            # a valid camera anchor and create the points at the new instant.
            page.locator('#measure-instruments').click()
            settled(page)
            assert lua('return openspace.navigation.getNavigationState()')['Anchor'] == 'LabCameraAnchor'
            evolved = get('/api/state')
            assert evolved['instruments_preview']['time'] == evolved['physics']['time']
            assert evolved['instruments_preview']['time'] > preview['time']
            page.locator('#load').click()
            settled(page)
            restored = get('/api/state')['physics']
            assert restored['instruments']['probes'] == definitions['probes']
            assert restored['bodies'] == original['bodies'] and restored['time'] == original['time']
            # Removing the followed physical body never reassigns by row index.
            post({'command': 'remove_body', **guard(restored), 'body': followed_id})
            page.evaluate('updateState()')
            settled(page)
            page.locator('#measure-instruments').click()
            settled(page)
            missing = get('/api/state')['instruments_preview']['readings'][1]
            assert not missing['available'] and missing['definition']['body_id'] == followed_id
            assert 'acceleration_m_s2' not in missing
            before_clear = physical(get('/api/state')['physics'])
            page.locator('#clear-instruments').click()
            settled(page)
            cleared = get('/api/state')
            assert cleared['instruments_preview'] is None and cleared['physics']['instruments']['probes'] == definitions['probes']
            assert physical(cleared['physics']) == before_clear
            cases.append({'atlas_copy': atlas_copy, 'native_position_max_component_difference_m': error,
                          'configure_sample_and_clear_physics_preserved': True,
                          'checkpoint_definition_and_phase_exact': True, 'JSON_export_has_sources_and_stamp': True,
                          'stale_reading_and_camera_anchor_replacement': True,
                          'missing_follow_target_preserves_original_ID': True})
finally:
    try:
        post({'command': 'atlas'})
    finally:
        socket.close()
        if original_latest is None:
            latest.unlink(missing_ok=True)
        else:
            latest.write_bytes(original_latest)
assert get('/api/atlas/state')['epoch'] == atlas_before['epoch'] and not errors
report = {'browser': 'native CEF', 'cases': cases, 'page_errors': errors,
          'checkpoint_pointer_restored': True, 'atlas_epoch_preserved': True,
          'scope': 'First C2-11 probe slice; no complete acceptance of fields/J2/tides/256/test-particle profiles.'}
(ROOT / 'evidence/gravity-instruments-ui-check.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
