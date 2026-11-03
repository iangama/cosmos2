"""Dipole controls and diagrams in the existing native application CEF."""
from pathlib import Path
import json
import subprocess
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
errors=[]
def capture(name):
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                    str(ROOT/'scripts/capture-window.ps1'),'-Name',name],check=True,capture_output=True)
with Page() as page:
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto('http://127.0.0.1:4700/forces.html')
    page.wait_for_function("document.getElementById('force-status').textContent.startsWith('Cálculo concluído')")
    assert page.locator('[data-scenario]').count()==page.evaluate('catalog.scenarios && Object.keys(catalog.scenarios).length')
    page.locator('[data-scenario="dipole"]').click();page.wait_for_function('!pending')
    assert page.evaluate('response.result.dipole.parallel_reversals')>=1
    assert page.evaluate('projectedArrows.length')==96
    assert page.evaluate('document.getElementById("curve-legend").offsetHeight===0')
    page.locator('#dipole-field').select_option('both')
    assert page.evaluate('projectedArrows.length')==192
    page.locator('#measure-dipole').click()
    assert 'Pitch' in page.locator('#probe').inner_text()
    original=page.evaluate('response.result.reference');identity=page.evaluate('response.physics_sha256')
    page.evaluate('document.getElementById("science-view").scrollIntoView({block:"center"})')
    capture('cosmos2-native-dipole.png')
    page.locator('#dipole-view').select_option('curves')
    assert page.evaluate('response.physics_sha256')==identity
    assert page.locator('[data-curve]').count()==5
    assert page.evaluate('document.getElementById("reference-entry").offsetHeight===0')
    capture('cosmos2-native-dipole-curves.png')
    page.locator('#dipole-view').select_option('spatial')
    page.locator('[data-effect="magnetic_deflection"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.result.reference')==original
    assert 'não comprovam espelhamento' in page.locator('#channel-readings').inner_text()
    assert page.evaluate('projectedArrows.length')==192
    page.locator('#measure-dipole').click()
    assert 'Força magnética aplicada: 0 N' in page.locator('#probe').inner_text()
    capture('cosmos2-native-dipole-magnetic-off.png')
    page.locator('[data-effect="magnetic_deflection"]').set_checked(True);page.wait_for_function('!pending')
    contract=page.evaluate('response.scientific_contract')
    page.goto('http://127.0.0.1:4700/')
    assert not errors,errors
report={'session':json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig')),
        'runtime_receipt':json.loads((ROOT/'evidence/built-runtime.json').read_text()),
        'scientific_contract':contract,'browser':'existing native OpenSpace CEF','nine_stages':True,
        'magnetic_and_gravity_vectors':True,'particle_probe':True,'diagnostic_curves':True,
        'view_preserves_physics_identity':True,'magnetic_off_reference_preserved':True,
        'page_errors':errors,'scope':'native UI; scientific comparisons in dipole-check.json'}
(ROOT/'evidence/native-dipole-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('scientific_contract','runtime_receipt')},indent=2))
