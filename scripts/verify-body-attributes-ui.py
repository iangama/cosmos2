"""Native CEF radius/spin controls and actual renderer geometry/orientation."""
from pathlib import Path
import copy,json,runpy,subprocess,sys,time,urllib.request
import numpy as np
from scipy.spatial.transform import Rotation
from cef_page import Page
ROOT=Path(__file__).resolve().parents[1];BASE='http://127.0.0.1:4700';errors=[];results=[]
execute=runpy.run_path(str(ROOT/'scripts/engine-command.py'))['execute']
def native(code):return execute(code)['payload']['1']
def get(path):return json.load(urllib.request.urlopen(BASE+'/api/'+path,timeout=15))
def post(data):return json.load(urllib.request.urlopen(urllib.request.Request(BASE+'/api/command',data=json.dumps(data).encode(),headers={'Content-Type':'application/json'}),timeout=20))
def phase(p):return [{k:b[k] for k in ('id','mass','position','velocity')} for b in p['bodies']]
def fill(p,id,value):p.evaluate('document.getElementById('+json.dumps(id)+').value='+json.dumps(str(value))+';document.getElementById('+json.dumps(id)+').dispatchEvent(new Event("input",{bubbles:true}))')
def idle(p,condition='true'):p.wait_for_function('!pending&&('+condition+')')
def prepare(p):p.locator('#prepare-body-attributes').click();idle(p,'bodyAttributesSnapshot!==null&&!document.getElementById("body-attributes-fields").disabled')
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
   state=get('state')['physics'];index=1 if imported else 29;body=state['bodies'][index];source=copy.deepcopy(state.get('atlas_initial'));p.locator('#edit-body').select_option(body['id'])
   if not p.evaluate('document.getElementById("body-attributes").open'):p.locator('#body-attributes summary').click()
   prepare(p)
   if imported:assert 'esfera equivalente por volume' in p.locator('#body-attributes-origin').inner_text()
   else:assert p.evaluate('document.getElementById("body-radius-m").value')==''
   before=get('state')['physics'];radius=1e7;omega=[.0001,-.0002,.0003];fill(p,'body-radius-m',radius);p.locator('#body-spin-defined').set_checked(True)
   for i,v in enumerate(omega):fill(p,'body-spin-'+str(i),v)
   time.sleep(.35);assert float(p.evaluate('document.getElementById("body-radius-m").value'))==radius
   p.locator('#apply-body-attributes').click();idle(p,'appState.physics.revision==='+str(before['revision']+1));applied=get('state')['physics'];attributes=applied['bodies'][index]['attributes']
   assert phase(applied)==phase(before) and applied['energy_error']==before['energy_error'] and applied['energy_error_absolute']==before['energy_error_absolute'] and applied.get('atlas_initial')==source
   assert attributes['radius_m']==radius and attributes['angular_velocity_rad_s']==omega and applied['paused']
   p.locator('#body-radius-mode').select_option('physical');idle(p,'appState.display.physical_radii');p.locator('#body-show-axes').set_checked(True);idle(p,'appState.display.axes_body==='+json.dumps(body['id']))
   display_after=get('state')['physics'];assert display_after==applied
   p.locator('#view-edit-body').click();time.sleep(.15)
   geometry=native('return {size=openspace.propertyValue("Scene.'+body['shape_node']+'.Renderable.Size"),scale=openspace.propertyValue("Scene.'+body['spin_node']+'.Scale.Scale"),axes=openspace.propertyValue("Scene.'+body['spin_node']+'.Renderable.Enabled")}');assert geometry['size']==radius and geometry['scale']==radius*1.4 and geometry['axes'],geometry
   # Unknown radius remains gravitationally active without an invented physical sphere.
   unknown=next((b for b in applied['bodies'] if b['attributes']['radius_m'] is None),None)
   if unknown:assert native('return openspace.propertyValue("Scene.'+unknown['shape_node']+'.Renderable.Enabled")') is False
   p.locator('#play').click();idle(p,'!appState.physics.paused');time.sleep(.25);p.locator('#play').click();idle(p,'appState.physics.paused');evolved=get('state')['physics'];q=evolved['bodies'][index]['attributes']['orientation_wxyz'];expected=Rotation.from_quat([*q[1:],q[0]]).as_matrix()
   if imported:expected=np.array(source['j2000_to_render_frame'])@expected
   for _ in range(30):
    rendered=matrix(native('return openspace.worldRotation("'+body['spin_node']+'")'));error=float(np.max(abs(rendered-expected)))
    if error<1e-6:break
    time.sleep(.03)
   else:raise AssertionError(('Native spin orientation mismatch',error,rendered,expected))
   # Editing omega at a fixed model instant preserves its orientation in the motor.
   prepare(p);fill(p,'body-spin-0',-.0002);p.locator('#apply-body-attributes').click();idle(p,'appState.physics.revision==='+str(evolved['revision']+1));time.sleep(.05)
   continuous=matrix(native('return openspace.worldRotation("'+body['spin_node']+'")'));continuity=float(np.max(abs(continuous-rendered)));assert continuity<1e-6,continuity
   final=get('state')['physics'];p.locator('#save').click();idle(p);p.locator('#play').click();idle(p,'!appState.physics.paused');time.sleep(.12);p.locator('#load').click();idle(p,'appState.physics.paused&&appState.physics.edit_token!=='+json.dumps(final['edit_token']));loaded=get('state')['physics'];assert loaded['bodies']==final['bodies'] and loaded['interventions']==final['interventions'] and loaded.get('atlas_initial')==source
   p.locator('#view-edit-body').click();p.evaluate('document.getElementById("body-attributes-form").scrollIntoView({block:"center"})');time.sleep(.15)
   subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-native-attributes-'+('atlas' if imported else 'p32')+'.png'],capture_output=True,check=True)
   p.locator('#body-radius-mode').select_option('markers');idle(p,'!appState.display.physical_radii');marker=native('return openspace.propertyValue("Scene.'+body['scene_node']+'.Renderable.Size")');assert marker!=radius and get('state')['physics']==loaded
   post({'command':'display','physical_radii':False,'axes_body':None})
   results.append({'atlas_copy':imported,'SI_radius_native_exact_m':geometry['size'],'axes_scale_native_exact_m':geometry['scale'],'phase_and_energy_error_unchanged_by_attributes':True,'display_does_not_mutate_physics':True,'unknown_radius_no_invented_sphere':True,'native_rotation_max_matrix_difference':error,'omega_edit_native_orientation_difference':continuity,'checkpoint_exact':True,'original_source_preserved':True})
  post({'command':'atlas'});after=get('atlas/state');assert after['bodies']==atlas['bodies'] and after['epoch']==atlas['epoch'];assert not errors,errors
 finally:
  post({'command':'atlas'})
  if saved is None:latest.unlink(missing_ok=True)
  else:latest.write_bytes(saved)
report={'browser':'native CEF','cases':results,'input_survives_polling':True,'checkpoint_pointer_restored':True,'atlas_reference_and_clock_unchanged':True,'page_errors':errors,'scope':'Geometric radius and kinematic spin, no torques/J2/contact/internal-energy model. C2-06 remains partial.'}
(ROOT/'evidence/body-attributes-ui-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
