"""Real CEF/Laboratory/worker/native10k journey, with isolated candidate storage."""
from pathlib import Path
import hashlib
import json
import math
import subprocess
import time
import urllib.error
import urllib.request
from websockets.sync.client import connect
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
pointer=ROOT/'user/sessions/latest.json';original=pointer.read_bytes()
session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert session['cloudCandidate'] and session['runtimeVariant']=='cloud'
def state():
    return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/state',timeout=5))
def command(value):
    data=json.dumps(value).encode()
    return json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:4700/api/command',
        data=data,headers={'Content-Type':'application/json'}),timeout=70))
def wait(predicate,seconds=20):
    end=time.perf_counter()+seconds
    while time.perf_counter()<end:
        s=state()
        if s['error']:raise AssertionError(s['error'])
        if predicate(s):return s
        time.sleep(.05)
    raise TimeoutError(str(s)[:1000])
def confirmed(s):
    p=s.get('physics');n=(s.get('cloud_view') or {}).get('native')
    return bool(p and n and n['gpu_buffer_uploaded'] and n['metadata']['time_model']==p['time']
        and n['metadata']['edit_token']==p['edit_token'])
ws=connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=1,ping_interval=None)
ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}));topic=0
def lua(code):
    global topic
    topic+=1;ws.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True}}))
    r=json.loads(ws.recv(timeout=20));assert r.get('topic')==topic,r
    return r.get('payload',{}).get('1')
errors=[];results={}
try:
    with Page() as page:
        page.on('pageerror',lambda e:errors.append(e))
        page.goto('http://127.0.0.1:4700/')
        page.wait_for_function('appState!==null')
        if state()['mode']!='experiment':
            page.locator('#experiment').click()
            page.wait_for_function('appState?.mode==="experiment"&&!pending',timeout=60000)
        page.evaluate('document.getElementById("test-cloud").open=true')
        page.locator('#cloud-create').click()
        page.wait_for_function('appState?.physics?.test_particle_cloud?.test_particles===10000&&!pending',timeout=60000)
        s=wait(confirmed);p=s['physics'];cloud=p['test_particle_cloud']['cloud_id']
        assert len(p['bodies'])==1 and p['paused']
        print('create10000/native confirmed',flush=True)
        page.locator('#cloud-select').click()
        page.wait_for_function('appState?.cloud_view?.reading?.index===9999&&!pending',timeout=20000)
        s=wait(confirmed);point=s['cloud_view']['reading']
        native=lua('return {position=openspace.propertyValue("Scene.C2CloudSelection.Translation.Position"),count=openspace.propertyValue("Scene.C2CloudStream.Renderable.NumberOfDataPoints")}')
        assert native['position']==point['position_m'] and native['count']==10000
        assert not s['cloud_view']['reading_is_stale'] and math.isfinite(point['specific_energy_J_kg'])
        assert 'J/kg' in page.locator('#cloud-reading').inner_text()
        page.locator('#cloud-focus').click()
        end=time.perf_counter()+3
        while time.perf_counter()<end:
            if lua('return openspace.navigation.getNavigationState()')['Anchor']=='C2CloudSelection':break
            time.sleep(.02)
        else:raise AssertionError('Individual camera focus was not confirmed')
        first_time=p['time'];first_position=point['position_m']
        page.locator('#play').click()
        page.wait_for_function('!pending&&!appState.physics.paused')
        live=wait(lambda s:s['physics']['time']>first_time+.5 and s['cloud_view']['reading_is_stale'])
        assert live['cloud_view']['native']['metadata']['time_model']>first_time
        page.locator('#cloud-export-reading').click();page.wait_for_function('!pending&&document.getElementById("notice").textContent.includes("Leitura antiga preservada em:")')
        exported=page.locator('#notice').inner_text().split(' em: ',1)[-1]
        stale_export=json.loads(Path(exported).read_text(encoding='utf-8'))
        assert stale_export['reading_is_stale'] and stale_export['reading']['position_m']==first_position
        live_position=lua('return {p=openspace.propertyValue("Scene.C2CloudSelection.Translation.Position")}')['p']
        assert math.dist(live_position,first_position)>1e6
        page.locator('#play').click();page.wait_for_function('!pending&&appState.physics.paused')
        s=wait(confirmed);assert s['cloud_view']['reading_is_stale']
        page.locator('#cloud-select').click()
        page.wait_for_function('!pending&&!appState.cloud_view.reading_is_stale')
        s=wait(confirmed);point=s['cloud_view']['reading']
        assert lua('return {p=openspace.propertyValue("Scene.C2CloudSelection.Translation.Position")}')['p']==point['position_m']
        page.locator('#cloud-export-positions').click();page.wait_for_function('!pending&&document.getElementById("notice").textContent.includes("posições SI exportadas em:")')
        exported=page.locator('#notice').inner_text().split(' em: ',1)[-1]
        positions_export=json.loads(Path(exported).read_text(encoding='utf-8'))
        assert len(positions_export['positions_m'])==10000
        assert positions_export['metadata']['time_model']==point['time_model']
        assert positions_export['positions_m'][9999]==point['position_m']
        assert positions_export['particle_mass_kg']==0 and positions_export['source_si']['mass_kg']>0
        print('live evolution/stale reading/selection/focus/SI exports',flush=True)
        before=s['physics']
        try:
            command({'command':'select_cloud_particle','system_id':before['system_id'],'edit_token':'0'*32,
                'cloud_id':cloud,'index':9999})
        except urllib.error.HTTPError as e:assert e.code==400
        else:raise AssertionError('Accepted stale identity')
        assert state()['physics']['revision']==before['revision']
        page.locator('#save').click();page.wait_for_function('!pending&&appState.checkpoint_available',timeout=40000)
        saved_time=state()['physics']['time'];saved_position=point['position_m']
        command({'command':'reset','count':32});assert state()['physics']['test_particle_cloud'] is None
        page.locator('#load').click()
        page.wait_for_function('!pending&&appState.physics.test_particle_cloud?.test_particles===10000',timeout=60000)
        s=wait(confirmed);assert s['physics']['time']==saved_time
        assert s['physics']['edit_token']!=before['edit_token']
        assert s['physics']['test_particle_cloud']['cloud_id']==cloud
        page.locator('#cloud-select').click();page.wait_for_function('!pending&&appState.cloud_view.reading!==null')
        assert state()['cloud_view']['reading']['position_m']==saved_position
        page.locator('#lab-home').click()
        time.sleep(.5)
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),
            '-Name','cosmos2-cloud-product-candidate.png'],check=True,capture_output=True)
        final=state()
        page.locator('#atlas').click();page.wait_for_function('!pending&&appState.mode==="atlas"')
        assert lua('return {cloud=openspace.hasSceneGraphNode("C2CloudStream"),selection=openspace.hasSceneGraphNode("C2CloudSelection")}')=={'cloud':False,'selection':False}
        page.locator('#experiment').click();page.wait_for_function('!pending&&appState.mode==="experiment"',timeout=60000)
        assert wait(confirmed)['physics']['test_particle_cloud']['cloud_id']==cloud
        print('save/load/reset/atlas/reenter',flush=True)
        assert not errors,errors
        results={'status':'isolated_10k_CEF_Laboratory_worker_native_journey_verified_not_installed',
            'active_sources':1,'test_particles':10000,'created_through_CEF':True,
            'native_confirmed_SI_selection_exact':True,'individual_camera_focus':True,
            'live_position_anchor_moves':True,'frozen_reading_marked_stale':True,
            'remeasure_at_confirmed_instant':True,'stale_identity_refused':True,
            'export_all_10000_confirmed_SI_positions_exact':True,'export_frozen_reading_preserves_stale_flag':True,
            'save_reset_load_same_cloud_phase_and_new_edit_token':True,
            'atlas_clears_cloud_and_reenter_restores':True,'javascript_errors':errors,
            'final_reading':final['cloud_view']['reading'],'native_receipt':final['cloud_view']['native'],
            'owner_pointer_preserved':pointer.read_bytes()==original,
            'session':session,'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [ROOT/'output/c211-cloud-product/app/laboratory.py',ROOT/'output/c211-cloud-product/app/cloud_bridge.py',
                    ROOT/'output/c211-cloud-product/app/ui/test-cloud.js']},
            'scope':'Candidate integration only. Formal10k frame/memory/pause profile and promotion remain pending.'}
        (ROOT/'evidence/cloud-product-candidate-check.json').write_text(json.dumps(results,indent=2)+'\n')
        print(json.dumps({k:v for k,v in results.items() if k not in ('native_receipt','final_reading','session','source_sha256')},indent=2),flush=True)
finally:
    ws.close()
    assert pointer.read_bytes()==original
