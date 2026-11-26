"""Exercise the energy instrument in Edge and the actual OpenSpace CEF."""
from pathlib import Path
import argparse
import json
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--native', action='store_true')
args = parser.parse_args()
base = 'http://127.0.0.1:' + ('4700' if args.native else '4701')
path = ROOT / 'user/nuclei/energies-selection.json'
original = path.read_bytes() if path.exists() else None
errors = []


def get(route):
    return json.load(urllib.request.urlopen(base + route))


def settled(page):
    page.wait_for_function('energyResult && !energyBusy')


def fill(page, selector, value):
    page.evaluate('(() => {const e=document.querySelector(' + json.dumps(selector) + ');e.value=' + json.dumps(str(value)) + ';e.dispatchEvent(new Event("input",{bubbles:true}));})()')


def capture(page, label):
    if args.native:
        subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                        str(ROOT / 'scripts/capture-window.ps1'), '-Name', f'cosmos2-native-nuclear-energy-{label}.png'], check=True, capture_output=True)
    else:
        page.screenshot(path=str(ROOT / f'evidence/nuclear-energy-ui-{label}.png'), full_page=True)


def exercise(page):
    page.on('pageerror', lambda error: errors.append(str(error)))
    before, physics = get('/api/atlas/state'), get('/api/state')['physics']
    page.goto(base + '/nuclei.html')
    page.wait_for_function('nuclearCatalog&&nuclearCatalog.records.length===3558')
    page.locator('[data-nuclear-id="nucleus:ame2020:26:56"]').click()
    page.locator('#nuclear-energy-link').click()
    settled(page)
    assert page.evaluate('energyConfig.separation_id') == 'nucleus:ame2020:26:56'
    assert page.evaluate('energyResult.Q.value') == 17589.299865
    capture(page, 'dt')
    page.locator('#energy-preset').select_option('n14-n2n')
    settled(page)
    q = page.evaluate('energyResult.Q')
    identity = page.evaluate('energyResult.reaction_sha256')
    assert page.evaluate('energyResult.kinematics.accessible_by_energy') is True
    fill(page, '#incident-energy', 10)
    page.locator('#calculate-energy').click()
    settled(page)
    assert page.evaluate('energyResult.kinematics.accessible_by_energy') is False
    assert 'insuficiente' in page.locator('#kinematic-reading').inner_text()
    assert page.evaluate('energyResult.Q') == q and page.evaluate('energyResult.reaction_sha256') == identity
    capture(page, 'threshold')
    page.evaluate('document.getElementById("energy-slider").value="14";document.getElementById("energy-slider").dispatchEvent(new Event("input"));document.getElementById("energy-slider").dispatchEvent(new Event("change"));')
    settled(page)
    assert page.evaluate('energyResult.kinematics.accessible_by_energy') is True
    page.locator('#save-energy').click()
    settled(page)
    saved = page.evaluate('energyConfig')
    page.locator('#energy-preset').select_option('c12-photo3alpha')
    settled(page)
    assert page.evaluate('energyResult.kinematics.projectile_rest_keV') == 0
    page.locator('#load-energy').click()
    settled(page)
    assert page.evaluate('energyConfig') == saved
    assert 'mesma geração' in page.locator('#energy-restoration').inner_text()
    page.locator('#export-energy').click()
    page.wait_for_function('!energyBusy&&lastEnergyExport')
    exported = page.evaluate('lastEnergyExport')
    assert json.loads(Path(exported['export_file']).read_text(encoding='utf-8')) == exported
    assert exported['Q']['covariances_included'] is False
    # Invalid balanced-editor draft must preserve the accepted result.
    prior = page.evaluate('energyResult.configuration_sha256')
    fill(page, '#energy-target', 'C-12')
    page.locator('#calculate-energy').click()
    settled(page)
    assert page.evaluate('energyResult.configuration_sha256') == prior
    assert 'não conserva' in page.locator('#energy-status').inner_text()
    page.locator('#energy-preset').select_option('dt')
    settled(page)
    fill(page, '#energy-products .product-row:nth-child(1) input[list]', 'H-2')
    fill(page, '#energy-products .product-row:nth-child(2) input[list]', 'H-3')
    page.locator('#calculate-energy').click()
    settled(page)
    assert page.evaluate('energyResult.Q.value') == 0
    assert page.evaluate('energyResult.Q.terms.length') == 0
    assert page.evaluate('energyResult.Q.standard_uncertainty_independent') == 0
    fill(page, '#separation-species', 'H-1')
    page.locator('#calculate-separation').click()
    settled(page)
    assert page.locator('#separation-table').inner_text().count('Remanescente ausente') == 4
    # Actual editable extrapolated channel: n + Li-3 -> H-1 + He-3.
    fill(page, '#energy-projectile', 'n')
    fill(page, '#energy-target', 'Li-3')
    fill(page, '#energy-products .product-row:nth-child(1) input[list]', 'H-1')
    fill(page, '#energy-products .product-row:nth-child(2) input[list]', 'He-3')
    page.locator('#calculate-energy').click()
    settled(page)
    assert 'Estimativa (#)' in page.locator('#q-uncertainty').inner_text()
    page.locator('#mass-details summary').click()
    capture(page, 'estimated')
    if not args.native:
        page.set_viewport_size({'width': 720, 'height': 900})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        capture(page, '720')
    assert get('/api/atlas/state')['bodies'] == before['bodies']
    assert get('/api/atlas/state')['epoch'] == before['epoch']
    assert get('/api/state')['physics'] == physics
    page.goto(base + '/')
    assert not errors, errors
    return exported


try:
    if args.native:
        from cef_page import Page
        with Page() as page:
            exported = exercise(page)
    else:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            exported = exercise(browser.new_page(viewport={'width': 1600, 'height': 1080}))
            browser.close()
finally:
    if original is None:
        path.unlink(missing_ok=True)
    else:
        path.write_bytes(original)

report = {'ok': True, 'browser': 'native CEF' if args.native else 'Windows Edge',
          'catalog_link_preserves_selected_nucleus': True, 'presets_and_editor': True,
          'energy_slider_crosses_threshold': True, 'energy_change_preserves_Q_identity': True,
          'invalid_draft_preserves_result': True, 'same_mass_cancels_exactly': True,
          'unknown_and_estimates_visible': True, 'save_load_and_real_export': True,
          'source_scene_and_worker_preserved': True, 'user_save_restored': True,
          'overflow_720': None if args.native else False, 'page_errors': errors,
          'export_file': exported['export_file'], 'generation': exported['generation']}
name = 'native-nuclear-energy-check.json' if args.native else 'nuclear-energy-ui-check.json'
(ROOT / 'evidence' / name).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
