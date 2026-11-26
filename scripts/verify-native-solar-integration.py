"""Verify the isolated four-center candidate through its real OpenSpace CEF UI."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import math
import subprocess
import time
import traceback
import urllib.error
import urllib.request
import zipfile

from cef_page import Page
from importlib.machinery import SourceFileLoader

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:4700'
APP = ROOT / 'output/is12-solar-product/app'
EXPECTED_IDS = ['sol:naif:10', 'sol:naif:399', 'sol:naif:301', 'sol:naif:599']
LIMITS = {'native_position_component_m': .001, 'field_component_m_s2': 1e-12}
engine = SourceFileLoader('solar_test_engine', str(ROOT / 'scripts/engine-command.py')).load_module()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get(path):
    return json.load(urllib.request.urlopen(BASE + path, timeout=15))


def post(path, payload, expected=200):
    request = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                     headers={'Content-Type': 'application/json'})
    try:
        response = urllib.request.urlopen(request, timeout=70)
    except urllib.error.HTTPError as error:
        assert error.code == expected, (error.code, error.read().decode())
        return json.load(error)
    assert response.status == expected, response.status
    return json.load(response)


def native(code):
    response = engine.execute(code)
    assert 'payload' in response, response
    return response['payload']['1']


def guard(p):
    return {'system_id': p['system_id'], 'edit_token': p['edit_token'], 'revision': p['revision'],
            'expected_time': p['time'], 'frame': p['contract']['frame']}


def phase(p):
    return {key: p[key] for key in ['system_id', 'edit_token', 'revision', 'time', 'bodies', 'atlas_initial', 'interventions']}


def idle(page):
    page.wait_for_function('!pending', timeout=70000)


def click(page, selector):
    page.wait_for_function('document.querySelector('+json.dumps(selector)+')&&!document.querySelector('+json.dumps(selector)+').disabled', timeout=70000)
    page.locator(selector).click()
    idle(page)


def positions(p):
    rows = native('return {positions={' + ','.join(
        'openspace.propertyValue("Scene.' + b['scene_node'] + '.Translation.Position")'
        for b in p['bodies']) + '}}')['positions']
    matrix = p['atlas_initial']['j2000_to_render_frame']
    scale = p['physical_scale']['length_unit_m']
    expected = [[sum(row[k] * b['position'][k] for k in range(3)) * scale for row in matrix]
                for b in p['bodies']]
    error = max(abs(x-y) for i, row in enumerate(expected) for x, y in zip(rows[str(i+1)], row))
    assert error <= LIMITS['native_position_component_m'], (error, rows, expected)
    return error


def capture(label, name):
    filename = 'cosmos2-is12-' + label + '-' + name + '.png'
    subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                    str(ROOT / 'scripts/capture-window.ps1'), '-Name', filename],
                   check=True, capture_output=True)
    path = ROOT / 'evidence' / filename
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label.')
    folder = ROOT / ('output/is12-native-' + args.label)
    receipt = ROOT / ('evidence/is12-native-' + args.label + '.json')
    if folder.exists() or receipt.exists():
        raise FileExistsError('This label already has evidence; preserve it.')
    folder.mkdir()
    files = sorted(p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    files += [Path(__file__).resolve(), ROOT / 'scripts/cef_page.py', ROOT / 'scripts/capture-window.ps1',
              ROOT / 'scripts/start-is12-solar-candidate.ps1']
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in files}
    archive = folder / 'executed-sources.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.relative_to(ROOT).as_posix())
    baseline = json.loads((ROOT / 'evidence/is12-solar-candidate-prepared-20261023.json').read_text())
    owner = ROOT / 'user/sessions/latest.json'
    owner_before = sha(owner)
    report = {'schema': 1, 'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'session': json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig')),
              'source_sha256': hashes, 'source_archive': archive.relative_to(ROOT).as_posix(),
              'source_archive_sha256': sha(archive), 'limits_before_execution': LIMITS,
              'checks': {}, 'captures': [], 'completed': False, 'accepted': False,
              'scope': 'Real OpenSpace CEF/API/worker/native translations and persistence. Captures require separate visual review; no performance or EM/nuclear integration acceptance.'}

    def persist():
        receipt.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')

    persist()
    try:
        assert report['session'].get('solarIntegrationCandidate') is True
        assert report['session']['storage'].replace('\\', '/').endswith('/output/is12-solar-product/gravity-sessions')
        errors = []
        with Page() as page:
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(BASE + '/')
            page.wait_for_function('atlasState&&appState?.mode==="atlas"&&!$("copy-solar").disabled', timeout=30000)
            before = get('/api/atlas/state')
            original = get('/api/state')['physics']
            for path, payload in [('/api/solar/reference', {'utc': '2051-01-01T00:00:00Z'}),
                                  ('/api/solar/reference', {'utc': '2026-02-31T12:00:00Z'}),
                                  ('/api/solar/experiment', {'utc': before['epoch']['utc'], 'initial_state': {}}),
                                  ('/api/solar/experiment', {'utc': True})]:
                assert post(path, payload, 400)['ok'] is False
                after = get('/api/atlas/state')
                assert after['epoch'] == before['epoch'] and after['bodies'] == before['bodies']
                assert get('/api/state')['physics'] == original
            reference = post('/api/solar/reference', {'utc': before['epoch']['utc']})['reference']
            assert [b['id'] for b in reference['bodies']] == EXPECTED_IDS
            assert all(b['entity_kind'] == 'physical_body' for b in reference['bodies'])
            assert reference['bodies'][3]['naif_id'] == '599'
            report['checks']['reference_and_four_transactional_API_refusals'] = True
            persist()

            click(page, '#copy-solar')
            page.wait_for_function('appState?.physics?.atlas_initial?.kind==="solar_four_physical_centers"&&!pending', timeout=70000)
            first = get('/api/state')['physics']
            initial = first['atlas_initial']
            (folder / 'initial-snapshot.json').write_text(json.dumps(first, indent=2, ensure_ascii=False), encoding='utf-8')
            assert first['paused'] and first['time'] == 0 and len(first['bodies']) == 4
            assert [b['reference_id'] for b in first['bodies']] == EXPECTED_IDS
            assert initial['reference_catalog'] == reference
            assert page.evaluate('$("fixture").value') == 'atlas'
            assert 'Júpiter' in page.locator('#lab-intro').inner_text()
            assert '4 corpos' in page.locator('#lab-grid-note').inner_text()
            report['checks']['paused_four_physical_center_import'] = True
            report['checks']['native_initial_position_max_m'] = positions(first)
            report['captures'].append(capture(args.label, 'system'))
            click(page, '#solar-panel > summary')
            readings = []
            for body in first['bodies']:
                page.locator('#solar-body').select_option(body['id'])
                click(page, '#solar-sample')
                page.wait_for_function('solarReading?.body_id==='+json.dumps(body['id'])+'&&!pending')
                reading = page.evaluate('solarReading')
                assert reading['body_reference_id'] == body['reference_id']
                assert reading['time'] == 0 and len(reading['sources']) == 3
                assert body['id'] not in [s['id'] for s in reading['sources']]
                assert get('/api/state')['physics']['bodies'] == first['bodies']
                error = 0.
                for source in reading['sources']:
                    other = next(b for b in first['bodies'] if b['id'] == source['id'])
                    delta = [(other['position'][k]-body['position'][k])*first['physical_scale']['length_unit_m'] for k in range(3)]
                    radius = math.hypot(*delta)
                    expected = [other['applied_GM_m3_s2'] * v / radius**3 for v in delta]
                    error = max(error, *(abs(x-y) for x, y in zip(expected, source['acceleration_m_s2'])))
                assert error <= LIMITS['field_component_m_s2'], error
                assert all(math.isclose(math.fsum(s['acceleration_m_s2'][k] for s in reading['sources']),
                                        reading['acceleration_m_s2'][k], rel_tol=1e-14, abs_tol=1e-18) for k in range(3))
                assert page.locator('[data-solar-source]').count() == 3
                assert body['reference_id'] in page.locator('#solar-capabilities').inner_text()
                click(page, '#solar-view-body')
                time.sleep(.15)
                assert native('return {anchor=openspace.navigation.getNavigationState().Anchor}')['anchor'] == body['scene_node']
                readings.append({'id': body['reference_id'], 'component_error_m_s2': error,
                                 'native_camera_anchor': body['scene_node'], 'reading': reading})
                if body['reference_id'] in ['sol:naif:399', 'sol:naif:599']:
                    report['captures'].append(capture(args.label, 'body-' + body['reference_id'].split(':')[-1]))
            report['checks']['passive_readings_and_selection_cameras'] = readings
            persist()

            checkpoint = get('/api/state')['physics']
            for change in [{'body_id': 'missing'}, {'revision': checkpoint['revision']+1},
                           {'expected_time': checkpoint['time']+1}, {'frame': 'SSB'}, {'edit_token': 'stale'}]:
                payload = {**guard(checkpoint), 'command': 'solar_reading', 'body_id': checkpoint['bodies'][1]['id'], **change}
                assert post('/api/command', payload, 400)['ok'] is False
                assert phase(get('/api/state')['physics']) == phase(checkpoint)
            post('/api/solar/experiment', {'utc': before['epoch']['utc']}, 400)
            post('/api/command', {'command': 'import_atlas', 'initial_state': initial}, 400)
            assert phase(get('/api/state')['physics']) == phase(checkpoint)
            report['checks']['seven_experiment_refusals_without_phase_mutation'] = True

            click(page, '#lab-earth-moon')
            time.sleep(.2)
            assert native('return {anchor=openspace.navigation.getNavigationState().Anchor}')['anchor'] == 'LabPairFrame'
            report['captures'].append(capture(args.label, 'earth-moon'))
            click(page, '#lab-home')
            assert native('return {anchor=openspace.navigation.getNavigationState().Anchor}')['anchor'] == 'LabFrame'
            click(page, '#play')
            page.wait_for_function('!pending&&appState.physics.time>0&&!appState.physics.paused')
            time.sleep(.3)
            click(page, '#play')
            page.wait_for_function('appState.physics.paused&&!pending')
            evolved = get('/api/state')['physics']
            assert evolved['time'] > 0 and evolved['bodies'][1]['position'] != first['bodies'][1]['position']
            assert evolved['atlas_initial'] == initial and evolved['revision'] == 0
            assert 'Amostra fixa' in page.locator('#solar-reading').inner_text()
            report['checks']['native_evolved_position_max_m'] = positions(evolved)
            report['checks']['pause_evolution_and_stale_reading'] = True

            click(page, '#save')
            saved = get('/api/state')['physics']
            branch = post('/api/command', {**guard(saved), 'command': 'create_branch', 'name': 'IS12 ' + args.label})['ack']['result']
            click(page, '#reset')
            page.wait_for_function('appState.physics.time===0&&!pending')
            assert get('/api/state')['physics']['bodies'] == first['bodies']
            click(page, '#load')
            page.wait_for_function('appState.physics.time>0&&!pending')
            loaded = get('/api/state')['physics']
            assert loaded['bodies'] == saved['bodies'] and loaded['time'] == saved['time']
            assert loaded['atlas_initial'] == initial and loaded['restoration']['status'] == 'same_generation'
            assert 'mesma geração' in page.locator('#lab-restoration').inner_text()
            click(page, '#reset')
            reset = get('/api/state')['physics']
            post('/api/command', {**guard(reset), 'command': 'load_branch', 'branch_id': branch['id']})
            restored = get('/api/state')['physics']
            assert restored['bodies'] == saved['bodies'] and restored['time'] == saved['time'] and restored['atlas_initial'] == initial
            report['checks']['exact_native_checkpoint_branch_and_restart'] = True
            report['checks']['native_restored_position_max_m'] = positions(restored)
            persist()

            # Reload the CEF document: the worker keeps the confirmed phase and provenance.
            page.goto(BASE + '/')
            page.wait_for_function('appState?.physics?.atlas_initial?.kind==="solar_four_physical_centers"&&!pending')
            assert get('/api/state')['physics']['bodies'] == saved['bodies']
            assert page.locator('#solar-body').count() == 1
            click(page, '#atlas')
            page.wait_for_function('appState.mode==="atlas"&&!pending')
            after = get('/api/atlas/state')
            assert after['epoch'] == before['epoch'] and after['bodies'] == before['bodies']
            click(page, '#experiment')
            assert get('/api/state')['physics']['bodies'] == saved['bodies']
            click(page, '#atlas')
            click(page, '#copy-atlas')
            page.wait_for_function('appState?.physics?.bodies.length===3&&!pending')
            legacy = get('/api/state')['physics']
            assert legacy['atlas_initial']['kind'] == 'atlas_sun_earth_moon'
            assert [b['reference_id'] for b in legacy['bodies']] == EXPECTED_IDS[:3]
            assert page.evaluate('$("solar-panel").hidden') is True
            click(page, '#atlas')
            click(page, '#copy-solar')
            page.wait_for_function('appState?.physics?.bodies.length===4&&!pending')
            click(page, '#lab-origin > summary')
            assert page.locator('[data-reference-id]').count() == 4
            assert '126686531.9003704' in page.locator('#lab-source-GM').inner_text()
            report['captures'].append(capture(args.label, 'provenance'))
            report['checks']['CEF_reload_Atlas_return_and_legacy_import'] = True
            report['checks']['page_errors'] = errors
            assert not errors, errors
        assert sha(owner) == owner_before == baseline['owner_pointer_sha256']
        assert all(sha(ROOT / name) == value for name, value in baseline['base_files_sha256'].items())
        assert all(sha(ROOT / name) == value for name, value in hashes.items())
        report['checks']['owner_and_installed_preserved'] = True
        report['completed'] = report['accepted'] = True
    except Exception:
        report['failure'] = traceback.format_exc()
    finally:
        report['finished_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
        report['owner_pointer_preserved'] = sha(owner) == owner_before
        persist()
    print(json.dumps({'receipt': receipt.relative_to(ROOT).as_posix(), 'completed': report['completed'],
                      'accepted': report['accepted'], 'failure': report.get('failure')}, ensure_ascii=False))
    return 0 if report['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
