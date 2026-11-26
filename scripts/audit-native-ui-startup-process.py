"""Resolve B's unavailable psutil exit code using its own archived child handles."""
from pathlib import Path
import hashlib
import json
import psutil

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source = ROOT / 'evidence/local-ui-native-startup-20261104b.json'
out = ROOT / 'evidence/local-ui-native-startup-20261104b-r2.json'
if out.exists():
    raise FileExistsError('Preserve independent process audit')
r = json.loads(source.read_text(encoding='utf8'))
assert r['completed'] and not r.get('failure')
assert r['engine_exit'] == r['launcher_exit'] == 0 and r['server_exit'] is None
assert r['cleanup_failure'].strip().endswith('AssertionError')
assert "r.get('engine_exit') == r.get('server_exit') == r.get('launcher_exit') == 0" in r['cleanup_failure']
assert r['launcher_kind'] == 'candidate'
assert r['readiness']['http_ready_before_engine_start'] and r['readiness']['server_pid'] == r['session']['server']
assert r['ui_without_manual_navigation']['title'] == 'Cosmos2 — Atlas'
sources = dict(r['source_sha256'])
sources.update({source.relative_to(ROOT).as_posix(): sha(source),
                Path(__file__).relative_to(ROOT).as_posix(): sha(Path(__file__))})
matches = []
for path in (ROOT / 'output/is6-layers-product0.21.1/execution-logs').glob('*/session.json'):
    session = json.loads(path.read_text(encoding='utf-8-sig'))
    if all(session[key] == r['session'][key] for key in ['app', 'server', 'launcher']):
        matches.append(path)
assert len(matches) == 1
session_path = matches[0]
process_path = session_path.with_name('process-result.json')
process = json.loads(process_path.read_text(encoding='utf8'))
assert process == dict(app_exit=0, server_exit=0)
ready_path = session_path.with_name('local-ui-readiness.json')
assert json.loads(ready_path.read_text(encoding='utf8')) == r['readiness']
for path in [session_path, process_path, ready_path]:
    sources[path.relative_to(ROOT).as_posix()] = sha(path)
alive, reused = {}, {}
for key in ['app', 'server', 'launcher']:
    try:
        current = psutil.Process(r['session'][key])
        assert current.create_time() > process_path.stat().st_mtime + 1
        reused[key] = dict(pid=current.pid, created_unix=current.create_time(), name=current.name())
    except psutil.NoSuchProcess:
        pass
    alive[key] = False
image = r['capture']
assert sha(ROOT / image['path']) == image['sha256']
sources[image['path']] = image['sha256']
assert all(sha(ROOT / p) == seal for p, seal in sources.items())
assert all(sha(ROOT / p) == seal for p, seal in r['installed_app_before'].items())
assert sha(ROOT / 'user/sessions/latest.json') == r['owner_sha256']
result = dict(accepted=True, completed=True, source_sha256=sources, session=r['session'],
              readiness=r['readiness'], process_result=process, launcher_exit=0,
              pids_alive=alive, reused_numeric_pids=reused, capture=image,
              owner_sha256=r['owner_sha256'], entry_point_activated=False,
              manual_image_review='The raw native screenshot shows the Atlas UI and Earth, with Motor conectado; no connection-refused page. The launcher loaded the UI without manual navigation or reload.',
              correction='B incorrectly required psutil to recover the server exit code after its parent had already reaped it. The archived parent process handles confirm app/server0/0. Original B remains unchanged and refused.',
              scope='Candidate0.21.1 HTTP readiness gate and native startup only; installed shortcut verification remains pending while PowerShell startup is suspended. No promotion or performance acceptance.')
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps(dict(accepted=True, process_result=process, pids_alive=alive, readiness_wait_s=r['readiness']['elapsed_s'])))
