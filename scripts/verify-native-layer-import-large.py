"""Check readable import controls and restoration at the owner's150% scale."""
from pathlib import Path
import hashlib
import json
import time
import traceback
import urllib.request
from cef_page_v2 import Page
from ordinary_file_dialog_input_v4 import FileDialogInput

ROOT=Path(__file__).resolve().parents[1]
PRODUCT=ROOT/'output/original-flow-hotfix-product0.27.6'
FOLDER=ROOT/'output/native-reference-import-20261121a'
OUT=ROOT/'evidence/native-layer-import-large-20261121a.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def get(route):return json.load(urllib.request.urlopen('http://127.0.0.1:4700'+route,timeout=30))
def material(p):return {k:p.get(k) for k in ['system_id','edit_token','revision','time','paused','bodies','atlas_initial','interventions']}


def main():
    assert not OUT.exists()
    prior=json.loads((ROOT/'evidence/native-layer-import-restore-20261121c.json').read_text(encoding='utf8'))
    assert prior['accepted'] and prior['completed']
    source=ROOT/'output/original-flow-hotfix-product0.27.5/layer-checkpoints/exports/074696b5dc8141e1915156576f922b70.json'
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert session['app']==prior['session']['app']
    proof=dict(accepted=False,completed=False,checks=[],actions=[],captures=[],scale=1.5,session=session,
      script_sha256=sha(Path(__file__)),manifest_sha256=sha(PRODUCT/'build-manifest.json'),
      scope='Genuine Windows file picker, mouse, wheel and typing at150%: readable preview and enabled import action after name editing, cancel preview, restore saved/imported references through real controls. No second branch created, no new scientific acceptance.')
    def persist():OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    with Page() as page:
        window=FileDialogInput(session['app'],page)
        def wait(x):page.wait_for_function(x,timeout=90000)
        def click(selector,ready=None):
            proof['step']=selector;persist();window.click(selector)
            if ready:wait(ready)
        def capture(name):
            target=FOLDER/(name+'.png');assert not target.exists();time.sleep(.3)
            row=window.capture(target);row['sha256']=sha(target);proof['captures'].append(row);persist()
        def check(name,**data):proof['checks'].append(dict(name=name,**data));proof['actions']=list(window.actions);persist()
        try:
            before=get('/api/state');phase=material(before['physics']);assert before['mode']=='atlas' and phase['paused']
            ids={b['id'] for b in get('/api/layers/state')['branches']}
            window.select('#ui-scale','1.5');assert page.evaluate('Number(getComputedStyle(document.body).zoom)')==1.5
            click('#open-layers','!document.getElementById("layers-panel").hidden')
            if not page.evaluate('document.getElementById("layers-import").open'):click('#layers-import>summary')
            window.choose_file('#layers-import-file',source)
            click('#layers-import-preview','!layerInstrument.pending&&!layerInstrument.readingFile')
            assert get('/api/layers/state')['import_preview']['valid']
            click('#layers-import-reading');capture('layers-preview-origin-150')
            window.fill('#layers-import-name','Previa conferida em150 por cento')
            assert page.evaluate('!document.getElementById("layers-import-commit").disabled')
            click('#layers-import-name');capture('layers-import-action-150')
            check('preview-and-import-action-remain-readable-and-enabled-at150')
            click('#layers-import-cancel','!layerInstrument.pending&&!layerInstrument.snapshot.import_preview')
            assert {b['id'] for b in get('/api/layers/state')['branches']}==ids
            click('#layers-panel-close','document.getElementById("layers-panel").hidden')
            click('#experiment','!pending&&appState.mode==="experiment"')
            assert material(get('/api/state')['physics'])==phase
            click('#open-layers','!document.getElementById("layers-panel").hidden')
            click('#layers-load-saved','!layerInstrument.pending&&!layerInstrument.snapshot.busy&&layerInstrument.snapshot.active')
            assert material(get('/api/state')['physics'])==phase
            if not page.evaluate('document.getElementById("layers-storage").open'):click('#layers-storage>summary')
            window.open_options('#layers-branches');capture('layers-branch-options-150')
            window.select('#layers-branches',prior['created_branch']['id'])
            click('#layers-branch-load','!layerInstrument.pending&&!layerInstrument.snapshot.busy')
            state=get('/api/layers/state');assert state['loaded_record']['id']==prior['created_branch']['id']
            assert state['artifact']['sha256']==prior['created_branch']['scientific_sha256']
            assert material(get('/api/state')['physics'])==phase
            capture('layers-imported-branch-150')
            check('saved-and-imported-branch-restore-at150-preserve-orbit',sha256=state['artifact']['sha256'])
            click('#layers-leave','!layerInstrument.pending&&!layerInstrument.snapshot.active&&!layerInstrument.snapshot.recovery_required')
            click('#layers-panel-close','document.getElementById("layers-panel").hidden')
            click('#atlas','!pending&&appState.mode==="atlas"')
            window.select('#ui-scale','1')
            assert material(get('/api/state')['physics'])==phase
            assert {b['id'] for b in get('/api/layers/state')['branches']}==ids
            proof.update(accepted=True,completed=True)
        except Exception:proof['failure']=traceback.format_exc()
        finally:proof['actions']=list(window.actions);persist()
    print(json.dumps({k:proof.get(k) for k in ['accepted','completed','step','checks','failure']},ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
