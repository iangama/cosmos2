"""I real five-experience framing, guarded canvas view3 and legacy2 journey."""
from pathlib import Path
from copy import deepcopy
import argparse
import hashlib
import json
import math
import shutil
import subprocess
from cef_page import Page
ROOT=Path(__file__).resolve().parents[1];I=ROOT/'output/c212-em-framing-product'
parser=argparse.ArgumentParser();parser.add_argument('--label',default='initial');args=parser.parse_args();assert args.label.isalnum()
dest=ROOT/f'evidence/em-framing-ui-{args.label}-check.json';assert not dest.exists()
session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'));assert session['emFramingCandidate']
owner=(ROOT/'user/sessions/latest.json').read_bytes();report={'completed':False,'checks':[],'JS_errors':[],'screenshots_sha256':{}}
reference=json.loads((ROOT/'evidence/em-cloud-editor-five-experiences-check.json').read_bytes())['checks']
storage=I/'c212-em-worker/product'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def idle(p):p.wait_for_function('state&&state.paused&&!pending&&!nativeState.error&&nativeState.confirmation?.metadata.time_s===state.time_s',timeout=30000)
def panel(p,name):
    if p.evaluate('workspacePanel')!=name:p.locator('[data-panel="'+name+'"]').click()
def click(p,name,which=None):
    if which:panel(p,which)
    p.locator('#'+name).click();idle(p)
def snap(p):return p.evaluate('JSON.parse(JSON.stringify(state))')
def cmd(p,name,values={}):return p.evaluate('command('+json.dumps(name)+',{...guard(),...'+json.dumps(values)+'})')
def frames(p):return sum(e.get('method')=='Network.requestWillBeSent' and e['params']['request']['url'].endswith('/api/em/frame') for e in p.events)
def capture(name):
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',name],check=True,capture_output=True)
    report['screenshots_sha256'][name]=sha(ROOT/'evidence'/name)
try:
    with Page() as p:
        p.on('pageerror',lambda e:report['JS_errors'].append(e));p.goto('http://127.0.0.1:4700/')
        p.wait_for_function('typeof appState!=="undefined"&&appState');p.locator('#em-lab').click();idle(p)
        p.locator('#interface-scale').select_option('1')
        for old in reference:
            preset=old['preset'];panel(p,'experience');p.locator('#preset').select_option(preset);click(p,'load-preset')
            p.evaluate('(async()=>{for(let i=0;i<16;i++)await command("advance",{...guard(),steps:32});return true;})()');idle(p)
            click(p,'measure','layers');click(p,'trace-fields');click(p,'measure-potential');click(p,'measure-particle','readings')
            reading=p.evaluate('particleMeasurement');assert reading['time_s']==old['time_s'] and reading['force']['force_N']==old['reading_force_N']
            assert reading['source_snapshot']==snap(p)['experiment']
            if not p.evaluate('nativeMode'):click(p,'native-toggle')
            before=snap(p);click(p,'frame-layers');assert snap(p)['experiment']==before['experiment']
            view=p.evaluate('nativeRequest("frame",{include_layers:true})')['view']
            assert view['framing_scope']=='visible_layers' and view['radius_model_m']>0
            # Native bounds are derived from actual SI meshes, not visual axes.
            corners=p.evaluate('(()=>{let points=[];for(const layer of [nativeState.map,nativeState.lines])for(const m of layer?.meshes||[]){if(!state.editor.visual[m.quantity+"_visible"])continue;const b=m.bounds_model_m;for(const x of [b.minimum_m[0],b.maximum_m[0]])for(const y of [b.minimum_m[1],b.maximum_m[1]])for(const z of [b.minimum_m[2],b.maximum_m[2]])points.push([x,y,z]);}return points;})()')
            assert all(math.dist(q,view['center_model_m'])<=view['radius_model_m']*(1+1e-14) for q in corners)
            panel(p,'layers');p.evaluate('document.querySelectorAll("aside").forEach(a=>a.scrollTop=0)')
            capture(f'cosmos2-i-{args.label}-{preset}-native.png')
            click(p,'native-toggle');assert '10⁹' not in p.locator('.native-scale').inner_text()
            count=frames(p);click(p,'native-frame');assert frames(p)==count
            assert p.evaluate('nativeState.canvas_view')=={'scope':'matter','zoom':1}
            p.locator('#canvas-zoom').select_option('2');idle(p);assert p.evaluate('nativeState.canvas_view.zoom')==2
            click(p,'frame-layers');assert frames(p)==count
            assert p.evaluate('nativeState.canvas_view')=={'scope':'layers','zoom':1}
            click(p,'orient-cut');after=snap(p);assert after['experiment']==before['experiment'] and after['revision']==before['revision']
            metrics=p.evaluate('JSON.parse(JSON.stringify(canvasProjectionState))');fractions=[s*metrics['scale_px_per_m']/d for s,d in zip(metrics['projected_extent_m'],(metrics['width'],metrics['height']))]
            assert max(fractions)<=.841 and max(fractions)>=.80,(preset,metrics,fractions)
            capture(f'cosmos2-i-{args.label}-{preset}-canvas.png')
            report['checks'].append({'preset':preset,'time_s':after['time_s'],'phase_and_force_equal_H':True,'native_frame_bounds_contain_all_meshes':True,'canvas_frame_uses_no_native_camera_request':True,'canvas_visible_data_fraction':max(fractions)})
        # Save/restore new preferences, with an actual phase intervention between.
        p.locator('#canvas-zoom').select_option('2');idle(p)
        click(p,'save','experience');saved=snap(p)
        view=json.loads((storage/'ui-phase.view.json').read_bytes())['payload']['view'];assert view['schema']==3 and view['canvas_view']=={'scope':'layers','zoom':2}
        click(p,'one-step');click(p,'native-frame');click(p,'restore','experience')
        assert snap(p)['experiment']==saved['experiment'] and p.evaluate('nativeState.canvas_view')==view['canvas_view']
        # Real G view2 remains byte-identical while explicit new defaults apply.
        base=ROOT/'output/c212-em-integration-product/c212-em-worker/product'
        for suffix in ('.json','.view.json','.timing.json'):shutil.copyfile(base/('ui-phase'+suffix),storage/('legacy-g'+suffix))
        legacy_hash=sha(storage/'legacy-g.view.json');result=cmd(p,'load',{'file':'legacy-g'});idle(p)
        assert result['native_view_source_schema']==2 and p.evaluate('nativeState.canvas_view')=={'scope':'layers','zoom':1}
        assert 'mapa com enquadramento' in p.locator('#status').inner_text() and sha(storage/'legacy-g.view.json')==legacy_hash
        cmd(p,'load',{'file':'ui-phase'});idle(p)
        # Correctly sealed invalid view3 must be refused before changing phase.
        base_view=json.loads((storage/'ui-phase.view.json').read_bytes());refusals=[]
        for suffix in ('.json','.timing.json'):shutil.copyfile(storage/('ui-phase'+suffix),storage/('invalid-map'+suffix))
        for changes in ({'scope':'missing'},{'zoom':True},{'zoom':8},{'extra':1}):
            env=deepcopy(base_view);env['payload']['view']['canvas_view'].update(changes);env['sha256']=hashlib.sha256(json.dumps(env['payload'],sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()
            (storage/'invalid-map.view.json').write_text(json.dumps(env)+'\n');before=snap(p)
            r=p.evaluate('(async()=>{const r=await fetch("/api/em/command",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({command:"load",file:"invalid-map",...guard()})});return {status:r.status,body:await r.json()};})()')
            assert r['status']==400;r=p.evaluate('refresh(true)');assert snap(p)['experiment']==before['experiment'];refusals.append(changes)
        report['refusals']=refusals
        before=snap(p);canvas_before=p.evaluate('nativeState.canvas_view')
        for values in ({'revision':before['revision']+1,'changes':{'zoom':1}}, {'expected_time_s':before['time_s']+1,'changes':{'zoom':1}}, {'changes':{'zoom':True}}, {'changes':{'extra':1}}):
            r=p.evaluate('(async()=>{const r=await fetch("/api/em/command",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({command:"configure_canvas_view",...guard(),...'+json.dumps(values)+'})});return {status:r.status,body:await r.json()};})()')
            assert r['status']==400;p.evaluate('refresh(true)');assert snap(p)['experiment']==before['experiment'] and p.evaluate('nativeState.canvas_view')==canvas_before
        click(p,'one-step');view_path=storage/'ui-phase.view.json';backup=storage/'io-view-backup.json';assert not backup.exists();view_path.rename(backup);view_path.mkdir()
        try:
            click(p,'save','experience');message=p.locator('#status').inner_text()
            assert 'Fase salva; preferências de vista/tempo incompletas' in message and p.evaluate('nativeState.error') is None,message
            assert json.loads((storage/'ui-phase.json').read_bytes())['payload']['phase']['time_s']==snap(p)['time_s']
            report['small_view3_real_IO_partial_save']=message
        finally:view_path.rmdir();backup.rename(view_path)
        click(p,'save','experience')

        # All controls and the fixed pause stay usable at150%.
        p.locator('#interface-scale').select_option('1.5');panel(p,'layers');click(p,'native-toggle')
        layout=p.evaluate('(()=>{const z=Number(getComputedStyle(document.body).zoom)||1,b=$("play").getBoundingClientRect(),a=document.querySelector("article").getBoundingClientRect();return {scene_fraction:a.width*z/innerWidth,pause_visible:b.top*z>=0&&b.bottom*z<=innerHeight,overflow:document.documentElement.scrollWidth>innerWidth+1};})()')
        assert layout['scene_fraction']>=.65 and layout['pause_visible'] and not layout['overflow'];report['layout150']=layout
        capture(f'cosmos2-i-{args.label}-coulomb-zoom150.png');p.locator('#interface-scale').select_option('1')
        cmd(p,'load',{'file':'ui-phase'});idle(p);click(p,'save','experience')
        expected={'state':snap(p),'canvas_view':p.evaluate('nativeState.canvas_view'),'files_sha256':{suffix:sha(storage/('ui-phase'+suffix)) for suffix in ('.json','.view.json','.timing.json')}}
        (ROOT/'output/em-framing-restart-expected.json').write_text(json.dumps(expected,indent=2)+'\n')
        p.locator('#native-return').click();p.wait_for_function('location.pathname==="/"')
        assert not report['JS_errors'] and owner==(ROOT/'user/sessions/latest.json').read_bytes()
        report.update(completed=True,owner_pointer_preserved=True,scope='I real native/canvas framing, five layers/readings, view3 saved preferences, genuine legacy2 and resealed refusal. Screenshots require inspection; fresh restart and own formal profiles pending.')
finally:
    report['source_sha256']={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),*sorted((I/'app').rglob('*'))] if p.is_file() and '__pycache__' not in p.parts}
    dest.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'completed':report['completed'],'presets':len(report['checks']),'JS_errors':report['JS_errors'],'screenshots':len(report['screenshots_sha256'])}),flush=True)
