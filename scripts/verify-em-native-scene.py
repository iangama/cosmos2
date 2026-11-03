"""Actual candidate native scene, SI mesh reconstruction and safe navigation cycles."""
from pathlib import Path
import hashlib
import json
import math
import subprocess
import sys
import time
import urllib.request
import numpy as np
from cef_page import Page
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parents[1];V03='--v03' in sys.argv;CANDIDATE=ROOT/('output/c212-em-v03-product' if V03 else 'output/c212-em-product')
sys.path.insert(0,str(CANDIDATE/'app'))
from em_native import normalize
owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes();errors=[];cases=[];geometry=[]
baseline=json.loads((ROOT/'evidence/c212-em-candidate-baseline.json').read_text())
launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'));assert launch['emCandidate']
def state():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/em/state',timeout=10))
ws=connect('ws://127.0.0.1:4682',open_timeout=3,close_timeout=.2,ping_interval=None);topic=0
ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
def native(code):
    global topic
    topic+=1;ws.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True}}))
    response=json.loads(ws.recv(timeout=5));assert response.get('topic')==topic,response
    value=response.get('payload',{}).get('1');assert isinstance(value,dict),response;return normalize(value)
def confirm_positions():
    value=state();s=value['state'];c=value['native']['confirmation'];assert c['state']=='accepted' and not value['native']['error']
    metadata={k:s[k] for k in ('system_id','edit_token','revision','sequence','time_s','frame')};assert c['metadata']==metadata
    ex=s['experiment'];phase=ex['phase'];expected={}
    if ex['mode']=='test_particle':
        expected={'source:'+row['id']:row['position_m'] for row in ex['model']['sources']};expected['test-particle']=phase['position_m']
    else:expected={'body:'+sid:x for sid,x in zip(ex['system']['ids'],phase['position_m'])}
    code='local positions={};'
    for identity in expected:
        node='C2EMBody_'+hashlib.sha256(identity.encode()).hexdigest()[:24]
        code+='positions['+json.dumps(identity)+']=openspace.propertyValue("Scene.'+node+'.Translation.Position");'
    actual=native(code+'return {positions=positions,metadata=__c2EMNativeStamp}')
    assert actual['metadata']==metadata
    for identity,x in expected.items():assert actual['positions'][identity]==[v*1e9 for v in x]
    return value
def mesh_geometry(value,ui_map):
    m=value['native']['map'];s=value['state'];assert m['sample_count']==97
    assert m['metadata']=={k:ui_map[k] for k in ('system_id','edit_token','revision','time_s','frame')}
    for mesh in m['meshes']:
        file=Path(mesh['file']);raw=file.read_bytes();assert hashlib.sha256(raw).hexdigest()==mesh['file_sha256']
        lines=raw.decode().splitlines();paths=[];i=0
        while i<len(lines):
            if lines[i].startswith('mesh '):
                count=int(lines[i+2]);assert count==5;paths.append(np.array([[float(v) for v in row.split()] for row in lines[i+3:i+3+count]]));i+=count+4
            else:i+=1
        assert len(paths)==mesh['arrow_count']==len(mesh['sample_indices'])
        radius=mesh['local_unit_model_m'];length=mesh['graphic_length_model_m'];maximum=0.
        for path,index in zip(paths,mesh['sample_indices']):
            sample=ui_map['samples'][index];assert sample['valid'];key='electric_field_V_m' if mesh['quantity']=='electric' else 'magnetic_field_T'
            expected=np.array(sample[key]);direction=expected/math.hypot(*expected);world=path*radius
            assert np.max(abs(world[0]-sample['position_m']))<=3e-14*radius
            assert np.max(abs(world[1]-world[0]-length*direction))<=3e-14*radius
            assert np.max(abs((world[2]+world[4])/2-(world[1]-.25*length*direction)))<=3e-14*radius
            assert np.max(abs(world[3]-world[1]))==0
            maximum=max(maximum,float(np.max(abs(path.astype(np.float32).astype(float)-path)))*radius)
        assert maximum==mesh['float32_vertex_component_error_model_m'] and maximum<=3e-7*radius
        actual=native('return {enabled=openspace.propertyValue("Scene.'+mesh['node']+'.Renderable.Enabled"),scale=openspace.propertyValue("Scene.'+mesh['node']+'.Scale.Scale")}')
        assert actual['scale']==radius*1e9 and actual['enabled']==s['editor']['visual'][mesh['quantity']+'_visible']
        geometry.append({'quantity':mesh['quantity'],'arrows':len(paths),'float32_max_component_error_model_m':maximum})

try:
    with Page() as page:
        previous=page.evaluate('location.href');page.on('pageerror',lambda e:errors.append(e))
        def idle(expression='true'):page.wait_for_function('!pending&&('+expression+')',timeout=30000)
        def root():
            page.call('Page.navigate',{'url':'http://127.0.0.1:4700/'});page.wait_for_function('typeof appState!=="undefined"&&appState!==null')
        def enter():
            page.locator('#em-lab').click();page.wait_for_function('location.pathname==="/em.html"&&typeof nativeState!=="undefined"&&nativeState?.confirmation?.state==="accepted"&&!pending',timeout=30000)
        def preset(name):
            old=page.evaluate('state.system_id');page.locator('#preset').select_option(name);page.locator('#load-preset').click();idle('state.system_id!=='+json.dumps(old))
        root();enter()
        assert page.evaluate('document.documentElement.classList.contains("native-view")')
        for name in ('electric','helix','crossed','dipole','coulomb'):
            preset(name);page.locator('#measure').click();idle('map!==null');value=confirm_positions();mesh_geometry(value,page.evaluate('map'))
            page.locator('#native-frame').click();idle()
            assert native('return {anchor=openspace.navigation.getNavigationState().Anchor}')['anchor']=='C2EMCamera'
            cases.append({'preset':name,'native_positions_from_independent_connection_exact':True,'SI_mesh_direction_reconstructed':True})
        preset('crossed');page.locator('#measure').click();idle('map!==null');physical=page.evaluate('state.experiment');counts=[]
        for e,b in ((True,True),(False,True),(True,False),(False,False),(True,True)):
            page.locator('#visible-e').set_checked(e);idle('state.editor.visual.electric_visible==='+str(e).lower())
            page.locator('#visible-b').set_checked(b);idle('state.editor.visual.magnetic_visible==='+str(b).lower())
            value=confirm_positions();shown=0
            for mesh in value['native']['map']['meshes']:
                enabled=native('return {enabled=openspace.propertyValue("Scene.'+mesh['node']+'.Renderable.Enabled")}')['enabled']
                assert enabled==(e if mesh['quantity']=='electric' else b);shown+=mesh['arrow_count']*enabled
            assert page.evaluate('state.experiment')==physical and shown==97*(int(e)+int(b));counts.append({'E':e,'B':b,'native_visible_arrows':shown})
        start=page.evaluate('state.time_s');map_metadata=state()['native']['map']['metadata'];page.locator('#play').click();idle('!state.paused')
        page.wait_for_function('nativeState.confirmation.metadata.time_s>'+str(start+.04));page.locator('#play').click();idle('state.paused');confirm_positions()
        assert state()['native']['map']['metadata']==map_metadata and 'MAPA CONGELADO' in page.locator('#map-state').inner_text()
        cases.append({'live_native_marker_updates':True,'frozen_map_stamp_retained':True})
        preset('dipole');page.locator('#source-select').select_option('synthetic-dipole');idle('state.editor.visual.selected_id==="synthetic-dipole"')
        before=page.evaluate('state.experiment');page.locator('#native-focus').click();idle();assert page.evaluate('state.experiment')==before
        page.locator('#measure').click();idle('map!==null');page.locator('#native-frame').click();idle()
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-em-native-scene.png'],check=True,capture_output=True)
        # Six full leave/enter cycles exercise cleanup after camera focusing and
        # map construction. Inspect actual surviving nodes, not only API flags.
        cycles=[]
        for i in range(6):
            page.locator('#native-return').click();page.wait_for_function('location.pathname==="/"&&typeof appState!=="undefined"&&appState!==null',timeout=30000)
            assert native('return {remaining=openspace.hasSceneGraphNode("C2EMRoot"),anchor=openspace.navigation.getNavigationState().Anchor}')=={'remaining':False,'anchor':'Earth'}
            assert not state()['native']['active'];enter();confirm_positions();page.locator('#measure').click();idle('map!==null');cycles.append(i+1)
        page.locator('#native-return').click();page.wait_for_function('location.pathname==="/"&&typeof appState!=="undefined"&&appState!==null',timeout=30000)
        page.locator('#experiment').click();page.wait_for_function('!pending&&appState?.mode==="experiment"',timeout=60000)
        gravity=page.evaluate('appState.physics');assert len(gravity['bodies'])==32
        enter();assert not native('return {lab=openspace.hasSceneGraphNode("LabRoot")}')['lab'];confirm_positions()
        page.locator('#native-return').click();page.wait_for_function('location.pathname==="/"&&typeof appState!=="undefined"&&appState!==null',timeout=30000)
        assert page.evaluate('appState.physics.system_id')==gravity['system_id'] and page.evaluate('appState.physics.paused')
        assert not errors,errors;assert owner.read_bytes()==original
        for name,sha in baseline['installed_app_sha256'].items():assert hashlib.sha256((ROOT/'app'/name).read_bytes()).hexdigest()==sha
        report={'status':'C212_candidate_native_markers_E_B_meshes_navigation_and_cleanup_verified','cases':cases,
                'mesh_geometry':geometry,'native_visibility':counts,'safe_Atlas_EM_cycles':cycles,
                'gravity32_to_EM_removes_gravity_scene_and_preserves_paused_worker':True,'javascript_errors':errors,
                'installed_product_files_preserved':82,'owner_pointer_preserved':True,'graphic_render_m_per_model_m':1e9,
                'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (CANDIDATE/'app/em_native.py',CANDIDATE/'app/em_laboratory.py',CANDIDATE/'app/server.py',*CANDIDATE.glob('app/ui/em/*'),Path(__file__))},
                'scope':'Real native node/property queries over independent WebSocket, SI-to-mesh reconstruction and CEF journeys. Not a formal frame/rate/resource profile or installed release; no body catalogue or field-line acceptance.'}
        (ROOT/('evidence/em-v03-native-scene-check.json' if V03 else 'evidence/em-native-scene-check.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('mesh_geometry','source_sha256')},indent=2))
finally:
    ws.close();assert owner.read_bytes()==original
