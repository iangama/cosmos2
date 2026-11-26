"""Native camera persistence, adjunct refusal and honest display-failure recovery."""
from pathlib import Path
import sys
import hashlib
import json
import time
import urllib.error
import urllib.request
from cef_page import Page
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parents[1];V04='--v04' in sys.argv;CANDIDATE=ROOT/('output/c212-em-v04-product' if V04 else 'output/c212-em-product');STORAGE=CANDIDATE/'c212-em-worker/product'
sys.path.insert(0,str(CANDIDATE/'app'))
from em_native import normalize
owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes();errors=[];cases=[]
def get():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/em/state',timeout=10))
def guard():
    state=get()['state'];return {k:state[k] for k in ('system_id','edit_token','revision','frame')}|{'expected_time_s':state['time_s']}
def post(path,value,error=False):
    request=urllib.request.Request('http://127.0.0.1:4700/api/em/'+path,data=json.dumps(value,allow_nan=False).encode(),headers={'Content-Type':'application/json'})
    try:
        result=json.load(urllib.request.urlopen(request,timeout=15));assert not error;return result
    except urllib.error.HTTPError as response:
        assert error;return json.load(response)
ws=connect('ws://127.0.0.1:4682',open_timeout=3,close_timeout=.2,ping_interval=None);topic=0
ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
def native(code):
    global topic
    topic+=1;ws.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True}}));response=json.loads(ws.recv(timeout=5));assert response.get('topic')==topic;return normalize(response['payload']['1'])
sky_script='return {CatalogStars=openspace.propertyValue("Scene.CatalogStars.Renderable.Enabled"),MilkyWaySky=openspace.propertyValue("Scene.MilkyWaySky.Renderable.Enabled"),MilkyWayVolume=openspace.propertyValue("Scene.MilkyWayVolume.Renderable.Enabled")}'
initial_sky=native(sky_script)
try:
    with Page() as page:
        previous=page.evaluate('location.href');page.on('pageerror',lambda e:errors.append(e))
        def idle(expression='true'):page.wait_for_function('!pending&&('+expression+')',timeout=30000)
        page.locator('#em-lab').click();page.wait_for_function('location.pathname==="/em.html"&&nativeState?.confirmation?.state==="accepted"&&!pending',timeout=30000)
        assert native(sky_script)=={k:False for k in initial_sky}
        old=page.evaluate('state.system_id');page.locator('#preset').select_option('dipole');page.locator('#load-preset').click();idle('state.system_id!=='+json.dumps(old))
        native('openspace.setPropertyValueSingle("Scene.C2EMCamera.Translation.Position",{1e9,2e9,-1e9});openspace.navigation.setNavigationState({Anchor="C2EMCamera",ReferenceFrame="C2EMRoot",Position={6e9,-9e9,4e9},Up={0,0,1},Yaw=.1,Pitch=-.2});return {queued=true}')
        time.sleep(.1);page.locator('#save').click();idle()
        checkpoint=STORAGE/'ui-phase.json';adjunct=STORAGE/'ui-phase.view.json';assert adjunct.is_file()
        original_view=adjunct.read_bytes();saved=json.loads(original_view)['payload'];assert saved['checkpoint_sha256']==hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        assert saved['view']['focus_model_m']==[1,2,-1]
        physical=page.evaluate('state.experiment')
        native('openspace.setPropertyValueSingle("Scene.C2EMCamera.Translation.Position",{0,0,0});openspace.navigation.setNavigationState({Anchor="C2EMCamera",ReferenceFrame="C2EMRoot",Position={-5e9,-4e9,8e9},Up={0,0,1}});return {queued=true}')
        time.sleep(.1);old=page.evaluate('state.edit_token');page.locator('#restore').click();idle('state.edit_token!=='+json.dumps(old))
        assert page.evaluate('state.experiment')==physical
        actual=native('return {navigation=openspace.navigation.getNavigationState("C2EMRoot"),focus=openspace.propertyValue("Scene.C2EMCamera.Translation.Position")}')
        assert actual['focus']==[v*1e9 for v in saved['view']['focus_model_m']]
        for key in ('Position','Up'):
            assert max(abs(a-b) for a,b in zip(actual['navigation'][key],saved['view']['navigation'][key]))<=max(1e-10,max(abs(v) for v in saved['view']['navigation'][key])*1e-11),(key,actual,saved)
        cases.append('save/restore native focus and full camera pose tied to exact scientific checkpoint hash')
        # Resealing invalid view values must still fail before the worker loads.
        before=get()['state']
        for kind in ('anchor','checkpoint'):
            record=json.loads(original_view)
            if kind=='anchor':record['payload']['view']['navigation']['Anchor']='Earth'
            else:record['payload']['checkpoint_sha256']='0'*64
            record['sha256']=hashlib.sha256(json.dumps(record['payload'],sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()
            adjunct.write_text(json.dumps(record),encoding='utf-8')
            response=post('command',{'command':'load',**guard(),'file':'ui-phase'},error=True)
            assert get()['state']['experiment']==before['experiment'] and get()['state']['edit_token']==before['edit_token']
        adjunct.write_bytes(original_view);cases.append('resealed invalid camera anchor and wrong checkpoint hash refused before scientific mutation')
        source={'id':'valid-model-outside-display','position_m':[1e300,0,0],'exclusion_radius_m':.1,'charge_C':0.,'magnetic_moment_A_m2':[0,0,0]}
        ack=post('command',{'command':'edit',**guard(),'edit':{'operation':'create_source','source':source}})
        assert ack['type']=='ack' and ack['display']['worker_command_confirmed'] and ack['display']['state']=='failed'
        assert get()['state']['experiment']['model']['sources'][-1]['id']==source['id'] and get()['native']['error']
        ack=post('command',{'command':'edit',**guard(),'edit':{'operation':'remove_source','id':source['id']}})
        assert 'display' not in ack and get()['native']['error'] is None
        cases.append('valid scientific edit with unrepresentable graphic coordinate is confirmed with display failure; removal recovers native scene')
        before=get()['state']['experiment'];post('frame',{'selected':'yes'},error=True);assert get()['state']['experiment']==before
        page.wait_for_function('state.revision==='+str(get()['state']['revision']))
        page.locator('#measure').click();idle('map!==null');page.locator('#native-frame').click();idle()
        import subprocess
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-em-native-dark.png'],check=True,capture_output=True)
        page.locator('#native-return').click();page.wait_for_function('location.pathname==="/"&&typeof appState!=="undefined"&&appState!==null',timeout=30000)
        assert native(sky_script)==initial_sky and not get()['native']['active']
        assert not errors,errors;assert owner.read_bytes()==original
        report={'status':'candidate_EM_native_camera_persistence_atomic_adjunct_refusals_and_display_recovery_verified','cases':cases,
                'dark_laboratory_restores_previous_Atlas_sky':initial_sky,'javascript_errors':errors,'owner_pointer_preserved':True,
                'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (CANDIDATE/'app/em_native.py',CANDIDATE/'app/em_laboratory.py',CANDIDATE/'app/ui/em/native.js',Path(__file__))},
                'scope':'Candidate only. Native view is a separately sealed adjunct bound to the EM checkpoint SHA; no gravitational Session conversion or performance acceptance.'}
        (ROOT/('evidence/em-v04-native-resilience-check.json' if V04 else 'evidence/em-native-resilience-check.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
finally:
    ws.close()
    if 'previous' in locals():
        with Page() as cleanup:cleanup.call('Page.navigate',{'url':previous})
    assert owner.read_bytes()==original
