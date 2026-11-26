"""Prove normal four-process exits and reopen the planets through the owner's shortcut."""
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
h=SourceFileLoader('planet_reopen_helpers',str(ROOT/'scripts/benchmark-body-points-native.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True)
    label=parser.parse_args().label
    if not label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):parser.error('Invalid label')
    folder=ROOT/f'output/is6-planet-navigation-reopen-{label}'
    out=ROOT/f'evidence/is6-planet-navigation-reopen-{label}.json'
    if folder.exists() or out.exists():raise FileExistsError('Preserve native reopen evidence')
    folder.mkdir()
    report=dict(completed=False,accepted=False,script_sha256=sha(Path(__file__)),
                shortcut_sha256=sha(ROOT/'Abrir-Planetas.cmd'),opener_sha256=sha(ROOT/'scripts/open-planet-app.py'))
    protected={name:sha(ROOT/name) for name in ['user/sessions/latest.json','Iniciar-Cosmos2.cmd']}
    original_id=None
    def persist():out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    def open_app():
        done=subprocess.run(['cmd.exe','/d','/c',str(ROOT/'Abrir-Planetas.cmd')],cwd=ROOT,
            stdin=subprocess.DEVNULL,capture_output=True,timeout=360)
        log=folder/('shortcut-'+str(len(list(folder.glob('shortcut-*.log'))))+'.log')
        log.write_bytes(done.stdout+b'\n'+done.stderr)
        assert done.returncode==0,(done.returncode,log.as_posix())
        return dict(exit=done.returncode,log=log.relative_to(ROOT).as_posix(),sha256=sha(log))
    persist()
    try:
        profile=json.loads((ROOT/'evidence/is6-planet-navigation-profile-20261111a.json').read_text())
        assert profile['completed'] or profile.get('failure') and profile.get('owner_app_kept_open')
        session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
        original=h.get('/api/navigation/state');report['original_navigation']=original
        before=h.get('/api/navigation/favorites')['views']
        saved=h.post('/api/navigation/save',dict(name='Reabertura temporária · vista inicial'))['navigation']['views']
        original_id=next(x['id'] for x in saved if x['id'] not in {b['id'] for b in before})
        wrapper=psutil.Process(session['launcher']).parent()
        assert any('launch-is6-planet-navigation-candidate.py' in arg for arg in wrapper.cmdline())
        report['previous_session']=session;report['wrapper_pid']=wrapper.pid
        host=Host(folder,h,candidate='output/is6-planet-navigation-product0.24.0',
                  launcher='scripts/launch-is6-planet-navigation-candidate.py')
        host.session=session;host.process=wrapper
        for role in ['app','server','launcher']:
            handle=host.kernel.OpenProcess(0x101000,False,session[role])
            if not handle:raise OSError('Could not retain process exit handle: '+role)
            host.handles['engine' if role=='app' else role]=handle
        persist()
        report['processes']=host.close();h._socket=None
        assert len(report['processes'])==4 and set(report['processes'].values())=={0}
        persist()
        report['shortcut']=open_app()
        fresh=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
        assert fresh['app']!=session['app'] and fresh['is6PlanetNavigationCandidate']
        report['new_session']=fresh
        restored=h.post('/api/navigation/restore',dict(id=original_id))['navigation']
        assert restored['navigation']['Anchor']==original['navigation']['Anchor'] and restored['et']==original['et']
        h.post('/api/navigation/delete',dict(id=original_id));original_id=None
        reference=h.get('/api/atlas/state');assert len(reference['bodies'])==len(reference['renderer']['positions'])==10
        with Page() as page:
            page.wait_for_function('navigationState&&atlasState&&appState?.mode==="atlas"')
            page.evaluate('selectTarget('+json.dumps(restored['target'])+',true)')
            page.locator('#ui-scale').select_option('1')
            report['visible_ui']=dict(title=page.locator('#object-name').inner_text(),url=page.evaluate('location.href'))
        report['shortcut_reuses_existing_window']=open_app()
        assert json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))['app']==fresh['app']
        report['protected_unchanged']={name:sha(ROOT/name)==seal for name,seal in protected.items()}
        assert all(report['protected_unchanged'].values())
        report.update(completed=True,accepted=True,owner_app_kept_open=True)
    except Exception:report['failure']=traceback.format_exc()
    finally:
        try:
            if not any((p.info['name'] or '').lower()=='openspace.exe' and p.info['exe'] and Path(p.info['exe']).is_relative_to(ROOT)
                       for p in psutil.process_iter(['name','exe'])):
                report['recovery_shortcut']=open_app();h._socket=None
            if original_id:
                h.post('/api/navigation/restore',dict(id=original_id));h.post('/api/navigation/delete',dict(id=original_id))
        except Exception:report['recovery_failure']=traceback.format_exc()
        persist()
    print(json.dumps(dict(accepted=report['accepted'],processes=report.get('processes'),
                          failure=report.get('failure'),recovery_failure=report.get('recovery_failure'))))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
