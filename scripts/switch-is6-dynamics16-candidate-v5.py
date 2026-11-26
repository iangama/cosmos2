"""Preserve the visible Atlas view, close normally and open the isolated dynamics16 candidate detached."""
import argparse
import copy
import hashlib
from importlib.machinery import SourceFileLoader
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import uuid
import psutil
from cef_page_v2 import Page
from is6_owned_profile_host import Host

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'output/is6-dynamics16-product0.26.2'
LAUNCHER=ROOT/'scripts/launch-is6-dynamics16-candidate-v5.py'
h=SourceFileLoader('moons_switch_helpers',str(ROOT/'scripts/benchmark-body-points-native.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True)
    label=parser.parse_args().label
    if not label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):parser.error('Invalid label')
    folder=ROOT/f'output/is6-dynamics16-switch-{label}';out=ROOT/f'evidence/is6-dynamics16-switch-{label}.json'
    if folder.exists() or out.exists():raise FileExistsError('Preserve version switch evidence')
    for kind in ['service','http']:
        assert json.loads((ROOT/f'evidence/is6-dynamics16-{kind}-20261112c.json').read_text())['accepted']
    packet=json.loads((TARGET/'build-manifest.json').read_text())
    assert packet['candidate']=='0.26.2' and packet['promoted'] is False
    assert all(sha(TARGET/'app'/n)==s for n,s in packet['files_sha256'].items())
    folder.mkdir()
    result=dict(completed=False,accepted=False,script_sha256=sha(Path(__file__)),launcher_sha256=sha(LAUNCHER))
    protected={name:sha(ROOT/name) for name in ['user/sessions/latest.json','Iniciar-Cosmos2.cmd']}
    def persist():out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    persist()
    try:
        old=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
        assert Path(old['serverScript']).resolve() in [ROOT/'output/is6-planet-navigation-product0.24.0/app/server.py',ROOT/'output/is6-principal-moons-navigation-product0.25.1/app/server.py',ROOT/'output/is6-dynamics16-product0.26.0/app/server.py',ROOT/'output/is6-dynamics16-product0.26.1/app/server.py',TARGET/'app/server.py']
        assert h.get('/api/state')['mode']=='atlas','Preserve current experiment before switching'
        state=h.get('/api/navigation/state');assert not state['flying']
        before=h.get('/api/navigation/favorites')['views']
        saved=h.post('/api/navigation/save',dict(name='Troca temporária · vista anterior'))['navigation']['views']
        row=next(x for x in saved if x['id'] not in {b['id'] for b in before})
        h.post('/api/navigation/delete',dict(id=row['id']))
        assert h.get('/api/navigation/favorites')['views']==before
        result.update(previous_session=old,previous_navigation=state,view=copy.deepcopy(row['view']))
        with Page() as page:result['previous_ui_scale']=page.evaluate('$("ui-scale").value')
        favorite_path=TARGET/'navigation/favorites.json'
        if favorite_path.exists():
            envelope=json.loads(favorite_path.read_text());payload=envelope['payload']
            assert hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=True,allow_nan=False).encode()).hexdigest()==envelope['sha256']
        else:payload=dict(schema=1,views=[])
        assert len(payload['views'])<64
        temporary_id=uuid.uuid4().hex;payload['views'].append(dict(id=temporary_id,name='Vista anterior à troca',view=row['view']))
        envelope=dict(payload=payload,sha256=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=True,allow_nan=False).encode()).hexdigest())
        favorite_path.parent.mkdir(parents=True,exist_ok=True)
        temporary=favorite_path.with_suffix('.tmp');temporary.write_text(json.dumps(envelope,ensure_ascii=True,indent=2)+'\n',encoding='ascii');os.replace(temporary,favorite_path)
        wrapper=psutil.Process(old['launcher']).parent()
        assert any(Path(old['launcher_script']).name in arg for arg in wrapper.cmdline())
        host=Host(folder,h);host.session=old;host.process=wrapper
        for role in ['app','server','launcher']:
            handle=host.kernel.OpenProcess(0x101000,False,old[role]);assert handle
            host.handles['engine' if role=='app' else role]=handle
        result['previous_exits']=host.close();h._socket=None
        assert len(result['previous_exits'])==4 and set(result['previous_exits'].values())=={0}
        with (folder/'host.log').open('xb') as log,(folder/'host-errors.log').open('xb') as err:
            process=subprocess.Popen([sys.executable,'-u','-Xutf8',str(LAUNCHER)],cwd=ROOT,
                stdin=subprocess.DEVNULL,stdout=log,stderr=err,
                creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP)
        result['new_launcher_wrapper_pid']=process.pid;persist()
        deadline=time.monotonic()+300
        while True:
            if process.poll() is not None:raise RuntimeError('Dynamics16 candidate launcher exited before bootstrap')
            try:
                fresh=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
                app=psutil.Process(fresh['app'])
                if (fresh['app']!=old['app'] and Path(fresh['serverScript']).resolve()==TARGET/'app/server.py'
                    and (ROOT/'output/bootstrap-ui.json').stat().st_mtime>=app.create_time()):break
            except (OSError,ValueError,KeyError,psutil.NoSuchProcess):pass
            if time.monotonic()>=deadline:raise TimeoutError('Dynamics16 candidate bootstrap not confirmed')
            time.sleep(.1)
        result['new_session']=fresh
        restored=h.post('/api/navigation/restore',dict(id=temporary_id))['navigation']
        h.post('/api/navigation/delete',dict(id=temporary_id))
        assert restored['et']==state['et'] and restored['navigation']['Anchor']==state['navigation']['Anchor']
        reference=h.get('/api/atlas/state');assert len(reference['bodies'])==len(reference['renderer']['positions'])==16
        with Page() as page:
            page.wait_for_function('navigationState&&atlasState&&appState?.mode==="atlas"')
            page.locator('#ui-scale').select_option(result['previous_ui_scale'])
            page.evaluate('selectTarget('+json.dumps(restored['target'])+',true)')
            result['visible_title']=page.locator('#object-name').inner_text()
        result['protected_unchanged']={name:sha(ROOT/name)==seal for name,seal in protected.items()}
        assert all(result['protected_unchanged'].values())
        result.update(completed=True,accepted=True,owner_app_kept_open=True)
    except Exception:result['failure']=traceback.format_exc()
    finally:
        try:
            if not any((p.info['name'] or '').lower()=='openspace.exe' and p.info['exe'] and Path(p.info['exe']).is_relative_to(ROOT) for p in psutil.process_iter(['name','exe'])):
                recovery=subprocess.run([sys.executable,'-Xutf8',str(ROOT/'scripts/open-planet-app.py')],cwd=ROOT,capture_output=True,timeout=360)
                (folder/'recovery.log').write_bytes(recovery.stdout+recovery.stderr);result['recovery_exit']=recovery.returncode
        except Exception:result['recovery_failure']=traceback.format_exc()
        persist()
    print(json.dumps(dict(accepted=result['accepted'],previous_exits=result.get('previous_exits'),
        new_app=result.get('new_session',{}).get('app'),failure=result.get('failure'),recovery_failure=result.get('recovery_failure'))),flush=True)
    return 0 if result['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
