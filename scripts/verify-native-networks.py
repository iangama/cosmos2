"""Check the new pp/CNO views inside the already running OpenSpace CEF."""
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
    page.goto('http://127.0.0.1:4700/forces.html')
    page.wait_for_function("document.getElementById('force-status').textContent.startsWith('Cálculo concluído')")
    for stage,count in [('stellar',4),('cno',8)]:
        page.locator(f'[data-scenario="{stage}"]').click();page.wait_for_function('!pending')
        physical=page.evaluate('response.result.network')
        fingerprint=page.evaluate('response.configuration_sha256')
        page.locator('#network-view').select_option('reactions')
        assert page.locator('[data-nucleus]').count()==count
        page.locator('[data-nucleus="p"]').click()
        assert 'Densidade numérica' in page.locator('#probe').inner_text()
        assert page.evaluate('response.configuration_sha256')==fingerprint
        page.locator('[data-force="weak"][data-control="acting"]').set_checked(False);page.wait_for_function('!pending')
        assert page.evaluate('response.result.network.neutrino_count_m3[240]')==0
        assert page.evaluate('response.result.reference.mean_neutrino_MeV') if stage=='cno' else True
        page.locator('[data-force="weak"][data-control="acting"]').set_checked(True);page.wait_for_function('!pending')
        assert page.evaluate('response.result.network')==physical
        page.evaluate('document.getElementById("science-view").scrollIntoView({block:"center"})')
        capture(f'cosmos2-native-{stage}-network.png')
    assert not errors,errors
    page.goto('http://127.0.0.1:4700/')
report={'session':session,'browser':'existing native OpenSpace CEF',
        'pp_and_cno_networks':True,'eight_cno_species':True,'density_probes':True,
        'weak_off_preserves_reference':True,'view_preserves_science':True,'page_errors':errors,
        'runtime_receipt':json.loads((ROOT/'evidence/built-runtime.json').read_text()),
        'scope':'Native interface verification, not full stellar simulation acceptance'}
(ROOT/'evidence/native-networks-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='runtime_receipt'},indent=2))
