"""Native CEF current/proposed conics, renderer transform and live COM diagnostics."""
from pathlib import Path
import copy,json,runpy,subprocess,time,urllib.error,urllib.request
import numpy as np
from cef_page import Page
ROOT=Path(__file__).resolve().parents[1];BASE='http://127.0.0.1:4700';errors=[];results=[]
execute=runpy.run_path(str(ROOT/'scripts/engine-command.py'))['execute']
def native(code):return execute(code)['payload']['1']
def get(path):return json.load(urllib.request.urlopen(BASE+'/api/'+path,timeout=15))
def post(data):return json.load(urllib.request.urlopen(urllib.request.Request(BASE+'/api/command',data=json.dumps(data).encode(),headers={'Content-Type':'application/json'}),timeout=20))
def fill(p,id,value):p.evaluate('document.getElementById('+json.dumps(id)+').value='+json.dumps(str(value))+';document.getElementById('+json.dumps(id)+').dispatchEvent(new Event("input",{bubbles:true}))')
def idle(p,condition='true'):p.wait_for_function('!pending&&('+condition+')')
def matrix(value):return np.array([value[str(i)] for i in range(1,10)] if isinstance(value,dict) else value).reshape(3,3,order='F')
latest=ROOT/'user/sessions/latest.json';saved=latest.read_bytes() if latest.exists() else None;atlas=get('atlas/state')
with Page() as p:
 p.on('pageerror',lambda e:errors.append(str(e)));p.goto(BASE+'/');p.wait_for_function('appState&&atlasState')
 try:
  for imported in (False,True):
   if imported:
    post({'command':'atlas'});p.wait_for_function('appState.mode==="atlas"');p.locator('#copy-atlas').click();idle(p,'appState.physics.atlas_initial&&appState.mode==="experiment"')
   else:
    p.locator('#experiment').click();idle(p,'appState.mode==="experiment"');p.locator('#fixture').select_option('32');p.locator('#reset').click();idle(p,'appState.physics.fixture_count===32')
   if not p.evaluate('document.getElementById("body-editor").open'):p.locator('#body-editor summary').click()
   state=get('state')['physics'];body=state['bodies'][2 if imported else 29];primary=state['bodies'][1 if imported else 0];source=copy.deepcopy(state.get('atlas_initial'));p.locator('#edit-body').select_option(body['id']);p.locator('#prepare-body-edit').click();idle(p,'bodyEditSnapshot!==null')
   # Tangential velocity change makes the proposed conic visibly distinct.
   velocity=body['velocity'];pv=primary['velocity'];u=state['physical_scale']
   for i in range(3):fill(p,'edit-velocity-'+str(i),(pv[i]+1.12*(velocity[i]-pv[i]))*u['velocity_unit_m_s'])
   if not p.evaluate('document.getElementById("orbit-editor").open'):p.locator('#orbit-editor summary').click()
   p.locator('#orbit-primary').select_option(primary['id']);before=get('state')['physics'];pointer=latest.read_bytes() if latest.exists() else None
   p.locator('#compare-orbit').click();idle(p,'appState.orbit_preview?.after');status=get('state');preview=status['orbit_preview'];assert status['physics']==before and (latest.read_bytes() if latest.exists() else None)==pointer
   assert preview['before']['primary']==primary['id'] and preview['before']['body']==body['id'] and preview['after']['eccentricity']!=preview['before']['eccentricity']
   assert preview['names']=={'body':body['name'],'primary':primary['name']} and len(preview['render']['nodes'])==2
   assert p.locator('#orbit-table th').count()==3 and 'Proposto' in p.locator('#orbit-table').inner_text() and '8×' in p.locator('#orbit-model-note').inner_text()
   transform=np.array(source['j2000_to_render_frame']) if imported else np.eye(3);root=np.array(native('return openspace.worldPosition("LabRoot")'));maximum=0.
   for curve in preview['render']['curves']:
    values=native('return {position=openspace.worldPosition("'+curve['node']+'"),rotation=openspace.worldRotation("'+curve['node']+'"),scale=openspace.propertyValue("Scene.'+curve['node']+'.Scale.Scale"),file=openspace.propertyValue("Scene.'+curve['node']+'.Renderable.File")}')
    assert values['scale']==1e9 and Path(values['file'])==Path(curve['file'])
    diagnostic=preview[curve['branch']];origin=np.array(diagnostic['preview']['primary_position_model_units']);rotation=matrix(values['rotation']);offset=np.array(values['position'])
    for segment in diagnostic['preview']['segments_model_units']:
     points=np.array(segment);native_positions=(points-origin).astype(np.float32).astype(float)@rotation.T*1e9+offset;scientific=points@transform.T*1e9+root;error=float(np.max(abs(native_positions-scientific)));maximum=max(maximum,error);assert error<=curve['conservative_display_position_error_bound_m'],(error,curve)
   p.locator('#view-orbit').click();time.sleep(.15);assert native('return openspace.navigation.getNavigationState("Root")')['Anchor']=='LabOrbitFrame'
   p.evaluate('document.getElementById("orbit-table").scrollIntoView({block:"center"})')
   subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-native-orbit-'+('atlas' if imported else 'p32')+'.png'],capture_output=True,check=True)
   # Invalid current state never replaces an existing preview or mutates the model.
   bad={'command':'orbit','system_id':before['system_id'],'edit_token':before['edit_token'],'revision':before['revision']-1,'expected_time':before['time'],'frame':before['contract']['frame'],'body':body['id'],'primary':primary['id']}
   try:post(bad)
   except urllib.error.HTTPError as e:assert e.code==400
   else:raise AssertionError('Stale preview accepted')
   frozen=get('state');assert frozen['physics']==before and frozen['orbit_preview']==preview and frozen['engine_connected']
   # Curves remain stamped at their source time when the actual N-body system evolves.
   p.locator('#play').click();idle(p,'!appState.physics.paused');time.sleep(.12);p.locator('#play').click();idle(p,'appState.physics.paused');p.wait_for_function('document.getElementById("orbit-status").textContent.includes("PRÉVIA FIXA")')
   evolved=get('state')['physics'];assert evolved.get('atlas_initial')==source
   if not p.evaluate('document.getElementById("conservation-panel").open'):p.locator('#conservation-panel summary').click()
   p.locator('#view-barycenter').click();time.sleep(.1);assert native('return openspace.navigation.getNavigationState("Root")')['Anchor']=='LabBarycenter'
   expected=np.array(evolved['conservation']['current']['barycenter'])@transform.T*1e9;local=np.array(native('return openspace.propertyValue("Scene.LabBarycenter.Translation.Position")'));assert np.max(abs(local-expected))<.001
   assert 'Erro P normalizado' in p.locator('#conservation-reading').inner_text()
   p.locator('#clear-orbit').click();idle(p,'appState.orbit_preview===null');assert all(not native('return openspace.hasSceneGraphNode("'+node+'")') for node in preview['render']['nodes']) and get('state')['physics']==evolved
   results.append({'atlas_copy':imported,'current_and_proposed_pair':True,'preview_does_not_mutate_physics_or_checkpoint':True,'float32_native_curve_transform_max_component_difference_m':maximum,'display_error_bounded_separately_from_science':True,'stale_preview_rejected_preserving_prior_curve':True,'frozen_time_badge_after_evolution':True,'native_COM_position_max_component_difference_m':float(np.max(abs(local-expected))),'source_preserved':True})
  post({'command':'atlas'});after=get('atlas/state');assert after['bodies']==atlas['bodies'] and after['epoch']==atlas['epoch'];assert not errors,errors
 finally:
  post({'command':'atlas'})
  if saved is None:latest.unlink(missing_ok=True)
  else:latest.write_bytes(saved)
report={'browser':'native CEF','cases':results,'checkpoint_pointer_restored':True,'atlas_reference_and_clock_unchanged':True,'page_errors':errors,'scope':'Frozen pair previews/translation integrals; encounter/capture/ejection scenarios and128 performance still pending for complete C2-06.'}
(ROOT/'evidence/orbit-editor-ui-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
