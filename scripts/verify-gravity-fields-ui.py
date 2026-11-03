"""Native CEF maps: geometry, shared SI readings, move/rotate/save and stale state."""
from pathlib import Path
import copy
import json
import subprocess
import time
import urllib.error
import urllib.request

import numpy as np
from cef_page import Page
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:4700'
latest = ROOT / 'user/sessions/latest.json'
saved = latest.read_bytes() if latest.exists() else None
errors, cases = [], []


def get(path):
    return json.load(urllib.request.urlopen(BASE + '/api/' + path, timeout=20))


def post(body, path='command'):
    request = urllib.request.Request(BASE + '/api/' + path, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(request, timeout=25))


def physical(state):
    return {k: copy.deepcopy(state[k]) for k in ('bodies', 'time', 'revision', 'conservation', 'system_id', 'edit_token', 'scientific_generation', 'instruments')}


def guard(p):
    return {k: p[k] for k in ('system_id', 'edit_token', 'revision')} | {'expected_time': p['time'], 'frame': p['contract']['frame'], 'fields_revision': p['field_layers']['revision']}


def idle(page, condition='true'):
    page.wait_for_function('!pending&&(' + condition + ')')
    time.sleep(.05)


def fill(page, key, value):
    page.evaluate('document.getElementById(' + json.dumps(key) + ').value=' + json.dumps(str(value)))


socket = connect('ws://127.0.0.1:4682', open_timeout=5, close_timeout=.2, ping_interval=None)
socket.send(json.dumps({'type': 'apiHandshake', 'apiVersion': {'major': 1, 'minor': 0, 'patch': 0}}))
serial = 0


def lua(code):
    global serial
    serial += 1
    socket.send(json.dumps({'topic': serial, 'type': 'luascript', 'payload': {'script': code, 'return': True}}))
    response = json.loads(socket.recv(timeout=15))
    assert response.get('topic') == serial and '1' in response.get('payload', {}), response
    return response['payload']['1']


def rotation(value):
    return np.array([value[str(k)] for k in range(1, 10)] if isinstance(value, dict) else value).reshape((3, 3), order='F')


def export(page):
    page.locator('#export-fields').click()
    idle(page)
    page.wait_for_function('document.getElementById("notice").textContent.startsWith("Exportado:")')
    path = Path(page.locator('#notice').inner_text().removeprefix('Exportado: '))
    return json.loads(path.read_text(encoding='utf8'))


def vertices(path):
    lines = Path(path).read_text().splitlines()
    segments, index = [], 0
    while index < len(lines):
        if lines[index].startswith('mesh '):
            count = int(lines[index + 2])
            segments.append(np.array([[float(v) for v in line.split()] for line in lines[index + 3:index + 3 + count]]))
            index += count + 4
        else:
            index += 1
    return segments


atlas = get('atlas/state')
try:
    with Page() as page:
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(BASE + '/')
        page.wait_for_function('appState!==null')
        page.locator('#ui-scale').select_option('1')
        for kind in ('single', 'fixture', 'atlas'):
            print('NATIVE MAP ' + kind, flush=True)
            post({'command': 'atlas'})
            if kind == 'atlas':
                assert post({'utc': atlas['epoch']['utc']}, 'atlas/experiment')['ok']
            else:
                post({'command': 'enter'})
                post({'command': 'reset', 'count': 32})
                if kind == 'single':
                    state = get('state')['physics']
                    assert post({'command': 'new_system', **guard(state), 'name': 'Massa isolada',
                                 'mass_kg': 1e30, 'position_m': [3e9, -2e9, 7e9], 'velocity_m_s': [0, 0, 0]})['ok']
            page.evaluate('updateState()')
            idle(page, 'appState.physics?.field_layers!==undefined')
            state = get('state')['physics']
            assert state['scientific_generation']['model_version'] in ('3.6.0','3.7.0','3.8.0')
            baseline = physical(state)
            if not page.evaluate('document.getElementById("gravity-fields").open'):
                page.locator('#gravity-fields summary').click()
            page.locator('#prepare-fields').click()
            idle(page)
            page.locator('#field-center-mode').select_option('follow')
            page.locator('#field-body').select_option(state['bodies'][0]['id'])
            fill(page, 'field-radius', 2e10)
            fill(page, 'field-cut-width', 3e10)
            fill(page, 'field-cut-offset', 3e9)
            for k, v in enumerate((30, -20, 15)):
                fill(page, 'field-angle-' + str(k), v)
            page.locator('#apply-fields').click()
            idle(page, 'appState.physics.field_layers.revision===1')
            assert physical(get('state')['physics']) == baseline
            definitions = copy.deepcopy(get('state')['physics']['field_layers'])
            page.locator('#measure-fields').click()
            idle(page, 'appState.fields_preview!==null')
            current = get('state')
            assert physical(current['physics']) == baseline
            summary = current['fields_preview']
            assert summary['sample_count'] == 385 and 'samples' not in summary['cut']
            summary_bytes = len(json.dumps(summary).encode())
            assert summary_bytes < 30000, summary_bytes
            exported = export(page)
            full = exported['reading']
            assert not exported['reading_is_stale'] and len(full['source_snapshot_si']) == len(state['bodies'])
            assert len(full['cut']['samples']) == 289 and len(full['shell']['samples']) == 96
            # A selected map sample and a separate probe use exactly the same evaluator.
            page.evaluate('document.querySelector("#gravity-fields details").open=true')
            page.locator('#field-sample-layer').select_option('cut')
            fill(page, 'field-sample-index', 145)
            page.locator('#read-field-sample').click()
            idle(page, 'appState.field_reading?.sample.index===145')
            reading = get('state')['field_reading']['sample']
            assert reading == full['cut']['samples'][145] and reading['valid']
            probe = post({'command': 'probe', **guard(state), 'position_m': reading['position_m']})['ack']['result']
            for key in ('acceleration_m_s2', 'potential_J_kg', 'tidal_tensor_s_2'):
                assert reading[key] == probe[key]
            assert physical(get('state')['physics']) == baseline
            transform = np.array(state['atlas_initial']['j2000_to_render_frame']) if kind == 'atlas' else np.eye(3)
            root = np.array(lua('return openspace.worldPosition("LabRoot")'))
            maximum = 0.
            for mesh in full['render']['meshes']:
                node = mesh['node']
                native = lua('return {position=openspace.worldPosition("' + node + '"),rotation=openspace.worldRotation("' + node + '"),scale=openspace.propertyValue("Scene.' + node + '.Scale.Scale"),file=openspace.propertyValue("Scene.' + node + '.Renderable.File")}')
                assert native['scale'] == mesh['scale_m'] and Path(native['file']) == Path(mesh['file'])
                name = mesh['layer']
                if name.endswith('_vectors'):
                    expected = [a['segment_m'] for a in full[name.split('_')[0]]['geometry']['arrows'] if a['drawn']]
                elif name == 'cut_border':
                    expected = [full['cut']['outline_m']]
                else:
                    source_edges = full['cut']['equipotentials']['contours'][int(name.split('_')[1])]['segments_m']
                    if 'source_segment_orders' in mesh:
                        expected = []
                        assert sorted(abs(i) - 1 for order in mesh['source_segment_orders'] for i in order) == list(range(len(source_edges)))
                        for order in mesh['source_segment_orders']:
                            path = []
                            for edge in order:
                                a, b = source_edges[abs(edge) - 1][::1 if edge > 0 else -1]
                                if path:
                                    assert path[-1] == a
                                else:
                                    path.append(a)
                                path.append(b)
                            expected.append(path)
                    else:
                        expected = source_edges
                loaded = vertices(native['file'])
                assert len(loaded) == len(expected) == mesh['segment_count']
                for display, scientific in zip(loaded, expected):
                    actual = display.astype(np.float32).astype(float) @ rotation(native['rotation']).T * native['scale'] + native['position']
                    reference = np.array(scientific) @ transform.T + root
                    difference = float(np.max(abs(actual - reference)))
                    maximum = max(maximum, difference)
                    assert difference <= mesh['conservative_display_position_error_bound_m'], (difference, mesh)
            page.locator('#view-fields').click()
            time.sleep(.6)
            assert lua('return openspace.navigation.getNavigationState()')['Anchor'] == full['render']['frame_node']
            page.evaluate('document.getElementById("fields-status").scrollIntoView({block:"start"})')
            time.sleep(.2)
            subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT / 'scripts/capture-window.ps1'), '-Name', 'cosmos2-fields-' + kind + '.png'], capture_output=True, check=True)
            page.locator('#toggle-fields').click()
            idle(page, '!appState.fields_visible')
            assert physical(get('state')['physics']) == baseline
            assert all(lua('return openspace.propertyValue("Scene.' + m['node'] + '.Renderable.Enabled")') is False for m in full['render']['meshes'])
            page.locator('#toggle-fields').click()
            idle(page, 'appState.fields_visible')
            # An old sample request must preserve the existing map/selected reading.
            before = get('state')
            try:
                post({'command': 'select_field_sample', 'map_id': 'old', 'layer': 'cut', 'index': 145})
            except urllib.error.HTTPError as error:
                assert error.code == 400
            else:
                raise AssertionError('Old map selection accepted')
            assert get('state')['fields_preview'] == before['fields_preview']
            page.locator('#save').click()
            idle(page)
            manifest = json.loads(latest.read_text())
            assert manifest['field_layers']['settings'] == definitions['settings']
            post({'command': 'resume'})
            time.sleep(.2)
            post({'command': 'pause'})
            page.evaluate('updateState()')
            idle(page)
            page.wait_for_function('document.getElementById("fields-status").textContent.includes("MAPA CONGELADO")')
            assert export(page)['reading_is_stale']
            # Replace a map while the camera is anchored to its old frame.
            page.locator('#measure-fields').click()
            idle(page)
            assert lua('return openspace.navigation.getNavigationState()')['Anchor'] == 'LabCameraAnchor'
            assert all(not lua('return openspace.hasSceneGraphNode("' + node + '")') for node in full['render']['nodes'])
            page.locator('#load').click()
            idle(page)
            restored = get('state')
            assert restored['physics']['field_layers'] == definitions
            assert restored['physics']['bodies'] == baseline['bodies'] and restored['physics']['time'] == baseline['time']
            assert restored['fields_preview'] is None
            page.locator('#prepare-fields').click()
            idle(page)
            fill(page, 'field-cut-offset', -4e9)
            fill(page, 'field-angle-2', -25)
            page.locator('#field-magnitude-scale').select_option('linear')
            page.locator('#apply-fields').click()
            idle(page, 'appState.physics.field_layers.revision===2')
            page.locator('#measure-fields').click()
            idle(page)
            moved = get('state')
            assert moved['fields_preview']['cut']['grid'] != summary['cut']['grid']
            before_clear = physical(moved['physics'])
            nodes = moved['fields_preview']['render']['nodes']
            page.locator('#clear-fields').click()
            idle(page, 'appState.fields_preview===null')
            assert physical(get('state')['physics']) == before_clear
            assert all(not lua('return openspace.hasSceneGraphNode("' + node + '")') for node in nodes)
            cases.append({'kind': kind, 'shared_map_probe_reading_exact': True, 'configure_sample_display_and_clear_physics_preserved': True,
                          'native_float32_max_component_difference_m': maximum, 'display_error_within_receipt_bound': True,
                          'poll_map_summary_bytes': summary_bytes, 'full_SI_export_stamped': True,
                          'checkpoint_definition_phase_exact': True, 'stale_and_old_selection_guarded': True,
                          'camera_survives_map_replacement': True, 'cut_moves_rotates_and_changes_scale': True})
finally:
    try:
        post({'command': 'atlas'})
    finally:
        socket.close()
        if saved is None:
            latest.unlink(missing_ok=True)
        else:
            latest.write_bytes(saved)
assert not errors, errors
assert get('atlas/state')['epoch'] == atlas['epoch']
report = {'browser': 'native CEF', 'generation': state['scientific_generation']['model_version'], 'cases': cases, 'page_errors': errors,
          'checkpoint_pointer_restored': True, 'atlas_epoch_preserved': True,
          'scope': 'Partial C2-11 maps/probes; no J2/material tides/branch charts or256/10k profiles acceptance.'}
(ROOT / 'evidence/gravity-fields-ui-check.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
