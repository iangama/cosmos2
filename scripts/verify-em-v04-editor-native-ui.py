"""Source editor journey through actual native CEF controls and downloaded SI JSON."""
from pathlib import Path
import hashlib
import json
import math
import subprocess
import sys
import urllib.request
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1];V04='--v04' in sys.argv;CANDIDATE='--candidate' in sys.argv or V04
PRODUCT=ROOT/('output/c212-em-v04-product' if V04 else 'output/c212-em-product')
STAGE=PRODUCT/'em' if CANDIDATE else ROOT/'output/c212-em-staging';sys.path.insert(0,str(STAGE))
BASE='http://127.0.0.1:'+('4700' if CANDIDATE else '4716')
from em_experiment import generation
from em_fields import K_E,MU_0
owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes();errors=[];cases=[]
def product_hashes():return {str(p.relative_to(ROOT/'app')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
product=product_hashes()
with Page() as page:
    previous=page.evaluate('location.href');page.on('pageerror',lambda e:errors.append(e))
    def go(url):
        page.call('Page.navigate',{'url':url});page.wait_for_function('location.href==='+json.dumps(url)+'&&document.readyState==="complete"')
    def idle(expression='true'):page.wait_for_function('!pending&&('+expression+')',timeout=30000)
    def fill(name,value):
        page.evaluate('(()=>{const e=document.getElementById('+json.dumps(name)+');e.focus();e.value="";})()')
        page.call('Input.insertText',{'text':str(value)})
        assert page.evaluate('document.getElementById('+json.dumps(name)+').valueAsNumber' if name!='source-id' else 'document.getElementById("source-id").value')==(float(value) if name!='source-id' else value)
    def fields(values):
        for name,value in values.items():fill(name,value)
    def preset(name):
        old=page.evaluate('state.system_id');page.locator('#preset').select_option(name);page.locator('#load-preset').click();idle('state.system_id!=='+json.dumps(old))
    def select(sid):
        page.locator('#source-select').select_option(sid or '');idle('state.editor.visual.selected_id==='+json.dumps(sid))
    def create(sid,values):
        select(None);fill('source-id',sid);fields(values);page.locator('#apply-source').click();idle('state.editor.visual.selected_id==='+json.dumps(sid))
    try:
        go(BASE+('/em.html' if CANDIDATE else '/'));page.wait_for_function('typeof state!=="undefined"&&state')
        if CANDIDATE:
            page.wait_for_function('!pending&&nativeState?.confirmation?.state==="accepted"')
            page.locator('#native-toggle').click()
        assert page.evaluate('state.scientific_generation')==generation()
        preset('crossed');phase=page.evaluate('state.experiment.phase')
        create('cef-positive',{'source-x':-2,'source-y':1,'source-z':.5,'source-charge':1e-11})
        create('cef-negative',{'source-x':2,'source-y':-1,'source-z':1,'source-charge':-2e-11})
        assert page.evaluate('state.experiment.phase')==phase
        assert page.evaluate('Object.values(state.editor.origins).every(v=>v==="user_model")')
        page.locator('#measure').click();idle('map!==null');map_before=page.evaluate('map')
        old_revision=page.evaluate('state.revision');fields({'source-charge':-3e-11,'source-x':2.5});page.locator('#apply-source').click();idle('state.revision==='+str(old_revision+1))
        assert page.evaluate('state.experiment.phase')==phase and page.evaluate('map')==map_before
        assert 'MAPA CONGELADO' in page.locator('#map-state').inner_text()
        assert page.evaluate('state.editor.reference.physics_revision===state.revision')
        page.locator('#probe').click();idle();assert 'Sonda confirmada' in page.locator('#reading').inner_text()
        page.locator('#export').click();idle('lastExport!==null&&lastArtifact!==null')
        exported=page.evaluate('lastExport');artifact=page.evaluate('lastArtifact')
        raw=urllib.request.urlopen(BASE+artifact['url'],timeout=5).read()
        assert hashlib.sha256(raw).hexdigest()==artifact['sha256'] and len(raw)==artifact['bytes'] and json.loads(raw)==exported
        assert exported['experiment']==page.evaluate('state.experiment') and exported['editor']==page.evaluate('state.editor')
        assert exported['time_s']==page.evaluate('state.time_s') and exported['revision']==page.evaluate('state.revision')
        x=exported['sample']['position_m'];expected=list(exported['experiment']['model']['uniform_E_V_m'])
        for source in exported['experiment']['model']['sources']:
            r=[a-b for a,b in zip(x,source['position_m'])];distance=math.sqrt(sum(a*a for a in r))
            expected=[e+K_E*source['charge_C']*v/distance**3 for e,v in zip(expected,r)]
        assert max(abs(a-b) for a,b in zip(expected,exported['sample']['electric_field_V_m']))<1e-12
        cases.append('create two asymmetric signed sources, edit without phase change, frozen old map, probe and actual SI export artifact')
        # Refuse a complete candidate whose source covers the moving particle.
        before=page.evaluate('({experiment:state.experiment,editor:state.editor,revision:state.revision})')
        fields({'source-x':phase['position_m'][0],'source-y':phase['position_m'][1],'source-z':phase['position_m'][2]})
        page.locator('#apply-source').click();idle();assert page.evaluate('({experiment:state.experiment,editor:state.editor,revision:state.revision})')==before
        assert 'domain' in page.locator('#status').inner_text().lower()
        # Restore valid draft before capture; loading selection rebuilds from confirmed state.
        select(None);select('cef-negative');page.locator('#measure').click();idle('map!==null')
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-em-source-editor'+('-v04' if V04 else '-candidate' if CANDIDATE else '')+'.png'],check=True,capture_output=True)
        cases.append('invalid source covering particle refused atomically through visible apply control')
        # Session includes source selection, E/B visibility, maps and all physical interventions.
        page.locator('#visible-e').set_checked(False);idle('!state.editor.visual.electric_visible')
        page.evaluate('document.querySelector("#map-form").parentElement.open=true')
        fields({'map-radius':4,'map-cut':.4});page.locator('#apply-map').click();idle('state.editor.visual.map_radius_m===4')
        page.locator('#save').click();idle();saved=page.evaluate('({experiment:state.experiment,editor:state.editor})')
        page.locator('#play').click();idle('!state.paused');start=page.evaluate('state.time_s')
        page.locator('#visible-b').set_checked(False);idle('!state.editor.visual.magnetic_visible')
        assert not page.evaluate('state.paused')
        page.wait_for_function('state.time_s>'+str(start+.03));page.locator('#play').click();idle('state.paused')
        page.locator('#restore').click();idle('state.time_s==='+str(saved['experiment']['phase']['time_s']))
        assert page.evaluate('({experiment:state.experiment,editor:state.editor})')==saved
        assert page.evaluate('!document.querySelector("#visible-e").checked&&document.querySelector("#visible-b").checked')
        assert page.evaluate('document.querySelector("#source-select").value')=='cef-negative'
        page.locator('#remove-source').click();idle('state.editor.visual.selected_id===null')
        assert page.evaluate('state.experiment.model.sources.length')==1 and page.evaluate('document.querySelector("#source-select").value')==''
        cases.append('running visibility keeps evolving; save/evolve/restore retains sources/history/selection/map and deletion clears identity')
        preset('dipole');select('synthetic-dipole')
        fields({'source-mx':2e5,'source-my':-1e5,'source-mz':3e5,'source-x':.2,'source-y':-.1,'source-z':.3})
        rev=page.evaluate('state.revision');page.locator('#apply-source').click();idle('state.revision==='+str(rev+1))
        page.locator('#export').click();idle('lastExport!==null');dipole=page.evaluate('lastExport')
        source=dipole['experiment']['model']['sources'][0];r=[a-b for a,b in zip(dipole['sample']['position_m'],source['position_m'])];length=math.sqrt(sum(v*v for v in r));dot=sum(a*b for a,b in zip(source['magnetic_moment_A_m2'],r))
        expected=[MU_0/(4*math.pi)*(3*dot*v/length**5-m/length**3) for v,m in zip(r,source['magnetic_moment_A_m2'])]
        assert max(abs(a-b) for a,b in zip(expected,dipole['sample']['magnetic_field_T']))<1e-14
        page.evaluate('document.getElementById("background-editor").open=true')
        fields({'background-ex':.05,'background-ey':-.02,'background-ez':.03,'background-bx':.01,'background-by':.02,'background-bz':.03})
        rev=page.evaluate('state.revision');phase=page.evaluate('state.experiment.phase');page.locator('#apply-background').click();idle('state.revision==='+str(rev+1))
        assert page.evaluate('state.experiment.phase')==phase
        cases.append('translate and rotate magnetic dipole with independently checked 3D B; change uniform E/B and preserve synchronized phase')
        preset('coulomb');create('cef-third',{'source-x':3,'source-y':2,'source-z':1,'source-charge':1e-7,'source-mass':2,'source-vx':.1,'source-vy':-.2,'source-vz':.3})
        fields({'source-charge':-1e-7,'source-mass':3});rev=page.evaluate('state.revision');page.locator('#apply-source').click();idle('state.revision==='+str(rev+1))
        assert page.evaluate('state.experiment.system.mass_kg[2]')==3
        page.locator('#remove-source').click();idle('state.experiment.system.ids.length===2')
        cases.append('create/edit/remove active charge including mass, position and velocity in mutual mode')
        assert not errors,errors;assert owner.read_bytes()==original;assert product_hashes()==product
        report={'status':'isolated_EM_source_editor_journey_verified_in_actual_native_CEF','cases':cases,
                'downloaded_export_sha256':artifact['sha256'],'downloaded_export_bytes':artifact['bytes'],
                'javascript_errors':errors,'installed_product_files_preserved':len(product),'owner_pointer_preserved':True,
                'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (*STAGE.glob('*.py'),*STAGE.glob('ui/*'),*((PRODUCT/'app').rglob('*') if CANDIDATE else []),Path(__file__)) if p.is_file() and '__pycache__' not in p.parts},
                'scope':'Candidate product server4700 and experimental EM editor' if CANDIDATE else 'Experimental canvas3D in native CEF, server4716 and real worker. Export artifact served and verified; OS download directory is not asserted. Formal native frame/rate profile has separate acceptance.'}
        (ROOT/'evidence'/('em-v04-editor-candidate-ui-check.json' if V04 else 'em-editor-candidate-ui-check.json' if CANDIDATE else 'em-editor-native-ui-check.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    finally:go(previous)
