"""Complete the original Layers file import, saved restore and branch-selection journey."""
from pathlib import Path
import hashlib
import json
import time
import traceback
import urllib.request
from cef_page_v2 import Page
from ordinary_file_dialog_input_v4 import FileDialogInput,window_text,user

ROOT=Path(__file__).resolve().parents[1]
PRODUCT=ROOT/'output/original-flow-hotfix-product0.27.5'
FOLDER=ROOT/'output/native-reference-import-20261121a'
OUT=ROOT/'evidence/native-layer-import-restore-20261121b.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def get(route):return json.load(urllib.request.urlopen('http://127.0.0.1:4700'+route,timeout=30))
def material(phase):return {key:phase.get(key) for key in ['system_id','edit_token','revision','time','paused','bodies','atlas_initial','interventions']}


def main():
    assert FOLDER.is_dir() and not OUT.exists()
    picker=json.loads((ROOT/'evidence/native-reference-import-picker-20261121c.json').read_text(encoding='utf8'))
    assert picker['accepted'] and picker['completed']
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert session['app']==picker['session']['app']
    source=ROOT/picker['source_file'];assert sha(source)==picker['source_sha256']
    exported=json.loads(source.read_text(encoding='utf8'))['checkpoint']
    layer_latest=PRODUCT/'layer-checkpoints/latest.json'
    saved_layer=json.loads(layer_latest.read_text(encoding='utf8'))
    saved_gravity=PRODUCT/'gravity-sessions/latest.json'
    gravity=json.loads(saved_gravity.read_text(encoding='utf8'))
    protected={str(path.relative_to(ROOT)).replace('\\','/'):sha(path) for path in [source,layer_latest,saved_gravity,*sorted((PRODUCT/'layer-checkpoints/branches').glob('*.json'))]}
    manifest=json.loads((PRODUCT/'build-manifest.json').read_text(encoding='utf8'))
    assert all(sha(PRODUCT/name)==digest for name,digest in manifest['files_sha256'].items())
    proof=dict(accepted=False,completed=False,session=session,checks=[],captures=[],actions=[],protected_sha256=protected,
      source_manifest_sha256=sha(PRODUCT/'build-manifest.json'),
      source_sha256={name:sha(ROOT/name) for name in ['scripts/verify-native-layer-import-restore-v2.py','scripts/ordinary_file_dialog_input_v4.py','scripts/ordinary_option_input_v3.py','scripts/ordinary_native_input_v9.py','scripts/cef_page_v2.py']},
      scope='Native owner header/panels and Windows file picker: read preview, import a new branch, load the existing paused four-body save, restore the saved Layers and choose existing/imported branches by mouse. DOM/HTTP only observe. Original scientific files/checkpoints remain intact; the new branch is an intentional curation artifact. No overall workflow, calculation-cancellation, benchmark or scientific milestone acceptance.')
    def persist():OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    with Page() as page:
        window=FileDialogInput(session['app'],page)
        def wait(expression):page.wait_for_function(expression,timeout=90000)
        def click(selector,ready=None):
            proof['step']=selector;persist();window.click(selector)
            if ready:wait(ready)
        def capture(name):
            target=FOLDER/('b-'+name+'.png');assert not target.exists();time.sleep(.3)
            row=window.capture(target);row['sha256']=sha(target);proof['captures'].append(row);persist()
        def check(name,**values):
            proof['checks'].append(dict(name=name,**values));proof['actions']=list(window.actions);persist()
        def stable(phase):assert material(get('/api/state')['physics'])==phase
        def layer_settled():wait('!layerInstrument.pending&&!layerInstrument.snapshot.busy')
        try:
            assert page.evaluate('location.pathname==="/"&&appState.mode==="atlas"&&!pending')
            before=get('/api/layers/state');assert not before['active'] and not before['import_preview']
            previous_ids={branch['id'] for branch in before['branches']}
            click('#open-layers','!document.getElementById("layers-panel").hidden')
            if not page.evaluate('document.getElementById("layers-import").open'):click('#layers-import>summary')
            proof['step']='choose-existing-Layers-export';persist();window.choose_file('#layers-import-file',source)
            click('#layers-import-preview','!layerInstrument.readingFile&&!layerInstrument.pending')
            preview=get('/api/layers/state')['import_preview'];assert preview and preview['valid']
            assert preview['scientific_sha256']==exported['scientific_sha256']
            assert preview['source_sha256']==sha(source)
            assert preview['body_reference_id']=='sol:naif:399' and preview['magnetic_model']=='IGRF14'
            click('#layers-import-reading');capture('layers-preview-origin-readable')
            check('original-export-origin-is-readable-before-import',body=preview['body_reference_id'],model=preview['magnetic_model'],scientific_sha256=preview['scientific_sha256'])
            window.fill('#layers-import-name','Origem curada 21-11 Terra')
            click('#layers-import-commit','!layerInstrument.readingFile&&!layerInstrument.pending')
            imported=get('/api/layers/state');new=[branch for branch in imported['branches'] if branch['id'] not in previous_ids]
            assert len(new)==1 and new[0]['name']=='Origem curada 21-11 Terra'
            branch=new[0];assert branch['scientific_sha256']==exported['scientific_sha256']
            assert not imported['active'] and not imported['import_preview']
            assert not get('/api/state').get('physics')
            proof['created_branch']=branch;check('imports-a-new-branch-without-opening-or-changing-orbit',branch=branch)
            click('#experiment','appState.mode==="experiment"&&!pending')
            click('#load','!pending&&appState.physics?.paused&&appState.physics.bodies.length===4')
            phase=material(get('/api/state')['physics']);assert phase['system_id']==gravity['system_id']
            proof['orbital_phase_after_saved_load']=phase
            click('#open-layers','!document.getElementById("layers-panel").hidden')
            click('#layers-load-saved','!layerInstrument.pending&&!layerInstrument.snapshot.busy&&layerInstrument.snapshot.active')
            restored=get('/api/layers/state')
            assert restored['artifact']['sha256']==saved_layer['checkpoint']['scientific_sha256']
            assert restored['artifact']['visible']==saved_layer['checkpoint']['visible']
            stable(phase);check('restores-saved-science-and-visibility-with-current-orbit-preserved',visible=restored['artifact']['visible'],sha256=restored['artifact']['sha256'])
            if not page.evaluate('document.getElementById("layers-storage").open'):click('#layers-storage>summary')
            jovian=next(row for row in before['branches'] if row['scientific_sha256']!=branch['scientific_sha256'])
            window.select('#layers-branches',jovian['id'])
            click('#layers-branch-load','!layerInstrument.pending&&!layerInstrument.snapshot.busy')
            current=get('/api/layers/state');assert current['artifact']['sha256']==jovian['scientific_sha256']
            assert current['loaded_record']['id']==jovian['id']
            assert current['artifact']['magnetic']['body_reference_id']=='sol:naif:599'
            stable(phase);check('mouse-selects-existing-jupiter-branch',branch=jovian['id'],sha256=current['artifact']['sha256'])
            window.select('#layers-branches',branch['id'])
            click('#layers-branch-load','!layerInstrument.pending&&!layerInstrument.snapshot.busy')
            current=get('/api/layers/state');assert current['loaded_record']['id']==branch['id']
            assert current['artifact']['sha256']==exported['scientific_sha256']
            assert current['artifact']['visible']==exported['visible']
            assert current['artifact']['magnetic']['body_reference_id']=='sol:naif:399'
            stable(phase);capture('layers-imported-branch-selected')
            check('restores-the-imported-earth-branch-with-original-science-and-visibility',branch=branch['id'],sha256=current['artifact']['sha256'])
            click('#layers-leave','!layerInstrument.pending&&!layerInstrument.snapshot.active&&!layerInstrument.snapshot.recovery_required')
            stable(phase)
            click('#layers-panel-close','document.getElementById("layers-panel").hidden')
            click('#atlas','!pending&&appState.mode==="atlas"')
            assert all(sha(ROOT/name)==digest for name,digest in protected.items())
            assert all(sha(PRODUCT/name)==digest for name,digest in manifest['files_sha256'].items())
            proof['original_files_preserved']=True;proof.update(accepted=True,completed=True)
        except Exception:
            proof['failure']=traceback.format_exc()
            if window_text(user.GetForegroundWindow(),'GetClassNameW')=='#32770':window.key(27)
        finally:proof['actions']=list(window.actions);persist()
    print(json.dumps({key:proof.get(key) for key in ['accepted','completed','step','checks','failure']},ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
