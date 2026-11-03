"""Native CEF instrument, spatial snapshot, field comparison and operator gates."""
from pathlib import Path
import json
import subprocess
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1];errors=[]
def capture(name):
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                    str(ROOT/'scripts/capture-window.ps1'),'-Name',name],check=True,capture_output=True)
with Page() as page:
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:4700/forces.html')
    page.wait_for_function("document.getElementById('force-status').textContent.startsWith('Cálculo concluído')")
    assert page.locator('[data-scenario]').count()==10
    page.locator('[data-scenario="geomagnetic"]').click();page.wait_for_function('!pending')
    assert page.evaluate('response.scientific_contract.sampling.kind')=='spatial_snapshot'
    assert page.evaluate('response.result.time_s.length')==0
    assert page.evaluate('document.querySelector(".timeline").offsetHeight')==0
    assert page.evaluate('projectedArrows.length')>200
    assert page.evaluate('document.getElementById("probe").parentElement.id')=='probe-panel'
    assert 'Norte X' in page.locator('#probe').inner_text()
    identity=page.evaluate('response.physics_sha256');field=page.evaluate('response.result.geomagnetic.full.field_ned_T')
    page.evaluate('document.querySelector("article").scrollTop=0')
    capture('cosmos2-native-igrf-globe.png')
    page.locator('#geomagnetic-view').select_option('map')
    page.wait_for_function('geomagneticTexture.complete&&geomagneticTexture.naturalWidth>0')
    assert page.evaluate('projectedArrows.length')==704
    point=page.evaluate('(() => {const p=projectedArrows.find(p=>p.geomagnetic.latitude_deg===0&&p.geomagnetic.longitude_deg===0),r=canvas.getBoundingClientRect();return {x:r.x+p.x,y:r.y+p.y};})()')
    for kind in ('mousePressed','mouseReleased'):
        page.call('Input.dispatchMouseEvent',{'type':kind,**point,'button':'left','clickCount':1})
    assert page.evaluate('geomagneticProbe.latitude_deg')==0
    page.locator('#geomagnetic-component').select_option('D_deg')
    assert page.evaluate('response.physics_sha256')==identity
    capture('cosmos2-native-igrf-map.png')
    page.locator('#geomagnetic-model').select_option('dipole')
    assert 'Comparação dipolar' in page.locator('#probe').inner_text()
    assert page.evaluate('response.physics_sha256')==identity
    page.locator('#geomagnetic-model').select_option('full')
    page.locator('[data-effect="magnetic_deflection"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.result.geomagnetic.full.field_ned_T')==field
    assert page.evaluate('response.result.geomagnetic.full.magnetic_force_ned_N')==[0,0,0]
    assert page.evaluate('projectedArrows.length')==704
    physical=page.evaluate('response.physics_sha256')
    page.locator('[data-force="electromagnetic"][data-control="visible"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.physics_sha256')==physical
    assert page.evaluate('projectedArrows.length')==1
    page.locator('[data-force="electromagnetic"][data-control="visible"]').set_checked(True);page.wait_for_function('!pending')
    page.evaluate('document.querySelector("article").scrollTop=0')
    capture('cosmos2-native-igrf-magnetic-off.png')
    contract=page.evaluate('response.scientific_contract')
    page.locator('[data-effect="magnetic_deflection"]').set_checked(True);page.wait_for_function('!pending')
    page.locator('[data-scenario="gravity"]').click();page.wait_for_function('!pending')
    assert page.evaluate('document.getElementById("probe").parentElement.id')=='viewport'
    assert page.evaluate('document.querySelector(".timeline").offsetHeight')>0
    page.goto('http://127.0.0.1:4700/')
    assert not errors,errors
report={'session':json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig')),
        'browser':'native OpenSpace CEF','scientific_contract':contract,'ten_stages':True,
        'spatial_snapshot_without_fake_time':True,'map_and_globe':True,'map_probe':True,
        'components_and_degree1_comparison':True,'presentation_identity_preserved':True,
        'magnetic_off_preserves_reference':True,'reference_visibility_independent':True,
        'separate_probe_panel':True,'return_to_other_stages':True,'page_errors':errors,
        'scope':'Native UI; independent numerical comparison in igrf-check.json, not observed Earth accuracy'}
(ROOT/'evidence/native-igrf-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='scientific_contract'},indent=2))
