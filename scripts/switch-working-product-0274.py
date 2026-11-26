"""Preserve the idle Atlas and on-disk sessions, then select the mouse-option fix."""
from importlib.machinery import SourceFileLoader
from pathlib import Path
import hashlib
import json
import shutil
import time
import traceback

import psutil
from cef_page_v2 import Page
from ordinary_native_input_v6 import NativeInput

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT/'output/original-flow-hotfix-product0.27.3'
NEW = ROOT/'output/original-flow-hotfix-product0.27.4'
FOLDER = ROOT/'output/working-product-switch-20261120c'
OUT = ROOT/'evidence/working-product-switch-20261120c.json'
preservation = SourceFileLoader('session_preservation',str(ROOT/'scripts/preserve-working-session-for-upgrade.py')).load_module()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not FOLDER.exists() and not OUT.exists()
    FOLDER.mkdir()
    proof=dict(accepted=False,completed=False,files=[],scope='Preserve idle Atlas context and all mutable product files; normal Windows shutdown, then local revision selection. No scientific promotion. Native mouse acceptance remains pending.')
    try:
        choice=json.loads((ROOT/'config/local-working-product.json').read_text(encoding='utf8'))
        assert choice['candidate']=='0.27.3'
        for product in [OLD,NEW]:
            manifest=json.loads((product/'build-manifest.json').read_text(encoding='utf8'))
            assert all(sha(product/name)==digest for name,digest in manifest['files_sha256'].items())
        session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
        assert Path(session['serverScript']).parent.parent==OLD
        before=preservation.get('/api/state')
        assert before['mode']=='atlas' and not before.get('physics'), 'A live experiment requires saving before a switch'
        for kind in ['spatial','layers','particles','solar-zone']:
            state=preservation.get('/api/'+kind+'/state')
            assert not state.get('active') and not state.get('busy') and not state.get('recovery_required')
        proof['session']=session
        proof['context']=preservation.native_read('local n=openspace.navigation.getNavigationState("Root");return {navigation=n,et=openspace.time.currentTime(),utc=openspace.time.UTC(),paused=openspace.time.isPaused(),rate=openspace.time.deltaTime()}')
        assert proof['context']['paused'] is True
        for name in ['config/local-working-product.json','Iniciar-Cosmos2.cmd','Abrir-Planetas.cmd','Abrir-Planetas-e-Luas.cmd']:
            destination=FOLDER/'entry-before'/name
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/name,destination)
        # Snapshot disk state before closing, then verify that shutdown did not change it.
        for directory in OLD.iterdir():
            if not directory.is_dir() or directory.name in {'app','data','execution-logs','__pycache__'}:
                continue
            for source in sorted(directory.rglob('*')):
                if not source.is_file() or '__pycache__' in source.parts:
                    continue
                relative=source.relative_to(OLD)
                preserved=FOLDER/'mutable-state'/relative
                preserved.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(source,preserved)
                assert sha(source)==sha(preserved)
                proof['files'].append(dict(relative=relative.as_posix(),sha256=sha(preserved)))
        with Page() as page:
            assert page.evaluate('location.pathname==="/"&&!pending')
            window=NativeInput(session['app'],page)
            process=psutil.Process(session['app'])
            window.key(115,alt=True)
            proof['app_exit']=process.wait(timeout=30)
            proof['close_actions']=window.actions
        assert proof['app_exit']==0
        deadline=time.monotonic()+40
        lifecycle=None
        while time.monotonic()<deadline:
            for record in (ROOT/'output/local-product-launches').glob('*/process-result.json'):
                metadata=record.parent/'session.json'
                if metadata.exists() and json.loads(metadata.read_text(encoding='utf8')).get('app')==session['app']:
                    lifecycle=json.loads(record.read_text(encoding='utf8'))
                    proof['process_result']=record.relative_to(ROOT).as_posix()
                    break
            if lifecycle is not None:break
            time.sleep(.1)
        assert lifecycle and lifecycle['completed'] and lifecycle['server_exit']==0,lifecycle
        for row in proof['files']:
            relative=row['relative']
            assert sha(OLD/relative)==sha(FOLDER/'mutable-state'/relative)==row['sha256']
            destination=NEW/relative
            assert not destination.exists()
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(FOLDER/'mutable-state'/relative,destination)
            assert sha(destination)==row['sha256']
        choice.update(product=NEW.relative_to(ROOT).as_posix(),candidate='0.27.4',scope='Local manual option-selection fix; native mouse acceptance pending, no milestone promotion.')
        temporary=ROOT/'config/local-working-product.tmp'
        temporary.write_text(json.dumps(choice,indent=2)+'\n',encoding='utf8')
        temporary.replace(ROOT/'config/local-working-product.json')
        proof['selection_sha256']=sha(ROOT/'config/local-working-product.json')
        proof['source_manifest_sha256']=sha(OLD/'build-manifest.json')
        proof['target_manifest_sha256']=sha(NEW/'build-manifest.json')
        proof['script_sha256']=sha(Path(__file__))
        proof.update(accepted=True,completed=True)
    except Exception:
        proof['failure']=traceback.format_exc()
    finally:
        OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({key:proof.get(key) for key in ['accepted','completed','app_exit','failure']},ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':
    raise SystemExit(main())
