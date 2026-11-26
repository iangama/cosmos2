"""Check the app's existing CEF via loopback CDP, never launch another browser."""
from pathlib import Path
import importlib.util
import json
import subprocess
import time
from cef_page import Page
Error = RuntimeError

ROOT = Path(__file__).resolve().parents[1]
session = json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
if not session.get('offline'):
    raise RuntimeError('Este ensaio exige a sessão -Built -Offline -InspectCEF.')
spec = importlib.util.spec_from_file_location('engine_command', ROOT/'scripts/engine-command.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
errors = []
report = {'session':session, 'browser':'Existing native OpenSpace CEF; no Edge/headless process',
          'runtime_receipt':json.loads((ROOT/'evidence/built-runtime.json').read_text())}

def capture(name):
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                    str(ROOT/'scripts/capture-window.ps1'),'-Name',name], check=True, capture_output=True)

with Page() as page:
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:4700/forces.html')
    page.wait_for_function("document.getElementById('force-status').textContent.startsWith('Cálculo concluído')")
    baseline = page.evaluate('response.result')
    page.locator('[data-force="gravity"][data-control="acting"]').set_checked(False)
    page.wait_for_function('!pending')
    assert page.evaluate('response.result.measurements[1].value') == 0
    assert page.evaluate('response.result.reference') == baseline['reference']
    assert page.evaluate('projectedArrows.length') == 144
    capture('cosmos2-native-gravity-off.png')
    page.locator('[data-force="gravity"][data-control="acting"]').set_checked(True)
    page.wait_for_function('!pending')
    page.locator('[data-scenario="strong"]').click(); page.wait_for_function('!pending')
    assert page.locator('#channel-readings table').count() == 1
    page.locator('[data-effect="dt_fusion"]').set_checked(False); page.wait_for_function('!pending')
    assert page.evaluate('response.result.curves[0].values.every(value => value===1)')
    page.locator('[data-effect="dt_fusion"]').set_checked(True); page.wait_for_function('!pending')
    page.locator('[data-scenario="weak"]').click(); page.wait_for_function('!pending')
    page.locator('[name="species"]').select_option('be7');page.locator('#calculate').click();page.wait_for_function('!pending')
    assert page.evaluate('response.result.reference.products') == ['li7','nu_e']
    page.locator('[data-scenario="stellar"]').click();page.wait_for_function('!pending')
    page.locator('[data-effect="pp_fusion"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.result.network.neutrino_count_m3[240]') == 0
    page.locator('[data-effect="pp_fusion"]').set_checked(True);page.wait_for_function('!pending')
    page.locator('[data-scenario="relativity"]').click();page.wait_for_function('!pending')
    assert page.evaluate('response.result.ray.status') == 'escaped'
    page.locator('[data-effect="ray_bending"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.result.ray.status') == 'straight_counterfactual'
    assert page.evaluate('projectedArrows.length') == 72
    capture('cosmos2-native-curvature-off.png')
    page.locator('[data-effect="ray_bending"]').set_checked(True);page.wait_for_function('!pending')
    capture('cosmos2-native-relativity.png')
    report['native_controls'] = {'gravity_off_field_on':True,'strong_channel_off':True,
                                 'electron_capture':True,'stellar_weak_channel_off':True,
                                 'curvature_off_metric_on':True,'ray_escape':True}
    assert not errors, errors
    # A genuine renderer navigation exercises CEF's proxy, rather than a
    # request from the Python automation client.
    try:
        page.goto('https://cosmos2-offline-probe.invalid/', timeout=10000)
    except Error as error:
        report['cef_external_request_error'] = str(error).splitlines()[0]
        assert 'ERR_PROXY_CONNECTION_FAILED' in str(error), str(error)
    else:
        raise AssertionError('CEF reached an external URL in the offline profile.')
    finally:
        page.goto('http://127.0.0.1:4700/')
    assert page.locator('.brand').count() > 0
    report['loopback_ui_after_denial'] = True
    # Probe the engine download path too. The tiny test node is always removed;
    # it contributes no celestial data and never changes user checkpoints.
    try:
        engine.execute('openspace.addSceneGraphNode({Identifier="Cosmos2OfflineProbe",Renderable={Type="RenderableSphereImageOnline",Size=1,Segments=8,URL="https://cosmos2-offline-probe.invalid/probe.png"}})')
        deadline = time.monotonic()+5
        while time.monotonic() < deadline:
            raw = (ROOT/'output/engine.log').read_bytes()
            log = raw.decode('utf-8',errors='replace').replace('\x00','')
            if "Cosmos2 offline blocked external URL 'https://cosmos2-offline-probe.invalid/probe.png'" in log:
                report['engine_external_request_denied_before_connection'] = True
                break
            time.sleep(.1)
        else:
            raise AssertionError('Não encontrou confirmação de bloqueio HTTP do motor.')
    finally:
        engine.execute('openspace.removeSceneGraphNode("Cosmos2OfflineProbe")')
    # The CDP connection ends with Playwright; do not close the user's CEF.
report['page_errors'] = errors
report['scope'] = 'Native prototype UI and engine/CEF external HTTP denial; not full scientific acceptance'
(ROOT/'evidence/native-cef-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({key:value for key,value in report.items() if key != 'runtime_receipt'}, indent=2))
