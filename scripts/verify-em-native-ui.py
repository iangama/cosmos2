"""Drive the isolated worker UI inside the existing native OpenSpace CEF."""
from pathlib import Path
import hashlib
import json
import subprocess
import time
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes();errors=[];cases=[]
with Page() as page:
    previous=page.evaluate('location.href');page.on('pageerror',lambda e:errors.append(e))
    def go(url):
        page.call('Page.navigate',{'url':url});page.wait_for_function('location.href==='+json.dumps(url)+'&&document.readyState==="complete"')
    def idle(expression='true'):page.wait_for_function('!pending&&('+expression+')',timeout=30000)
    def preset(name):
        old=page.evaluate('state.system_id')
        page.locator('#preset').select_option(name);page.locator('#load-preset').click()
        idle('state.system_id!=='+json.dumps(old))
    try:
        go('http://127.0.0.1:4716/');page.wait_for_function('typeof state!=="undefined"&&state')
        for name in ('electric','helix','crossed','dipole','coulomb'):
            preset(name);page.locator('#measure').click();idle('map!==null')
            m=page.evaluate('map');s=page.evaluate('state')
            assert len(m['samples'])==97 and m['time_s']==s['time_s'] and m['edit_token']==s['edit_token']
            assert page.evaluate('state.paused')
            assert page.evaluate('arrows.length')>0
            cases.append({'preset':name,'measured_samples':97,'confirmed_worker_time_and_identity':True})
        preset('crossed');page.locator('#measure').click();idle('map!==null')
        before=page.evaluate('state.experiment');counts=[]
        for e,b in ((True,True),(False,True),(True,False),(False,False),(True,True)):
            page.locator('#visible-e').set_checked(e);idle('state.editor.visual.electric_visible==='+str(e).lower())
            page.locator('#visible-b').set_checked(b)
            idle('state.editor.visual.electric_visible==='+str(e).lower()+'&&state.editor.visual.magnetic_visible==='+str(b).lower())
            count=page.evaluate('arrows.length');counts.append({'E':e,'B':b,'arrows':count})
            assert count==97*(int(e)+int(b))
            assert page.evaluate('state.experiment')==before
        a=page.evaluate('arrows.find(a=>a.x>30&&a.y>30&&a.x<canvas.clientWidth-30&&a.y<canvas.clientHeight-30)')
        rect=page.evaluate('(()=>{const r=canvas.getBoundingClientRect();return {x:r.x,y:r.y}})()')
        for kind in ('mousePressed','mouseReleased'):
            page.call('Input.dispatchMouseEvent',{'type':kind,'x':rect['x']+a['x'],'y':rect['y']+a['y'],'button':'left','clickCount':1})
        assert 'V/m' in page.locator('#reading').inner_text() and 'T' in page.locator('#reading').inner_text()
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-em-prototype-fields.png'],check=True,capture_output=True)
        page.locator('#save').click();idle();saved=page.evaluate('state.experiment')
        start=page.evaluate('state.time_s');page.locator('#play').click();idle('!state.paused');page.wait_for_function('state.time_s>'+str(start+.05))
        page.locator('#play').click();idle('state.paused')
        assert 'MAPA CONGELADO' in page.locator('#map-state').inner_text()
        page.locator('#restore').click();idle('state.time_s==='+str(start))
        assert page.evaluate('state.experiment')==saved
        assert page.evaluate('map===null'),'Restored identity must clear the old map'
        page.locator('#measure').click();idle('map!==null')
        page.locator('#acting-e').set_checked(False);idle('!state.experiment.controls.electric_acting')
        assert page.evaluate('state.experiment.phase')==saved['phase']
        page.locator('#acting-e').set_checked(True);idle('state.experiment.controls.electric_acting')
        assert not errors,errors
        assert owner.read_bytes()==original
        report={'status':'isolated_EM_worker_UI_verified_in_actual_native_CEF_not_installed',
            'cases':cases,'separate_E_B_visibility_counts':counts,'visibility_preserves_physical_state':True,
            'same_worker_sample_SI_inspector':True,'live_evolution_marks_map_stale':True,
            'save_evolve_restore_exact_phase':True,'restored_identity_clears_stale_map':True,
            'physical_E_control_preserves_phase':True,'javascript_errors':errors,'owner_pointer_preserved':True,
            'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'output/c212-em-staging/ui/server.py',ROOT/'output/c212-em-staging/ui/index.html',ROOT/'output/c212-em-staging/ui/app.js',ROOT/'output/c212-em-staging/ui/style.css',Path(__file__))},
            'scope':'Standalone experimental server4716, real worker and canvas3D in OpenSpace CEF. This regression covers the original five-preset journey; source editor has a separate receipt. No native scene graph, product integration or body-associated field acceptance.'}
        (ROOT/'evidence/em-native-ui-check.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    finally:go(previous)
