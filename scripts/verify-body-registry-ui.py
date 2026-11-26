"""Real native CEF creation/removal, identity, camera and checkpoint transactions."""
from pathlib import Path
import copy,json,runpy,subprocess,sys,time,urllib.error,urllib.request
import numpy as np
from cef_page import Page
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from navigation import pose
BASE='http://127.0.0.1:4700';execute=runpy.run_path(str(ROOT/'scripts/engine-command.py'))['execute'];errors=[];cases=[]
def get(path):return json.load(urllib.request.urlopen(BASE+'/api/'+path,timeout=15))
def post(data):return json.load(urllib.request.urlopen(urllib.request.Request(BASE+'/api/command',data=json.dumps(data).encode(),headers={'Content-Type':'application/json'}),timeout=20))
def fill(p,identifier,value):p.evaluate('document.getElementById('+json.dumps(identifier)+').value='+json.dumps(str(value))+';document.getElementById('+json.dumps(identifier)+').dispatchEvent(new Event("input",{bubbles:true}))')
def native(code):return execute(code)['payload']['1']
def camera():
 s=native('local n=openspace.navigation.getNavigationState("Root");return {navigation=n,anchor=openspace.worldPosition(n.Anchor)}');return pose(s['navigation'],s['anchor'])
def wait_idle(p,condition='true'):p.wait_for_function('!pending&&('+condition+')')
def start_form(p,operation):
 p.locator('#edit-operation').select_option(operation);p.locator('#prepare-body-edit').click();wait_idle(p,'bodyEditSnapshot!==null&&!document.getElementById("body-edit-fields").disabled')
latest=ROOT/'user/sessions/latest.json';saved=latest.read_bytes() if latest.exists() else None
before_atlas=get('atlas/state')
with Page() as p:
 p.on('pageerror',lambda e:errors.append(str(e)));p.goto(BASE+'/');p.wait_for_function('appState&&atlasState')
 try:
  for kind,count in [('fixture32',32),('fixture128',128),('atlas',None),('user',None)]:
   if kind=='atlas':
    post({'command':'atlas'});p.wait_for_function('appState.mode==="atlas"');p.locator('#copy-atlas').click();wait_idle(p,'appState.mode==="experiment"&&appState.physics.atlas_initial')
   else:
    p.locator('#experiment').click();wait_idle(p,'appState.mode==="experiment"')
    if count:
     p.locator('#fixture').select_option(str(count));p.locator('#reset').click();wait_idle(p,'appState.physics.bodies.length==='+str(count))
   if not p.evaluate('document.getElementById("body-editor").open'):p.locator('#body-editor summary').click()
   if kind=='user':
    start_form(p,'new');fill(p,'edit-name','Inicial "ação" \\ teste');p.locator('#apply-body-edit').click();wait_idle(p,'appState.physics.origin_kind==="user_system"&&appState.physics.bodies.length===1')
    state=get('state')['physics'];assert state['contract']['epoch'] is None and state['energy_error'] is None
    assert p.evaluate('document.getElementById("remove-edit-body").disabled')
    start_form(p,'create');p.locator('#apply-body-edit').click();wait_idle(p,'appState.physics.bodies.length===2')
   state=get('state')['physics'];original=copy.deepcopy(state.get('atlas_initial'));index=len(state['bodies'])//2;removed=state['bodies'][index]
   survivor=state['bodies'][0];p.locator('#edit-body').select_option(removed['id']);p.locator('#view-edit-body').click();time.sleep(.15)
   assert native('return openspace.navigation.getNavigationState("Root")')['Anchor']==removed['scene_node']
   before_camera=camera();old_revision=state['revision'];p.locator('#remove-edit-body').click();wait_idle(p,'appState.physics.revision==='+str(old_revision+1))
   after_camera=camera();position_error=float(np.max(abs(np.array(after_camera['position_render_m'])-before_camera['position_render_m'])));direction_error=float(np.max(abs(np.array(after_camera['forward'])-before_camera['forward'])))
   assert position_error<.1 and direction_error<1e-8,(position_error,direction_error)
   reduced=get('state')['physics'];assert removed['id'] not in [b['id'] for b in reduced['bodies']] and reduced['bodies'][0]==survivor
   assert reduced.get('atlas_initial')==original
   absent=native('return {removed=openspace.hasSceneGraphNode("'+removed['scene_node']+'"),surviving=openspace.hasSceneGraphNode("'+survivor['scene_node']+'")}');assert absent=={'removed':False,'surviving':True}
   start_form(p,'create');label='Corpo "órbita" \\ teste; return 9';fill(p,'edit-name',label);fill(p,'edit-velocity-1',reduced['physical_scale']['velocity_unit_m_s']*reduced['bodies'][0]['mass']**.5);old_revision=reduced['revision'];p.locator('#apply-body-edit').click();wait_idle(p,'appState.physics.revision==='+str(old_revision+1))
   added=get('state')['physics'];body=added['bodies'][-1];assert body['id']!=removed['id'] and body['name']==label and 'reference_id' not in body
   assert added['bodies'][:-1]==reduced['bodies'] and added.get('atlas_initial')==original and added['paused']
   assert p.evaluate('document.getElementById("edit-body").value')==body['id']
   name=native('return openspace.propertyValue("Scene.'+body['scene_node']+'.GuiName")');assert name==label,name
   displayed=native('return openspace.propertyValue("Scene.'+body['label_node']+'.Renderable.Text")');assert displayed==label[:23]+'…'
   source_count=p.locator('[data-reference-id]').count();assert source_count==(3 if original else 0)
   assert str(len(added['bodies']))+' corpos ativos' in p.locator('#lab-intro').inner_text()
   expected=np.array(body['position'])*1e9
   if original:expected=np.array(original['j2000_to_render_frame'])@expected
   for _ in range(30):
    local=native('return openspace.propertyValue("Scene.'+body['scene_node']+'.Translation.Position")')
    if np.max(abs(np.array(local)-expected))<.001:break
    time.sleep(.03)
   else:raise AssertionError(('New body render mismatch',local,expected))
   p.locator('#save').click();wait_idle(p);stale_token=added['edit_token'];p.locator('#play').click();wait_idle(p,'!appState.physics.paused');time.sleep(.15);p.locator('#load').click();wait_idle(p,'appState.physics.paused&&appState.physics.edit_token!=='+json.dumps(stale_token))
   loaded=get('state')['physics'];assert loaded['bodies']==added['bodies'] and loaded.get('atlas_initial')==original and loaded['interventions']==added['interventions']
   # Invalid external API command while running cannot pause or change the worker.
   post({'command':'resume'});bad={'command':'remove_body','body':body['id'],'system_id':loaded['system_id'],'edit_token':stale_token,'revision':loaded['revision'],'expected_time':loaded['time'],'frame':loaded['contract']['frame']}
   try:post(bad)
   except urllib.error.HTTPError as e:assert e.code==400
   else:raise AssertionError('Stale token accepted')
   running=get('state')['physics'];assert not running['paused'] and running['revision']==loaded['revision'];post({'command':'pause'});p.wait_for_function('appState.physics.paused')
   p.locator('#lab-home').click();time.sleep(.15)
   p.evaluate('document.getElementById("body-edit-event").scrollIntoView({block:"center"})')
   subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-native-registry-'+kind+'.png'],capture_output=True,check=True)
   cases.append({'model':kind,'active_count':len(added['bodies']),'stable_IDs_and_source':True,'UTF8_quotes_backslash_native_label':True,'camera_position_max_difference_m':position_error,'camera_forward_max_difference':direction_error,'new_body_render_max_component_m':float(np.max(abs(np.array(local)-expected))),'checkpoint_exact':True,'stale_command_does_not_pause_running_worker':True})
  post({'command':'atlas'});after=get('atlas/state');assert after['epoch']==before_atlas['epoch'] and after['bodies']==before_atlas['bodies'];assert not errors,errors
 finally:
  post({'command':'atlas'})
  if saved is None:latest.unlink(missing_ok=True)
  else:latest.write_bytes(saved)
report={'browser':'native CEF','cases':cases,'atlas_reference_and_clock_unchanged':True,'checkpoint_pointer_restored':True,'page_errors':errors,'scope':'Creation/removal/custom systems; C2-06 remains partial until radius/spin/orbit previews/experiments.'}
(ROOT/'evidence/body-registry-ui-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
