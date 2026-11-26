"""E/B reference layers and evolving particle energy probe through DOM events."""
from pathlib import Path
import argparse
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=4701);args=parser.parse_args()
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    page=browser.new_page(viewport={'width':1600,'height':1080});page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(f'http://127.0.0.1:{args.port}/forces.html');page.wait_for_function("document.getElementById('force-status').textContent.startsWith('Cálculo concluído')")
    page.locator('[data-scenario="electromagnetic"]').click();page.wait_for_function('!pending')
    page.locator('[name="E_Vm"]').fill('.8');page.locator('#calculate').click();page.wait_for_function('!pending')
    fingerprint=page.evaluate('response.physics_sha256');configuration=page.evaluate('response.configuration_sha256')
    page.locator('#em-field').select_option('electric');assert page.evaluate('projectedArrows.length')==36
    page.locator('#science-view').scroll_into_view_if_needed();box=page.locator('#science-view').bounding_box();point=page.evaluate('projectedArrows[5]')
    page.mouse.click(box['x']+point['x'],box['y']+point['y']);assert 'V/m' in page.locator('#probe').inner_text()
    page.locator('#em-field').select_option('both');assert page.evaluate('projectedArrows.length')==72
    page.locator('#measure-particle').click();assert 'Potência magnética' in page.locator('#probe').inner_text()
    page.locator('#time-index').fill('30');first=page.locator('#probe').inner_text()
    page.locator('#time-index').fill('90');assert page.locator('#probe').inner_text()!=first
    assert page.evaluate('response.physics_sha256')==fingerprint
    assert page.evaluate('response.configuration_sha256')==configuration
    page.locator('#science-view').scroll_into_view_if_needed();page.screenshot(path=str(ROOT/'evidence/forces-ui-em-readings.png'),full_page=True)
    original=page.evaluate('response.result.reference')
    page.locator('[data-force="electromagnetic"][data-control="acting"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.result.reference')==original
    assert page.evaluate('projectedArrows.length')==72
    page.locator('#measure-particle').click();assert 'Força elétrica: 0 N' in page.locator('#probe').inner_text()
    page.set_viewport_size({'width':720,'height':900});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors,errors
    browser.close()
report={'browser':'native Windows Edge headless','electric_probe_units':True,'both_reference_layers':True,
        'particle_probe_follows_time':True,'view_preserves_physics_identity':True,
        'force_off_field_preserved':True,'narrow_no_horizontal_overflow':True,'page_errors':errors}
(ROOT/'evidence/em-readings-ui-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
