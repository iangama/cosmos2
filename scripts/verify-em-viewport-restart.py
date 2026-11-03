"""Verify I's real normal restart and exact saved scientific continuation."""
from pathlib import Path
import hashlib
import json
import sys
import time
from cef_page import Page
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parents[1];G=ROOT/'output/c212-em-viewport-product'
sys.path.insert(0,str(ROOT/'output/c212-em-integration-product/em'))
from em_experiment import Experiment
expected=json.loads((ROOT/'output/em-viewport-restart-expected.json').read_bytes())
destination=ROOT/'evidence/em-viewport-restart-check.json';assert not destination.exists()
session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert session.get('emViewportCandidate') and Path(session['serverScript']).resolve()==(G/'app/server.py').resolve()
owner=(ROOT/'user/sessions/latest.json').read_bytes();errors=[]
storage=G/'c212-em-worker/product'
assert all(hashlib.sha256((storage/('ui-phase'+ending)).read_bytes()).hexdigest()==digest for ending,digest in expected['files_sha256'].items())
reference=Experiment.from_payload(expected['state']['experiment']);reference.advance(777)
with Page() as page:
    page.on('pageerror',lambda value:errors.append(value));page.goto('http://127.0.0.1:4700/')
    page.wait_for_function('typeof appState!=="undefined"&&appState');page.locator('#em-lab').click()
    page.wait_for_function('state&&state.paused&&!pending&&nativeState?.confirmation?.state==="accepted"',timeout=30000)
    page.locator('#restore').click()
    page.wait_for_function('state&&state.paused&&!pending&&state.time_s==='+repr(expected['state']['experiment']['phase']['time_s'])+'&&state.system_id===nativeState.confirmation.metadata.system_id&&state.time_s===nativeState.confirmation.metadata.time_s',timeout=30000)
    restored=page.evaluate('JSON.parse(JSON.stringify(state))')
    for name in ('experiment','editor','time_preferences','scientific_generation','execution_generation'):
        assert restored[name]==expected['state'][name],name
    assert page.evaluate('nativeState.canvas_view')==expected['canvas_view']
    page.locator('#native-toggle').click();assert page.evaluate('document.getElementById("canvas-zoom").value')==str(expected['canvas_view']['zoom'])
    page.locator('#native-toggle').click()
    saved_view=json.loads((storage/'ui-phase.view.json').read_bytes())['payload']['view']
    with connect('ws://127.0.0.1:4682',open_timeout=3,close_timeout=.2,ping_interval=None) as ws:
        ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
        ws.send(json.dumps({'topic':1,'type':'luascript','payload':{'return':True,'script':'return {nav=openspace.navigation.getNavigationState("C2EMRoot"),focus=openspace.propertyValue("Scene.C2EMCamera.Translation.Position")}'}}))
        actual=json.loads(ws.recv(timeout=5))['payload']['1']
    def vector(value):return [value[str(i)] for i in range(1,4)] if isinstance(value,dict) else value
    for key in ('Position','Up'):
        av=vector(actual['nav'][key]);ev=saved_view['navigation'][key]
        assert max(abs(a-b) for a,b in zip(av,ev))<=max(1e-6,max(map(abs,ev))*1e-12),(key,av,ev)
    assert actual['nav']['Anchor']=='C2EMCamera'
    for key in ('Yaw','Pitch'):
        assert abs(actual['nav'].get(key,0)-saved_view['navigation'].get(key,0))<1e-12,key
    focus=vector(actual['focus']);expected_focus=[x*1e9 for x in saved_view['focus_model_m']]
    assert max(abs(a-b) for a,b in zip(focus,expected_focus))<=max(1e-6,max(map(abs,expected_focus))*1e-12)
    page.evaluate('(async()=>{for(let offset=0;offset<777;offset+=32)await command("advance",{...guard(),steps:Math.min(32,777-offset)});return true;})()')
    page.wait_for_function('state.time_s==='+repr(reference.phase.time_s)+'&&!pending&&nativeState.confirmation.metadata.time_s===state.time_s',timeout=30000)
    assert page.evaluate('JSON.parse(JSON.stringify(state.experiment))')==json.loads(json.dumps(reference.payload()))
    assert all(hashlib.sha256((storage/('ui-phase'+ending)).read_bytes()).hexdigest()==digest for ending,digest in expected['files_sha256'].items())
    page.locator('#native-return').click();page.wait_for_function('location.pathname==="/"')
assert not errors and (ROOT/'user/sessions/latest.json').read_bytes()==owner
report={'status':'J_normal_restart_view3_canvas_and777_future_steps_verified',
        'owner_pointer_preserved':True,'saved_files_preserved':True,'scientific_future_exact':True,
        'saved_native_camera_restored':True,'JS_errors':errors,
        'source_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),ROOT/'output/em-viewport-restart-expected.json')},
        'scope':'Fresh normal restart, native camera and canvas scope/zoom, saved small-lab phase/selection/time and777-step continuation. No whole C2-12 or formal G throughput acceptance.'}
destination.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
