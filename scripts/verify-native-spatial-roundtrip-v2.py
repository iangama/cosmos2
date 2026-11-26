"""Export, import, restore and route spatial files through the original native UI."""
from pathlib import Path
import hashlib
import json
import time
import traceback
import urllib.request
from cef_page_v2 import Page
from ordinary_file_dialog_input_v4 import FileDialogInput

ROOT=Path(__file__).resolve().parents[1]
PRODUCT=ROOT/'output/original-flow-hotfix-product0.27.7'
FOLDER=ROOT/'output/native-spatial-roundtrip-20261121b'
OUT=ROOT/'evidence/native-spatial-roundtrip-20261121b.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def get(kind=''):return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/'+(kind+'/state' if kind else 'state'),timeout=30))
def material(p):return {k:p.get(k) for k in ['system_id','revision','time','paused','bodies','atlas_initial','interventions']}


def main():
    assert not FOLDER.exists() and not OUT.exists();FOLDER.mkdir()
    entry=json.loads((ROOT/'evidence/original-flow-entry-spatial-20261121a.json').read_text(encoding='utf8'))
    saved=json.loads((ROOT/'evidence/spatial-session-preservation-20261121a.json').read_text(encoding='utf8'))
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert entry['accepted'] and entry['session']['app']==session['app'] and saved['accepted']
    manifest=json.loads((PRODUCT/'build-manifest.json').read_text(encoding='utf8'))
    assert all(sha(PRODUCT/name)==digest for name,digest in manifest['files_sha256'].items())
    protected={p.relative_to(ROOT).as_posix():sha(p) for folder in ['gravity-sessions','is6-spatial-import-service-records','layer-checkpoints']
               for p in (PRODUCT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    proof=dict(accepted=False,completed=False,session=session,checks=[],captures=[],actions=[],exports=[],created_branches=[],
      protected_sha256=protected,script_sha256=sha(Path(__file__)),manifest_sha256=sha(PRODUCT/'build-manifest.json'),
      scope='Original Iniciar-Cosmos2.cmd, header/panels and genuine Windows file picker: export saved spatial reference, import that exact file as a new branch, restore, export/reimport its nested origin, route schema2 from Layers, cancel preview and return to Atlas. Ordinary mouse/keyboard feature actions; DOM/HTTP observe only. Existing paused experiment and original files preserved. No broader workflow or scientific milestone acceptance.')
    def persist():OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    with Page() as page:
        window=FileDialogInput(session['app'],page)
        def wait(expr):page.wait_for_function(expr,timeout=90000)
        def click(selector,ready=None):
            proof['step']=selector;persist();window.click(selector)
            if ready:wait(ready)
        def capture(label):
            path=FOLDER/(label+'.png');assert not path.exists();time.sleep(.3)
            row=window.capture(path);row['sha256']=sha(path);proof['captures'].append(row);persist()
        def check(name,**values):
            proof['checks'].append(dict(name=name,**values));proof['actions']=list(window.actions);persist()
        def stable():assert material(get()['physics'])==phase
        def settled():wait('!spatialInstrument.pending&&!spatialInstrument.readingFile&&!spatialInstrument.snapshot.busy')
        def export_current():
            click('#spatial-export');settled()
            status=page.evaluate('document.getElementById("spatial-storage-status").textContent')
            assert status.startswith('Exportado para: '),status
            path=Path(status.removeprefix('Exportado para: '));assert path.is_file() and path.is_relative_to(PRODUCT)
            document=json.loads(path.read_text(encoding='utf8'))
            assert document['schema']==2 and document['kind']=='is6_spatial_body_mesh_checkpoint_with_origin'
            row=dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size)
            proof['exports'].append(row);persist();return path,document
        def close_reference():
            click('#spatial-leave','!spatialInstrument.pending&&!spatialInstrument.snapshot.active&&!spatialInstrument.snapshot.recovery_required');stable()
        def import_file(path,name):
            if not page.evaluate('document.getElementById("spatial-import-section").open'):click('#spatial-import-section>summary')
            proof['step']='Windows picker '+path.name;persist();window.choose_file('#spatial-import-file',path)
            click('#spatial-import-preview');settled()
            preview=get('spatial')['import_preview'];assert preview and preview['valid'],get('spatial')['error']
            assert preview['source_sha256']==sha(path) and preview['source_format']=='spatial-checkpoint-with-origin-2'
            assert not preview['magnetic_sample_created'] and not preview['scientific_resampling']
            click('#spatial-import-reading');capture('preview-'+str(len(proof['created_branches'])+1))
            before={row['id'] for row in get('spatial')['branches']}
            window.fill('#spatial-import-name',name)
            wait('!document.getElementById("spatial-import-commit").disabled')
            click('#spatial-import-commit');settled()
            state=get('spatial');created=[row for row in state['branches'] if row['id'] not in before]
            assert len(created)==1 and created[0]['name']==name and not state['active'] and not state['import_preview']
            branch=created[0];proof['created_branches'].append(branch);stable()
            return preview,branch
        def restore(branch,expected,expected_origin):
            window.select('#spatial-branches',branch['id'])
            click('#spatial-branch-load');settled()
            state=get('spatial');assert state['active'] and not state['recovery_required'],state['error']
            assert state['artifact']['sha256']==expected['artifact_sha256']
            assert state['artifact']['view']==expected['view']
            assert state['artifact']['origin']['source_sha256']==expected_origin
            stable();return state
        try:
            assert page.evaluate('location.pathname==="/"&&appState.mode==="atlas"&&!pending')
            assert page.evaluate('Number(getComputedStyle(document.body).zoom)')==1
            click('#experiment','!pending&&appState.mode==="experiment"')
            click('#load','!pending&&appState.physics?.paused')
            phase=material(get()['physics']);assert phase=={k:saved['physical_after'].get(k) for k in phase}
            proof['restored_phase']=phase
            check('ordinary-saved-load-restores-the-preserved-owner-experiment',system_id=phase['system_id'])
            click('#open-spatial','!document.getElementById("spatial-panel").hidden')
            click('#spatial-load-saved','!spatialInstrument.pending&&!spatialInstrument.snapshot.busy&&spatialInstrument.snapshot.active')
            initial=get('spatial');stable();first,first_document=export_current();close_reference()
            preview,branch=import_file(first,'Espacial roundtrip 21-11')
            assert preview['artifact_sha256']==initial['artifact']['sha256'] and preview['view']==first_document['view']
            check('current-native-export-previews-and-imports-with-exact-origin',source_sha256=sha(first),branch=branch['id'])
            restored=restore(branch,preview,sha(first));capture('first-import-restored')
            check('mouse-restores-new-branch-with-science-view-and-phase-preserved',branch=branch['id'],artifact_sha256=restored['artifact']['sha256'])
            second,second_document=export_current()
            assert second_document['origin']['source_sha256']==sha(first)
            assert second_document['artifact']==first_document['artifact'] and second_document['view']==first_document['view']
            close_reference()
            preview2,branch2=import_file(second,'Espacial origem encadeada 21-11')
            assert preview2['artifact_sha256']==preview['artifact_sha256'] and preview2['view']==preview['view']
            restored=restore(branch2,preview2,sha(second));capture('nested-import-restored')
            check('native-export-and-reimport-retain-both-generations-of-origin',source_sha256=sha(second),nested_source_sha256=sha(first),branch=branch2['id'])
            close_reference()
            click('#spatial-panel-close','document.getElementById("spatial-panel").hidden')
            layers_before=get('layers');assert not layers_before['active']
            layer_ids=[row['id'] for row in layers_before['branches']]
            click('#open-layers','!document.getElementById("layers-panel").hidden')
            if not page.evaluate('document.getElementById("layers-import").open'):click('#layers-import>summary')
            window.choose_file('#layers-import-file',second)
            click('#layers-import-preview','!layerInstrument.pending&&!layerInstrument.readingFile')
            wait('!document.getElementById("layers-spatial-route").hidden')
            click('#layers-import-reading');capture('layers-spatial-handoff')
            click('#layers-spatial-route','document.getElementById("layers-panel").hidden&&!document.getElementById("spatial-panel").hidden')
            assert page.evaluate('document.getElementById("spatial-import-file").files[0]?.name')==second.name
            click('#spatial-import-preview');settled()
            routed=get('spatial')['import_preview'];assert routed and routed['valid'] and routed['source_sha256']==sha(second)
            assert [row['id'] for row in get('layers')['branches']]==layer_ids and not get('layers')['active']
            check('layers-routes-current-spatial-format-with-original-bytes-and-no-magnetic-sample',source_sha256=sha(second))
            click('#spatial-import-cancel','!spatialInstrument.pending&&!spatialInstrument.snapshot.import_preview')
            assert not get('spatial')['active'];stable()
            click('#spatial-load-saved','!spatialInstrument.pending&&!spatialInstrument.snapshot.busy&&spatialInstrument.snapshot.active')
            final=get('spatial');assert final['artifact']['sha256']==initial['artifact']['sha256'] and final['artifact']['view']==initial['artifact']['view']
            close_reference();click('#spatial-panel-close','document.getElementById("spatial-panel").hidden')
            click('#atlas','!pending&&appState.mode==="atlas"');stable()
            check('cancel-preview-and-restore-existing-save-return-to-atlas-with-owner-phase-intact')
            assert all(sha(ROOT/name)==digest for name,digest in protected.items())
            assert all(sha(PRODUCT/name)==digest for name,digest in manifest['files_sha256'].items())
            proof['original_files_preserved']=True;proof.update(accepted=True,completed=True)
        except Exception:proof['failure']=traceback.format_exc()
        finally:proof['actions']=list(window.actions);persist()
    print(json.dumps({k:proof.get(k) for k in ['accepted','completed','step','checks','failure']},ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
