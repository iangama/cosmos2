"""Fresh host restore, real CEF branch/export, and damaged-file rollback."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import argparse
import hashlib
import json
import sys
import time
import traceback
import zipfile
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is6-spatial-product0.18.1/app'
h=SourceFileLoader('is6_persistence_helpers',str(ROOT/'scripts/verify-native-solar-integration.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/('output/is6-persistence-native-'+args.label);receipt=ROOT/('evidence/is6-persistence-native-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve evidence')
    manifest=json.loads((APP.parent/'build-manifest.json').read_text());hashes=dict(manifest['source_sha256'])
    hashes.update({(APP/n).relative_to(ROOT).as_posix():v for n,v in manifest['files_sha256'].items()})
    for p in [Path(__file__),APP.parent/'build-manifest.json',ROOT/'scripts/cef_page.py',ROOT/'scripts/verify-native-solar-integration.py',ROOT/'scripts/engine-command.py']:hashes[p.relative_to(ROOT).as_posix()]=sha(p)
    assert all(sha(ROOT/n)==v for n,v in hashes.items());folder.mkdir()
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,checks={},source_sha256=hashes,page_errors=[],owner_sha256=sha(ROOT/'user/sessions/latest.json'),scope='Fresh native host restoration/CEF persistence and damaged-file atomicity; no visual or performance acceptance.')
    saved_path=APP.parent/'spatial-checkpoints/saved.json';saved=saved_path.read_bytes()
    payload=json.loads(saved)['artifact'];old_id=payload['id'];view=json.loads(saved)['view']
    def persist():receipt.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def state():return h.get('/api/spatial/state')
    def click(page,id):
        page.wait_for_function('!document.getElementById('+json.dumps('spatial-'+id)+').disabled',timeout=30000)
        page.locator('#spatial-'+id).click();page.wait_for_function('!spatialInstrument.pending&&!spatialInstrument.snapshot.busy',timeout=40000)
    def native(s):return h.native('return {draw=openspace.propertyValue("Scene.'+s['scene']['wire']+'.Renderable.DrawElements"),camera=openspace.navigation.getNavigationState("Root")}')
    persist()
    try:
        with Page() as page:
            page.on('pageerror',lambda error:r['page_errors'].append(error));page.goto(h.BASE+'/');page.wait_for_function('appState&&atlasState&&spatialInstrument.snapshot&&!pending')
            assert not state()['active']
            page.locator('#open-spatial').click();click(page,'copy');page.wait_for_function('appState?.mode==="experiment"&&!pending',timeout=70000)
            phase=h.get('/api/state')['physics'];held=h.phase(phase)
            assert phase['system_id']!=payload['phase']['system_id'],'Fresh four-center phase required'
            click(page,'load-saved');s=state();assert s['artifact']['id']==old_id and s['artifact']['view']==view
            r['checks']['new_phase_restores_archived_reference_without_changing_orbit']=h.phase(h.get('/api/state')['physics'])==held
            r['controls']=page.evaluate('({bodyValue:document.getElementById("spatial-body").value,bodyText:document.getElementById("spatial-body").selectedOptions[0]?.textContent,radial:Number(document.getElementById("spatial-radial").value),caption:document.getElementById("spatial-caption-source").textContent})')
            r['checks']['restored_source_identified_in_body_control']=r['controls'].get('bodyText')==s['artifact']['source']['name']
            r['checks']['restored_probe_control_exact']=r['controls']['radial']==view['selected_radial_index']
            before=state();context=native(before)
            saved_path.write_text('{}',encoding='utf-8')
            page.evaluate('document.getElementById("spatial-storage-fields").closest("details").open=true')
            click(page,'load');after=state()
            r['checks']['damaged_checkpoint_preserves_artifact_view_camera_and_guard']=after['artifact']==before['artifact'] and after['guard']==before['guard'] and native(after)==context
            saved_path.write_bytes(saved)
            name='Ramo CEF · '+args.label;page.evaluate('document.getElementById("spatial-branch-name").value='+json.dumps(name));click(page,'branch-create')
            branch=state()['branch_parent'];r['branch_id']=branch
            page.wait_for_function('spatialInstrument.snapshot.branch_parent==='+json.dumps(branch))
            page.locator('#spatial-branches').select_option(branch);click(page,'branch-load')
            r['checks']['CEF_branch_creation_selection_and_restore']=state()['branch_parent']==branch and state()['artifact']==before['artifact']
            click(page,'export');message=page.locator('#spatial-storage-status').inner_text();r['export_message']=message
            export_path=Path(message.removeprefix('Exportado para: '));export=json.loads(export_path.read_text())
            r['checks']['CEF_export_exact_reference_view_lineage']=export['artifact']==payload and export['view']==view and export['lineage_parent']==branch
            click(page,'leave');page.wait_for_function('!spatialInstrument.snapshot.active');assert not state()['active']
            r['checks']['phase_and_owner_preserved']=h.phase(h.get('/api/state')['physics'])==held and sha(ROOT/'user/sessions/latest.json')==r['owner_sha256']
            assert all(sha(ROOT/n)==v for n,v in hashes.items()) and not r['page_errors']
            r['completed']=True;r['accepted']=all(r['checks'].values())
    except Exception:r['failure']=traceback.format_exc()
    finally:
        saved_path.write_bytes(saved)
        try:
            s=state()
            if s['active']:h.post('/api/spatial/command',dict(command='leave',guard=s['guard']))
            if h.get('/api/state')['mode']=='experiment':h.post('/api/command',dict(command='atlas'))
            h.native('openspace.toggleShutdown();return {closing=true}')
        except Exception:r['cleanup_failure']=traceback.format_exc();r['accepted']=False
        persist()
    print(json.dumps({k:v for k,v in r.items() if k!='source_sha256'},ensure_ascii=False),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
