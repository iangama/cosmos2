"""Confirm the real -Built default boot after the launcher-only followup."""
from pathlib import Path
import hashlib
import json
import urllib.request
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
session = json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
cloud=session['runtimeVariant']=='cloud'
assert session['runtimeVariant'] in ('query','cloud')
assert session['runtimeSelectionReason']==('approved-C211-engine-and-app-hashes' if cloud else 'approved-P256-engine-hash')
if cloud:
    assert not session['cloudCandidate']
    assert Path(session['serverScript']).resolve()==(ROOT/'app/server.py').resolve()
approval = json.loads((ROOT/('evidence/c211-cloud-validated.json' if cloud else 'evidence/c211-p256-validated.json')).read_text())
assert hashlib.sha256((Path(session['runtime'])/'bin/OpenSpace.exe').read_bytes()).hexdigest() == approval['engine_sha256']
with connect('ws://127.0.0.1:4682', open_timeout=5, ping_interval=None) as ws:
    ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
    ws.send(json.dumps({'topic':1,'type':'luascript','payload':{'return':True,'script':
        'return {navigation=openspace.navigation.getNavigationState(),gui=openspace.propertyValue("Modules.CefWebGui.GuiUrl"),earth=openspace.hasSceneGraphNode("Earth")}'}}))
    reply = json.loads(ws.recv(timeout=15))
    assert reply['topic'] == 1
    native = reply['payload']['1']
    assert native['navigation']['Anchor'] == 'Earth' and native['earth']
    assert native['gui'] == 'http://127.0.0.1:4700/'
with urllib.request.urlopen('http://127.0.0.1:4700/api/state', timeout=10) as response:
    state = json.load(response)
assert state['mode'] == 'atlas' and state['physics'] is None and state['error'] is None
pointer = hashlib.sha256((ROOT/'user/sessions/latest.json').read_bytes()).hexdigest()
assert pointer == 'ee9c4cc86e0696afde128ec319f98f6ad5b3932f27f8b5bd6a25d57a4025b825'
report = {'default_Built_boot_verified':True,'session':session,'native':native,
    'laboratory_lazy_until_enter':state['physics'] is None,
    'owner_pointer_sha256':pointer,'engine_sha256':approval['engine_sha256'],
    'launcher_sha256':hashlib.sha256((ROOT/'scripts/start-cosmos2.ps1').read_bytes()).hexdigest(),
    'selector_sha256':hashlib.sha256((ROOT/'scripts/select-runtime.ps1').read_bytes()).hexdigest(),
    'selection_checks':'evidence/runtime-cloud-auto-selection-check.json' if cloud else 'evidence/runtime-auto-selection-check.json',
    'scope':'Real default installed boot with approved engine and backend. Formal frame profiles and native UI journeys have separate receipts.'}
(ROOT/'evidence/runtime-default-boot-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
