"""Compare CEF surface, engine framebuffer and PrintWindow on the same frozen view."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import base64
import hashlib
import json
import shutil
import subprocess
import time
import traceback
import urllib.request
from cef_page_v2 import Page

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
h = SourceFileLoader('caption_diagnostic_helpers', str(ROOT / 'scripts/benchmark-body-points-native.py')).load_module()
out = ROOT / 'evidence/is6-import-caption-diagnostic-20261104v.json'
if out.exists():
    raise FileExistsError('Preserve diagnostic')
host = ROOT / 'output/is6-layers-import-host-k5-capture-u-20261104.log'
deadline = time.monotonic() + 180
while True:
    lines = host.read_text().splitlines() if host.exists() else []
    entries = [json.loads(line) for line in lines if line.startswith('{')]
    initial = next((row for row in entries if 'bootstrap_exit' in row), None)
    if initial:
        assert initial['bootstrap_exit'] == 0
        break
    if time.monotonic() > deadline:
        raise TimeoutError('Diagnostic bootstrap')
    time.sleep(1)
launch = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
assert launch['app'] == initial['app'] and '0.21.1' in launch['serverScript']
seed = json.loads((ROOT / 'evidence/is6-layers-import-native-20261104s.json').read_text())
store = ROOT / 'output/is6-layers-product0.21.1/layer-checkpoints'
before = {p.relative_to(store).as_posix(): sha(p) for p in store.rglob('*.json')}
record = dict(accepted=False, completed=False, session=launch, captures=[],
              owner_sha256=sha(ROOT / 'user/sessions/latest.json'), persisted_before=before,
              source_sha256={Path(__file__).relative_to(ROOT).as_posix(): sha(Path(__file__))},
              method_sources=['https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-captureScreenshot',
                              'https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-printwindow'],
              scope='Capture-method diagnostic only; no visual or product acceptance.')
def state():
    return h.get('/api/layers/state')
def command(name, **fields):
    return h.post('/api/layers/command', dict(command=name, guard=state()['guard'], **fields))
def click(page, selector):
    page.evaluate('(()=>{let e=document.querySelector(' + json.dumps(selector) + ');for(let p=e.parentElement;p;p=p.parentElement)if(p.tagName==="DETAILS")p.open=true})()')
    page.wait_for_function('!layerInstrument.pending&&!layerInstrument.readingFile&&!layerInstrument.snapshot.busy&&!document.querySelector(' + json.dumps(selector) + ').disabled', timeout=80000)
    page.locator(selector).click()
    page.wait_for_function('!layerInstrument.pending&&!layerInstrument.readingFile&&!layerInstrument.snapshot.busy', timeout=80000)
try:
    until=time.monotonic()+180
    while True:
        try:
            urllib.request.urlopen(h.test.BASE+'/health',timeout=3).close();break
        except OSError:
            if time.monotonic()>until:raise TimeoutError('API readiness')
            time.sleep(1)
    with Page() as page:
        page.goto(h.test.BASE + '/')
        page.wait_for_function('appState&&atlasState&&layerInstrument.snapshot&&!pending')
        click(page, '#open-layers')
        click(page, '#layers-copy')
        page.wait_for_function('appState.physics?.bodies.length===4&&!pending', timeout=70000)
        phase = h.test.phase(h.get('/api/state')['physics'])
        click(page, '#layers-load-saved')
        page.locator('#layers-branches').select_option(seed['imports']['399']['branch_id'])
        click(page, '#layers-branch-load')
        assert state()['artifact']['sha256'] == seed['saved']['399']['digest']
        assert state()['artifact']['visible'] == dict(spatial=False, magnetic=True)
        original = ROOT / 'output/is6-layers-migration-20261104h/legacy-399-01.json'
        root = page.call('DOM.getDocument')['root']['nodeId']
        node = page.call('DOM.querySelector', dict(nodeId=root, selector='#layers-import-file'))['nodeId']
        page.call('DOM.setFileInputFiles', dict(nodeId=node, files=[str(original)]))
        page.evaluate('document.getElementById("layers-import-file").dispatchEvent(new Event("change",{bubbles:true}))')
        click(page, '#layers-import-preview')
        page.locator('#ui-scale').select_option('1.5')
        page.evaluate('document.getElementById("layers-import").open=true;document.getElementById("layers-import-fields").scrollIntoView({block:"start"})')
        time.sleep(2)
        record['layers'] = state()
        record['ui'] = page.evaluate('({caption:document.getElementById("layers-caption-visible").textContent,notice:document.getElementById("notice").textContent,preview:document.getElementById("layers-import-reading").textContent,scale:document.getElementById("ui-scale").value})')
        existing = set((ROOT / 'user/screenshots').rglob('*.png'))
        h.native('openspace.takeScreenshot();return {requested=true}')
        until = time.monotonic() + 15
        while not (fresh := set((ROOT / 'user/screenshots').rglob('*.png')) - existing):
            if time.monotonic() > until:
                raise TimeoutError('Engine screenshot')
            time.sleep(.1)
        assert len(fresh) == 1
        path = ROOT / 'evidence/cosmos2-is6-caption-v-engine-before.png'
        source = fresh.pop()
        time.sleep(.25)
        shutil.copy2(source, path)
        record['captures'].append(dict(method='Engine framebuffer before CEF capture', path=path.relative_to(ROOT).as_posix(), sha256=sha(path)))
        name = 'cosmos2-is6-caption-v-printwindow.png'
        subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT / 'scripts/capture-window.ps1'), '-Name', name], check=True, capture_output=True)
        path = ROOT / 'evidence' / name
        record['captures'].append(dict(method='PrintWindow', path=path.relative_to(ROOT).as_posix(), sha256=sha(path)))
        try:
            data = page.call('Page.captureScreenshot', dict(format='png', fromSurface=True))['data']
            path = ROOT / 'evidence/cosmos2-is6-caption-v-cef.png'
            path.write_bytes(base64.b64decode(data))
            record['captures'].append(dict(method='CEF surface', path=path.relative_to(ROOT).as_posix(), sha256=sha(path)))
        except Exception as error:
            record['cef_capture_error'] = str(error)
        existing = set((ROOT / 'user/screenshots').rglob('*.png'))
        h.native('openspace.takeScreenshot();return {requested=true}')
        until = time.monotonic() + 15
        while not (fresh := set((ROOT / 'user/screenshots').rglob('*.png')) - existing):
            if time.monotonic() > until:
                raise TimeoutError('Engine screenshot')
            time.sleep(.1)
        assert len(fresh) == 1
        path = ROOT / 'evidence/cosmos2-is6-caption-v-engine-after.png'
        source = fresh.pop()
        time.sleep(.25)
        shutil.copy2(source, path)
        record['captures'].append(dict(method='Engine framebuffer after CEF capture', path=path.relative_to(ROOT).as_posix(), sha256=sha(path)))
        assert state()['guard'] == record['layers']['guard'] and h.test.phase(h.get('/api/state')['physics']) == phase
        record['completed'] = True
except Exception:
    record['failure']=traceback.format_exc();raise
finally:
    try:
        current = state()
        if current.get('import_preview'):
            command('import_cancel', preview_id=current['import_preview']['id'])
        if state()['active'] or state()['recovery_required']:
            command('leave')
        h.post('/api/command', dict(command='atlas'))
        h.native('openspace.toggleShutdown();return {closing=true}')
        assert before == {p.relative_to(store).as_posix(): sha(p) for p in store.rglob('*.json')}
        assert sha(ROOT / 'user/sessions/latest.json') == record['owner_sha256']
    except Exception:
        record['cleanup_failure']=traceback.format_exc()
    finally:
        out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
        if h._socket:
            h._socket.close()
print(json.dumps(dict(completed=record['completed'], captures=len(record['captures']), ui=record.get('ui'))))
