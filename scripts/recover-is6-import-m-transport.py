"""Inspect the completed preview after M's CDP overflow, then close its host normally."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import hashlib
import json
import subprocess
import sys
import time
import psutil
from cef_page_v2 import Page

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
h = SourceFileLoader('import_m_recovery_helpers', str(ROOT / 'scripts/benchmark-body-points-native.py')).load_module()
out = ROOT / 'evidence/is6-layers-import-recovery-20261104m.json'
if out.exists():
    raise FileExistsError('Preserve recovery evidence')
launch = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
assert launch['is6LayerImportCandidate'] and '0.21.0' in launch['serverScript']
state = h.get('/api/layers/state')
assert not state['busy'] and not state['active'] and not state['recovery_required']
assert state['import_preview']['valid'] and state['import_preview']['body_reference_id'] == 'sol:naif:399'
folder = ROOT / 'output/is6-layers-product0.21.0/layer-checkpoints'
assert not list(folder.rglob('*.json'))
phase = h.test.phase(h.get('/api/state')['physics'])
record = dict(accepted=False, completed=False, recovered=False, session=launch, before=state,
              owner_sha256=sha(ROOT / 'user/sessions/latest.json'), captures=[],
              source_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in
                  [Path(__file__), ROOT / 'scripts/cef_page_v2.py',
                   ROOT / 'scripts/capture-window.ps1', ROOT / 'evidence/is6-layers-import-native-20261104m.json']},
              scope='Diagnostic preview/recovery only; M functional failure remains refused.')
with Page() as page:
    page.wait_for_function('!layerInstrument.pending&&!layerInstrument.readingFile&&!layerInstrument.snapshot.busy', timeout=80000)
    for scale in ['1', '1.5']:
        page.locator('#ui-scale').select_option(scale)
        page.evaluate('document.getElementById("layers-import").open=true;document.getElementById("layers-import-fields").scrollIntoView({block:"start"})')
        time.sleep(.2)
        name = 'cosmos2-is6-import-diagnostic-m-preview-' + str(int(float(scale) * 100)) + '.png'
        subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                        str(ROOT / 'scripts/capture-window.ps1'), '-Name', name], check=True, capture_output=True)
        path = ROOT / 'evidence' / name
        record['captures'].append(dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path)))
    record['ui_reading'] = page.locator('#layers-import-reading').inner_text()
    page.locator('#ui-scale').select_option('1')
h.post('/api/layers/command', dict(command='import_cancel', guard=state['guard'], preview_id=state['import_preview']['id']))
after = h.get('/api/layers/state')
assert after['guard'] == state['guard'] and after['import_preview'] is None and not after['active']
assert h.test.phase(h.get('/api/state')['physics']) == phase and not list(folder.rglob('*.json'))
h.post('/api/command', dict(command='atlas'))
h.native('openspace.toggleShutdown();return {closing=true}')
if h._socket:
    h._socket.close()
until = time.monotonic() + 60
while any(psutil.pid_exists(launch[k]) for k in ['app', 'server', 'launcher']):
    if time.monotonic() > until:
        raise TimeoutError('Normal M host exit pending')
    time.sleep(.25)
assert sha(ROOT / 'user/sessions/latest.json') == record['owner_sha256']
record.update(completed=True, recovered=True, after=after, pids_alive=False)
out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps(dict(recovered=True, original_test_accepted=False, captures=len(record['captures']))))
