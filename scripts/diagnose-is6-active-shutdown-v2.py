"""Normal native app shutdown while its spatial instrument still owns a view."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import argparse
import copy
import hashlib
import json
import sys
import time
import traceback
import zipfile
import psutil
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is6-spatial-product0.18.3/app'
sys.path.insert(0,str(APP))
from is6_product_scene import artifact
h=SourceFileLoader('is6_shutdown_helpers',str(ROOT/'scripts/verify-native-solar-integration.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/('output/is6-active-shutdown-'+args.label);receipt=ROOT/('evidence/is6-active-shutdown-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve evidence')
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert Path(session['serverScript']).resolve()==(APP/'server.py').resolve()
    manifest=json.loads((APP.parent/'build-manifest.json').read_text());hashes=dict(manifest['source_sha256'])
    hashes.update({(APP/n).relative_to(ROOT).as_posix():v for n,v in manifest['files_sha256'].items()})
    for p in [Path(__file__),APP.parent/'build-manifest.json',ROOT/'IS-6-ENCERRAMENTO-ATIVO-CONTRATO.md',ROOT/'scripts/cef_page.py',ROOT/'scripts/verify-native-solar-integration.py',ROOT/'scripts/engine-command.py']:hashes[p.relative_to(ROOT).as_posix()]=sha(p)
    assert all(sha(ROOT/n)==v for n,v in hashes.items());folder.mkdir()
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=hashes,session=session,owner_sha256=sha(ROOT/'user/sessions/latest.json'),limit_s=20.,scope='Normal app shutdown with active spatial view only; not profile/visual acceptance.')
    def persist():receipt.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    shutdown_requested=False
    persist()
    try:
        with Page() as page:
            page.goto(h.BASE+'/');page.wait_for_function('appState&&atlasState&&spatialInstrument.snapshot&&!pending')
            assert not h.get('/api/spatial/state')['active']
            if h.get('/api/state')['mode']=='experiment':h.post('/api/command',dict(command='atlas'))
            page.wait_for_function('appState.mode==="atlas"&&!pending');h.click(page,'#copy-solar')
            page.wait_for_function('appState.physics?.bodies.length===4&&appState.physics.paused&&!pending',timeout=70000)
            phase=h.get('/api/state')['physics'];s=h.get('/api/spatial/state')
            opened=h.post('/api/spatial/command',dict(command='create',guard=s['guard'],source_guard=artifact.body.guard(phase),body_id=phase['bodies'][0]['id'],configuration=copy.deepcopy(artifact.DEFAULT_CONFIGURATION)))
            assert opened['spatial']['active'] and not opened['spatial']['error']
            r['active_scene']=opened['spatial']['scene'];r['source_phase']=h.phase(phase)
            inventory={}
            for root_pid in [session['app'],session['server']]:
                root=psutil.Process(root_pid)
                for process in [root,*root.children(recursive=True)]:
                    try:inventory[process.pid]=dict(pid=process.pid,parent=process.ppid(),name=process.name(),created=process.create_time())
                    except psutil.NoSuchProcess:pass
            r['inventory_before']=list(inventory.values());persist()
            began=time.monotonic();shutdown_requested=True;h.native('openspace.toggleShutdown();return {closing=true}')
        while time.monotonic()-began<=20:
            live=[]
            for pid,p in inventory.items():
                try:
                    process=psutil.Process(pid)
                    if process.create_time()==p['created'] and process.is_running():live.append(p)
                except psutil.NoSuchProcess:pass
            if not live:break
            time.sleep(.1)
        r['elapsed_s']=time.monotonic()-began;r['processes_still_running']=live
        result=None
        until=time.monotonic()+5
        while time.monotonic()<until:
            for path in (APP.parent/'execution-logs').glob('*/process-result.json'):
                sibling=path.parent/'session.json'
                if sibling.is_file() and json.loads(sibling.read_text(encoding='utf-8-sig'))['app']==session['app']:
                    result=json.loads(path.read_text());r['process_result_path']=path.relative_to(ROOT).as_posix();break
            if result is not None:break
            time.sleep(.1)
        r['process_result']=result
        assert sha(ROOT/'user/sessions/latest.json')==r['owner_sha256'] and all(sha(ROOT/n)==v for n,v in hashes.items())
        r['completed']=True;r['accepted']=not live and result==dict(app_exit=0,server_exit=0)
    except Exception:r['failure']=traceback.format_exc()
    finally:
        if not shutdown_requested:
            try:h.native('openspace.toggleShutdown();return {closing=true}')
            except Exception:r['cleanup_failure']=traceback.format_exc()
        persist()
    print(json.dumps({k:v for k,v in r.items() if k not in {'source_sha256','session','source_phase','active_scene','inventory_before'}},ensure_ascii=False),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
