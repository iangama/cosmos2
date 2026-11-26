"""Original Layers controls: native Windows file picker, preview and cancellation."""
from pathlib import Path
import hashlib
import json
import time
import traceback
import urllib.request
from cef_page_v2 import Page
from ordinary_file_dialog_input_v2 import FileDialogInput,window_text,user

ROOT=Path(__file__).resolve().parents[1]
PRODUCT=ROOT/'output/original-flow-hotfix-product0.27.5'
FOLDER=ROOT/'output/native-reference-import-20261121a'
OUT=ROOT/'evidence/native-reference-import-picker-20261121b.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def get(route):return json.load(urllib.request.urlopen('http://127.0.0.1:4700'+route,timeout=30))


def main():
    assert FOLDER.is_dir() and not OUT.exists()
    preflight=json.loads((ROOT/'evidence/native-reference-import-preflight-20261121a.json').read_text(encoding='utf8'))
    assert preflight['accepted'] and preflight['completed']
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert session['app']==preflight['session']['app']
    source=PRODUCT/'layer-checkpoints/exports/074696b5dc8141e1915156576f922b70.json'
    source_data=json.loads(source.read_text(encoding='utf8'))
    proof=dict(accepted=False,completed=False,checks=[],captures=[],actions=[],
      session=session,source_file=source.relative_to(ROOT).as_posix(),source_sha256=sha(source),
      expected_scientific_sha256=source_data['checkpoint']['scientific_sha256'],
      saved_session_sha256=sha(PRODUCT/'gravity-sessions/latest.json'),
      script_sha256=sha(Path(__file__)),input_helper_sha256=sha(ROOT/'scripts/ordinary_file_dialog_input_v2.py'),
      scope='Original header, Layers panel and native Windows file dialog, ordinary mouse/typing/keys only. Choose an existing exported reference, preview its origin and cancel the preview. DOM/HTTP read only. No import commit, branch restore, scientific promotion or calculation-cancellation acceptance.')
    def persist():OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    with Page() as page:
        window=FileDialogInput(session['app'],page)
        def wait(expression):page.wait_for_function(expression,timeout=20000)
        def click(selector,ready=None):
            proof['step']=selector;persist();window.click(selector)
            if ready:wait(ready)
        def capture(name,dialog=False):
            target=FOLDER/(name+'.png');assert not target.exists()
            row=window.capture_dialog(target) if dialog else window.capture(target)
            row['sha256']=sha(target);proof['captures'].append(row);persist()
        def check(name,**values):
            proof['checks'].append(dict(name=name,**values));proof['actions']=list(window.actions);persist()
        try:
            assert get('/api/state')['mode']=='atlas' and not get('/api/state').get('physics')
            assert page.evaluate('location.pathname==="/"&&!pending')
            before=get('/api/layers/state');branches=[row['id'] for row in before['branches']]
            click('#open-layers','!document.getElementById("layers-panel").hidden')
            if not page.evaluate('document.getElementById("layers-import").open'):click('#layers-import>summary')
            proof['step']='open-and-cancel-Windows-dialog';persist()
            window.open_file_dialog('#layers-import-file');capture('windows-file-dialog',dialog=True)
            window.cancel_file_dialog()
            assert page.evaluate('document.getElementById("layers-import-file").files.length')==0
            assert not get('/api/layers/state')['import_preview']
            check('native-file-dialog-cancels-without-selection')
            proof['step']='choose-original-export-in-Windows';persist()
            window.choose_file('#layers-import-file',source)
            assert page.evaluate('document.getElementById("layers-import-file").files[0].size')==source.stat().st_size
            check('native-file-dialog-selects-real-export',file_name=source.name,bytes=source.stat().st_size)
            click('#layers-import-preview','!layerInstrument.readingFile&&!layerInstrument.pending')
            current=get('/api/layers/state')
            assert current['import_preview'] and current['import_preview']['valid'],page.evaluate('document.getElementById("layers-error").textContent')
            assert [row['id'] for row in current['branches']]==branches
            assert not current['active'] and not current['busy']
            proof['preview']=current['import_preview'];capture('layers-export-preview')
            click('#layers-import-cancel','!layerInstrument.pending&&!layerInstrument.snapshot.import_preview')
            current=get('/api/layers/state');assert [row['id'] for row in current['branches']]==branches
            assert not current['active'] and not current['recovery_required']
            check('export-preview-and-cancel-preserve-branches-and-scene',branches=len(branches))
            click('#layers-panel-close','document.getElementById("layers-panel").hidden')
            assert get('/api/state')['mode']=='atlas' and not get('/api/state').get('physics')
            assert sha(source)==proof['source_sha256']
            assert sha(PRODUCT/'gravity-sessions/latest.json')==proof['saved_session_sha256']
            proof.update(accepted=True,completed=True)
        except Exception:
            proof['failure']=traceback.format_exc()
            if window_text(user.GetForegroundWindow(),'GetClassNameW')=='#32770':window.key(27)
        finally:proof['actions']=list(window.actions);persist()
    print(json.dumps({key:proof.get(key) for key in ['accepted','completed','step','checks','failure']},ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
