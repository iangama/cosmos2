"""Capture I's five actual layered experiences at both interface scales.

Read-only to product sources and saved phase/preferences; screenshots require
human/model inspection separately from the functional assertions here.
"""
from pathlib import Path
import hashlib
import json
import subprocess
from cef_page import Page

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / 'output/c212-em-framing-product'
DEST = ROOT / 'evidence/em-framing-five-scenes-check.json'
assert not DEST.exists()
session = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
assert session['emFramingCandidate']
owner = (ROOT / 'user/sessions/latest.json').read_bytes()
saved = {str(p): p.read_bytes() for p in (PRODUCT / 'c212-em-worker/product').glob('ui-phase*') if p.is_file()}
report = {'completed': False, 'checks': [], 'screenshots_sha256': {}, 'JS_errors': []}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
            for scale in ('1', '1.5'):
                page.locator('#interface-scale').select_option(scale)
                panel(page, 'layers')
                page.evaluate('document.querySelectorAll("aside").forEach(a=>a.scrollTop=0)')
                for mode in ('native', 'canvas'):
                    if page.evaluate('nativeMode') != (mode == 'native'):
                        click(page, 'native-toggle')
                    click(page, 'frame-layers')
                    if mode == 'canvas':
                        click(page, 'orient-cut')
                    metrics = page.evaluate('(()=>{const z=Number(getComputedStyle(document.body).zoom)||1;const rect=id=>{const r=$(id).getBoundingClientRect();return {left:r.left*z,top:r.top*z,right:r.right*z,bottom:r.bottom*z,width:r.width*z,height:r.height*z};};return {width:innerWidth,height:innerHeight,pause:rect("play"),viewport:rect("view"),overflow:document.documentElement.scrollWidth>innerWidth+1,trail:trail.length,lines:fieldLines.curves.length,potential_segments:potentialLayer.geometry.segments.length,scale:z,projection:canvasProjectionState};})()')
                    assert not metrics['overflow'] and metrics['pause']['top'] >= 0 and metrics['pause']['bottom'] <= metrics['height'], metrics
                    assert metrics['trail'] >= 65 and metrics['lines']
                    if preset in ('electric', 'crossed', 'coulomb'):
                        assert metrics['potential_segments']
                    assert page.evaluate('JSON.stringify(state.experiment)') == phase
                    assert page.evaluate('particleMeasurement.time_s') == reading['time_s']
                    name = f'cosmos2-i-final-{preset}-{mode}-{100 if scale == "1" else 150}.png'
                    capture(name)
                    report['checks'].append({'preset': preset, 'mode': mode, 'interface_scale': float(scale), 'time_s': reading['time_s'], 'layout': metrics, 'screenshot': name})
                    print(json.dumps({'captured': name}), flush=True)
        page.locator('#interface-scale').select_option('1')
        page.evaluate('command("load",{...guard(),file:"ui-phase"})')
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
