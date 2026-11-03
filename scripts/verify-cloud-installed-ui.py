"""Installed default flow without saving over the owner's checkpoint."""
from pathlib import Path
import hashlib
import json
import time
import urllib.request
from websockets.sync.client import connect
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert launch['runtimeVariant']=='cloud' and not launch['cloudCandidate']
assert launch['runtimeSelectionReason']=='approved-C211-engine-and-app-hashes'
owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes()
def state():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/state',timeout=10))
def command(value):
    r=urllib.request.Request('http://127.0.0.1:4700/api/command',data=json.dumps(value).encode(),headers={'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(r,timeout=65))
assert state()['physics'] is None,'Start from a fresh default boot'
errors=[]
ws=connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=1,ping_interval=None)
ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
try:
    with Page() as page:
        page.on('pageerror',lambda e:errors.append(e));page.goto('http://127.0.0.1:4700/')
        page.wait_for_function('appState!==null');page.locator('#experiment').click()
        page.wait_for_function('!pending&&appState.mode==="experiment"',timeout=60000)
        assert state()['cloud_supported'] is True
        page.evaluate('document.getElementById("test-cloud").open=true')
        page.locator('#cloud-create').click()
        page.wait_for_function('!pending&&appState.physics.test_particle_cloud?.test_particles===10000',timeout=60000)
        page.locator('#play').click();page.wait_for_function('!pending&&!appState.physics.paused')
        page.wait_for_function('appState.physics.time>.3')
        page.locator('#cloud-select').click()
        page.wait_for_function('!pending&&appState.cloud_view?.reading?.index===9999',timeout=20000)
        s=state();p=s['physics'];point=s['cloud_view']['reading']
        assert p['paused'] and p['scientific_generation']['model_version']=='3.13.0'
        assert not s['cloud_view']['reading_is_stale']
        ws.send(json.dumps({'topic':1,'type':'luascript','payload':{'return':True,'script':
            'return {count=openspace.propertyValue("Scene.C2CloudStream.Renderable.NumberOfDataPoints"),position=openspace.propertyValue("Scene.C2CloudSelection.Translation.Position")}'}}))
        native=json.loads(ws.recv(timeout=15))['payload']['1']
        assert native['count']==10000 and native['position']==point['position_m']
        assert not errors,errors
        assert owner.read_bytes()==original
        report={'status':'installed_default_cloud_UI_verified_without_owner_save',
            'session':launch,'active_sources':1,'test_particles':10000,'actual_3_13_worker':True,
            'native_selection_SI_exact':True,'javascript_errors':errors,
            'owner_pointer_preserved':True,'owner_pointer_sha256':hashlib.sha256(original).hexdigest(),
            'scope':'Fresh default installed launcher/backend/runtime, creation/evolution/pause/selection; full save/load and exports proved separately on identical staged bytes.'}
        (ROOT/'evidence/cloud-installed-ui-check.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k!='session'},indent=2),flush=True)
finally:
    try:command({'command':'pause'});command({'command':'atlas'})
    finally:
        ws.close()
        assert owner.read_bytes()==original
