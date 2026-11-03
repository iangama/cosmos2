"""Actual CEF navigation across all four stages and both isolated EM labs."""
from pathlib import Path
import argparse
import hashlib
import json
import urllib.request
from cef_page import Page
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parents[1];G=ROOT/'output/c212-em-viewport-product'
parser=argparse.ArgumentParser();parser.add_argument('--label',default='initial');args=parser.parse_args()
assert args.label.isalnum() and len(args.label)<=16
destination=ROOT/f'evidence/em-viewport-navigation-{args.label}-check.json';assert not destination.exists()
session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert session.get('emViewportCandidate') and Path(session['serverScript']).resolve()==(G/'app/server.py').resolve()
owner=(ROOT/'user/sessions/latest.json').read_bytes();report={'completed':False,'force_checks':[],'JS_errors':[]}
def api(path):return json.load(urllib.request.urlopen('http://127.0.0.1:4700'+path,timeout=10))
def native_snapshot():
    with connect('ws://127.0.0.1:4682',open_timeout=3,close_timeout=.2,ping_interval=None) as ws:
        ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
        ws.send(json.dumps({'topic':1,'type':'luascript','payload':{'return':True,'script':'return {em=openspace.hasSceneGraphNode("C2EMRoot"),nav=openspace.navigation.getNavigationState("Root")}'}}))
        return json.loads(ws.recv(timeout=5))['payload']['1']
def small_idle(page):page.wait_for_function('state&&state.paused&&!pending&&nativeState?.active&&nativeState.confirmation?.metadata.time_s===state.time_s&&!nativeState.error',timeout=30000)
def cloud_idle(page):page.wait_for_function('state&&state.paused&&!pending&&native?.active&&native.confirmation?.metadata.time_s===state.time_s&&!native.error',timeout=30000)

try:
    with Page() as page:
        page.on('pageerror',lambda value:report['JS_errors'].append(value))
        page.goto('http://127.0.0.1:4700/');page.wait_for_function('typeof appState!=="undefined"&&appState')
        initial=native_snapshot();assert not initial['em']
        page.locator('#forces').click();page.wait_for_function('typeof response!=="undefined"&&response&&!pending',timeout=30000)
        for force in ('gravity','electromagnetic','strong','weak'):
            page.locator('[data-scenario="'+force+'"]').click()
            page.wait_for_function('!pending&&config.scenario==='+json.dumps(force))
            effects=page.evaluate('JSON.parse(JSON.stringify(config.controls['+json.dumps(force)+'].effects))')
            for acting in (False,True):
                page.locator('[data-force="'+force+'"][data-control="acting"]').set_checked(acting)
                page.wait_for_function('!pending');physical=None
                for visible in (False,True):
                    page.locator('[data-force="'+force+'"][data-control="visible"]').set_checked(visible)
                    page.wait_for_function('!pending')
                    value=page.evaluate('({control:config.controls['+json.dumps(force)+'],result:response.result,counterfactual:response.counterfactual})')
                    assert value['control']['acting'] is acting and value['control']['visible'] is visible
                    assert value['control']['effects']==effects
                    assert value['counterfactual']==(not acting)
                    magnitude=value['result']['measurements'][1]['value'];assert magnitude>0 if acting else magnitude==0
                    if physical is None:physical=value['result']
                    else:assert physical==value['result']
                    report['force_checks'].append({'force':force,'acting':acting,'visible':visible,'physical_result_verified':True})
        page.locator('#open-em-lab').click();small_idle(page)
        small=api('/api/em/state');assert small['native']['active']
        page.locator('#open-cloud').click();cloud_idle(page)
        paused_small=api('/api/em/state');assert not paused_small['native']['active'] and paused_small['state']['paused']
        page.locator('#count').select_option('128');page.locator('#load-preset').click();cloud_idle(page)
        assert api('/api/em-cloud/state')['state']['count']==128
        page.locator('#play').click();page.wait_for_function('state&&!state.paused&&state.time_s>.05')
        page.locator('#play').click();cloud_idle(page)
        cloud=api('/api/em-cloud/state');assert cloud['native']['confirmation']['metadata']['count']==128
        page.locator('#small-em').click();small_idle(page)
        paused_cloud=api('/api/em-cloud/state');assert not paused_cloud['native']['active'] and paused_cloud['state']['paused']
        assert api('/api/em/state')['state']['experiment']==paused_small['state']['experiment']
        page.locator('#native-return').click();page.wait_for_function('location.pathname==="/"')
        final=native_snapshot();assert not final['em']
        assert final['nav']['Anchor']==initial['nav']['Anchor']
        def vector(v):return [v[str(i)] for i in range(1,4)] if isinstance(v,dict) else v
        a,b=vector(initial['nav']['Position']),vector(final['nav']['Position'])
        assert max(abs(x-y) for x,y in zip(a,b))<=max(1e-4,max(map(abs,a))*1e-10),(a,b)
        assert not api('/api/em/state')['native']['active'] and not api('/api/em-cloud/state')['native']['active']
        assert not report['JS_errors'],report['JS_errors']
        assert (ROOT/'user/sessions/latest.json').read_bytes()==owner
        report.update(completed=True,owner_pointer_preserved=True,native_EM_root_removed=True,
                      atlas_camera_restored=True,leaving_labs_pauses_workers=True,
                      small_phase_preserved_across_cloud=True,
                      scope='Real CEF navigation and all sixteen existing force acting/visibility combinations in separate J. Does not accept planetary fields, relativistic mesh, all-stage persistence or full C2-12.')
finally:
    report['source_sha256']={str(Path(__file__).relative_to(ROOT)).replace('\\','/'):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    destination.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'completed':report['completed'],'force_combinations':len(report['force_checks'])}),flush=True)
