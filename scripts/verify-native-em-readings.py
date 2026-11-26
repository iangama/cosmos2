"""Native EM measurement controls, export metadata and laboratory SI labels."""
from pathlib import Path
import json
import subprocess
from cef_page import Page
ROOT=Path(__file__).resolve().parents[1]
errors=[]
session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
def capture(name):
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                    str(ROOT/'scripts/capture-window.ps1'),'-Name',name],check=True,capture_output=True)
with Page() as page:
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto('http://127.0.0.1:4700/')
    page.wait_for_function('document.getElementById("sim-time").textContent.endsWith(" h")')
    assert 'h/s' in page.locator('#effective-rate').inner_text()
    assert '2745' not in page.locator('#unit-note').inner_text() # locale groups thousands
    assert '2.745' in page.locator('#unit-note').inner_text()
    capture('cosmos2-native-laboratory-units.png')
    page.locator('#forces').click()
    page.wait_for_function("document.getElementById('force-status').textContent.startsWith('Cálculo concluído')")
    assert page.locator('[data-scenario]').count()==page.evaluate('Object.keys(catalog.scenarios).length')
    page.locator('[data-scenario="electromagnetic"]').click();page.wait_for_function('!pending')
    page.evaluate('document.querySelector("[name=E_Vm]").value=".8"')
    page.locator('#calculate').click();page.wait_for_function('!pending')
    metadata=page.evaluate('response.scientific_contract')
    assert metadata['model_id']=='cosmos2:uniform-field-lorentz-classical'
    assert metadata['quantities']['particle_readings']['electric_power_W']=='W'
    fingerprint=page.evaluate('response.physics_sha256')
    page.locator('#em-field').select_option('both');assert page.evaluate('projectedArrows.length')==72
    page.locator('#measure-particle').click();assert 'Trabalho elétrico' in page.locator('#probe').inner_text()
    page.evaluate('document.getElementById("time-index").value=90;document.getElementById("time-index").dispatchEvent(new Event("input",{bubbles:true}))')
    assert page.evaluate('response.physics_sha256')==fingerprint
    page.evaluate('document.getElementById("science-view").scrollIntoView({block:"center"})')
    capture('cosmos2-native-em-readings.png')
    page.locator('[data-force="electromagnetic"][data-control="acting"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.result.measurements[1].value')==0
    assert page.evaluate('projectedArrows.length')==72
    page.locator('#measure-particle').click();assert 'Força magnética: 0 N' in page.locator('#probe').inner_text()
    page.locator('[data-force="electromagnetic"][data-control="acting"]').set_checked(True);page.wait_for_function('!pending')
    page.goto('http://127.0.0.1:4700/')
    assert not errors,errors
report={'session':session,'browser':'existing native OpenSpace CEF','eight_stages':True,
        'laboratory_hours_and_rate':True,'electric_and_magnetic_reference':True,
        'force_work_power_probe':True,'metadata_present_in_export_source':True,
        'physical_identity_preserved_by_view':True,'acting_off_preserves_fields':True,
        'page_errors':errors,'scope':'native UI and export-source checks, not general model acceptance'}
(ROOT/'evidence/native-em-readings-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
