"""Frozen field lines in real CEF/native scene, independent geometry and exports."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import urllib.request
import numpy as np
from cef_page import Page
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parents[1];V04='--v04' in sys.argv;CANDIDATE=ROOT/('output/c212-em-v04-product' if V04 else 'output/c212-em-product');owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes()
sys.path.insert(0,str(CANDIDATE/'app'));from em_native import normalize
errors=[];cases=[];geometry=[];ws=connect('ws://127.0.0.1:4682',open_timeout=3,close_timeout=.2,ping_interval=None);topic=0
ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
def native(code):
    global topic
    topic+=1;ws.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True}}));response=json.loads(ws.recv(timeout=5));assert response.get('topic')==topic;return normalize(response['payload']['1'])
def get():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/em/state',timeout=10))
try:
    with Page() as page:
        previous=page.evaluate('location.href');page.on('pageerror',lambda e:errors.append(e))
        def idle(expr='true'):page.wait_for_function('!pending&&('+expr+')',timeout=30000)
        page.locator('#em-lab').click();page.wait_for_function('location.pathname==="/em.html"&&nativeState?.confirmation?.state==="accepted"&&!pending',timeout=30000)
        old=page.evaluate('state.system_id');page.locator('#preset').select_option('dipole');page.locator('#load-preset').click();idle('state.system_id!=='+json.dumps(old))
        page.locator('#source-select').select_option('synthetic-dipole');idle('state.editor.visual.selected_id==="synthetic-dipole"')
        page.locator('#measure').click();idle('map!==null');before=page.evaluate('state.experiment')
        page.locator('#trace-fields').click();idle('fieldLines!==null');traced=page.evaluate('fieldLines');value=get();render=value['native']['lines']
        assert page.evaluate('state.experiment')==before and len(traced['curves'])==32
        assert traced['tracer']['sha256']==hashlib.sha256((CANDIDATE/'app/em_trace.py').read_bytes()).hexdigest()
        assert all(c['termination']=='null_or_cancellation_direction' for c in traced['curves'] if c['quantity']=='electric')
        valid=[c for c in traced['curves'] if c['quantity']=='magnetic' and len(c['points_m'])>1];assert valid
        maximum=0.
        for curve in valid:
            points=np.array(curve['points_m']);r=np.linalg.norm(points,axis=1);invariant=r**3/(points[:,0]**2+points[:,1]**2)
            maximum=max(maximum,float(np.max(abs(invariant/invariant[0]-1))));assert np.all(r>1.)
        assert maximum<1e-4,maximum
        line_nodes=[]
        for mesh in render['meshes']:
            line_nodes.append(mesh['node']);raw=Path(mesh['file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==mesh['file_sha256']
            rows=raw.decode().splitlines();paths={};i=0
            while i<len(rows):
                if rows[i].startswith('mesh '):
                    index=int(rows[i+1].removeprefix('id curve'));count=int(rows[i+2]);paths[index]=np.array([[float(x) for x in row.split()] for row in rows[i+3:i+3+count]]);i+=count+4
                else:i+=1
            assert set(paths)==set(mesh['curve_indices'])
            for index,path in paths.items():assert np.allclose(path*mesh['local_unit_model_m'],traced['curves'][index]['points_m'],rtol=1e-14,atol=1e-13)
            actual=native('return {enabled=openspace.propertyValue("Scene.'+mesh['node']+'.Renderable.Enabled"),scale=openspace.propertyValue("Scene.'+mesh['node']+'.Scale.Scale")}')
            assert actual['enabled'] and actual['scale']==mesh['local_unit_model_m']*1e9
            geometry.append({'quantity':mesh['quantity'],'curves':mesh['curve_count'],'vertices':mesh['vertex_count'],'float32_max_error_model_m':mesh['float32_vertex_component_error_model_m']})
        cases.append('dipole integral curves satisfy independent r/sin²theta invariant, exclusions and actual native mesh coordinates')
        page.locator('#native-frame').click();idle()
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-em-native-lines.png'],check=True,capture_output=True)
        phase=page.evaluate('state.experiment.phase');page.locator('#visible-b').set_checked(False);idle('!state.editor.visual.magnetic_visible')
        for node in line_nodes:assert not native('return {enabled=openspace.propertyValue("Scene.'+node+'.Renderable.Enabled")}')['enabled']
        assert page.evaluate('state.experiment.phase')==phase
        page.locator('#visible-b').set_checked(True);idle('state.editor.visual.magnetic_visible')
        start=page.evaluate('state.time_s');page.locator('#play').click();idle('!state.paused');page.wait_for_function('state.time_s>'+str(start+.03));page.locator('#play').click();idle('state.paused')
        assert 'LINHAS CONGELADAS' in page.locator('#line-state').inner_text() and get()['native']['lines']['metadata']['time_s']==traced['time_s']
        page.locator('#export-layers').click();idle('lastLayersArtifact!==null');artifact=page.evaluate('lastLayersArtifact');exported=page.evaluate('lastLayersExport')
        raw=urllib.request.urlopen('http://127.0.0.1:4700'+artifact['url'],timeout=10).read();assert hashlib.sha256(raw).hexdigest()==artifact['sha256'] and json.loads(raw)==exported
        assert 'time_s' not in exported and exported['kind']=='cosmos2_em_frozen_layers'
        assert exported['layers']['field_lines']['measurement']==traced and exported['layers']['field_map']['measurement']['samples']==page.evaluate('map.samples')
        assert exported['layers']['field_lines']['measurement']['time_s']<page.evaluate('state.time_s')
        cases.append('hide/show lines preserves physics; evolution freezes old curves; exported layers retain their own exact time/source snapshots')
        page.locator('#native-return').click();page.wait_for_function('location.pathname==="/"&&typeof appState!=="undefined"&&appState!==null',timeout=30000)
        for node in line_nodes:assert not native('return {present=openspace.hasSceneGraphNode("'+node+'")}')['present']
        assert not errors,errors;assert owner.read_bytes()==original
        report={'status':'candidate_EM_field_lines_native_CEF_geometry_export_and_cleanup_verified','cases':cases,'native_geometry':geometry,
                'dipole_maximum_relative_r_over_sin2theta_error':maximum,'trace_evaluation_ms':traced['evaluation_ms'],
                'termination_counts':{s:sum(c['termination']==s for c in traced['curves']) for s in {c['termination'] for c in traced['curves']}},
                'export_bytes':len(raw),'export_sha256':artifact['sha256'],'javascript_errors':errors,'owner_pointer_preserved':True,
                'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (CANDIDATE/'app/em_trace.py',CANDIDATE/'app/em_native.py',CANDIDATE/'app/em_laboratory.py',CANDIDATE/'app/server.py',CANDIDATE/'app/ui/em.html',*CANDIDATE.glob('app/ui/em/*'),Path(__file__))},
                'scope':'Candidate static E/B integral curves and frozen numeric exports, not trajectories, propagation or body-associated fields. Per-command2s bound is not a formal frame/throughput profile.'}
        (ROOT/('evidence/em-v04-lines-native-ui-check.json' if V04 else 'evidence/em-lines-native-ui-check.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'},indent=2))
finally:
    ws.close()
    if 'previous' in locals():
        with Page() as cleanup:cleanup.call('Page.navigate',{'url':previous})
    assert owner.read_bytes()==original
