"""H real small-lab five-experience native/canvas layer and reading captures."""
from pathlib import Path
import hashlib
import json
import subprocess
from cef_page import Page
ROOT=Path(__file__).resolve().parents[1];H=ROOT/'output/c212-em-cloud-editor-product'
dest=ROOT/'evidence/em-cloud-editor-five-experiences-check.json';assert not dest.exists()
owner=(ROOT/'user/sessions/latest.json').read_bytes();errors=[];checks=[];screens={}
session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'));assert session['emCloudEditorCandidate']
def idle(p):p.wait_for_function('state&&state.paused&&!pending&&!nativeState.error&&nativeState.confirmation?.metadata.time_s===state.time_s',timeout=30000)
def panel(p,name):
    if p.evaluate('workspacePanel')!=name:p.locator('[data-panel="'+name+'"]').click()
def click(p,name,which=None):
    if which:panel(p,which)
    p.locator('#'+name).click();idle(p)
def capture(name):
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',name],check=True,capture_output=True)
    screens[name]=hashlib.sha256((ROOT/'evidence'/name).read_bytes()).hexdigest()
with Page() as p:
    p.on('pageerror',lambda e:errors.append(e));p.goto('http://127.0.0.1:4700/')
    p.wait_for_function('typeof appState!=="undefined"&&appState');p.locator('#em-lab').click();idle(p)
    p.locator('#interface-scale').select_option('1')
    for preset in ('electric','helix','crossed','dipole','coulomb'):
        panel(p,'experience');p.locator('#preset').select_option(preset);click(p,'load-preset')
        p.evaluate('(async()=>{for(let n=0;n<16;n++)await command("advance",{...guard(),steps:32});return true;})()');idle(p)
        click(p,'measure','layers');click(p,'trace-fields');click(p,'measure-potential')
        click(p,'measure-particle','readings')
        reading=p.evaluate('JSON.parse(JSON.stringify(particleMeasurement))')
        assert reading['time_s']==p.evaluate('state.time_s')
        assert reading['source_snapshot']==p.evaluate('state.experiment')
        if not p.evaluate('nativeMode'):click(p,'native-toggle')
        click(p,'native-frame');panel(p,'layers')
        p.evaluate('document.querySelectorAll("aside").forEach(a=>a.scrollTop=0)')
        capture('cosmos2-h-'+preset+'-native.png')
        before=p.evaluate('JSON.stringify(state.experiment)');click(p,'native-toggle')
        assert '10⁹' not in p.locator('.native-scale').inner_text()
        assert 'projeção 3D' in p.locator('.native-scale').inner_text()
        box=p.evaluate('(()=>{const r=$("view").getBoundingClientRect();return {x:r.x+r.width*.65,y:r.y+r.height*.55};})()')
        p.call('Input.dispatchMouseEvent',{'type':'mousePressed',**box,'button':'left','buttons':1,'clickCount':1})
        p.call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':box['x']+100,'y':box['y']-60,'button':'left','buttons':1})
        p.call('Input.dispatchMouseEvent',{'type':'mouseReleased','x':box['x']+100,'y':box['y']-60,'button':'left','clickCount':1})
        assert p.evaluate('JSON.stringify(state.experiment)')==before
        capture('cosmos2-h-'+preset+'-canvas.png')
        checks.append({'preset':preset,'time_s':reading['time_s'],'reading_force_N':reading['force']['force_N'],
                       'view_switch_and_drag_preserve_phase':True,'native_scale_only_in_native_legend':True,
                       'field_map_samples':p.evaluate('map.samples.length'),'field_lines':p.evaluate('fieldLines!==null'),
                       'scope':'Actual calculated layers and reading at declared phase; images still require visual assessment.'})
    p.locator('#native-return').click();p.wait_for_function('location.pathname==="/"')
assert not errors and owner==(ROOT/'user/sessions/latest.json').read_bytes()
report={'status':'H_five_experience_layer_canvas_journey_executed','checks':checks,'JS_errors':errors,
        'screenshots_sha256':screens,'owner_pointer_preserved':True,
        'source_sha256':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [Path(__file__),*sorted((H/'app').rglob('*'))] if f.is_file() and '__pycache__' not in f.parts},
        'scope':'Five presets evolved512steps with maps/lines/potential/readings and real native/canvas input. Images require review; not independent trajectory convergence or formal H performance acceptance.'}
dest.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'screenshots':len(screens),'JS_errors':errors}),flush=True)
