"""Real CEF clone, worker namespace/checkpoint and display-frame verification."""
from pathlib import Path
import json
import math
import subprocess
import time
import urllib.error
import urllib.request
from websockets.sync.client import connect
from cef_page import Page

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:4700'
errors = []
latest = ROOT / 'user/sessions/latest.json'
original_latest = latest.read_bytes() if latest.exists() else None

def get(path):
    return json.load(urllib.request.urlopen(BASE + path, timeout=10))

def post(path, payload, expected=200):
    request = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    try:
        response = urllib.request.urlopen(request, timeout=20)
    except urllib.error.HTTPError as error:
        assert error.code == expected, (error.code, error.read().decode())
        return json.load(error)
    assert response.status == expected
    return json.load(response)

def capture(label):
    subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                    str(ROOT / 'scripts/capture-window.ps1'), '-Name', f'cosmos2-native-atlas-import-{label}.png'],
                   check=True, capture_output=True)

def lua(ws, code, number):
    ws.send(json.dumps({'topic': number, 'type': 'luascript', 'payload': {'script': code, 'return': True}}))
    response = json.loads(ws.recv(timeout=5))
    assert response.get('topic') == number, response
    return response['payload']['1']

try:
    with Page() as page:
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(BASE + '/')
        page.wait_for_function('atlasState&&appState&&appState.mode==="atlas"&&!document.getElementById("copy-atlas").disabled')
        before = get('/api/atlas/state')
        original_physics = get('/api/state')['physics']
        invalid = post('/api/atlas/experiment', {'utc': '2051-01-01T00:00:00Z'}, expected=400)
        assert invalid['ok'] is False
        after = get('/api/atlas/state')
        assert after['epoch'] == before['epoch'] and after['bodies'] == before['bodies']
        assert get('/api/state')['physics'] == original_physics
        page.locator('#copy-atlas').click()
        page.wait_for_function('!pending&&appState?.mode==="experiment"&&appState.physics?.atlas_initial')
        first = get('/api/state')['physics']; initial = first['atlas_initial']
        assert first['paused'] and first['time'] == 0 and len(first['bodies']) == 3
        assert initial['source']['epoch'] == before['epoch']
        assert first['contract']['frame'] == 'initial_subset_barycenter_inertial_axes_J2000'
        assert page.evaluate('document.getElementById("fixture").value') == 'atlas'
        assert page.evaluate('!document.getElementById("lab-origin").hidden')
        assert before['epoch']['utc'] in page.locator('#lab-epoch').inner_text()
        assert 'Outros planetas' in page.locator('.atlas-copy').inner_text()
        # Verify local translation rather than subtract 1e14m display root,
        # whose float64 ulp would otherwise obscure a millimetre comparison.
        with connect('ws://127.0.0.1:4682', open_timeout=3, close_timeout=.2, ping_interval=None) as ws:
            ws.send(json.dumps({'type': 'apiHandshake', 'apiVersion': {'major': 1, 'minor': 0, 'patch': 0}}))
            code = 'return {positions={' + ','.join(f'openspace.propertyValue("Scene.{b["scene_node"]}.Translation.Position")' for b in first['bodies']) + '}}'
            native = lua(ws, code, 1)
        matrix = initial['j2000_to_render_frame']; unit = first['physical_scale']['length_unit_m']
        expected = [[sum(row[k] * b['position'][k] for k in range(3)) * unit for row in matrix] for b in first['bodies']]
        local_positions = [native['positions'][str(i + 1)] for i in range(3)]
        position_error = max(abs(a - b) for p, q in zip(local_positions, expected) for a, b in zip(p, q))
        assert position_error <= .001, (position_error, native, expected)
        capture('system')
        page.locator('#lab-earth-moon').click()
        time.sleep(.2)
        capture('earth-moon')
        page.locator('#lab-origin').click()
        assert page.locator('[data-reference-id]').count() == 3
        assert '398600.435544' in page.locator('#lab-source-GM').inner_text()
        capture('provenance')
        # Dedicated input rejects arbitrary initial states and duplicate copy
        # while in a laboratory. Native reference objects remain untouched.
        post('/api/command', {'command': 'import_atlas', 'initial_state': initial}, expected=400)
        post('/api/atlas/experiment', {'utc': before['epoch']['utc']}, expected=400)
        assert get('/api/state')['physics']['atlas_initial'] == initial
        central_id = first['bodies'][0]['id']
        page.evaluate('const m=document.getElementById("mass");m.focus();m.value="2";m.dispatchEvent(new Event("input",{bubbles:true}));m.blur()')
        time.sleep(.4)
        assert page.evaluate('document.getElementById("mass").value') == '2'
        page.locator('#apply-mass').click()
        page.wait_for_function('!pending&&appState.physics.revision===1')
        changed = get('/api/state')['physics']
        assert changed['interventions'][0]['body'] == central_id
        assert changed['bodies'][0]['mass'] == 2
        assert changed['atlas_initial'] == initial
        assert changed['bodies'][0]['position'] == first['bodies'][0]['position']
        page.locator('#save').click(); page.wait_for_function('!pending&&appState.checkpoint_available')
        page.locator('#play').click(); page.wait_for_function('!pending&&!appState.physics.paused')
        time.sleep(.3)
        page.locator('#play').click(); page.wait_for_function('!pending&&appState.physics.paused')
        assert get('/api/state')['physics']['time'] > 0
        page.locator('#load').click(); page.wait_for_function('!pending&&appState.physics.time===0')
        loaded = get('/api/state')['physics']
        assert loaded['bodies'] == changed['bodies'] and loaded['atlas_initial'] == initial
        assert loaded['restoration']['status'] == 'same_generation'
        assert 'mesma geração' in page.locator('#lab-restoration').inner_text()
        # Restart restores original GM state, not the edited solar mass.
        page.locator('#reset').click(); page.wait_for_function('!pending&&appState.physics.revision===0')
        assert get('/api/state')['physics']['bodies'] == first['bodies']
        page.locator('#atlas').click(); page.wait_for_function('!pending&&appState.mode==="atlas"')
        restored = get('/api/atlas/state')
        assert restored['epoch'] == before['epoch'] and restored['bodies'] == before['bodies']
        page.locator('#experiment').click(); page.wait_for_function('!pending&&appState.mode==="experiment"')
        assert get('/api/state')['physics']['atlas_initial'] == initial
        page.locator('#play').click(); page.wait_for_function('!pending&&!appState.physics.paused')
        page.locator('#open-content').click(); page.wait_for_function('contentAtlas&&packageCatalog')
        assert get('/api/state')['physics']['paused']
        assert get('/api/state')['physics']['atlas_initial'] == initial
        page.locator('.back').click(); page.wait_for_function('appState?.mode==="experiment"&&appState.physics.paused')
        # The previous P32/P128 fixtures stay usable after a copied scenario.
        page.locator('#fixture').select_option('128'); page.locator('#reset').click()
        page.wait_for_function('!pending&&appState.physics.bodies.length===128')
        assert not get('/api/state')['physics'].get('atlas_initial')
        assert page.evaluate('document.getElementById("lab-origin").hidden')
        page.locator('#play').click(); page.wait_for_function('!pending&&!appState.physics.paused')
        time.sleep(.2); page.locator('#play').click(); page.wait_for_function('!pending&&appState.physics.paused')
        page.locator('#fixture').select_option('32'); page.locator('#reset').click()
        page.wait_for_function('!pending&&appState.physics.bodies.length===32')
        page.locator('#atlas').click(); page.wait_for_function('!pending&&appState.mode==="atlas"')
        assert not errors, errors
finally:
    if original_latest is None:
        latest.unlink(missing_ok=True)
    else:
        latest.write_bytes(original_latest)

report = {'session': json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig')),
          'native_browser': 'OpenSpace CEF', 'source_epoch': before['epoch'], 'branch_id': initial['branch_id'],
          'copied_reference_ids': [b['reference_id'] for b in first['bodies']],
          'paused_first_snapshot': True, 'native_local_position_max_difference_m': position_error,
          'namespace_mass_intervention': True, 'source_survives_intervention': True,
          'checkpoint_exact_bodies_source': True, 'restart_restores_original_parameters': True,
          'atlas_epoch_sources_preserved': True, 'invalid_copy_no_mutation': True,
          'dedicated_API_provenance_required': True, 'P32_P128_regression': True,
          'system_and_earth_moon_cameras': True, 'user_checkpoint_pointer_restored': True,
          'pending_mass_input_survives_polling_after_blur': True,
          'opening_data_view_pauses_preserves_experiment': True,
          'page_errors': errors,
          'scope': 'Native data/worker/render flow. Scientific SI integration comparison is in atlas-import-check.json. Visual review is separate.'}
(ROOT / 'evidence/native-atlas-import-check.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
