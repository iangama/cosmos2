"""Exercise geodesic/clock controls through the actual HTTP scientific UI."""
from pathlib import Path
import argparse
import json
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=4701)
args = parser.parse_args()
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', headless=True)
    page = browser.new_page(viewport={'width':1600, 'height':1080})
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(f'http://127.0.0.1:{args.port}/forces.html')
    page.wait_for_function("document.getElementById('force-status').textContent.startsWith('Cálculo concluído')")
    page.locator('[data-scenario="relativity"]').click()
    page.wait_for_function('!pending')
    assert page.evaluate('response.result.ray.status') == 'escaped'
    baseline = page.evaluate('response.result')
    for bending in (False, True):
        page.locator('[data-effect="ray_bending"]').set_checked(bending)
        page.wait_for_function('!pending')
        assert page.evaluate('response.result.ray.curvature_term_applied') == bending
        assert page.evaluate('response.result.reference') == baseline['reference']
    page.locator('[data-effect="static_clock_rate"]').set_checked(False)
    page.wait_for_function('!pending')
    assert page.evaluate('response.result.measurements[1].value') == 1
    assert page.evaluate('response.result.ray.curvature_term_applied') is True
    page.locator('[data-effect="static_clock_rate"]').set_checked(True)
    page.wait_for_function('!pending')
    physical = page.evaluate('response.result')
    page.locator('[data-force="gravity"][data-control="visible"]').set_checked(False)
    page.wait_for_function('!pending')
    assert page.evaluate('response.result') == physical
    assert page.evaluate('projectedArrows.length') == 0
    page.locator('[data-force="gravity"][data-control="visible"]').set_checked(True)
    page.wait_for_function('!pending')
    box = page.locator('#science-view').bounding_box()
    probe = page.evaluate('projectedArrows.find(p => p.x>30 && p.x<canvas.clientWidth-30 && p.y>30 && p.y<canvas.clientHeight-30)')
    page.mouse.click(box['x']+probe['x'], box['y']+probe['y'])
    assert 'Kretschmann' in page.locator('#probe').inner_text()
    assert 'λ =' in page.locator('#time-label').inner_text()
    fingerprint = page.evaluate('response.configuration_sha256')
    page.locator('#framing').select_option('whole')
    assert page.evaluate('response.configuration_sha256') == fingerprint
    page.locator('#framing').select_option('focus')
    page.screenshot(path=str(ROOT/'evidence/forces-ui-relativity.png'), full_page=True)
    page.locator('[name="impact_rs"]').fill('2')
    page.locator('#calculate').click()
    page.wait_for_function('!pending')
    assert page.evaluate('response.result.ray.status') == 'captured'
    assert page.evaluate('response.result.measurements[3].value') is None
    assert 'Não se aplica' in page.locator('#measurements').inner_text()
    page.screenshot(path=str(ROOT/'evidence/forces-ui-ray-capture.png'), full_page=True)
    page.locator('[data-force="gravity"][data-control="acting"]').set_checked(False)
    page.wait_for_function('!pending')
    assert page.evaluate('response.result.ray.status') == 'straight_counterfactual'
    assert page.evaluate('response.result.reference.status') == 'captured'
    assert page.evaluate('projectedArrows.length') == 72
    page.screenshot(path=str(ROOT/'evidence/forces-ui-curvature-off.png'), full_page=True)
    page.set_viewport_size({'width':720, 'height':900})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors, errors
    browser.close()
report = {'browser':'native Windows Edge headless', 'ray_bending_independent_of_clock':True,
          'metric_preserved_when_action_off':True, 'capture_and_escape':True,
          'affine_parameter_labelled':True, 'metric_probe':True, 'framing_only_changes_view':True,
          'narrow_no_horizontal_overflow':True, 'page_errors':errors,
          'scope':'UI/HTTP; native OpenSpace CEF is checked separately'}
(ROOT/'evidence/relativity-ui-check.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
