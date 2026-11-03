"""Actual binary source gates, tidal probe and coordinate-view controls."""
from pathlib import Path
import argparse
import json
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=4701);args=parser.parse_args()
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    page=browser.new_page(viewport={'width':1600,'height':1080})
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(f'http://127.0.0.1:{args.port}/forces.html')
    page.wait_for_function("document.getElementById('force-status').textContent.startsWith('Cálculo concluído')")
    page.locator('[data-scenario="binary"]').click();page.wait_for_function('!pending')
    original=page.evaluate('response.result');fingerprint=page.evaluate('response.configuration_sha256')
    page.locator('#binary-view').select_option('inertial')
    assert page.evaluate('response.configuration_sha256')==fingerprint
    page.locator('#binary-view').select_option('rotating')
    page.locator('#science-view').scroll_into_view_if_needed()
    box=page.locator('#science-view').bounding_box();probe=page.evaluate('projectedArrows[projectedArrows.length-1]')
    page.mouse.click(box['x']+probe['x'],box['y']+probe['y'])
    assert 'Maré (autovalores)' in page.locator('#probe').inner_text()
    page.locator('[data-effect="primary_attraction"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.result.binary.gates')==[False,True]
    assert page.evaluate('response.result.reference')==original['reference']
    page.locator('[data-effect="primary_attraction"]').set_checked(True);page.wait_for_function('!pending')
    page.locator('[data-effect="secondary_attraction"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.result.binary.gates')==[True,False]
    page.locator('[data-effect="secondary_attraction"]').set_checked(True);page.wait_for_function('!pending')
    page.locator('[data-force="gravity"][data-control="acting"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.result.measurements[1].value')==0
    assert page.evaluate('response.result.reference')==original['reference']
    assert page.evaluate('projectedArrows.length')==97
    page.locator('#binary-view').select_option('inertial');page.locator('#science-view').scroll_into_view_if_needed()
    page.screenshot(path=str(ROOT/'evidence/forces-ui-binary-off.png'),full_page=True)
    physical=page.evaluate('response.result')
    page.locator('[data-force="gravity"][data-control="visible"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.result')==physical
    assert page.evaluate('projectedArrows.length')==0
    page.locator('[data-force="gravity"][data-control="visible"]').set_checked(True);page.wait_for_function('!pending')
    page.locator('[data-force="gravity"][data-control="acting"]').set_checked(True);page.wait_for_function('!pending')
    page.locator('[name="initial_mode"]').select_option('l4')
    assert not page.locator('[name="x"]').is_visible()
    page.locator('#calculate').click();page.wait_for_function('!pending')
    page.locator('#binary-view').select_option('rotating');page.locator('#science-view').scroll_into_view_if_needed()
    page.screenshot(path=str(ROOT/'evidence/forces-ui-binary-l4.png'),full_page=True)
    page.locator('[name="initial_mode"]').select_option('custom');page.locator('#calculate').click();page.wait_for_function('!pending')
    page.locator('#science-view').scroll_into_view_if_needed()
    page.screenshot(path=str(ROOT/'evidence/forces-ui-binary.png'),full_page=True)
    page.set_viewport_size({'width':720,'height':900})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors,errors
    browser.close()
report={'browser':'native Windows Edge headless','source_gates':True,
        'gravity_off_reference_on':True,'reference_and_visibility_independent':True,
        'coordinate_view_preserves_physics':True,'tidal_probe':True,'l4_initial_conditions':True,
        'narrow_no_horizontal_overflow':True,'page_errors':errors,'scope':'UI/HTTP, native CEF separate'}
(ROOT/'evidence/binary-ui-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
