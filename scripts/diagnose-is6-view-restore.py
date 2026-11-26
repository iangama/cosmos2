"""Record confirmed view versus visible controls after same-artifact restore."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import json
import time
import traceback
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
h=SourceFileLoader('is6_restore_helpers',str(ROOT/'scripts/verify-native-solar-integration.py')).load_module()
receipt=ROOT/'evidence/is6-view-restore-diagnostic-20261102a.json'
if receipt.exists():raise FileExistsError('Preserve diagnostic')
r=dict(completed=False,scope='Targeted CEF control coherence diagnostic, not acceptance.')
try:
    with Page() as page:
        page.goto(h.BASE+'/');page.wait_for_function('appState&&spatialInstrument.snapshot&&!pending')
        page.locator('#open-spatial').click();page.locator('#spatial-copy').click()
        page.wait_for_function('!pending&&appState?.mode==="experiment"',timeout=70000)
        def click(id):
            page.locator('#spatial-'+id).click()
            page.wait_for_function('!spatialInstrument.pending&&!spatialInstrument.snapshot.busy',timeout=40000)
        click('create')
        page.evaluate('document.getElementById("spatial-radial").value="16"');click('sample')
        page.evaluate('document.getElementById("spatial-storage-fields").closest("details").open=true')
        click('save');saved=h.get('/api/spatial/state')['artifact']
        page.evaluate('document.getElementById("spatial-radial").value="64"');click('sample');click('load')
        r['restored']=h.get('/api/spatial/state')['artifact'];r['saved']=saved
        r['controls']=page.evaluate('({radial:Number(document.getElementById("spatial-radial").value),azimuth:Number(document.getElementById("spatial-azimuth").value),reference:Number(document.getElementById("spatial-reference").value),reading:document.getElementById("spatial-reading").textContent})')
        r['artifact_restored_exactly']=r['restored']==saved
        r['controls_match_confirmed_view']=r['controls']['radial']==saved['view']['selected_radial_index']
        r['completed']=True
except Exception:r['failure']=traceback.format_exc()
finally:
    try:
        state=h.get('/api/spatial/state')
        if state['active']:h.post('/api/spatial/command',dict(command='leave',guard=state['guard']))
        if h.get('/api/state')['mode']=='experiment':h.post('/api/command',dict(command='atlas'))
        h.native('openspace.toggleShutdown();return {closing=true}')
    except Exception:r['cleanup_failure']=traceback.format_exc()
    receipt.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k not in {'saved','restored'}},ensure_ascii=False))
