"""Real IGRF map/globe/component/probe/operator UI through the local HTTP host."""
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
    assert not page.locator('#geomagnetic-controls').is_visible()
    page.locator('[data-scenario="geomagnetic"]').click();page.wait_for_function('!pending')
    assert page.evaluate('response.scientific_contract.model_id')=='cosmos2:igrf14-internal-main-field-instrument'
    assert not page.locator('.timeline').is_visible()
    assert page.evaluate('projectedArrows.length')>200
    assert page.evaluate('document.getElementById("probe").parentElement.id')=='probe-panel'
    initial=page.evaluate('[azimuth,elevation]')
    rect=page.locator('#science-view').bounding_box()
    page.mouse.move(rect['x']+rect['width']/2,rect['y']+rect['height']/2)
    page.mouse.down();page.mouse.move(rect['x']+rect['width']/2+60,rect['y']+rect['height']/2+20);page.mouse.up()
    assert page.evaluate('[azimuth,elevation]')!=initial
    page.locator('#center-geomagnetic').click()
    identity=page.evaluate('response.physics_sha256');full=page.evaluate('response.result.geomagnetic.full')
    assert 'Norte X' in page.locator('#probe').inner_text()
    page.locator('#science-view').scroll_into_view_if_needed()
    page.screenshot(path=str(ROOT/'evidence/forces-ui-igrf-globe.png'),full_page=True)
    page.locator('#geomagnetic-view').select_option('map')
    page.wait_for_function('geomagneticTexture.complete&&geomagneticTexture.naturalWidth>0')
    assert page.evaluate('projectedArrows.length')==704
    box=page.locator('#science-view').bounding_box();point=page.evaluate('projectedArrows.find(p=>p.geomagnetic.latitude_deg===0&&p.geomagnetic.longitude_deg===0)')
    page.mouse.click(box['x']+point['x'],box['y']+point['y'])
    assert page.evaluate('geomagneticProbe.latitude_deg')==0
    assert page.evaluate('geomagneticProbe.longitude_deg')==0
    page.locator('#geomagnetic-component').select_option('D_deg')
    assert page.evaluate('response.physics_sha256')==identity
    page.locator('#geomagnetic-component').select_option('F_nT')
    page.screenshot(path=str(ROOT/'evidence/forces-ui-igrf-map.png'),full_page=True)
    page.locator('#geomagnetic-model').select_option('dipole')
    assert page.evaluate('response.physics_sha256')==identity
    assert 'Comparação dipolar' in page.locator('#probe').inner_text()
    page.screenshot(path=str(ROOT/'evidence/forces-ui-igrf-dipole.png'),full_page=True)
    page.locator('#geomagnetic-model').select_option('full')
    page.locator('[data-effect="magnetic_deflection"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.result.geomagnetic.full.field_ned_T')==full['field_ned_T']
    assert page.evaluate('response.result.geomagnetic.full.magnetic_force_ned_N')==[0,0,0]
    assert page.evaluate('projectedArrows.length')==704
    physical=page.evaluate('response.physics_sha256')
    page.locator('[data-force="electromagnetic"][data-control="visible"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.physics_sha256')==physical
    assert page.evaluate('projectedArrows.length')==1 # source/probe retained, field layer hidden
    page.locator('[data-force="electromagnetic"][data-control="visible"]').set_checked(True);page.wait_for_function('!pending')
    page.locator('[data-effect="magnetic_deflection"]').set_checked(True);page.wait_for_function('!pending')
    page.locator('[name="year"]').fill('2030');page.locator('[name="latitude_deg"]').fill('90');page.locator('[name="altitude_km"]').fill('1000')
    page.locator('#calculate').click();page.wait_for_function('!pending')
    assert page.evaluate('response.scientific_contract.quantities.epoch.value')==2030
    assert 'meridiano' in page.locator('#probe').inner_text()
    assert page.evaluate('response.result.geomagnetic.altitude_m')==1000000
    page.set_viewport_size({'width':720,'height':900})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.locator('[data-scenario="gravity"]').click();page.wait_for_function('!pending')
    assert page.locator('.timeline').is_visible()
    assert not page.locator('#geomagnetic-controls').is_visible()
    assert not errors,errors
    browser.close()
report={'browser':'Windows Edge headless','ten_stages':True,'globe_and_geographic_map':True,
        'component_and_degree1_comparison':True,'map_probe':True,'view_preserves_physics_identity':True,
        'magnetic_off_preserves_igrf':True,'reference_visibility_independent':True,
        'epoch_altitude_pole_readings':True,'narrow_no_horizontal_overflow':True,'page_errors':errors,
        'scope':'Instrument UI; independent numerical comparison in igrf-check.json; native CEF separate'}
(ROOT/'evidence/igrf-ui-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
