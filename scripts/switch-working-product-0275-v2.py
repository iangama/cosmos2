"""Switch the local working revision only after verified live-state preservation and normal shutdown."""
from importlib.machinery import SourceFileLoader
from pathlib import Path
import hashlib
import json
import shutil
import time
import traceback
import urllib.request

import psutil
from cef_page_v2 import Page
from ordinary_native_input_v8 import NativeInput

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'output/original-flow-hotfix-product0.27.4'
NEW = ROOT / 'output/original-flow-hotfix-product0.27.5'
FOLDER = ROOT / 'output/working-product-switch-20261120e'
OUT = ROOT / 'evidence/working-product-switch-20261120e.json'
preservation = SourceFileLoader('working_state_preservation',str(ROOT/'scripts/preserve-working-session-for-upgrade.py')).load_module()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not FOLDER.exists() and not OUT.exists()
    FOLDER.mkdir()
    saved=json.loads((ROOT/'evidence/forces-session-preservation-20261120b.json').read_text(encoding='utf8'))
    checked=json.loads((ROOT/'evidence/forces-confirmed-ui-20261120b-after.json').read_text(encoding='utf8'))
    manifest=json.loads((NEW/'build-manifest.json').read_text(encoding='utf8'))
    proof=dict(accepted=False,completed=False,native_user_flow_accepted=False,files=[],
               scope='Local revision switch after ordinary UI save and normal Windows close. Scientific milestones remain unpromoted. Raw native clock/camera is recorded for supplementary session restoration.')
    try:
        assert saved['accepted'] and checked['accepted'] and checked['failed']==0
        assert all(sha(NEW/name)==digest for name,digest in manifest['files_sha256'].items())
        session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
        assert Path(session['serverScript']).parent.parent==OLD and session['app']==saved['session']['app']
        current=preservation.get('/api/state')
        assert current['mode']=='experiment' and preservation.material(current['physics'])==saved['physical_after']
        for kind in ['spatial','layers','particles','solar-zone']:
            state=preservation.get('/api/'+kind+'/state')
            assert not state.get('active') and not state.get('busy') and not state.get('recovery_required')
        for row in saved['files']:
            assert sha(ROOT/row['source'])==sha(ROOT/row['preserved'])==row['sha256'],row['source']
        for name in ['config/local-working-product.json','Iniciar-Cosmos2.cmd','Abrir-Planetas.cmd','Abrir-Planetas-e-Luas.cmd']:
            destination=FOLDER/'entry-before'/name
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/name,destination)
            proof.setdefault('entry_before_sha256',{})[name]=sha(destination)
        proof['context']=preservation.native_read('local n=openspace.navigation.getNavigationState("Root");return {navigation=n,et=openspace.time.currentTime(),utc=openspace.time.UTC(),paused=openspace.time.isPaused(),rate=openspace.time.deltaTime()}')
        assert proof['context']['navigation']['Anchor'] and proof['context']['paused'] is True
        proof['physical_before']=saved['physical_after']
        with Page() as page:
            assert page.evaluate('location.pathname==="/"&&!pending')
            window=NativeInput(session['app'],page)
            app=psutil.Process(session['app'])
            window.key(115,alt=True)
            proof['close_actions']=window.actions
            proof['app_exit']=app.wait(timeout=30)
        assert proof['app_exit']==0
        deadline=time.monotonic()+40
        lifecycle=None
        while time.monotonic()<deadline:
            for record in (ROOT/'output/local-product-launches').glob('*/process-result.json'):
                meta=record.parent/'session.json'
                if meta.exists() and json.loads(meta.read_text(encoding='utf8')).get('app')==session['app']:
                    lifecycle=json.loads(record.read_text(encoding='utf8'))
                    proof['previous_process_result']=record.relative_to(ROOT).as_posix()
                    break
            if lifecycle is not None:
                break
            time.sleep(.1)
        assert lifecycle and lifecycle['completed'] and lifecycle['app_exit']==0 and lifecycle['server_exit']==0,lifecycle
        assert not [p for p in psutil.process_iter(['name']) if (p.info['name'] or '').lower()=='openspace.exe']
        for row in saved['files']:
            source=ROOT/row['preserved'];destination=NEW/row['relative']
            assert not destination.exists(), 'Preserve existing target state: '+str(destination)
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,destination)
            assert sha(destination)==row['sha256']
            proof['files'].append(dict(relative=row['relative'],sha256=row['sha256']))
        selection=json.loads((ROOT/'config/local-working-product.json').read_text(encoding='utf8'))
        selection.update(product=NEW.relative_to(ROOT).as_posix(),candidate='0.27.5',scope='Local working correction; native functional review pending, no milestone promotion.')
        temporary=ROOT/'config/local-working-product.tmp'
        temporary.write_text(json.dumps(selection,indent=2)+'\n',encoding='utf8')
        temporary.replace(ROOT/'config/local-working-product.json')
        body='@echo off\ncd /d "%~dp0"\n"%~dp0.tooling\\python\\Scripts\\python.exe" -Xutf8 "%~dp0scripts\\open-working-cosmos2-v2.py"\nif errorlevel 1 (\n  pause\n  exit /b 1\n)\nexit /b 0\n'
        for name in ['Iniciar-Cosmos2.cmd','Abrir-Planetas.cmd','Abrir-Planetas-e-Luas.cmd']:
            (ROOT/name).write_text(body,encoding='utf8',newline='')
        proof['selection_sha256']=sha(ROOT/'config/local-working-product.json')
        proof['source_manifest_sha256']=sha(OLD/'build-manifest.json')
        proof['target_manifest_sha256']=sha(NEW/'build-manifest.json')
        proof['script_sha256']=sha(Path(__file__))
        proof.update(accepted=True,completed=True)
    except Exception:
        proof['failure']=traceback.format_exc()
    finally:
        OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({key:proof.get(key) for key in ['accepted','completed','app_exit','previous_process_result','failure']},ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':
    raise SystemExit(main())
