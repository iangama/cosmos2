"""Focused native150% scrolling proof after the initial capture showed only part of the ring."""
from pathlib import Path
import hashlib
import json
import time
import traceback
from cef_page_v2 import Page
from ordinary_option_input_v3 import OptionInput

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'output/native-point-lens-large-plot-20261121a'
OUT=ROOT/'evidence/native-point-lens-large-plot-20261121a.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not OUT.exists() and not FOLDER.exists();FOLDER.mkdir()
    prior=json.loads((ROOT/'evidence/native-point-lens-20261121a.json').read_text());assert prior['accepted']
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'));assert session['app']==prior['session']['app']
    proof=dict(accepted=False,completed=False,session=session,actions=[],captures=[],script_sha256=sha(Path(__file__)),
      scope='Focused genuine Windows input after native delivery:150% ring can be fully read by ordinary article scrolling; legend and singular status remain available; return to Atlas100%. No new scientific/performance acceptance.')
    with Page() as page:
        window=OptionInput(session['app'],page)
        def click(selector,ready=None):
            proof['step']=selector;window.click(selector)
            if ready:page.wait_for_function(ready,timeout=60000)
        try:
            assert page.evaluate('location.pathname==="/"&&appState.mode==="atlas"&&!pending')
            window.select('#ui-scale','1.5')
            click('#forces','location.pathname==="/forces.html"&&typeof response!=="undefined"&&response&&!pending')
            click('[data-scenario="point-lens"]','!pending&&Boolean(response?.result.point_lens)')
            click('#point-lens-align','!pending&&response.result.point_lens.actual.magnification_total===null')
            click('#point-lens-restore-view')
            # Ordinary scrolling to this real output brings the entire preceding canvas into view.
            click('#point-lens-geometry')
            rect=page.evaluate('(()=>{const r=canvas.getBoundingClientRect(),z=Number(getComputedStyle(document.body).zoom)||1,b=document.body.getBoundingClientRect(),layout=parseFloat(getComputedStyle(document.body).width),f=Math.abs(b.width/layout-1)<.02?z:1;return{top:r.top*f,bottom:r.bottom*f,height:innerHeight,scale:z}})()')
            assert rect['scale']==1.5 and rect['top']>=122 and rect['bottom']<=rect['height'],rect
            path=FOLDER/'full-ring-and-geometry-at150.png';time.sleep(.3)
            capture=window.capture(path);capture['sha256']=sha(path);proof['captures'].append(capture)
            proof['visible_canvas']=rect
            click('#point-lens-limit')
            assert page.evaluate('byId("point-lens-limit").textContent.includes("não fornece amplificação finita")')
            click('a.back','location.pathname==="/"&&typeof appState!=="undefined"&&appState&&!pending')
            window.select('#ui-scale','1')
            proof.update(accepted=True,completed=True)
        except Exception:proof['failure']=traceback.format_exc()
        finally:proof['actions']=window.actions;OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:proof.get(k) for k in ['accepted','completed','visible_canvas','step','failure']},ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
