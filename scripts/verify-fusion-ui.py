"""Real controls, timeline, native JSON export and scene isolation."""
from pathlib import Path
import argparse
import json
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from forces import evaluate
parser = argparse.ArgumentParser()
parser.add_argument('--native', action='store_true')
args = parser.parse_args()
base = 'http://127.0.0.1:' + ('4700' if args.native else '4701')
save_path = ROOT / 'user/forces/latest.json'
original = save_path.read_bytes() if save_path.exists() else None
errors = []


def get(path):
    return json.load(urllib.request.urlopen(base + path, timeout=20))


def settled(page):
    page.wait_for_function('response&&response.result.fusion&&!pending')
    assert 'Cálculo concluído' in page.locator('#force-status').inner_text(), page.locator('#force-status').inner_text()


def apply(page, key, value):
    page.evaluate('document.querySelector(' + json.dumps('[name="' + key + '"]') + ').value=' + json.dumps(str(value)))
    page.locator('#calculate').click()
    settled(page)


def capture(page, label, selector='#science-view'):
    page.evaluate('document.querySelector(' + json.dumps(selector) + ').scrollIntoView({block:"center"})')
    if args.native:
        subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                        str(ROOT / 'scripts/capture-window.ps1'), '-Name', f'cosmos2-native-fusion-{label}.png'],
                       check=True, capture_output=True)
    else:
        page.screenshot(path=str(ROOT / f'evidence/fusion-ui-{label}.png'), full_page=True)


def exercise(page):
    page.on('pageerror', lambda error: errors.append(str(error)))
    before, physics = get('/api/atlas/state'), get('/api/state')['physics']
    page.goto(base + '/forces.html#fusion')
    settled(page)
    examples = []
    for mixture, species_count, radiative in [('dt', 4, False), ('dd', 5, False), ('dp', 3, True),
                                               ('he3he3', 3, False), ('li7p', 3, False), ('c12alpha', 3, True)]:
        page.locator('[name="mixture"]').select_option(mixture)
        settled(page)
        page.locator('#fusion-conditions').click()
        settled(page)
        f = page.evaluate('response.result.fusion')
        assert len(f['species']) == species_count
        assert page.locator('#fusion-composition tbody tr').count() == species_count
        assert .15 < f['mass_fractions'][-1][0] / f['mass_fractions'][0][0] < .25
        assert page.locator('[data-effect="fusion_radiative_capture"]').count() == int(radiative)
        assert page.evaluate('!document.querySelector(\'[data-parameter="partner_ratio"]\').hidden') != (mixture in ('dd', 'he3he3'))
        first = f['species'][0]
        initial = f['initial_density_m3'][first]
        page.evaluate('document.getElementById("time-index").value="0";document.getElementById("time-index").dispatchEvent(new Event("input"));')
        assert page.locator('#fusion-composition tbody tr').count() == species_count
        initial_reading = page.locator('#fusion-composition tbody tr:nth-child(1)').inner_text()
        page.evaluate('document.getElementById("time-index").value="240";document.getElementById("time-index").dispatchEvent(new Event("input"));')
        assert page.locator('#fusion-composition tbody tr:nth-child(1)').inner_text() != initial_reading
        hash_before = page.evaluate('response.physics_sha256')
        page.locator('#chart-axis').select_option('log')
        page.locator('[data-curve="0"]').set_checked(False)
        assert page.evaluate('response.physics_sha256') == hash_before
        page.locator('[data-curve="0"]').set_checked(True)
        page.locator('#chart-axis').select_option('linear')
        if mixture == 'dd':
            page.locator('[data-effect="fusion_ddp"]').set_checked(False)
            settled(page)
            assert page.evaluate('response.result.fusion.reaction_extents_m3[240][1]') == 0
            assert page.evaluate('response.result.reference.composition.reaction_extents_m3[240][1]') > 0
            capture(page, 'dd')
            capture(page, 'dd-readings', '#fusion-composition')
            page.locator('[data-effect="fusion_ddp"]').set_checked(True)
            settled(page)
        if radiative:
            page.locator('[data-force="electromagnetic"][data-control="acting"]').set_checked(False)
            settled(page)
            assert page.evaluate('response.result.fusion.energy_available_J_m3[240]') == 0
            assert page.evaluate('response.result.reference.composition.energy_available_J_m3[240]') > 0
            if mixture == 'dp': capture(page, 'radiative-off')
            page.locator('[data-force="electromagnetic"][data-control="acting"]').set_checked(True)
            settled(page)
        before_hide = page.evaluate('response.result')
        page.locator('[data-force="strong"][data-control="visible"]').set_checked(False)
        settled(page)
        assert page.evaluate('response.result') == before_hide
        page.locator('[data-force="strong"][data-control="visible"]').set_checked(True)
        settled(page)
        examples.append({'mixture': mixture, 'species': species_count, 'radiative': radiative})
    # Native export creates an actual local file; not a CEF download gesture.
    page.locator('#save-forces').click()
    page.wait_for_function('document.getElementById("force-status").textContent.startsWith("Condições, controles")')
    saved = page.evaluate('config')
    page.locator('[name="mixture"]').select_option('dt')
    settled(page)
    page.locator('#load-forces').click()
    page.wait_for_function('!pending&&!document.getElementById("restoration-note").hidden')
    assert page.evaluate('config') == saved
    assert page.evaluate('document.getElementById("restoration-note").dataset.state') == 'same_generation'
    page.locator('#export-forces').click()
    page.wait_for_function('!pending&&lastForcesExport')
    exported = page.evaluate('lastForcesExport')
    on_disk = json.loads(Path(exported['export_file']).read_text(encoding='utf-8'))
    # JS Number may round large numeric values on the browser boundary.
    # The local artifact must retain the authoritative backend result exactly.
    assert {k: v for k, v in on_disk.items() if k != 'export_file'} == evaluate(on_disk['configuration'])
    assert on_disk['physics_sha256'] == exported['physics_sha256']
    assert exported['physics_sha256'] == page.evaluate('response.physics_sha256')
    page.locator('.fusion-mass-link').click()
    page.wait_for_function('energyResult&&!energyBusy')
    assert page.evaluate('document.getElementById("energy-preset").value') == 'c12alpha'
    page.goto(base + '/forces.html#fusion')
    settled(page)
    duration = page.evaluate('config.parameters.duration_s')
    old_burn = page.evaluate('response.result.fusion.mass_fractions[240][0]')
    apply(page, 'temperature_K', 1e7)
    assert page.evaluate('config.parameters.duration_s') == duration
    assert page.evaluate('response.result.fusion.mass_fractions[240][0]') > old_burn
    # Reject an API request without mutating accepted display or renderer state.
    identity = page.evaluate('response.physics_sha256')
    invalid = page.evaluate('fetch("/api/forces/evaluate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({scenario:"fusion",parameters:{duration_s:0}})}).then(async r=>({status:r.status,body:await r.json()}))')
    assert invalid['status'] == 400 and invalid['body']['ok'] is False
    assert page.evaluate('response.physics_sha256') == identity
    if not args.native:
        page.set_viewport_size({'width': 720, 'height': 900})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        capture(page, '720')
    assert get('/api/atlas/state')['bodies'] == before['bodies']
    assert get('/api/atlas/state')['epoch'] == before['epoch']
    assert get('/api/state')['physics'] == physics
    page.goto(base + '/')
    assert not errors, errors
    return examples, exported


try:
    if args.native:
        from cef_page import Page
        with Page() as page:
            examples, exported = exercise(page)
    else:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            examples, exported = exercise(browser.new_page(viewport={'width': 1600, 'height': 1080}))
            browser.close()
finally:
    if original is None: save_path.unlink(missing_ok=True)
    else: save_path.write_bytes(original)

report = {'ok': True, 'browser': 'native CEF' if args.native else 'Windows Edge', 'mixtures': examples,
          'timeline_updates_rates_composition_energy': True, 'view_does_not_change_physics': True,
          'DD_channels_independent_shared_fuel': True, 'EM_off_suppresses_radiative_capture': True,
          'reference_preserved': True, 'explicit_comparison_conditions': True,
          'fixed_physical_duration_after_temperature_change': True, 'generation_save_load': True,
          'actual_JSON_export': exported['export_file'], 'linked_mass_preset': True,
          'invalid_request_and_scene_preserved': True, 'user_save_restored': True,
          'page_errors': errors, 'overflow_720': None if args.native else False}
name = 'native-fusion-check.json' if args.native else 'fusion-ui-check.json'
(ROOT / 'evidence' / name).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
