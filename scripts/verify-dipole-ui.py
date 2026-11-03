"""Actual browser controls, field probes, time-resolved curves and exports."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    page=browser.new_page(viewport={'width':1600,'height':1080})
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto('http://127.0.0.1:4701/forces.html')
    page.wait_for_function("document.getElementById('force-status').textContent.startsWith('Cálculo concluído')")
    page.locator('[data-scenario="dipole"]').click();page.wait_for_function('!pending')
    assert page.evaluate('response.scientific_contract.model_id')=='cosmos2:static-dipole-newton-classical-test-particle'
    assert page.evaluate('response.result.dipole.parallel_reversals')>=1
    assert page.evaluate('projectedArrows.length')==96
    assert not page.locator('#curve-legend').is_visible()
    baseline=page.evaluate('response.result.reference');fingerprint=page.evaluate('response.physics_sha256')
    page.locator('#dipole-field').select_option('both');assert page.evaluate('projectedArrows.length')==192
    page.locator('#dipole-field').select_option('gravity')
    page.locator('#science-view').scroll_into_view_if_needed();box=page.locator('#science-view').bounding_box()
    point=page.evaluate('projectedArrows.find(a=>a.field.force==="gravity"&&a.x>30&&a.y>30&&a.x<canvas.clientWidth-30&&a.y<canvas.clientHeight-30)')
    page.mouse.click(box['x']+point['x'],box['y']+point['y']);assert 'Potencial' in page.locator('#probe').inner_text()
    page.locator('#dipole-field').select_option('both')
    page.locator('#measure-dipole').click();assert 'Força gravitacional aplicada' in page.locator('#probe').inner_text()
    page.locator('#time-index').fill('40');first=page.locator('#probe').inner_text()
    page.locator('#time-index').fill('90');assert page.locator('#probe').inner_text()!=first
    assert page.evaluate('response.physics_sha256')==fingerprint
    page.screenshot(path=str(ROOT/'evidence/forces-ui-dipole.png'),full_page=True)
    page.locator('#dipole-view').select_option('curves')
    assert page.locator('[data-curve]').count()==5
    assert page.locator('#curve-legend').is_visible()
    assert not page.locator('#reference-entry').is_visible()
    assert page.evaluate('projectedArrows.length')==0
    assert page.evaluate('response.physics_sha256')==fingerprint
    page.locator('#time-index').fill('240');page.locator('#chart-axis').select_option('log')
    page.locator('#chart-axis').select_option('linear')
    page.screenshot(path=str(ROOT/'evidence/forces-ui-dipole-curves.png'),full_page=True)
    page.locator('[data-curve="4"]').set_checked(False)
    assert page.evaluate('response.physics_sha256')==fingerprint
    page.locator('#dipole-view').select_option('spatial')
    page.locator('[data-force="electromagnetic"][data-control="acting"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.result.reference')==baseline
    assert 'não comprovam espelhamento' in page.locator('#channel-readings').inner_text()
    assert page.evaluate('projectedArrows.length')==192
    page.locator('#measure-dipole').click();assert 'Força magnética aplicada: 0 N' in page.locator('#probe').inner_text()
    physical=page.evaluate('response.physics_sha256')
    page.locator('[data-force="electromagnetic"][data-control="visible"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.physics_sha256')==physical
    assert page.evaluate('projectedArrows.length')==96
    page.locator('[data-force="gravity"][data-control="visible"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('projectedArrows.length')==0
    assert page.evaluate('response.result.dipole.radius_m')==6371000
    page.locator('[data-force="gravity"][data-control="visible"]').set_checked(True);page.wait_for_function('!pending')
    page.locator('[data-force="electromagnetic"][data-control="visible"]').set_checked(True);page.wait_for_function('!pending')
    page.locator('[data-force="electromagnetic"][data-control="acting"]').set_checked(True);page.wait_for_function('!pending')
    page.locator('#export-forces').click()
    page.locator('[data-scenario="gravity"]').click();page.wait_for_function('!pending')
    assert not page.locator('#dipole-controls').is_visible()
    page.set_viewport_size({'width':720,'height':900})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors,errors
    browser.close()
report={'browser':'Windows Edge headless','dipole_and_gravity_fields':True,'potential_probe':True,
        'particle_probe_follows_time':True,'five_diagnostic_curves':True,'view_preserves_physics_identity':True,
        'magnetic_off_reference_preserved':True,'independent_visibility':True,'material_source_preserved':True,
        'export_button':True,'narrow_no_horizontal_overflow':True,'page_errors':errors,
        'scope':'UI/HTTP, native CEF separate; model acceptance in dipole-check.json'}
(ROOT/'evidence/dipole-ui-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
