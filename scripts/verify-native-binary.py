"""Binary field and attraction controls inside the running native CEF."""
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
    page.wait_for_function('document.getElementById("connection")?.textContent.includes("Motor conectado")',timeout=30000)
    page.goto('http://127.0.0.1:4700/forces.html')
    page.wait_for_function("document.getElementById('force-status').textContent.startsWith('Cálculo concluído')")
    page.locator('[data-scenario="binary"]').click();page.wait_for_function('!pending')
    original=page.evaluate('response.result')
    page.locator('[data-effect="primary_attraction"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.result.binary.gates')==[False,True]
    assert page.evaluate('response.result.reference')==original['reference']
    page.locator('[data-effect="primary_attraction"]').set_checked(True);page.wait_for_function('!pending')
    page.locator('[data-force="gravity"][data-control="acting"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.result.measurements[1].value')==0
    assert page.evaluate('projectedArrows.length')==97
    page.locator('#binary-view').select_option('inertial')
    fingerprint=page.evaluate('response.configuration_sha256')
    page.locator('#framing').select_option('whole')
    assert page.evaluate('response.configuration_sha256')==fingerprint
    page.evaluate('document.getElementById("science-view").scrollIntoView({block:"center"})')
    capture('cosmos2-native-binary-off.png')
    page.locator('[data-force="gravity"][data-control="acting"]').set_checked(True);page.wait_for_function('!pending')
    page.locator('#binary-view').select_option('rotating');page.locator('#framing').select_option('focus')
    page.evaluate('document.getElementById("science-view").scrollIntoView({block:"center"})')
    point=page.evaluate('(() => {const a=projectedArrows[projectedArrows.length-1],r=canvas.getBoundingClientRect();return {x:r.x+a.x,y:r.y+a.y};})()')
    for kind in ('mousePressed','mouseReleased'):
        page.call('Input.dispatchMouseEvent',{'type':kind,'x':point['x'],'y':point['y'],'button':'left','clickCount':1})
    assert 'Maré (autovalores)' in page.locator('#probe').inner_text()
    capture('cosmos2-native-binary.png')
    assert not errors,errors
    page.goto('http://127.0.0.1:4700/')
report={'session':session,'browser':'existing native OpenSpace CEF',
        'individual_sources':True,'gravity_off_field_on':True,'tidal_and_potential_probe':True,
        'view_preserves_physics':True,'page_errors':errors,
        'scope':'native bounded-model controls, not G0 or general N-body acceptance'}
(ROOT/'evidence/native-binary-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
