"""Original launcher/header and genuine Windows input for the delivered point-lens journey."""
from pathlib import Path
import hashlib
import json
import math
import shutil
import time
import traceback
import urllib.request
from cef_page_v2 import Page
from ordinary_option_input_v3 import OptionInput
from ordinary_native_input_v9 import user

ROOT=Path(__file__).resolve().parents[1]
PRODUCT=ROOT/'output/original-flow-hotfix-product0.29.0'
FOLDER=ROOT/'output/native-point-lens-20261121a'
OUT=ROOT/'evidence/native-point-lens-20261121a.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def get(route='/api/state'):return json.load(urllib.request.urlopen('http://127.0.0.1:4700'+route,timeout=30))
def material(p):return {k:p.get(k) for k in ['system_id','revision','time','paused','bodies','atlas_initial','interventions']}
def close_values(a,b):
    if isinstance(a,dict):return set(a)==set(b) and all(close_values(a[k],b[k]) for k in a)
    if isinstance(a,list):return len(a)==len(b) and all(close_values(x,y) for x,y in zip(a,b))
    if type(a) in (int,float) and type(b) in (int,float):return math.isclose(a,b,rel_tol=1e-11,abs_tol=1e-10)
    return a==b


def main():
    assert not FOLDER.exists() and not OUT.exists();FOLDER.mkdir()
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    entry=json.loads((ROOT/'evidence/original-flow-entry-point-lens-20261121a.json').read_text());assert entry['accepted'] and entry['session']['app']==session['app']
    saved=json.loads((ROOT/'evidence/point-lens-session-preservation-20261121a.json').read_text());assert saved['accepted']
    manifest=json.loads((PRODUCT/'build-manifest.json').read_text());assert all(sha(PRODUCT/n)==s for n,s in manifest['files_sha256'].items())
    force_save=PRODUCT/'user/forces/latest.json';old_save=None
    if force_save.exists():
        old_save=FOLDER/'saved-before/latest.json';old_save.parent.mkdir();shutil.copy2(force_save,old_save)
    proof=dict(accepted=False,completed=False,checks=[],captures=[],actions=[],session=session,
      manifest_sha256=sha(PRODUCT/'build-manifest.json'),script_sha256=sha(Path(__file__)),
      scope='Original Iniciar-Cosmos2.cmd/header/scenario and genuine Windows mouse/keyboard at100/150%. Visible options, sky picking, ray probes, three positions, aligned limit, actuation/visibility, real error/recovery, confirmed save/export/restore and return. DOM/HTTP observe only. Previous force-save bytes are archived and restored separately; no performance or whole C2-14 promotion.')
    created_save_sha=None
    def persist():OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    with Page() as page:
        window=OptionInput(session['app'],page)
        def wait(expr):page.wait_for_function(expr,timeout=60000)
        def click(selector,ready=None):
            proof['step']=selector;persist();window.click(selector)
            if ready:wait(ready)
        def ready():wait('!pending&&response?.result.point_lens&&!byId("force-status").classList.contains("error")')
        def group(kind):
            if not page.evaluate('document.querySelector('+json.dumps('[data-point-position='+kind+']')+').open'):click('[data-point-position='+kind+']>summary')
        def capture(name):
            path=FOLDER/(name+'.png');assert not path.exists();time.sleep(.3)
            row=window.capture(path);row['sha256']=sha(path);proof['captures'].append(row);persist()
        def check(name,**values):proof['checks'].append(dict(name=name,**values));proof['actions']=list(window.actions);persist()
        def phase_stable():assert material(get()['physics'])==phase
        def plot_point():
            row=page.evaluate('''(()=>{const p=projectedArrows.find(p=>p.pointLens?.image?.label==='outer'&&!p.pointLens.reference),r=canvas.getBoundingClientRect(),z=Number(getComputedStyle(document.body).zoom)||1,b=document.body.getBoundingClientRect(),layout=parseFloat(getComputedStyle(document.body).width),factor=Math.abs(b.width/layout-1)<.02?z:1;const x=(r.left+p.x)*factor,y=(r.top+p.y)*factor;return{x,y,vw:innerWidth,vh:innerHeight,hit:document.elementFromPoint(x,y)?.id};})()''')
            assert row['hit']=='science-view',row
            _,_,width,height=window.bounds();return row['x']*width/row['vw'],row['y']*height/row['vh']
        try:
            assert page.evaluate('location.pathname==="/"&&!pending&&appState.mode==="atlas"')
            click('#experiment','!pending&&appState.mode==="experiment"');click('#load','!pending&&appState.physics?.paused')
            phase=material(get()['physics']);assert phase=={k:saved['physical_after'].get(k) for k in phase}
            click('#atlas','!pending&&appState.mode==="atlas"')
            nav_before=get('/api/navigation/state');favorites_before=get('/api/navigation/favorites')['views']
            click('#forces','location.pathname==="/forces.html"&&typeof response!=="undefined"&&response&&!pending')
            click('[data-scenario="point-lens"]');ready()
            assert page.evaluate('response.result.point_lens.actual.images.length')==2
            assert page.evaluate('byId("effects").textContent.includes("Desvio gravitacional da luz")')
            fingerprint=page.evaluate('response.physics_sha256')
            click('#point-lens-restore-view');x,y=plot_point();window.click_at(x,y,'visible outer lens image')
            wait('byId("probe").textContent.includes("Imagem externa")')
            left,top,_,_=window.bounds();user.SetCursorPos(round(left+x),round(top+y));user.mouse_event(0x0800,0,0,240,0)
            window.actions.append(dict(input='Windows mouse',action='wheel',delta=240,target='science-view'))
            wait('zoom!==1');click('#point-lens-restore-view','zoom===1&&!byId("probe").textContent')
            assert page.evaluate('response.physics_sha256')==fingerprint
            check('native-sky-picking-and-restore-view-preserve-science')
            window.select('#point-lens-view','rays')
            assert page.evaluate('byId("framing-control").hidden')
            click('#point-lens-measure-inner');assert '−1' in page.evaluate('byId("probe").textContent')
            capture('100-ray-construction-inner-parity')
            check('mouse-selects-ray-view-and-measures-negative-parity-with-positive-flux')
            observed=[]
            for kind,value in [('source','9'),('lens','1'),('observer','1')]:
                group(kind);window.fill('#parameters [name='+kind+'_x_au]',value);click('#calculate');ready()
                observed.append(page.evaluate('response.result.point_lens.geometry.u'));phase_stable()
            assert len(set(observed))==3
            check('ordinary-source-lens-and-observer-position-controls-change-the-lens',u_sequence=observed)
            window.select('#point-lens-view','sky');click('#point-lens-align');ready()
            assert page.evaluate('response.result.point_lens.actual.magnification_total') is None
            assert page.evaluate('!byId("point-lens-limit").hidden')
            click('#point-lens-measure-ring');assert 'indefinida' in page.evaluate('byId("probe").textContent')
            click('#point-lens-restore-view');capture('100-aligned-ring-clear-limit')
            click('[data-force="gravity"][data-control="acting"]');ready()
            assert page.evaluate('response.result.point_lens.actual.magnification_total')==1
            assert page.evaluate('response.result.point_lens.reference.magnification_total') is None
            click('[data-force="gravity"][data-control="acting"]');ready()
            before=page.evaluate('response.physics_sha256')
            click('[data-force="gravity"][data-control="visible"]');ready()
            assert page.evaluate('response.physics_sha256')==before
            check('aligned-limit-actuation-and-reference-visibility-remain-separate');phase_stable()
            before=page.evaluate('JSON.stringify(response)')
            group('source');window.fill('#parameters [name=source_z_kpc]','2')
            click('#calculate','!pending&&byId("force-status").classList.contains("error")')
            assert page.evaluate('JSON.stringify(response)')==before
            assert page.evaluate('!byId("result-draft-note").hidden')
            click('#restore-result-conditions');assert page.evaluate('byId("parameters").elements.source_z_kpc.value')=='8'
            window.fill('#parameters [name=source_x_au]','8');click('#calculate');ready()
            check('invalid-plane-keeps-confirmed-result-and-ordinary-recovery-reapplies-valid-geometry')
            fingerprint=page.evaluate('response.physics_sha256');confirmed=page.evaluate('config')
            click('#save-forces','!pending');created_save_sha=sha(force_save)
            shutil.copy2(force_save,FOLDER/'created-point-lens-save.json')
            window.fill('#parameters [name=source_x_au]','9')
            click('#export-forces','!pending&&Boolean(lastForcesExport)')
            assert page.evaluate('lastForcesExport.configuration')==confirmed
            assert page.evaluate('lastForcesExport.physics_sha256')==fingerprint
            exported=Path(page.evaluate('lastForcesExport.export_file'));assert exported.is_relative_to(PRODUCT)
            proof['export']=dict(path=exported.relative_to(ROOT).as_posix(),sha256=sha(exported))
            click('#load-forces');ready();assert page.evaluate('config')==confirmed
            check('ordinary-save-export-and-restore-use-confirmed-geometry-while-draft-is-edited')
            click('a.back','location.pathname==="/"&&typeof appState!=="undefined"&&appState&&!pending');phase_stable()
            assert close_values(nav_before['navigation'],get('/api/navigation/state')['navigation'])
            assert nav_before['et']==get('/api/navigation/state')['et']
            window.select('#ui-scale','1.5')
            click('#forces','location.pathname==="/forces.html"&&typeof response!=="undefined"&&response&&!pending')
            click('[data-scenario="point-lens"]');ready()
            assert page.evaluate('Number(getComputedStyle(document.body).zoom)')==1.5
            window.select('#point-lens-view','rays');click('#point-lens-measure-inner')
            click('#point-lens-restore-view');capture('150-ray-view-cleared')
            group('observer');window.fill('#parameters [name=observer_x_au]','1');click('#calculate');ready()
            assert page.evaluate('config.parameters.observer_x_au')==1
            window.select('#point-lens-view','sky');click('#point-lens-align');ready()
            click('#point-lens-restore-view');capture('150-aligned-ring-readable-labels')
            check('native-view-position-and-alignment-controls-remain-usable-at150');phase_stable()
            click('a.back','location.pathname==="/"&&typeof appState!=="undefined"&&appState&&!pending')
            window.select('#ui-scale','1');phase_stable()
            nav_after=get('/api/navigation/state')
            assert close_values(nav_before['navigation'],nav_after['navigation']) and nav_before['et']==nav_after['et']
            assert get('/api/navigation/favorites')['views']==favorites_before
            assert all(sha(PRODUCT/n)==s for n,s in manifest['files_sha256'].items())
            proof['navigation_before']=nav_before;proof['navigation_after']=nav_after
            check('returns-to-atlas100-with-owner-phase-camera-epoch-and-favorites-preserved')
            proof.update(accepted=True,completed=True)
        except Exception:proof['failure']=traceback.format_exc()
        finally:
            # Session preservation only, outside feature acceptance: retain our new save
            # artifact and return the previous mutable pointer byte for byte.
            if created_save_sha:
                try:
                    assert sha(force_save)==created_save_sha,'Owner force-save changed; preserve it'
                    if old_save:
                        temporary=force_save.with_suffix('.preserve.tmp');shutil.copy2(old_save,temporary);temporary.replace(force_save)
                        assert sha(force_save)==sha(old_save);proof['previous_force_save_restored']=True
                    else:force_save.unlink();proof['previous_force_save_absence_restored']=True
                except Exception:proof['save_restoration_failure']=traceback.format_exc();proof['accepted']=False
            proof['actions']=list(window.actions);persist()
    print(json.dumps({k:proof.get(k) for k in ['accepted','completed','checks','step','failure','save_restoration_failure']},ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
