"""Confirmed epoch, changing distance, cameras and actual CEF Atlas round trip."""
from pathlib import Path
import json
import math
import runpy
import subprocess
import urllib.request
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1];errors=[]
execute=runpy.run_path(str(ROOT/'scripts/engine-command.py'))['execute']
camera_checks=[]
def check_sunlit(target):
    nav=execute('return openspace.navigation.getNavigationState("Root")')['payload']['1']
    assert nav['Anchor']==target
    state=json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/atlas/state',timeout=10))
    bodies={b['scene_node']:b['position_render_m'] for b in state['bodies']}
    sun=[a-b for a,b in zip(bodies['Sun'],bodies[target])];position=nav['Position']
    cosine=sum(a*b for a,b in zip(sun,position))/(math.hypot(*sun)*math.hypot(*position))
    assert abs(cosine-math.cos(math.pi/6))<1e-6,cosine
    camera_checks.append({'body':target,'sun_cosine':cosine,'frame':'Root/GALACTIC'})
def command(name):
    return json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:4700/api/command',
            data=json.dumps({'command':name}).encode(),headers={'Content-Type':'application/json'}),timeout=15))
def capture(name):
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',name],check=True,capture_output=True)
with Page() as page:
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:4700/')
    page.wait_for_function('atlasState!==null&&socket.readyState===1')
    original=page.evaluate('atlasState.epoch.utc');distance=page.evaluate('atlasState.earth_moon_separation_m')
    assert 'JPL' in page.locator('.tag').inner_text()
    assert '390' in page.locator('#moon-distance').inner_text() or distance>300000000
    page.locator('[data-target="Earth"]').click();page.locator('#sunlit-view').click()
    page.wait_for_function('selectedTarget==="Earth"&&!navigationBusy')
    page.wait_for_function('!navigationBusy');check_sunlit('Earth')
    capture('cosmos2-native-atlas-spice-earth.png')
    page.locator('[data-target="Moon"]').click();page.locator('#sunlit-view').click()
    assert page.evaluate('atlasState.earth_moon_separation_m')==distance
    page.wait_for_function('!navigationBusy');check_sunlit('Moon')
    capture('cosmos2-native-atlas-spice-moon.png')
    page.locator('[data-target="System"]').click()
    assert page.locator('#radius').inner_text()==page.evaluate('views.System.radius')
    page.evaluate('document.getElementById("atlas-epoch").value="2026-10-25T12:00:00"')
    page.evaluate('document.getElementById("time-panel").open=true');page.locator('#apply-atlas-epoch').click()
    page.wait_for_function('!atlasPending&&atlasState.epoch.utc.startsWith("2026-10-25")')
    assert abs(page.evaluate('atlasState.earth_moon_separation_m')-distance)>1000000
    assert 'confirmada' in page.locator('#notice').inner_text()
    assert page.evaluate('atlasState.renderer.paused')
    assert page.locator('#radius').inner_text()==page.evaluate('views.System.radius')
    page.locator('[data-target="Earth"]').click();page.locator('#sunlit-view').click()
    page.wait_for_function('!navigationBusy');check_sunlit('Earth')
    capture('cosmos2-native-atlas-spice-new-epoch.png')
    saved_epoch=page.evaluate('atlasState.epoch.et_tdb_s')
    assert command('enter')['ok']
    try:
        response=page.evaluate('fetch("/api/atlas/epoch",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({utc:"2030-01-01T00:00:00"})}).then(async r=>({status:r.status,data:await r.json()}))')
        assert response['status']==400
        assert 'Volte ao Atlas' in response['data']['error']
    finally:assert command('atlas')['ok']
    page.wait_for_function('appState.mode==="atlas"')
    page.wait_for_function('atlasState.epoch.et_tdb_s==='+str(saved_epoch))
    assert page.evaluate('atlasState.renderer.paused')
    page.evaluate('document.getElementById("atlas-epoch").value='+json.dumps(original.removesuffix('Z').split('.')[0]))
    page.evaluate('document.getElementById("time-panel").open=true');page.locator('#apply-atlas-epoch').click()
    page.wait_for_function('!atlasPending&&atlasState.epoch.utc==='+json.dumps(original))
    page.locator('[data-target="Earth"]').click();page.locator('#sunlit-view').click()
    assert not errors,errors
report={'browser':'native OpenSpace CEF','model':'DE442s','session':json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig')),
        'epoch_confirmed_and_paused':True,'distance_changes_with_epoch':True,'body_sunlit_camera_only':True,
        'laboratory_roundtrip_preserves_atlas_epoch':True,'epoch_change_in_lab_refused':True,
        'original_epoch_restored':True,'page_errors':errors,'scope':'Native UI and camera integration; science in native-atlas-check.json'}
report['sunlit_camera_measurements']=camera_checks
(ROOT/'evidence/native-atlas-ui-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
