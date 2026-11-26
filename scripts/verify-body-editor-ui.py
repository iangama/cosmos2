"""Existing-body editor through real native CEF, worker and renderer acknowledgments."""
from pathlib import Path
import copy,json,runpy,subprocess,time,urllib.request,urllib.error
import numpy as np
from cef_page import Page
ROOT=Path(__file__).resolve().parents[1];BASE='http://127.0.0.1:4700';errors=[];cases=[]
execute=runpy.run_path(str(ROOT/'scripts/engine-command.py'))['execute']
def get(path):return json.load(urllib.request.urlopen(BASE+'/api/'+path,timeout=15))
def post(path,data):return json.load(urllib.request.urlopen(urllib.request.Request(BASE+'/api/'+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'}),timeout=15))
def fill(p,id,value):p.evaluate('document.getElementById('+json.dumps(id)+').value='+json.dumps(str(value))+';document.getElementById('+json.dumps(id)+').dispatchEvent(new Event("input",{bubbles:true}))')
latest=ROOT/'user/sessions/latest.json';saved_latest=latest.read_bytes() if latest.exists() else None
atlas=get('atlas/state');original_epoch=atlas['epoch']
with Page() as p:
 p.on('pageerror',lambda e:errors.append(str(e)));p.goto(BASE+'/');p.wait_for_function('appState!==null&&atlasState!==null')
 try:
  for imported,count in [(False,32),(False,128),(True,None)]:
   if imported:
    p.locator('#atlas').click();p.wait_for_function('!pending&&appState.mode==="atlas"');p.locator('#copy-atlas').click();p.wait_for_function('!pending&&appState.physics?.atlas_initial')
   else:
    p.locator('#experiment').click();p.wait_for_function('!pending&&appState.mode==="experiment"')
    p.locator('#fixture').select_option(str(count));p.locator('#reset').click();p.wait_for_function('!pending&&appState.physics.bodies.length==='+str(count))
   if not p.evaluate('document.getElementById("body-editor").open'):p.locator('#body-editor summary').click()
   state=get('state')['physics'];index=1 if imported else count-3;body=state['bodies'][index];source=copy.deepcopy(state.get('atlas_initial'))
   p.locator('#edit-body').select_option(body['id']);p.locator('#prepare-body-edit').click();p.wait_for_function('!pending&&bodyEditSnapshot!==null&&!document.getElementById("body-edit-fields").disabled')
   frame=p.locator('#body-edit-frame').inner_text();assert state['contract']['frame'] in frame
   mass=float(p.evaluate('document.getElementById("edit-mass-kg").value'))*1.2
   x=float(p.evaluate('document.getElementById("edit-position-0").value'))+1e8
   vz=float(p.evaluate('document.getElementById("edit-velocity-2").value'))+100
   fill(p,'edit-mass-kg',mass);fill(p,'edit-position-0',x);fill(p,'edit-velocity-2',vz);time.sleep(.4)
   assert float(p.evaluate('document.getElementById("edit-position-0").value'))==x
   revision=state['revision'];p.locator('#apply-body-edit').click();p.wait_for_function('!pending&&appState.physics.revision==='+str(revision+1))
   edited=get('state')['physics'];new=edited['bodies'][index];u=edited['physical_scale'];event=edited['interventions'][-1]
   assert edited['paused'] and event['type']=='set_body_si' and event['body']==body['id']
   assert abs(new['position'][0]*u['length_unit_m']-x)<=.001
   assert abs(new['velocity'][2]*u['velocity_unit_m_s']-vz)<1e-8
   assert abs(new['mass']*u['mass_unit_kg']/mass-1)<1e-14 and edited.get('atlas_initial')==source
   expected=np.array(new['position'])*1e9
   if imported:expected=np.array(source['j2000_to_render_frame'])@expected
   for _ in range(40):
    native=execute('return {p=openspace.propertyValue("Scene.'+new['scene_node']+'.Translation.Position")}')['payload']['1']['p']
    if np.max(np.abs(np.array(native)-expected))<=.001:break
    time.sleep(.03)
   else:raise AssertionError(('Native position mismatch',native,expected))
   p.locator('#save').click();p.wait_for_function('!pending');p.locator('#play').click();p.wait_for_function('!pending&&!appState.physics.paused');time.sleep(.15);p.locator('#load').click();p.wait_for_function('!pending&&appState.physics.paused&&appState.physics.time==='+str(edited['time']))
   loaded=get('state')['physics'];assert loaded['bodies']==edited['bodies'] and loaded['interventions']==edited['interventions'] and loaded.get('atlas_initial')==source
   # A stale edit via API is refused and leaves both session and native reference intact.
   bad=dict(event['input_SI'],command='set_body');bad['revision']-=1
   try:post('command',bad)
   except urllib.error.HTTPError as error:assert error.code==400
   else:raise AssertionError('Stale edit accepted')
   assert get('state')['physics']['bodies']==loaded['bodies']
   assert 'kg·m²/s' in p.locator('#body-edit-event').inner_text()
   p.locator('#view-edit-body').click();time.sleep(.1)
   assert execute('return openspace.navigation.getNavigationState("Root")')['payload']['1']['Anchor']==new['scene_node']
   assert p.evaluate('document.getElementById("scene-targets").hidden')
   p.evaluate('document.getElementById("body-edit-event").scrollIntoView({block:"center"})')
   subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-native-body-editor-'+('atlas' if imported else 'p'+str(count))+'.png'],check=True,capture_output=True)
   cases.append({'atlas_copy':imported,'count':len(edited['bodies']),'body_id':body['id'],'SI_mass_phase_applied':True,'native_max_component_difference_m':float(np.max(np.abs(np.array(native)-expected))),'checkpoint_exact':True,'original_reference_preserved':True})
  post('command',{'command':'atlas'});after=get('atlas/state');assert after['epoch']==original_epoch and after['bodies']==atlas['bodies'];assert not errors,errors
 finally:
  post('command',{'command':'atlas'})
  if saved_latest is None:latest.unlink(missing_ok=True)
  else:latest.write_bytes(saved_latest)
report={'browser':'native CEF','cases':cases,'input_survives_polling':True,'stale_revision_rejected':True,'atlas_state_unchanged':True,'checkpoint_pointer_restored':True,'page_errors':errors,'scope':'First C2-06 usable slice, existing point masses only. Creation/radius/spin/orbit previews pending.'}
(ROOT/'evidence/body-editor-ui-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
