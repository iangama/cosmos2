"""Save the live experiment through its real button and preserve mutable files before a local revision switch."""
from pathlib import Path
import hashlib
import json
import shutil
import time
import traceback
import urllib.request

from websockets.sync.client import connect
from cef_page_v2 import Page
from ordinary_native_input_v5 import NativeInput

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'output/forces-session-preservation-20261120a'
OUT = ROOT / 'evidence/forces-session-preservation-20261120a.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get(route):
    return json.load(urllib.request.urlopen('http://127.0.0.1:4700'+route, timeout=20))


def material(phase):
    return {key:phase.get(key) for key in ['system_id','edit_token','revision','time','paused','bodies','atlas_initial','interventions']}


def native_read(script):
    with connect('ws://127.0.0.1:4682',open_timeout=3,close_timeout=.2,ping_interval=None) as ws:
        ws.send(json.dumps(dict(type='apiHandshake',apiVersion=dict(major=1,minor=0,patch=0))))
        ws.send(json.dumps(dict(topic=1,type='luascript',payload=dict(script=script,return_=True))).replace('"return_":','"return":'))
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            value=json.loads(ws.recv(timeout=max(.1,deadline-time.monotonic())))
            if value.get('topic')==1:
                return value.get('payload',{}).get('1')
        raise TimeoutError('Native readback timeout')


def main():
    assert not FOLDER.exists() and not OUT.exists()
    FOLDER.mkdir()
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    product=Path(session['serverScript']).parent.parent
    assert product==ROOT/'output/original-flow-hotfix-product0.27.1'
    proof=dict(accepted=False,completed=False,session=session,files=[],actions=[],
               scope='Live session preservation only: ordinary Windows click on Salvar sessão; DOM/HTTP/native camera readback observes state. No version/process switch in this script.')
    try:
        for kind in ['spatial','layers','particles','solar-zone']:
            value=get('/api/'+kind+'/state')
            assert not value.get('active') and not value.get('busy') and not value.get('recovery_required'),kind
        before=get('/api/state')
        assert before['mode']=='experiment' and before['physics']['paused']
        proof['physical_before']=material(before['physics'])
        proof['navigation_before']=native_read('return openspace.navigation.getNavigationState("Root")')
        assert proof['navigation_before'] and proof['navigation_before']['Anchor']
        with Page() as page:
            window=NativeInput(session['app'],page)
            page.wait_for_function('location.pathname==="/"&&appState&&!pending')
            began=time.time()
            window.click('#save')
            page.wait_for_function('!pending&&document.getElementById("notice").textContent!=="Aplicando comando…"')
            manifest=product/'gravity-sessions/latest.json'
            assert manifest.stat().st_mtime>=began-1
            metadata=json.loads(manifest.read_text(encoding='utf8'))
            assert metadata['system_id']==before['physics']['system_id']
            after=get('/api/state')
            assert material(after['physics'])==proof['physical_before']
            proof['notice']=page.evaluate('document.getElementById("notice").textContent')
            proof['actions']=window.actions
            proof['physical_after']=material(after['physics'])
            capture=FOLDER/'saved-live-session.png'
            proof['capture']=window.capture(capture)
            proof['capture']['sha256']=sha(capture)
        for directory in product.iterdir():
            if not directory.is_dir() or directory.name in {'app','data','execution-logs','__pycache__'}:
                continue
            for source in sorted(directory.rglob('*')):
                if not source.is_file() or '__pycache__' in source.parts:
                    continue
                assert source.resolve().is_relative_to(product)
                relative=source.relative_to(product)
                destination=FOLDER/'mutable-state'/relative
                destination.parent.mkdir(parents=True,exist_ok=True)
                digest=sha(source)
                shutil.copy2(source,destination)
                assert sha(source)==sha(destination)==digest
                proof['files'].append(dict(source=source.relative_to(ROOT).as_posix(),relative=relative.as_posix(),preserved=destination.relative_to(ROOT).as_posix(),sha256=digest))
        proof['source_manifest_sha256']=sha(product/'build-manifest.json')
        proof['script_sha256']=sha(Path(__file__))
        proof.update(accepted=True,completed=True)
    except Exception:
        proof['failure']=traceback.format_exc()
    finally:
        OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(accepted=proof['accepted'],completed=proof['completed'],files=len(proof['files']),notice=proof.get('notice'),failure=proof.get('failure')),ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':
    raise SystemExit(main())
