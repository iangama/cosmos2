"""Reproduce the owner's Forces entry using actual visible links/buttons, without URL navigation."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import hashlib
import json
import shutil
import time
import traceback

from PIL import Image
from cef_page_v2 import Page

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
h=SourceFileLoader('original_forces_flow_helpers',str(ROOT/'scripts/benchmark-body-points-native.py')).load_module()


def main():
    folder=ROOT/'output/original-forces-user-flow-20261114b'
    out=ROOT/'evidence/original-forces-user-flow-20261114b.json'
    assert not folder.exists() and not out.exists()
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert Path(session['serverScript']).resolve()==ROOT/'output/is6-expanded-journey-product0.27.0/app/server.py'
    folder.mkdir()
    sources=[Path(__file__),ROOT/'scripts/cef_page_v2.py',ROOT/'output/is6-expanded-journey-product0.27.0/app/server.py',ROOT/'output/is6-expanded-journey-product0.27.0/app/ui/app.js']
    proof=dict(completed=False,feature_working=False,session=session,actions=[],source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in sources})
    before=h.get('/api/navigation/state')
    proof['initial_laboratory']=h.get('/api/state')
    favorites=h.get('/api/navigation/favorites')
    try:
        with Page() as page:
            proof['initial']=page.evaluate('({url:location.href,title:document.title,status:document.getElementById("force-status")?.textContent})')
            if proof['initial']['url'].endswith('/forces.html'):
                page.locator('a.back').click()
                proof['actions'].append('Mouse click: Voltar ao Atlas')
                page.wait_for_function('location.pathname==="/"&&appState&&!pending',timeout=30000)
            else:
                assert page.evaluate('location.pathname==="/"')
            page.locator('#forces').click()
            proof['actions'].append('Mouse click: Forças fundamentais in original Atlas header')
            page.wait_for_function('location.pathname==="/forces.html"&&document.readyState==="complete"')
            page.wait_for_function('document.getElementById("force-status").classList.contains("error")||document.querySelectorAll("#scenarios button").length>0',timeout=30000)
            proof['observed']=page.evaluate('({url:location.href,title:document.getElementById("scene-title").textContent,status:document.getElementById("force-status").textContent,error:document.getElementById("force-status").classList.contains("error"),scenarios:document.querySelectorAll("#scenarios button").length,parameters:document.getElementById("parameters").elements.length,calculate_disabled:document.getElementById("calculate").disabled})')
            assert proof['observed']['error'] and proof['observed']['scenarios']==0
            before_png=set((ROOT/'user/screenshots').rglob('*.png'))
            h.native('openspace.takeScreenshot();return {requested=true}')
            deadline=time.monotonic()+20
            while True:
                fresh=set((ROOT/'user/screenshots').rglob('*.png'))-before_png
                if fresh:
                    assert len(fresh)==1
                    source=fresh.pop()
                    try:
                        with Image.open(source) as im:im.load();assert im.size==(1920,1080)
                        break
                    except (OSError,SyntaxError):pass
                assert time.monotonic()<deadline
                time.sleep(.1)
            target=folder/'original-button-failure.png';shutil.copy2(source,target)
            assert sha(source)==sha(target)
            proof['capture']=dict(path=target.relative_to(ROOT).as_posix(),sha256=sha(target),method='Unedited original native framebuffer')
            page.locator('a.back').click()
            proof['actions'].append('Mouse click: Voltar ao Atlas after failure')
            page.wait_for_function('location.pathname==="/"&&appState&&!pending',timeout=30000)
            proof['atlas_returned']=True
        after=h.get('/api/navigation/state')
        assert after['et']==before['et'] and after['navigation']==before['navigation']
        assert h.get('/api/navigation/favorites')==favorites
        proof['final_laboratory']=h.get('/api/state')
        proof['return_mode']=proof['final_laboratory']['mode']
        proof['return_label_matches_mode']=proof['return_mode']=='atlas'
        assert all(sha(ROOT/name)==seal for name,seal in proof['source_sha256'].items())
        proof.update(completed=True,failure_reproduced=True,camera_epoch_favorites_preserved=True)
    except Exception:
        proof['failure']=traceback.format_exc()
    out.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:proof.get(k) for k in ['completed','failure_reproduced','observed','atlas_returned','failure']},ensure_ascii=False))
    return 0 if proof['completed'] else 1


if __name__=='__main__':raise SystemExit(main())
