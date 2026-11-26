"""Retain four real process handles, run the own profile, close, audit and reopen."""
import argparse
import hashlib
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import subprocess
import sys
import traceback

import psutil
from cef_page_v2 import Page
from is6_owned_profile_host import Host

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label',required=True)
    parser.add_argument('--plan-label',required=True)
    args=parser.parse_args()
    for label in [args.label,args.plan_label]:
        if not label or len(label)>20 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
            parser.error('Invalid label')
    folder=ROOT/f'output/is6-moons-layers-profile-{args.label}-host'
    receipt=ROOT/f'evidence/is6-moons-layers-profile-{args.label}.json'
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve own profile host')
    folder.mkdir()
    module=SourceFileLoader('moons_layers_profile',str(ROOT/'scripts/profile-is6-moons-layers.py')).load_module()
    h=module.h
    original_id=None
    host=None
    closure={}
    status=1

    def open_app():
        log=folder/('reopen-'+str(len(list(folder.glob('reopen-*.log'))))+'.log')
        with log.open('xb') as stream:
            done=subprocess.run([sys.executable,'-Xutf8',str(ROOT/'scripts/open-moons-app.py')],cwd=ROOT,
                                stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,timeout=360)
        assert done.returncode==0,log.as_posix()
        h._socket=None
        return dict(log=log.relative_to(ROOT).as_posix(),sha256=sha(log))

    try:
        original=h.get('/api/navigation/state')
        before=h.get('/api/navigation/favorites')['views']
        saved=h.post('/api/navigation/save',dict(name='Perfil de camadas temporário · vista inicial'))['navigation']['views']
        original_id=next(x['id'] for x in saved if x['id'] not in {b['id'] for b in before})
        session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
        assert Path(session['serverScript']).resolve()==ROOT/'output/is6-principal-moons-navigation-product0.25.1/app/server.py'
        wrapper=psutil.Process(session['launcher']).parent()
        assert any('launch-is6-principal-moons-candidate-v2.py' in arg for arg in wrapper.cmdline())
        host=Host(folder,h,candidate='output/is6-principal-moons-navigation-product0.25.1',
                  launcher='scripts/launch-is6-principal-moons-candidate-v2.py')
        host.session,host.process=session,wrapper
        for role in ['app','server','launcher']:
            handle=host.kernel.OpenProcess(0x101000,False,session[role])
            if not handle:raise OSError('Cannot retain process handle: '+role)
            host.handles['engine' if role=='app' else role]=handle
        sys.argv=[str(module.__file__),'--label',args.label,'--plan-label',args.plan_label]
        status=module.main()
    except Exception:
        closure['driver_failure']=traceback.format_exc()
    finally:
        try:
            if host:closure['processes']=host.close()
        except Exception:
            closure['cleanup_failure']=traceback.format_exc();status=1
        try:
            closure['reopen']=open_app()
            if original_id:
                restored=h.post('/api/navigation/restore',dict(id=original_id))['navigation']
                h.post('/api/navigation/delete',dict(id=original_id));original_id=None
                assert restored['et']==original['et']
                assert restored['navigation']['Anchor']==original['navigation']['Anchor']
                with Page() as page:
                    page.wait_for_function('navigationState&&atlasState&&appState?.mode==="atlas"')
                    page.evaluate('selectTarget('+json.dumps(restored['target'])+',true)')
                    page.locator('#ui-scale').select_option('1')
            assert h.get('/api/navigation/favorites')['views']==before
            assert len(h.get('/api/atlas/state')['bodies'])==16
            closure['owner_app_kept_open']=True
            closure['reopened_session']=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
        except Exception:
            closure['reopen_failure']=traceback.format_exc();status=1
        if receipt.exists():
            data=json.loads(receipt.read_text());data.update(closure)
            if any(k in closure for k in ['driver_failure','cleanup_failure','reopen_failure']):data['completed']=False
            receipt.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        (folder/'closure.json').write_text(json.dumps(closure,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    if status==0:
        status=subprocess.run([sys.executable,'-Xutf8',str(ROOT/'scripts/audit-is6-moons-layers-profile.py'),
                               '--label',args.label],cwd=ROOT).returncode
    print(json.dumps(dict(exit=status,owner_app_kept_open=closure.get('owner_app_kept_open'),
                          processes=closure.get('processes'))),flush=True)
    return status


if __name__=='__main__':raise SystemExit(main())
