"""Native composition controls, display-only interventions and image evidence."""
from pathlib import Path
import json
import math
import runpy
import subprocess
import time
import urllib.request
import numpy as np
from cef_page import Page
ROOT=Path(__file__).resolve().parents[1];BASE='http://127.0.0.1:4700';errors=[];cases=[]
execute=runpy.run_path(str(ROOT/'scripts/engine-command.py'))['execute']
def get(path):return json.load(urllib.request.urlopen(BASE+'/api/'+path,timeout=15))
def settled(p):p.wait_for_function('!navigationBusy');time.sleep(.2)
def capture(p,target,preset):
    p.evaluate('document.getElementById("atlas-panel").scrollTop=0;document.getElementById("atlas-details").scrollTop=0')
    name=f'cosmos2-visual-{target.lower()}-{preset}.png'
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',name],check=True,capture_output=True)
    return 'evidence/'+name
before=get('atlas/state');physics=get('state')['physics'];initial_display=get('navigation/display')
with Page() as p:
    p.on('pageerror',lambda e:errors.append(str(e)))
    p.goto(BASE+'/');p.wait_for_function('navigationState!==null&&atlasState!==null');p.locator('#ui-scale').select_option('1')
    try:
        for target in ['Earth','Moon','Saturn']:
            p.locator('[data-target="'+target+'"]').click()
            if not p.evaluate('document.getElementById("visual-controls").open'):p.locator('#visual-controls summary').click()
            for preset in ['overview','terminator','polar','detail']:
                p.locator('[data-viewpoint="'+preset+'"]').click();settled(p);s=get('navigation/state')
                assert s['navigation']['Anchor']==target and s['paused'] and s['et']==before['epoch']['et_tdb_s']
                d=np.array(s['positions']['Sun'])-s['positions'][target];position=np.array(s['navigation']['Position']);sun_cos=float(np.dot(d,position)/(np.linalg.norm(d)*np.linalg.norm(position)))
                if preset=='terminator':assert abs(sun_cos-math.cos(math.radians(75)))<1e-10
                cases.append({'target':target,'preset':preset,'distance_center_m':float(np.linalg.norm(position)),'camera_sun_cosine':sun_cos,'image':capture(p,target,preset)})
            assert 'Sem' in p.locator('#content-limit').inner_text() or 'sem' in p.locator('#content-limit').inner_text()
        # Display changes touch no ephemeris, physical state or pose.
        camera=get('navigation/state')['camera'];p.evaluate('document.getElementById("visual-exposure").value="1.5";document.getElementById("visual-exposure").dispatchEvent(new Event("change",{bubbles:true}))');settled(p)
        assert abs(get('navigation/display')['exposure']-1.5)<1e-6
        p.locator('#visual-sky').set_checked(False);settled(p);assert get('navigation/display')['stars'] is False
        state=get('navigation/state');assert np.max(np.abs(np.array(state['camera']['position_render_m'])-camera['position_render_m']))<.01
        assert get('atlas/state')['bodies']==before['bodies'] and get('atlas/state')['epoch']==before['epoch'];assert get('state')['physics']==physics
        cases.append({'image':capture(p,'Saturn','sky-off'),'exposure':1.5,'stars':False})
        # Source record matches the active map, not the inactive NASA candidate.
        p.locator('#open-content').click();p.wait_for_function('contentAtlas!==null');p.locator('#reference-body').select_option('699')
        p.locator('[data-property-id="texture"] summary').click()
        assert 'saturn-openspace.jpg' in p.locator('[data-property-id="texture"]').inner_text();assert 'não confirmadas' in p.locator('[data-property-id="texture"]').inner_text()
        assert not errors,errors
    finally:
        p.goto(BASE+'/');p.wait_for_function('navigationState!==null')
        p.evaluate('document.getElementById("visual-exposure").value='+str(initial_display['exposure'])+';document.getElementById("visual-sky").checked='+str(initial_display['stars']).lower()+';applyDisplay()');settled(p)
        p.locator('[data-target="Earth"]').click();p.locator('#visual-controls summary').click();p.locator('[data-viewpoint="overview"]').click();settled(p)
report={'browser':'native OpenSpace CEF','cases':cases,'terminator_solar_angle_verified':True,'display_controls_preserve_camera_epoch_bodies_worker':True,'active_map_source_matches_renderer':True,'page_errors':errors,'scope':'UI/native configuration and image evidence. Visual acceptance requires review; no claim of observed photometry, terrain or particle rings.'}
(ROOT/'evidence/visual-controls-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
