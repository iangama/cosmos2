"""Reference instrument through real local HTTP, Edge or native CEF."""
from pathlib import Path
import argparse
import json
import subprocess
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(); parser.add_argument('--native', action='store_true'); args = parser.parse_args()
errors = []; port = 4700 if args.native else 4701
base = f'http://127.0.0.1:{port}'
saved_path = ROOT / 'user/nuclei/selection.json'
saved_original = saved_path.read_bytes() if saved_path.exists() else None

def screenshot(page, label):
    if args.native:
        subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                        str(ROOT / 'scripts/capture-window.ps1'), '-Name', f'cosmos2-native-nuclei-{label}.png'],
                       check=True, capture_output=True)
    else:
        page.screenshot(path=str(ROOT / f'evidence/nuclei-ui-{label}.png'), full_page=True)

def exercise(page):
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(base + '/nuclei.html')
    page.wait_for_function('nuclearCatalog&&nuclearCatalog.records.length===3558')
    assert page.evaluate('nuclearHits.length') == 3558
    assert page.evaluate('nuclearCatalog.scientific_contract.time') is None
    original = page.evaluate('nuclearCatalog.generation')
    page.locator('#fit-nuclei').click()
    screenshot(page, 'chart')
    page.locator('#compare-nuclei').set_checked(True)
    page.locator('[data-nuclear-id="nucleus:ame2020:28:62"]').click()
    assert page.evaluate('nuclearConfig.selected_ids') == ['nucleus:ame2020:26:56', 'nucleus:ame2020:28:62']
    assert '0,0041992' in page.locator('#binding-comparison').inner_text()
    page.locator('#focus-nucleus').click()
    assert page.evaluate('nuclearScale') == 6
    assert page.evaluate('nuclearCatalog.generation') == original
    # Actual pointer click on a chart cell near the selected Ni62.
    point = page.evaluate('(() => {const p=nuclearHits.find(p=>p.record.id==="nucleus:ame2020:28:62"),r=nuclearCanvas.getBoundingClientRect();return {x:r.x+p.x,y:r.y+p.y};})()')
    if args.native:
        for kind in ('mousePressed', 'mouseReleased'):
            page.call('Input.dispatchMouseEvent', {'type': kind, **point, 'button': 'left', 'clickCount': 1})
    else:
        page.mouse.click(point['x'], point['y'])
    assert page.evaluate('nuclearConfig.selected_ids[1]') == 'nucleus:ame2020:28:62'
    page.evaluate('document.querySelector("article").scrollTop=350')
    screenshot(page, 'comparison')
    page.locator('#nuclear-view').select_option('binding')
    assert page.evaluate('nuclearHits.length') == 3558
    assert page.evaluate('nuclearCatalog.generation') == original
    page.evaluate('document.querySelector("article").scrollTop=0')
    screenshot(page, 'binding')
    page.locator('#include-estimates').set_checked(False)
    assert page.evaluate('nuclearHits.length') == 2550
    assert page.evaluate('nuclearCatalog.records.length') == 3558
    page.locator('#save-nuclei').click()
    page.wait_for_function('!nuclearBusy&&document.getElementById("nuclear-status").textContent.startsWith("Seleção, vista")')
    page.locator('#nuclear-view').select_option('chart')
    page.locator('#include-estimates').set_checked(True)
    page.locator('#load-nuclei').click()
    page.wait_for_function('!nuclearBusy&&document.getElementById("nuclear-status").textContent==="Seleção retomada."')
    assert page.evaluate('nuclearConfig.view') == 'binding'
    assert page.evaluate('nuclearConfig.include_estimates') is False
    assert 'mesma tabela' in page.locator('#nuclear-restoration').inner_text()
    # Export must carry selected central values, original uncertainties and pin.
    if args.native:
        page.locator('#export-nuclei').click()
        page.wait_for_function('!nuclearBusy&&lastNuclearExport')
    else:
        with page.expect_download() as download:
            page.locator('#export-nuclei').click()
        download.value.save_as(str(ROOT / 'output/nuclei-ui-export.json'))
        page.wait_for_function('!nuclearBusy&&lastNuclearExport')
        assert json.loads((ROOT / 'output/nuclei-ui-export.json').read_text(encoding='utf-8')) == page.evaluate('lastNuclearExport')
    exported = page.evaluate('lastNuclearExport')
    assert json.loads(Path(exported['export_file']).read_text(encoding='utf-8')) == exported
    assert len(exported['records']) == 2 and exported['records'][0]['quantities']['atomic_mass']['uncertainty'] > 0
    assert exported['scientific_contract']['binding'].endswith('not strong interaction alone')
    page.locator('#clear-comparison').click()
    # H1 has a missing beta value; it must not become a zero in the UI.
    page.locator('[data-nuclear-id="nucleus:ame2020:1:1"]').click()
    assert 'Não calculável (*)' in page.locator('#nuclear-properties').inner_text()
    # Selected estimated state remains in the inspector when filter hides it.
    page.evaluate('selectRecord(nuclearCatalog.records.find(r=>r.Z===3&&r.A===3))')
    assert 'Estimativa (#)' in page.locator('#nuclear-properties').inner_text()
    assert page.evaluate('!document.getElementById("selection-filter-note").hidden')
    # Exact N/Z lookup, including rejection without changing selection.
    page.evaluate('document.getElementById("nuclear-N").value="30";document.getElementById("nuclear-Z").value="26"')
    page.locator('#select-nucleus button').click()
    assert page.evaluate('nuclearConfig.selected_ids') == ['nucleus:ame2020:26:56']
    page.evaluate('document.getElementById("nuclear-N").value="0";document.getElementById("nuclear-Z").value="118"')
    page.locator('#select-nucleus button').click()
    assert page.evaluate('nuclearConfig.selected_ids') == ['nucleus:ame2020:26:56']
    assert 'Nenhum estado' in page.locator('#nuclear-status').inner_text()
    if not args.native:
        page.set_viewport_size({'width': 720, 'height': 900})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.locator('#nuclear-view').select_option('chart')
        page.locator('#include-estimates').set_checked(True)
        page.locator('#nuclear-canvas').scroll_into_view_if_needed()
        screenshot(page, '720')
    # Links open the intended independent force stage, without evolving data.
    for stage in ('strong', 'weak'):
        page.goto(base + '/forces.html#' + stage)
        page.wait_for_function('!pending&&response&&config.scenario===' + json.dumps(stage))
        assert page.evaluate('config.scenario') == stage
        assert page.locator('[href="/nuclei.html"]').count() == 1
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
            browser = p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', headless=True)
            page = browser.new_page(viewport={'width': 1600, 'height': 1080}, accept_downloads=True)
            exported = exercise(page)
            browser.close()
finally:
    if saved_original is None:
        saved_path.unlink(missing_ok=True)
    else:
        saved_path.write_bytes(saved_original)

# Validate actual HTTP refusal of unknown selection and cross-origin writes.
def request_status(body, origin=None):
    headers = {'Content-Type': 'application/json'}
    if origin:
        headers['Origin'] = origin
    request = urllib.request.Request(base + '/api/nuclei/export', data=json.dumps(body).encode(), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
assert request_status({'selected_ids': ['unknown']}) == 400
assert request_status({}, 'https://example.com') == 403
report = {'browser': 'native OpenSpace CEF' if args.native else 'Windows Edge headless',
          'states': 3558, 'binding_filter_states': 2550, 'chart_binding_views': True,
          'real_canvas_selection': True, 'N_Z_lookup_and_rejection': True,
          'comparison': True, 'estimates_and_absence_explicit': True,
          'presentation_keeps_generation': True, 'save_load_selection_filter_view': True,
          'export_preserves_fields_and_sources': True, 'export_generation': exported['generation'],
          'narrow_no_overflow': None if args.native else True,
          'force_stage_links': ['strong', 'weak'], 'invalid_api_refused': True,
          'page_errors': errors, 'user_save_restored': True,
          'scope': 'Reference data instrument; independent numerical validation in nuclei-check.json. Actual local JSON export verified in both CEF and Edge; browser download additionally verified in Edge.'}
name = 'native-nuclei-check.json' if args.native else 'nuclei-ui-check.json'
(ROOT / 'evidence' / name).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
