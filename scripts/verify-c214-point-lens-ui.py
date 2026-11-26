"""Real isolated HTTP plus a separate headless Windows browser; native owner acceptance remains separate."""
from pathlib import Path
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import traceback
import urllib.request
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/c214-point-lens-ui-staging'
FOLDER=ROOT/'output/c214-point-lens-ui-20261121a'
OUT=ROOT/'evidence/c214-point-lens-ui-20261121a.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not FOLDER.exists() and not OUT.exists();FOLDER.mkdir()
    prepared=json.loads((STAGE/'preparation.json').read_text());assert all(sha(STAGE/n)==s for n,s in prepared['files_sha256'].items())
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close();base=f'http://127.0.0.1:{port}'
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),STAGE/'preparation.json']}
    proof=dict(accepted=False,completed=False,checks=[],captures=[],javascript_errors=[],unexpected_requests=[],source_sha256=sources,
      scope='Headless Windows browser on actual separate full HTTP server and isolated records,100%/150%. Visible custom option lists, grouped positions, sky/ray views, probes/picking, alignment, operators, real domain errors/recovery and confirmed save/export/restore. This is supplementary UI evidence, not native original-launcher or performance acceptance.')
    def persist():OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    server=None;browser=None
    def call(route,value=None):
        request=urllib.request.Request(base+route,data=None if value is None else json.dumps(value).encode(),headers={'Content-Type':'application/json'})
        return json.load(urllib.request.urlopen(request,timeout=20))
    try:
        env=os.environ.copy();env.update(COSMOS2_ROOT=str(ROOT),COSMOS2_STORAGE=str(FOLDER/'private-legacy-storage'))
        with (FOLDER/'server.log').open('xb') as stream:
            server=subprocess.Popen([sys.executable,'-u','-Xutf8',str(STAGE/'app/server.py'),'--port',str(port)],cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+45
        while True:
            assert server.poll() is None,'UI backend exited before readiness'
            try:call('/api/forces/catalog');break
            except OSError:assert time.monotonic()<deadline;time.sleep(.05)
        with sync_playwright() as p:
            executable=Path(p.chromium.executable_path)
            if not executable.is_file():executable=Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
            assert executable.is_file(),'A separate headless browser is required'
            browser=p.chromium.launch(headless=True,executable_path=str(executable),args=['--disable-background-networking'])
            proof['browser_executable']=str(executable)
            for scale in ['1','1.5']:
                context=browser.new_context(viewport=dict(width=1440,height=900),device_scale_factor=1)
                context.add_init_script("localStorage.setItem('cosmos2-ui-scale',"+json.dumps(scale)+")")
                def route(request_route):
                    if not request_route.request.url.startswith(base+'/'):
                        proof['unexpected_requests'].append(request_route.request.url);request_route.abort()
                    else:request_route.continue_()
                context.route('**/*',route)
                page=context.new_page();page.set_default_timeout(10000)
                page.on('pageerror',lambda error:proof['javascript_errors'].append(str(error)))
                def wait(expr):page.wait_for_function(expr,timeout=20000)
                def click(selector,ready=None):
                    proof['step']=scale+':'+selector;persist();page.locator(selector).click()
                    if ready:wait(ready)
                def ready():wait('!pending&&response?.result.point_lens&&!byId("force-status").classList.contains("error")')
                def select(selector,value):
                    source=page.locator(selector);trigger=source.locator('..').locator('.c2-choice-trigger')
                    trigger.click();page.locator('[role=option][aria-disabled="false"][data-choice-value='+json.dumps(value)+']').click()
                    assert source.input_value()==value
                def group(kind):
                    details=page.locator('[data-point-position='+kind+']')
                    if details.get_attribute('open') is None:details.locator('summary').click()
                def capture(name):
                    path=FOLDER/(scale.replace('.','-')+'-'+name+'.png');assert not path.exists()
                    page.screenshot(path=str(path));proof['captures'].append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path)))
                def check(name,**values):proof['checks'].append(dict(name=name,scale=scale,**values));persist()
                try:
                    page.goto(base+'/forces.html');wait('typeof response!=="undefined"&&response?.ok&&!pending')
                    click('[data-scenario="point-lens"]');ready()
                    assert page.locator('.timeline').is_hidden()
                    assert page.evaluate('Number(getComputedStyle(document.body).zoom)')==float(scale)
                    assert page.evaluate('response.result.point_lens.actual.images.length')==2
                    assert page.locator('[data-point-position=source]').get_attribute('open') is not None
                    before=page.evaluate('response.physics_sha256')
                    select('#point-lens-view','rays');assert page.evaluate('response.physics_sha256')==before
                    click('#point-lens-measure-inner');assert '−1' in page.locator('#probe').text_content()
                    capture('ray-construction-and-inner-parity')
                    select('#point-lens-view','sky')
                    point=page.evaluate('(()=>{const p=projectedArrows.find(p=>p.pointLens?.image?.label==="outer"&&!p.pointLens.reference);return {x:p.x,y:p.y,width:canvas.width,height:canvas.height}})()')
                    box=page.locator('#science-view').bounding_box()
                    page.mouse.click(box['x']+point['x']*box['width']/point['width'],box['y']+point['y']*box['height']/point['height'])
                    assert 'Imagem externa' in page.locator('#probe').text_content()
                    check('visible-view-options-ray-probe-and-sky-canvas-picking')
                    observed=[]
                    for kind,value in [('source','9'),('lens','1'),('observer','1')]:
                        group(kind);page.locator('#parameters [name='+kind+'_x_au]').fill(value);click('#calculate');ready()
                        observed.append(page.evaluate('response.result.point_lens.geometry.u'))
                    assert len(set(observed))==3
                    check('all-three-grouped-position-controls-change-lensing',u_sequence=observed)
                    click('#point-lens-align');ready()
                    assert page.evaluate('response.result.point_lens.actual.magnification_total') is None
                    assert page.locator('#point-lens-limit').is_visible()
                    click('#point-lens-measure-ring');assert 'indefinida' in page.locator('#probe').text_content()
                    capture('aligned-ring-explicit-limit')
                    page.locator('[data-force=gravity][data-control=acting]').uncheck();ready()
                    assert page.evaluate('response.result.point_lens.actual.magnification_total')==1
                    assert page.evaluate('response.result.point_lens.reference.magnification_total') is None
                    page.locator('[data-force=gravity][data-control=acting]').check();ready()
                    before=page.evaluate('response.physics_sha256')
                    page.locator('[data-force=gravity][data-control=visible]').uncheck();ready()
                    assert page.evaluate('response.physics_sha256')==before
                    check('alignment-explicit-status-actuation-and-visibility-remain-distinct')
                    before=page.evaluate('JSON.stringify(response)')
                    group('source');page.locator('#parameters [name=source_z_kpc]').fill('2')
                    click('#calculate','!pending&&byId("force-status").classList.contains("error")')
                    assert page.evaluate('JSON.stringify(response)')==before
                    assert page.locator('#result-draft-note').is_visible()
                    click('#restore-result-conditions');assert page.locator('#parameters [name=source_z_kpc]').input_value()=='8'
                    page.locator('#parameters [name=mass_solar]').fill('10000')
                    page.locator('#parameters [name=source_z_kpc]').fill('4.01');page.locator('#parameters [name=source_x_au]').fill('10000')
                    click('#calculate','!pending&&byId("force-status").classList.contains("error")')
                    assert '1000rs' in page.locator('#force-status').text_content()
                    assert page.evaluate('JSON.stringify(response)')==before
                    click('#restore-result-conditions')
                    check('real-plane-and-secondary-impact-errors-preserve-confirmed-result-and-recover')
                    page.locator('#parameters [name=source_x_au]').fill('8');click('#calculate');ready()
                    if scale=='1':
                        confirmed=page.evaluate('response.configuration');fingerprint=page.evaluate('response.physics_sha256')
                        click('#save-forces','!pending')
                        page.locator('#parameters [name=source_x_au]').fill('9')
                        click('#export-forces','!pending&&Boolean(lastForcesExport)')
                        assert page.evaluate('lastForcesExport.configuration')==confirmed
                        assert page.evaluate('lastForcesExport.physics_sha256')==fingerprint
                        click('#load-forces');ready()
                        assert page.evaluate('config')==confirmed and page.locator('#parameters [name=source_x_au]').input_value()=='8'
                        check('save-export-and-restore-use-confirmed-geometry-while-draft-is-edited')
                    click('#scene-title');capture('complete-sky-view')
                    layout=page.evaluate('(()=>{const a=document.querySelector("article"),b=document.querySelector("aside");return {article:a.scrollWidth-a.clientWidth,aside:b.scrollWidth-b.clientWidth}})()')
                    assert layout['article']<=1 and layout['aside']<=1,layout
                    assert not proof['javascript_errors'] and not proof['unexpected_requests']
                    check('readable-scale-and-no-horizontal-panel-overflow',layout=layout)
                finally:context.close()
            browser.close();browser=None
        assert all(sha(STAGE/n)==s for n,s in prepared['files_sha256'].items())
        assert all(sha(ROOT/n)==s for n,s in sources.items())
        proof.update(accepted=True,completed=True)
    except Exception:proof['failure']=traceback.format_exc()
    finally:
        if browser:
            try:browser.close()
            except Exception:pass
        if server and server.poll() is None:
            try:call('/api/shutdown',{});proof['server_exit']=server.wait(timeout=20)
            except Exception:server.terminate();proof['server_exit']=server.wait(timeout=10)
        if proof.get('server_exit')!=0:proof.update(accepted=False,completed=False)
        persist()
    print(json.dumps({k:proof.get(k) for k in ['accepted','completed','checks','step','failure','server_exit','javascript_errors']},ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
