"""Use the current Mesh export button and attempt to preview that exact exported file."""
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
FOLDER=ROOT/'output/native-spatial-roundtrip-20261121a'
OUT=ROOT/'evidence/native-spatial-roundtrip-20261121a.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def get(kind):return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/'+(kind+'/state' if kind else 'state'),timeout=30))
def material(p):return {k:p.get(k) for k in ['system_id','edit_token','revision','time','paused','bodies','atlas_initial','interventions']}


def main():
    assert not OUT.exists() and not FOLDER.exists();FOLDER.mkdir()
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    proof=dict(accepted=False,completed=False,defect_reproduced=False,session=session,actions=[],captures=[],
      script_sha256=sha(Path(__file__)),manifest_sha256=sha(PRODUCT/'build-manifest.json'),
      scope='Original Mesh panel: restore saved mesh, export with its actual button, close, choose that newly exported file in Windows and request origin preview. Genuine Windows input; DOM/HTTP observe. No API command injection or file rewriting. A refusal is recorded as a defect, not acceptance of roundtrip.')
    def persist():OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    with Page() as page:
        window=FileDialogInput(session['app'],page)
        def wait(expression):page.wait_for_function(expression,timeout=90000)
        def click(selector,ready=None):
            proof['step']=selector;persist();window.click(selector)
            if ready:wait(ready)
        try:
            before=get('');assert before['mode']=='atlas' and before['physics']['paused']
            phase=material(before['physics']);saved=PRODUCT/'is6-spatial-import-service-records/saved.json'
            proof['saved_before_sha256']=sha(saved)
            click('#experiment','!pending&&appState.mode==="experiment"')
            assert material(get('')['physics'])==phase
            click('#open-spatial','!document.getElementById("spatial-panel").hidden')
            click('#spatial-load-saved','!spatialInstrument.pending&&!spatialInstrument.snapshot.busy&&spatialInstrument.snapshot.active')
            assert material(get('')['physics'])==phase
            click('#spatial-export','!spatialInstrument.pending&&!spatialInstrument.snapshot.busy')
            status=page.evaluate('document.getElementById("spatial-storage-status").textContent')
            assert status.startswith('Exportado para: '),status
            exported=Path(status.removeprefix('Exportado para: '));assert exported.is_file() and exported.is_relative_to(PRODUCT)
            document=json.loads(exported.read_text(encoding='utf8'))
            proof['export']=dict(path=exported.relative_to(ROOT).as_posix(),sha256=sha(exported),bytes=exported.stat().st_size,schema=document['schema'],kind=document['kind'])
            click('#spatial-leave','!spatialInstrument.pending&&!spatialInstrument.snapshot.active&&!spatialInstrument.snapshot.recovery_required')
            if not page.evaluate('document.getElementById("spatial-import-section").open'):click('#spatial-import-section>summary')
            window.choose_file('#spatial-import-file',exported)
            click('#spatial-import-preview','!spatialInstrument.pending&&!spatialInstrument.readingFile')
            state=get('spatial');proof['preview']=state['import_preview']
            proof['error']=page.evaluate('document.getElementById("spatial-error").textContent')
            click('#spatial-error') if proof['error'] else click('#spatial-import-reading')
            target=FOLDER/'current-export-preview-result.png';proof['capture']=window.capture(target);proof['capture']['sha256']=sha(target)
            proof['defect_reproduced']=bool(proof['error']) and not state['import_preview']
            proof['accepted']=bool(state['import_preview'] and state['import_preview']['valid'])
            assert material(get('')['physics'])==phase
            assert sha(saved)==proof['saved_before_sha256'] and sha(exported)==proof['export']['sha256']
            proof['physical_phase_preserved']=True
            click('#spatial-panel-close','document.getElementById("spatial-panel").hidden')
            click('#atlas','!pending&&appState.mode==="atlas"')
            proof['completed']=True
        except Exception:proof['failure']=traceback.format_exc()
        finally:proof['actions']=list(window.actions);persist()
    print(json.dumps({k:proof.get(k) for k in ['accepted','completed','defect_reproduced','step','export','error','failure']},ensure_ascii=False))
    return 0 if proof['completed'] else 1


if __name__=='__main__':raise SystemExit(main())
