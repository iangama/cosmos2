"""Resume messaging for matching, changed, legacy and damaged scientific records."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
from contextlib import ExitStack

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--native',action='store_true');args=parser.parse_args()
path=ROOT/'user/forces/latest.json';original=path.read_bytes() if path.exists() else None
errors=[]
def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',', ':'),allow_nan=False).encode()).hexdigest()
try:
    with ExitStack() as stack:
        if args.native:
            from cef_page import Page
            page=stack.enter_context(Page());port=4700
        else:
            from playwright.sync_api import sync_playwright
            p=stack.enter_context(sync_playwright())
            browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
            stack.callback(browser.close);page=browser.new_page(viewport={'width':1600,'height':1080});port=4701
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(f'http://127.0.0.1:{port}/forces.html')
        page.wait_for_function("document.getElementById('force-status').textContent.startsWith('Cálculo concluído')")
        page.locator('[data-scenario="geomagnetic"]').click();page.wait_for_function('!pending')
        page.locator('#save-forces').click()
        page.wait_for_function("document.getElementById('force-status').textContent.includes('fontes salvos')")
        record=json.loads(path.read_text(encoding='utf-8'));assert record['schema']==3
        page.locator('[data-scenario="weak"]').click();page.wait_for_function('!pending')
        page.locator('#load-forces').click()
        page.wait_for_function("document.getElementById('restoration-note').dataset.state==='same_generation'&&!pending")
        assert page.evaluate('config.scenario')=='geomagnetic'
        assert page.evaluate('response.scientific_contract.sampling.kind')=='spatial_snapshot'
        changed=json.loads(json.dumps(record));changed['scientific_generation']['code_sha256']['app/forces.py']='a'*64
        changed['generation_sha256']=digest(changed['scientific_generation'])
        changed['manifest_sha256']=digest({k:v for k,v in changed.items() if k!='manifest_sha256'})
        path.write_text(json.dumps(changed),encoding='utf-8')
        page.locator('#load-forces').click()
        page.wait_for_function("document.getElementById('restoration-note').dataset.state==='changed_generation'&&!pending")
        assert 'app/forces.py' in page.locator('#restoration-note').inner_text()
        assert 'versão atual' in page.locator('#restoration-note').inner_text()
        page.evaluate('document.querySelector("article").scrollTop=0')
        if args.native:
            subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-native-scientific-restoration.png'],check=True,capture_output=True)
        legacy={'schema':2,'configuration':record['configuration'],'sha256':digest(record['configuration'])}
        path.write_text(json.dumps(legacy),encoding='utf-8');page.locator('#load-forces').click()
        page.wait_for_function("document.getElementById('restoration-note').dataset.state==='unknown_generation'&&!pending")
        assert 'Registro antigo' in page.locator('#restoration-note').inner_text()
        before=page.evaluate('response.physics_sha256')
        record['scientific_generation']['runtime']['scipy']='corrupt'
        path.write_text(json.dumps(record),encoding='utf-8');page.locator('#load-forces').click()
        page.wait_for_function("document.getElementById('force-status').classList.contains('error')")
        assert 'corrompido' in page.locator('#force-status').inner_text()
        assert page.evaluate('response.physics_sha256')==before
        if args.native:page.goto('http://127.0.0.1:4700/')
        assert not errors,errors
finally:
    if original is None:path.unlink(missing_ok=True)
    else:path.write_bytes(original)
report={'browser':'native OpenSpace CEF' if args.native else 'Windows Edge headless','same_generation_resume':True,
        'changed_generation_visible_with_cause':True,'legacy_explicit_unknown_generation':True,
        'corrupt_metadata_refused_without_recalculation':True,'original_user_save_restored':True,'page_errors':errors,
        'scope':'Synthetic old/corrupt generations for UI verification; no actual scientific dataset modification'}
name='native-force-persistence-check.json' if args.native else 'force-persistence-ui-check.json'
(ROOT/'evidence'/name).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
