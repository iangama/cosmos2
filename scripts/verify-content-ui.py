"""Property and package consultation via real HTTP, Edge and native CEF."""
from pathlib import Path
import argparse
import json
import subprocess
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(); parser.add_argument('--native', action='store_true'); args = parser.parse_args()
port = 4700 if args.native else 4701
BASE = f'http://127.0.0.1:{port}'
errors = []


def get(path):
    return json.load(urllib.request.urlopen(BASE + path, timeout=10))


def capture(page, label):
    if args.native:
        subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                        str(ROOT / 'scripts/capture-window.ps1'), '-Name', f'cosmos2-native-content-{label}.png'], check=True, capture_output=True)
    else:
        page.screenshot(path=str(ROOT / f'evidence/content-ui-{label}.png'), full_page=True)


def assert_export(payload):
    # Playwright's object transport can serialize a float <1e21 as an integer
    # literal. Compare JSON number values as binary64, matching the browser's
    # semantics; scientific identifiers remain strings in both representations.
    disk = json.loads(Path(payload['export_file']).read_text(encoding='utf-8'), parse_int=float)
    browser = json.loads(json.dumps(payload), parse_int=float)
    assert disk == browser


def exercise(page):
    page.on('pageerror', lambda error: errors.append(str(error)))
    before = get('/api/atlas/state'); physics_before = get('/api/state')['physics']
    page.goto(BASE + '/content.html?body=399')
    page.wait_for_function('contentAtlas&&packageCatalog&&document.querySelectorAll(".property-card").length===7')
    assert page.evaluate('packageCatalog.packages.length') == 13
    assert page.evaluate('contentAtlas.observer.light_time_applied') is False
    assert 'emissão e recepção: não calculados' in page.locator('.coordinate-note').inner_text()
    assert '398600.435544' in page.locator('[data-property-id="GM"]').inner_text()
    assert 'forma adotada' in page.locator('[data-property-id="shape"]').inner_text().lower()
    assert 'imagem de superfície' in page.locator('[data-property-id="texture"]').inner_text().lower()
    assert page.evaluate('contentAtlas.bodies.every(b=>b.properties.every(p=>p.uncertainty.value===null))')
    capture(page, 'earth-properties')
    page.locator('#reference-body').select_option('10')
    assert 'Não cadastrado / desconhecido' in page.locator('[data-property-id="shape"]').inner_text()
    assert 'Não cadastrado / desconhecido' in page.locator('[data-property-id="texture"]').inner_text()
    page.locator('[data-property-id="mass"] summary').click()
    assert 'Contribuição de G, isoladamente' in page.locator('[data-property-id="mass"]').inner_text()
    page.locator('#reference-body').select_option('301')
    assert 'LRO WAC' in page.locator('[data-property-id="texture"]').inner_text()
    assert '1.737.400' in page.locator('[data-property-id="shape"]').inner_text()
    page.locator('#export-properties').click()
    page.wait_for_function('!contentBusy&&lastContentExport?.atlas')
    export_atlas = page.evaluate('lastContentExport')
    assert_export(export_atlas)
    assert export_atlas['atlas']['epoch'] == before['epoch']
    assert len(export_atlas['atlas']['bodies'][0]['properties']) == 7
    page.locator('#show-packages').click()
    assert page.locator('[data-package-id]').count() == 13
    page.locator('#verify-package').click()
    page.wait_for_function('!contentBusy&&packageCatalog.packages[0].last_verification?.status==="verified"')
    assert 'Conferido' in page.locator('#verification-status').inner_text()
    assert page.evaluate('packageCatalog.packages[0].last_verification.files.every(f=>f.status==="verified")')
    capture(page, 'solar-package')
    page.locator('[data-package-id="stars:amnh"]').click()
    assert 'redistribuição' in page.locator('#package-metadata').inner_text()
    assert 'uso público e comercial' in page.locator('#package-metadata').inner_text()
    page.evaluate('document.getElementById("package-search").value="ligação";document.getElementById("package-search").dispatchEvent(new Event("input",{bubbles:true}))')
    assert page.locator('[data-package-id]').count() == 1
    page.locator('[data-package-id="nuclear:ame2020"]').click()
    assert '3.558 estados' in page.locator('#package-metadata').inner_text()
    page.locator('#verify-package').click()
    page.wait_for_function('!contentBusy&&packageCatalog.packages.find(p=>p.id==="nuclear:ame2020").last_verification?.status==="verified"')
    page.locator('#export-packages').click()
    page.wait_for_function('!contentBusy&&lastContentExport?.catalog')
    export_packages = page.evaluate('lastContentExport')
    assert_export(export_packages)
    assert len(export_packages['catalog']['packages']) == 13
    page.evaluate('document.getElementById("package-search").value="";document.getElementById("package-search").dispatchEvent(new Event("input",{bubbles:true}))')
    page.locator('[data-package-id="science:cno1"]').click()
    assert 'CNO-I' in page.locator('#package-title').inner_text()
    assert page.locator('#package-files tr').count() == 7
    assert export_packages['catalog']['packages'][0]['last_verification']['status'] == 'verified'
    page.evaluate('document.getElementById("package-search").value="inexistente";document.getElementById("package-search").dispatchEvent(new Event("input",{bubbles:true}))')
    assert 'Nenhum pacote encontrado' in page.locator('#package-list').inner_text()
    request = urllib.request.Request(BASE + '/api/packages/verify', data=b'{"package_id":"../../outside"}', headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(request, timeout=5)
    except urllib.error.HTTPError as error:
        assert error.code == 400 and 'desconhecido' in json.load(error)['error']
    else:
        raise AssertionError('Unknown package accepted')
    assert get('/api/atlas/state')['bodies'] == before['bodies']
    assert get('/api/atlas/state')['epoch'] == before['epoch']
    assert get('/api/state')['physics'] == physics_before
    if not args.native:
        page.set_viewport_size({'width': 720, 'height': 900})
        page.locator('#show-properties').click()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        capture(page, '720')
    page.locator('.back').click()
    page.wait_for_function('atlasState&&appState')
    assert page.locator('#open-content').count() == 1
    page.locator('#open-content').click()
    page.wait_for_function('contentAtlas&&packageCatalog')
    assert not errors, errors
    page.locator('.back').click()
    page.wait_for_function('atlasState&&appState')
    page.locator('#export-atlas').click()
    page.wait_for_function('document.getElementById("notice").textContent.startsWith("Estado e fontes salvos: ")')
    main_export_path = page.locator('#notice').inner_text().removeprefix('Estado e fontes salvos: ')
    main_export = json.loads(Path(main_export_path).read_text(encoding='utf-8'))
    assert main_export['atlas']['epoch'] == before['epoch'] and len(main_export['atlas']['bodies'][0]['properties']) == 7
    return {'atlas_export_file': export_atlas['export_file'], 'packages_export_file': export_packages['export_file'], 'main_atlas_export_file': main_export_path}


if args.native:
    from cef_page import Page
    with Page() as page:
        exports = exercise(page)
else:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        try:
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            exports = exercise(page)
        finally:
            browser.close()

report = {'browser': 'OpenSpace CEF' if args.native else 'Edge Windows headless',
          'three_bodies_seven_properties': True, 'unknown_shape_texture_sun': True,
          'inferred_mass_G_contribution_not_total': True, 'geometric_observer_no_light_time': True,
          'package_filter_and_empty_result': True, 'solar_AME_SHA256_verified': True,
          'AMNH_terms_visible': True, 'actual_local_JSON_exports': exports,
          'consultation_verification_no_scene_worker_mutation': True, 'unknown_package_refused': True,
          'return_to_atlas_and_open_from_main': True, 'page_errors': errors,
          'overflow_720_checked': not args.native,
          'scope': 'Consultation UI and local content integrity, not renderer performance or installer validation.'}
(ROOT / ('evidence/native-content-check.json' if args.native else 'evidence/content-ui-check.json')).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
