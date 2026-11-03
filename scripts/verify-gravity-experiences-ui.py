"""Native controlled experiences through selection, clock, horizon and checkpoint."""
from pathlib import Path
import copy,json,runpy,subprocess,time,urllib.error,urllib.request
import numpy as np
from cef_page import Page
ROOT=Path(__file__).resolve().parents[1];BASE='http://127.0.0.1:4700';errors=[];results=[]
execute=runpy.run_path(str(ROOT/'scripts/engine-command.py'))['execute']
def native(code):return execute(code)['payload']['1']
def get(path):return json.load(urllib.request.urlopen(BASE+'/api/'+path,timeout=15))
def post(data):return json.load(urllib.request.urlopen(urllib.request.Request(BASE+'/api/command',data=json.dumps(data).encode(),headers={'Content-Type':'application/json'}),timeout=20))
def idle(p,condition='true'):p.wait_for_function('!pending&&('+condition+')')
def capture(name):subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-native-experience-'+name+'.png'],capture_output=True,check=True)
latest=ROOT/'user/sessions/latest.json';saved=latest.read_bytes() if latest.exists() else None;atlas=get('atlas/state')
with Page() as p:
 p.on('pageerror',lambda e:errors.append(str(e)));p.goto(BASE+'/');p.wait_for_function('appState&&atlasState&&gravityExperienceCatalog')
 try:
  p.locator('#experiment').click();idle(p,'appState.mode==="experiment"')
  if not p.evaluate('document.getElementById("gravity-experiences").open'):p.locator('#gravity-experiences summary').click()
  for identifier in ['flyby','capture','ejection']:
   p.locator('#gravity-experience').select_option(identifier);p.locator('#load-gravity-experience').click();idle(p,'appState.physics.experiment?.definition.id==='+json.dumps(identifier))
   initial=get('state')['physics'];e=initial['experiment'];horizon=e['definition']['horizon_model_time'];ids=e['initial_ids'];assert initial['paused'] and initial['time']==0 and len(initial['bodies'])==(2 if identifier=='flyby' else 3)
   assert all('reference_id' not in b for b in initial['bodies']) and not get('state')['display']['physical_radii']
   assert 'sem corpos observados' in p.locator('#gravity-experiences').inner_text() and 'Horizonte recomendado' in p.locator('#gravity-experience-goal').inner_text()
   p.locator('#rate').select_option('10');idle(p,'appState.physics.requested_rate===10');p.locator('#play').click();idle(p,'!appState.physics.paused')
   deadline=time.monotonic()+30;sample=None
   while time.monotonic()<deadline:
    state=get('state')['physics']
    if sample is None and state['time']>=e['definition']['verification_times_model'][0]:sample=copy.deepcopy(state)
    if state['paused'] and state['experiment_horizon_reached']:break
    time.sleep(.1)
   else:raise TimeoutError(('Experience did not pause at horizon',identifier,state['time']))
   p.wait_for_function('appState.physics.paused&&appState.physics.experiment_horizon_reached')
   final=get('state')['physics'];assert final['time']==horizon and final['experiment']['horizon_reached'] and sample
   assert final['energy_error']<1e-8 and final['conservation']['momentum_error_normalized']<1e-8 and final['conservation']['angular_momentum_error_normalized']<1e-8
   if identifier=='flyby':assert final['experiment']['status']=='isolated_flyby' and final['experiment']['analysis']['outward']
   else:assert final['experiment']['status']=='hierarchical_outgoing' and final['experiment']['analysis']['matches_selected_model_outcome'] and sample['experiment']['analysis']['matches_selected_model_outcome']
   p.locator('#view-gravity-pair').click();time.sleep(.15);assert native('return openspace.navigation.getNavigationState("Root")')['Anchor']=='LabPairFrame'
   pair=final['experiment']['analysis']['pair'];bodies=[b for b in final['bodies'] if b['id'] in pair];mass=sum(b['mass'] for b in bodies);expected=np.array([sum(b['mass']*b['position'][k] for b in bodies)/mass*1e9 for k in range(3)]);actual=np.array(native('return openspace.propertyValue("Scene.LabPairFrame.Translation.Position")'));assert np.max(abs(actual-expected))<.001
   p.evaluate('document.getElementById("gravity-experience-result").scrollIntoView({block:"center"})');capture(identifier)
   if identifier!='flyby':
    p.locator('#view-gravity-escaper').click();time.sleep(.1);escaper=final['experiment']['analysis']['escaper'];node=next(b['scene_node'] for b in final['bodies'] if b['id']==escaper);assert native('return openspace.navigation.getNavigationState("Root")')['Anchor']==node
   p.locator('#save').click();idle(p);p.locator('#play').click();idle(p,'!appState.physics.paused');time.sleep(.15);assert get('state')['physics']['time']>horizon
   p.locator('#load').click();idle(p,'appState.physics.paused&&appState.physics.time==='+str(horizon));loaded=get('state')['physics'];assert loaded['bodies']==final['bodies'] and loaded['experiment']==final['experiment'] and loaded['conservation']==final['conservation']
   p.locator('#reset').click();idle(p,'appState.physics.time===0&&appState.physics.system_id!=='+json.dumps(initial['system_id']));reset=get('state')['physics'];assert reset['experiment']['definition']==initial['experiment']['definition'] and [b['position'] for b in reset['bodies']]==[b['position'] for b in initial['bodies']] and reset['revision']==0
   results.append({'model':identifier,'native_count':len(initial['bodies']),'automatic_horizon_pause_model_time':horizon,'measured_intermediate_model_time':sample['time'],'measured_final_status':final['experiment']['status'],'energy_relative_error':final['energy_error'],'momentum_normalized_error':final['conservation']['momentum_error_normalized'],'angular_momentum_normalized_error':final['conservation']['angular_momentum_error_normalized'],'native_pair_COM_position_difference_m':float(np.max(abs(actual-expected))),'view_pair_and_escaper':True,'resume_beyond_horizon_allowed':True,'checkpoint_bodies_definition_conservation_exact':True,'restart_original_seed':True})
  post({'command':'atlas'});after=get('atlas/state');assert after['bodies']==atlas['bodies'] and after['epoch']==atlas['epoch'];assert not errors,errors
 finally:
  post({'command':'atlas'})
  if saved is None:latest.unlink(missing_ok=True)
  else:latest.write_bytes(saved)
report={'browser':'native CEF','models':results,'atlas_reference_and_clock_unchanged':True,'checkpoint_pointer_restored':True,'page_errors':errors,'scope':'Three finite local Newtonian experiences; not observed systems or a promise of eternal capture/escape.'}
(ROOT/'evidence/gravity-experiences-ui-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
