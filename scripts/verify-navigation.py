"""Native CEF journey and camera/clock/favorite invariants, including rejection paths."""
from pathlib import Path
import copy
import ctypes
import hashlib
import json
import math
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
import numpy as np
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from navigation import Navigation, pose, valid_state, occluded
from atlas import Atlas
BASE='http://127.0.0.1:4700';errors=[];measurements=[]
def get(path):return json.load(urllib.request.urlopen(BASE+'/api/'+path,timeout=15))
def post(path,body):return json.load(urllib.request.urlopen(urllib.request.Request(BASE+'/api/'+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'}),timeout=15))
def settled(page):page.wait_for_function('!navigationBusy&&navigationState!==null');time.sleep(.15)
def capture(label):subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-native-navigation-'+label+'.png'],check=True,capture_output=True)
def fill(page,id,value):page.evaluate('document.getElementById('+json.dumps(id)+').value='+json.dumps(value)+';document.getElementById('+json.dumps(id)+').dispatchEvent(new Event("input",{bubbles:true}))')
def close_position(a,b,tol=.001):assert np.max(np.abs(np.array(a)-b))<=tol,(a,b)
original=get('atlas/state')['epoch']['utc'];before_physics=get('state')['physics']
# Independent opaque-body ray cases include a clear and an occulted target.
identity={str(i+1):float(v) for i,v in enumerate(np.eye(3).ravel(order='F'))}
positions={'Earth':[0,0,0],'Moon':[1e8,0,0],'Saturn':[0,1e12,0]};rotations={k:identity for k in positions}
assert 'Moon' in occluded([-3e7,0,0],positions,rotations)
assert 'Earth' not in occluded([-3e7,0,0],positions,rotations)
positions['Earth']=[0,2e7,0];assert 'Moon' not in occluded([-3e7,0,0],positions,rotations)
created=[]
with Page() as page:
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE+'/');page.wait_for_function('navigationState!==null&&atlasState!==null');page.locator('#ui-scale').select_option('1')
    try:
        # Selection and filter never move camera or change epoch.
        start=get('navigation/state');fill(page,'search','saturno');time.sleep(.1)
        assert page.evaluate('[...document.querySelectorAll("#destinations button:not([hidden])")].map(b=>b.dataset.target)')==['Saturn']
        page.locator('[data-target="Saturn"]').click();settled(page)
        close_position(get('navigation/state')['camera']['position_render_m'],start['camera']['position_render_m'])
        assert get('atlas/state')['epoch']['utc']==original
        fill(page,'search','');page.locator('#type-filter').select_option('moon')
        assert page.evaluate('[...document.querySelectorAll("#destinations button:not([hidden])")].map(b=>b.dataset.target)')==['Moon']
        page.locator('#type-filter').select_option('all');page.locator('#distance-sort').select_option('nearest')
        assert page.evaluate('document.querySelector("#destinations button").dataset.target') in ['Moon','Earth']
        page.locator('#distance-sort').select_option('system')
        page.locator('#smooth-flight').set_checked(False)
        journey=[]
        for target in ['Earth','Moon','Saturn']:
            page.locator('[data-target="'+target+'"]').click();page.locator('#visit-target').click();settled(page)
            page.wait_for_function('navigationState.navigation.Anchor==='+json.dumps(target))
            s=get('navigation/state');expected=page.evaluate('views['+json.dumps(target)+'].position');close_position(s['navigation']['Position'],expected,.01)
            journey.append(target);measurements.append({'target':target,'native_navigation':s['navigation']})
        page.locator('[data-scene-target="Saturn"]').click();assert page.evaluate('selectedTarget')=='Saturn'
        page.locator('#nearby-filter').select_option('1e9')
        assert page.evaluate('[...document.querySelectorAll("#destinations button:not([hidden])")].map(b=>b.dataset.target)')==['Saturn']
        page.locator('#nearby-filter').select_option('0');page.locator('#system-tree summary').click();tree_before=get('navigation/state');page.locator('[data-tree-target="Moon"]').click();assert page.evaluate('selectedTarget')=='Moon';close_position(get('navigation/state')['camera']['position_render_m'],tree_before['camera']['position_render_m'],.01);page.locator('[data-tree-target="Saturn"]').click()
        page.locator('#favorites-panel summary').click();fill(page,'favorite-name','Teste C2-02 · Saturno');page.locator('#save-favorite').click();settled(page)
        rows=get('navigation/favorites')['views'];row=next(r for r in rows if r['name']=='Teste C2-02 · Saturno');created.append(row['id']);saved=get('navigation/state')
        page.locator('[data-target="Earth"]').click();page.locator('#visit-target').click();settled(page)
        page.locator('[data-favorite-id="'+row['id']+'"]').click();settled(page);restored=get('navigation/state')
        assert restored['navigation']['Anchor']=='Saturn';close_position(restored['camera']['position_render_m'],saved['camera']['position_render_m'],.01);assert restored['et']==saved['et'];journey.append('favorite:Saturn')
        # Follow only changes mode, with fixed epoch and pose; free has independent anchor.
        for mode in ['follow','orbit','free']:
            previous=get('navigation/state');page.locator('#camera-mode').select_option(mode);settled(page);current=get('navigation/state')
            close_position(current['camera']['position_render_m'],previous['camera']['position_render_m'],.01)
            assert np.linalg.norm(np.array(current['camera']['forward'])-previous['camera']['forward'])<1e-9
            assert current['et']==previous['et']
        free_start=get('navigation/state')
        page.evaluate('document.getElementById("camera-mode").focus()')
        page.call('Input.dispatchKeyEvent',{'type':'keyDown','key':'w','code':'KeyW','windowsVirtualKeyCode':87});time.sleep(.35);page.call('Input.dispatchKeyEvent',{'type':'keyUp','key':'w','code':'KeyW','windowsVirtualKeyCode':87});time.sleep(.15)
        # The select retains focus, so WASD must be ignored there.
        close_position(get('navigation/state')['camera']['position_render_m'],free_start['camera']['position_render_m'],.01)
        page.evaluate('document.activeElement.blur()')
        page.call('Input.dispatchKeyEvent',{'type':'keyDown','key':'w','code':'KeyW','windowsVirtualKeyCode':87});time.sleep(.35);page.call('Input.dispatchKeyEvent',{'type':'keyUp','key':'w','code':'KeyW','windowsVirtualKeyCode':87});time.sleep(.15)
        assert np.linalg.norm(np.array(get('navigation/state')['camera']['position_render_m'])-free_start['camera']['position_render_m'])>1e5
        # Look and move in a known discrete step checks translation against the camera basis.
        post('navigation/move',{'translation':[1,0,0],'look':[.13,-.08,0],'speed':1e7,'dt':.1});time.sleep(.1)
        free_look=get('navigation/state');assert np.linalg.norm(np.array(free_look['camera']['forward'])-free_start['camera']['forward'])>.05
        free_rows=post('navigation/save',{'name':'Teste C2-02 · voo livre'})['navigation']['views'];free_row=free_rows[-1];created.append(free_row['id'])
        post('navigation/move',{'translation':[0,1,0],'look':[-.1,.1,0],'speed':1e7,'dt':.1});time.sleep(.1);post('navigation/restore',{'id':free_row['id']});time.sleep(.1)
        free_restored=get('navigation/state');close_position(free_restored['camera']['position_render_m'],free_look['camera']['position_render_m'],.01);assert np.linalg.norm(np.array(free_restored['camera']['forward'])-free_look['camera']['forward'])<1e-8
        page.locator('#camera-mode').select_option('orbit');settled(page);orbit=get('navigation/state')
        close_position(orbit['camera']['position_render_m'],free_look['camera']['position_render_m'],.01)
        assert np.linalg.norm(np.array(orbit['camera']['forward'])-free_look['camera']['forward'])<1e-8
        # Native OS key events, including app shortcuts while a text input has focus.
        page.locator('#search').click();focused=get('navigation/state')
        user=ctypes.windll.user32;session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
        enum=ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
        def activate(hwnd,_):
            pid=ctypes.c_ulong();user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
            if pid.value==session['app'] and user.IsWindowVisible(hwnd):user.SetForegroundWindow(hwnd)
            return True
        user.EnumWindows(enum(activate),0)
        for code in [71,70,32,37,39]:user.keybd_event(code,0,0,0);time.sleep(.025);user.keybd_event(code,0,2,0)
        time.sleep(.3);after_keys=get('navigation/state');close_position(after_keys['camera']['position_render_m'],focused['camera']['position_render_m'],.01);assert after_keys['et']==focused['et'] and after_keys['paused']
        fill(page,'search','')
        # Smooth travel and cancellation are native, then a full trip reaches its pose.
        page.locator('#smooth-flight').set_checked(True);page.locator('[data-target="Moon"]').click();page.locator('#visit-target').click();settled(page)
        page.wait_for_function('navigationState.flying');page.locator('#cancel-flight').click();settled(page);assert not get('navigation/state')['flying']
        page.locator('#visit-target').click();settled(page);page.wait_for_function('!navigationState.flying',timeout=15000);assert get('navigation/state')['navigation']['Anchor']=='Moon'
        # Bounded clock, forward/backward and both coverage stops.
        page.locator('#time-panel summary').click();page.locator('#atlas-rate').select_option('3600');settled(page);s=get('navigation/state');assert s['rate']==3600 and s['paused']
        page.locator('#atlas-pause').click();settled(page);time.sleep(.3);assert get('navigation/state')['et']>s['et']+100
        page.locator('#atlas-pause').click();settled(page);assert get('navigation/state')['paused']
        page.evaluate('document.getElementById("epoch-slider").value="2000.5";document.getElementById("epoch-slider").dispatchEvent(new Event("change",{bubbles:true}))');page.wait_for_function('!atlasPending&&atlasState.epoch.utc.startsWith("2000-")')
        for utc,rate in [('2050-12-31T23:59:59',86400),('1950-01-01T00:00:00',-86400)]:
            post('atlas/epoch',{'utc':utc});post('navigation/clock',{'rate':rate,'paused':False});time.sleep(.5);s=get('navigation/state');assert s['paused'] and s['boundary'];assert abs(s['et']-get('atlas/state')['epoch']['et_tdb_s'])<1e-6
        post('atlas/epoch',{'utc':original});post('navigation/clock',{'rate':1,'paused':True})
        # 150% still supports actual clicks and favorite restore.
        page.locator('#ui-scale').select_option('1.5');page.locator('[data-favorite-id="'+row['id']+'"]').click();settled(page);assert get('navigation/state')['navigation']['Anchor']=='Saturn';capture('150')
        page.locator('#ui-scale').select_option('1');page.evaluate('document.getElementById("atlas-panel").scrollTop=0');capture('saturn')
        page.goto(BASE+'/');page.wait_for_function('navigationState!==null');assert page.evaluate('selectedTarget')=='Saturn'
        assert not errors,errors
        # Corrupted or semantically invalid favorites fail before any native mutation.
        rejection=[]
        with tempfile.TemporaryDirectory() as folder:
            fake=Navigation(Atlas(),folder);item=copy.deepcopy(row);original_view=copy.deepcopy(item['view'])
            for kind in ['hash','frame','epoch','nan','zero_up','mode','target','rate','free_anchor']:
                item['view']=copy.deepcopy(original_view);v=item['view']
                if kind=='frame':v['navigation']['ReferenceFrame']='Earth'
                elif kind=='epoch':v['et']=1e30
                elif kind=='nan':v['navigation']['Position']=[float('nan'),0,0]
                elif kind=='zero_up':v['navigation']['Up']=[0,0,0]
                elif kind=='mode':v['mode']='free'
                elif kind=='target':v['target']='unknown'
                elif kind=='rate':v['rate']=float('inf')
                elif kind=='free_anchor':v['mode']='free';v['navigation']['Anchor']='CosmosFreeAnchor';v['free_anchor_render_m']=[1,2]
                if kind in ['nan','rate']:
                    # Sealing itself rejects non-finite fields, before file write.
                    try:fake._write([item])
                    except ValueError:rejection.append(kind);continue
                    raise AssertionError(kind)
                fake._write([item])
                if kind=='hash':payload=json.loads(fake.path.read_text());payload['payload']['views'][0]['name']='modified';fake.path.write_text(json.dumps(payload))
                before=get('navigation/state')
                try:fake.restore(item['id'])
                except (ValueError,KeyError):rejection.append(kind)
                else:raise AssertionError('Invalid favorite accepted: '+kind)
                after=get('navigation/state');close_position(after['camera']['position_render_m'],before['camera']['position_render_m'],.01);assert after['et']==before['et']
            fake.atlas.close()
        assert get('state')['physics']==before_physics
        report={'browser':'native OpenSpace CEF','journey':journey,'measurements':measurements,'source_selection_no_camera_mutation':True,'follow_free_preserve_pose_epoch':True,'free_translation_and_look':True,'editable_focus_ignores_WASD':True,'native_OS_typing_does_not_trigger_shortcuts':True,'smooth_travel_cancel_complete':True,'clock_forward_and_both_coverage_stops':True,'favorite_pose_epoch_persist_reload_150percent':True,'corrupt_favorites_rejected_before_mutation':rejection,'laboratory_state_unchanged':True,'page_errors':errors}
        (ROOT/'evidence/navigation-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    finally:
        for id in created:post('navigation/delete',{'id':id})
        post('atlas/epoch',{'utc':original});post('navigation/clock',{'rate':1,'paused':True});post('navigation/visit',{'target':'Earth','sunlit':True})
        page.locator('#ui-scale').select_option('1')
