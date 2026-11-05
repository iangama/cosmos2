"""Exercise candidate spatial upload transport without starting a renderer."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import traceback
import urllib.error
import urllib.request
from native_ui_readiness import wait_for_ui

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is6-spatial-import-product0.22.0/app'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument('--label', required=True)
args = parser.parse_args()
if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
    parser.error('Invalid label')
folder = ROOT / ('output/is6-spatial-import-http-' + args.label)
out = ROOT / ('evidence/is6-spatial-import-http-' + args.label + '.json')
if folder.exists() or out.exists():
    raise FileExistsError('Preserve HTTP evidence')
manifest_path = APP.parent / 'build-manifest.json'
manifest = json.loads(manifest_path.read_text())
assert manifest['candidate'] == '0.22.0' and manifest['promoted'] is False
sources = dict(manifest['source_sha256'])
for path in [Path(__file__), manifest_path, ROOT / 'scripts/native_ui_readiness.py']:
    sources[path.relative_to(ROOT).as_posix()] = sha(path)
for name, seal in manifest['files_sha256'].items():
    sources[(APP / name).relative_to(ROOT).as_posix()] = seal
assert all(sha(ROOT / name) == seal for name, seal in sources.items())
folder.mkdir()
port = 4764
base = 'http://127.0.0.1:' + str(port)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
record = dict(accepted=False, completed=False, source_sha256=sources, imports=[], refusals=[],
    owner_sha256=sha(ROOT / 'user/sessions/latest.json'),
    scope='Actual 0.22.0 HTTP transport with real CPU validation/store and no renderer launch. Not CEF/UI, native restoration or performance acceptance.')
server = None
logs = []
def get(path):
    with opener.open(base+path, timeout=70) as response:
        return json.load(response)
def post(path, value, *, headers=None, raw=None):
    body = json.dumps(value, ensure_ascii=True).encode() if raw is None else raw
    request = urllib.request.Request(base+path, data=body,
        headers={'Content-Type':'application/json', **(headers or {})}, method='POST')
    with opener.open(request, timeout=70) as response:
        return json.load(response)
def refuse(case, path, value, **options):
    before = get('/api/spatial/state')
    files = {p.relative_to(APP.parent).as_posix():sha(p) for p in (APP.parent / 'is6-spatial-import-service-records').rglob('*.json')}
    try:
        post(path, value, **options)
    except urllib.error.HTTPError as error:
        assert error.code in [400,403], error.code
        message = json.loads(error.read())
        record['refusals'].append(dict(case=case, status=error.code, error=message['error']))
    else:
        raise AssertionError('Invalid HTTP request accepted: '+case)
    after = get('/api/spatial/state')
    assert after['guard'] == before['guard'] and after['import_preview'] == before['import_preview'] and not after['active']
    assert files == {p.relative_to(APP.parent).as_posix():sha(p) for p in (APP.parent / 'is6-spatial-import-service-records').rglob('*.json')}
try:
    for filename in ['server.log','server-errors.log']:
        logs.append((folder / filename).open('wb'))
    environment = os.environ.copy()
    environment['COSMOS2_STORAGE'] = str(folder / 'gravity-sessions')
    server = subprocess.Popen([sys.executable, '-u', '-Xutf8', str(APP / 'server.py'), '--port', str(port)],
        cwd=ROOT, env=environment, stdout=logs[0], stderr=logs[1])
    record['readiness'] = wait_for_ui(port=port, timeout_s=180, child_alive=lambda:server.poll() is None)
    state = get('/api/spatial/state')
    assert not state['active'] and not state['branches'] and get('/api/state')['mode'] == 'atlas'
    guard = state['guard']
    for case, headers in [('foreign Host', {'Host':'example.invalid'}), ('foreign Origin', {'Origin':'https://example.invalid'})]:
        refuse(case, '/api/spatial/import-preview', {'guard':guard,'source_text':'{}'}, headers=headers)
    refuse('Duplicate transport key', '/api/spatial/import-preview', {}, raw=b'{"guard":{},"guard":{}}')
    refuse('Transport NaN', '/api/spatial/import-preview', {}, raw=b'{"x":NaN}')
    refuse('Oversized content length before read', '/api/spatial/import-preview', {}, headers={'Content-Length':str(64*1024*1024+1)})
    refuse('Endpoint owns command', '/api/spatial/import-preview', dict(command='leave', guard=guard, source_text='{}'))
    foundation = json.loads((ROOT / 'evidence/is6-spatial-import-20261104a.json').read_text())
    for item in [row for row in foundation['conversions'] if row['form'] == 'saved']:
        guard = get('/api/spatial/state')['guard']
        text = (ROOT / item['source_path']).read_bytes().decode('utf8')
        preview = post('/api/spatial/import-preview', dict(guard=guard, source_text=text))['spatial']['import_preview']
        assert preview['valid'] and preview['view']['visible'] is item['visible']
        cancelled = post('/api/spatial/command', dict(command='import_cancel', guard=guard, preview_id=preview['id']))
        assert cancelled['spatial']['import_preview'] is None and cancelled['spatial']['guard'] == guard
        preview = post('/api/spatial/import-preview', dict(guard=guard, source_text=text))['spatial']['import_preview']
        refuse('Changed file after preview', '/api/spatial/import-commit', dict(guard=guard, preview_id=preview['id'], source_text=text+'\n', name='Espacial'))
        imported = post('/api/spatial/import-commit', dict(guard=guard, preview_id=preview['id'], source_text=text, name='HTTP solar '+str(int(item['visible']))))
        assert not imported['spatial']['active'] and not imported['spatial']['checkpoint_available']
        assert imported['result']['record']['branch']['parent'] is None
        path = Path(imported['result']['path'])
        saved = json.loads(path.read_text())
        assert saved['origin']['source_text'] == text and saved['view'] == preview['view']
        record['imports'].append(dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), branch=imported['result']['record']['branch']))
    state = get('/api/spatial/state')
    assert len(state['branches']) == 2 and all(row['valid'] for row in state['branches'])
    assert not state['active'] and not state['checkpoint_available']
    assert get('/api/state')['mode'] == 'atlas'
    post('/api/shutdown', {})
    record['server_exit'] = server.wait(timeout=30)
    assert record['server_exit'] == 0
    assert all(sha(ROOT / name) == seal for name, seal in sources.items())
    assert sha(ROOT / 'user/sessions/latest.json') == record['owner_sha256']
    record.update(accepted=True, completed=True)
except Exception:
    record['failure'] = traceback.format_exc()
finally:
    if server is not None and server.poll() is None:
        try:
            post('/api/shutdown', {})
            server.wait(timeout=15)
        except Exception:
            server.terminate()
            server.wait(timeout=10)
    for stream in logs:
        stream.close()
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
print(json.dumps(dict(accepted=record['accepted'], imports=len(record['imports']), refusals=len(record['refusals']), failure=record.get('failure'))))
raise SystemExit(0 if record['accepted'] else 1)
