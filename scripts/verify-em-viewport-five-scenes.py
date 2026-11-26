"""Capture J's five actual layered experiences at both interface scales.

Read-only to product sources and saved phase/preferences; screenshots require
human/model inspection separately from the functional assertions here.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
from cef_page import Page
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / 'output/c212-em-viewport-product'
parser=argparse.ArgumentParser()
parser.add_argument('--label',default='release1')
args=parser.parse_args()
assert args.label.isalnum()
DEST = ROOT / f'evidence/em-viewport-five-scenes-{args.label}-check.json'
assert not DEST.exists()
session = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
assert session['emViewportCandidate']
owner = (ROOT / 'user/sessions/latest.json').read_bytes()
saved = {str(p): p.read_bytes() for p in (PRODUCT / 'c212-em-worker/product').glob('ui-phase*') if p.is_file()}
report = {'completed': False, 'checks': [], 'screenshots_sha256': {}, 'JS_errors': []}
reference = {r['preset']: r for r in json.loads((ROOT / 'evidence/em-cloud-editor-five-experiences-check.json').read_bytes())['checks']}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_pose():
    with connect('ws://127.0.0.1:4682',open_timeout=3,close_timeout=.2,ping_interval=None) as ws:
        ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
        ws.send(json.dumps({'topic':1,'type':'luascript','payload':{'return':True,'script':'return {nav=openspace.navigation.getNavigationState("C2EMRoot"),focus=openspace.propertyValue("Scene.C2EMCamera.Translation.Position")}'}}))
        result=json.loads(ws.recv(timeout=5))['payload']['1']
    def normalize(value):
        if isinstance(value,dict):
            if value and set(value)=={str(i) for i in range(1,len(value)+1)}:
                return [normalize(value[str(i)]) for i in range(1,len(value)+1)]
            return {k:normalize(v) for k,v in value.items()}
        return value
    return normalize(result)


def idle(page):
    page.wait_for_function('state&&state.paused&&!pending&&!nativeState.error&&nativeState.confirmation?.metadata.time_s===state.time_s', timeout=30000)


def panel(page, name):
    if page.evaluate('workspacePanel') != name:
        page.locator('[data-panel="' + name + '"]').click()


def click(page, name, tool=None):
    if tool:
        panel(page, tool)
    page.locator('#' + name).click()
    idle(page)


def capture(name):
    path = ROOT / 'evidence' / name
    assert not path.exists()
    subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT / 'scripts/capture-window.ps1'), '-Name', name], check=True, capture_output=True)
    report['screenshots_sha256'][name] = digest(path)


try:
    with Page() as page:
        page.on('pageerror', lambda error: report['JS_errors'].append(error))
        page.goto('http://127.0.0.1:4700/')
        page.wait_for_function('typeof appState!=="undefined"&&appState')
        page.locator('#em-lab').click()
        idle(page)
        page.evaluate('command("save",{...guard(),file:"visual-before"})')
        for preset in ('electric', 'helix', 'crossed', 'dipole', 'coulomb'):
            page.locator('#interface-scale').select_option('1')
            panel(page, 'experience')
            page.locator('#preset').select_option(preset)
            click(page, 'load-preset')
            page.evaluate('(async()=>{for(let i=0;i<64;i++)await command("advance",{...guard(),steps:8});return true;})()')
            idle(page)
            click(page, 'measure', 'layers')
            click(page, 'trace-fields')
            click(page, 'measure-potential')
            click(page, 'measure-particle', 'readings')
            phase = page.evaluate('JSON.stringify(state.experiment)')
            reading = page.evaluate('JSON.parse(JSON.stringify(particleMeasurement))')
            assert reading['time_s'] == reference[preset]['time_s']
            assert reading['force']['force_N'] == reference[preset]['reading_force_N']
            for scale in ('1', '1.5'):
                page.locator('#interface-scale').select_option(scale)
                panel(page, 'layers')
                page.evaluate('document.querySelectorAll("aside").forEach(a=>a.scrollTop=0)')
                for mode in ('native', 'canvas'):
                    if page.evaluate('nativeMode') != (mode == 'native'):
                        click(page, 'native-toggle')
                    click(page, 'frame-layers')
                    if mode == 'native':
                        view=page.evaluate('nativeRequest("frame",{include_layers:true,viewport:availableNativeViewport()})')["view"]
                        fit_result=view["viewport_fit"]
                        assert fit_result and fit_result["algorithm"]=="available_rectangle_perspective_0.1.1"
                        bounds=fit_result["projected_bounds"];left,top,width,height=fit_result["viewport"]["rect_px"]
                        assert bounds["minimum_px"][0]>=left and bounds["maximum_px"][0]<=left+width
                        assert bounds["minimum_px"][1]>=top and bounds["maximum_px"][1]<=top+height
                        pose=native_pose()
                        assert pose['nav']['Anchor']=='C2EMCamera'
                        assert abs(pose['nav'].get('Yaw',0)-fit_result['yaw_rad'])<1e-10
                        assert abs(pose['nav'].get('Pitch',0)-fit_result['pitch_rad'])<1e-10
                        assert max(abs(a-b) for a,b in zip(pose['nav']['Position'],view['navigation']['Position']))<1
                        assert max(abs(a-b*1e9) for a,b in zip(pose['focus'],view['center_model_m']))<1
                    if mode == 'canvas':
                        click(page, 'orient-cut')
                    metrics = page.evaluate('(()=>{const z=Number(getComputedStyle(document.body).zoom)||1;const rect=id=>{const r=$(id).getBoundingClientRect();return {left:r.left*z,top:r.top*z,right:r.right*z,bottom:r.bottom*z,width:r.width*z,height:r.height*z};};return {width:innerWidth,height:innerHeight,scroll_y:scrollY,header:rect("interface-scale"),pause:rect("play"),viewport:rect("view"),overflow:document.documentElement.scrollWidth>innerWidth+1,trail:trail.length,lines:fieldLines.curves.length,potential_segments:potentialLayer.geometry.segments.length,scale:z,projection:canvasProjectionState};})()')
                    assert not metrics['overflow'] and metrics['pause']['top'] >= 0 and metrics['pause']['bottom'] <= metrics['height'], metrics
                    assert metrics['scroll_y']==0 and metrics['header']['top']>=0,metrics
                    assert metrics['viewport']['height']>=300,metrics
                    assert metrics['trail'] >= 65 and metrics['lines']
                    if preset in ('electric', 'crossed', 'coulomb'):
                        assert metrics['potential_segments']
                    assert page.evaluate('JSON.stringify(state.experiment)') == phase
                    assert page.evaluate('particleMeasurement.time_s') == reading['time_s']
                    name = f'cosmos2-j-{args.label}-{preset}-{mode}-{100 if scale == "1" else 150}.png'
                    capture(name)
                    report['checks'].append({'preset': preset, 'mode': mode, 'interface_scale': float(scale), 'time_s': reading['time_s'], 'layout': metrics, 'screenshot': name,'native_fit':fit_result if mode=='native' else None,'confirmed_engine_pose':pose if mode=='native' else None})
                    print(json.dumps({'captured': name}), flush=True)
        page.locator('#interface-scale').select_option('1')
        page.evaluate('command("load",{...guard(),file:"visual-before"})')
        idle(page)
        page.locator('#native-return').click()
        page.wait_for_function('location.pathname==="/"')
        assert not report['JS_errors']
        assert owner == (ROOT / 'user/sessions/latest.json').read_bytes()
        assert all(Path(path).read_bytes() == data for path, data in saved.items())
        report.update(completed=True, owner_and_saved_phase_preferences_preserved=True,
                      scope='Twenty real native/canvas captures with computed E/B lines, arrows and electric potential;65 observed trajectory positions; five experiences at100/150%. Functional layout checks only; separate visual review required. No wholeC2-12 or installation approval.')
finally:
    report['source_sha256'] = {str(p.relative_to(ROOT)): digest(p) for p in [Path(__file__), *sorted((PRODUCT / 'app').rglob('*'))] if p.is_file() and '__pycache__' not in p.parts}
    DEST.write_text(json.dumps(report, indent=2) + '\n')
