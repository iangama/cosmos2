"""Native P128 scene/probe and open/degenerate conic journeys."""
from pathlib import Path
import copy,json,math,runpy,subprocess,time,urllib.error,urllib.request
import numpy as np
from cef_page import Page
ROOT=Path(__file__).resolve().parents[1];BASE='http://127.0.0.1:4700';errors=[];results=[]
execute=runpy.run_path(str(ROOT/'scripts/engine-command.py'))['execute']
def native(code):return execute(code)['payload']['1']
def get(path):return json.load(urllib.request.urlopen(BASE+'/api/'+path,timeout=15))
def post(data):return json.load(urllib.request.urlopen(urllib.request.Request(BASE+'/api/command',data=json.dumps(data).encode(),headers={'Content-Type':'application/json'}),timeout=20))
def fill(p,id,value):p.evaluate('document.getElementById('+json.dumps(id)+').value='+json.dumps(str(value))+';document.getElementById('+json.dumps(id)+').dispatchEvent(new Event("input",{bubbles:true}))')
def idle(p,condition='true'):p.wait_for_function('!pending&&('+condition+')')
def guard(s):return {'system_id':s['system_id'],'edit_token':s['edit_token'],'revision':s['revision'],'expected_time':s['time'],'frame':s['contract']['frame']}
latest=ROOT/'user/sessions/latest.json';saved=latest.read_bytes() if latest.exists() else None;atlas=get('atlas/state')
with Page() as p:
 p.on('pageerror',lambda e:errors.append(str(e)));p.goto(BASE+'/');p.wait_for_function('appState&&atlasState')
 try:
  p.locator('#experiment').click();idle(p,'appState.mode==="experiment"')
  for imported in (False,True):
   if imported:
    post({'command':'atlas'});p.wait_for_function('appState.mode==="atlas"');p.locator('#copy-atlas').click();idle(p,'appState.physics.atlas_initial&&appState.mode==="experiment"')
   else:
    p.locator('#fixture').select_option('128');began=time.perf_counter();p.locator('#reset').click();idle(p,'appState.physics.fixture_count===128');creation_ms=(time.perf_counter()-began)*1000
   before=get('state')['physics'];ids=[b[k] for b in before['bodies'] for k in ['scene_node','label_node','spin_node','shape_node']]
   assert native('local n=0;for _,id in ipairs({'+','.join(json.dumps(v) for v in ids)+'}) do if openspace.hasSceneGraphNode(id) then n=n+1 end end;return n')==4*len(before['bodies'])
   if not p.evaluate('document.getElementById("gravity-probe").open'):p.locator('#gravity-probe summary').click()
   point=[1.7e10,-9e9,3e9]
   for i,v in enumerate(point):fill(p,'probe-position-'+str(i),v)
   pointer=latest.read_bytes() if latest.exists() else None;p.locator('#sample-probe').click();idle(p,'appState.probe_preview!==null');sample=get('state')['probe_preview'];assert get('state')['physics']==before and (latest.read_bytes() if latest.exists() else None)==pointer
   transform=np.array(before['atlas_initial']['j2000_to_render_frame']) if imported else np.eye(3);actual=np.array(native('return openspace.propertyValue("Scene.LabProbe.Translation.Position")'));expected=np.array(point)@transform.T;difference=float(np.max(abs(actual-expected)));assert difference<.001
   p.locator('#view-probe').click();time.sleep(.1);assert native('return openspace.navigation.getNavigationState("Root")')['Anchor']=='LabProbe'
   p.evaluate('document.getElementById("probe-reading").scrollIntoView({block:"center"})')
   subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-native-probe-'+('atlas' if imported else 'p128')+'.png'],capture_output=True,check=True)
   assert sample['position_m']==point and len(sample['sources'])==len(before['bodies']) and sample['frame']==before['contract']['frame'] and 'J/kg' in p.locator('#probe-reading').inner_text() and 'm/s²' in p.locator('#probe-reading').inner_text()
   try:post({'command':'probe',**guard(before),'position_m':[v*1e9 for v in before['bodies'][0]['position']]})
   except urllib.error.HTTPError as e:assert e.code==400
   else:raise AssertionError('Singular probe accepted')
   assert get('state')['probe_preview']==sample and get('state')['engine_connected'] and get('state')['physics']==before
   p.locator('#play').click();idle(p,'!appState.physics.paused');time.sleep(.12);p.locator('#play').click();idle(p,'appState.physics.paused');p.wait_for_function('document.getElementById("probe-reading").textContent.includes("AMOSTRA FIXA")')
   evolved=get('state')['physics'];p.locator('#clear-probe').click();idle(p,'appState.probe_preview===null');assert get('state')['physics']==evolved and native('return openspace.propertyValue("Scene.LabProbe.Renderable.Enabled")') is False
   results.append({'atlas_copy':imported,'mass_count':len(before['bodies']),'all_four_scene_nodes_per_body_present':True,'P128_scene_creation_ms':None if imported else creation_ms,'probe_native_position_max_component_difference_m':difference,'read_only_checkpoint_and_state_exact':True,'singular_probe_rejected_without_mutation':True,'frozen_sample_badge_and_hide_without_physical_change':True})
  s=get('state')['physics'];post({'command':'load_experiment',**guard(s),'scenario_id':'flyby'})
  p.wait_for_function('appState.physics.experiment?.definition.id==="flyby"');s=get('state')['physics'];body=s['bodies'][1];primary=s['bodies'][0]
  if not p.evaluate('document.getElementById("body-editor").open'):p.locator('#body-editor summary').click()
  p.locator('#edit-body').select_option(body['id']);p.locator('#prepare-body-edit').click();idle(p,'bodyEditSnapshot!==null')
  if not p.evaluate('document.getElementById("orbit-editor").open'):p.locator('#orbit-editor summary').click()
  p.locator('#orbit-primary').select_option(primary['id']);p.locator('#calculate-orbit').click();idle(p,'appState.orbit_preview!==null');hyper=get('state')['orbit_preview'];assert hyper['before']['classification']=='hyperbolic' and not hyper['before']['preview']['closed'] and hyper['before']['preview']['clipped'] and len(hyper['render']['nodes'])==1
  for segment in hyper['before']['preview']['segments_model_units']:assert all(math.isfinite(x) for point in segment for x in point)
  assert 'hiperbólica' in p.locator('#orbit-table').inner_text();p.locator('#view-orbit').click();time.sleep(.1);assert native('return openspace.navigation.getNavigationState("Root")')['Anchor']=='LabOrbitFrame'
  p.locator('#prepare-body-edit').click();idle(p,'bodyEditSnapshot!==null')
  for i in range(3):fill(p,'edit-velocity-'+str(i),primary['velocity'][i]*s['physical_scale']['velocity_unit_m_s'])
  p.locator('#compare-orbit').click();idle(p,'appState.orbit_preview?.after');radial=get('state')['orbit_preview'];assert radial['after']['classification']=='radial_degenerate' and radial['after']['preview']['segments_model_units']==[] and len(radial['render']['nodes'])==1
  assert 'plano indefinido' in p.locator('#orbit-table').inner_text() and 'indefinido' in p.locator('#orbit-table').inner_text() and get('state')['physics']==s
  p.evaluate('document.getElementById("orbit-table").scrollIntoView({block:"center"})');subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-native-orbit-hyperbola-radial.png'],capture_output=True,check=True)
  results.append({'hyperbolic_native_open_clipped_conic':True,'radial_proposal_no_invented_plane_or_curve':True,'proposal_read_only':True})
  post({'command':'atlas'});after=get('atlas/state');assert after['bodies']==atlas['bodies'] and after['epoch']==atlas['epoch'];assert not errors,errors
 finally:
  post({'command':'atlas'})
  if saved is None:latest.unlink(missing_ok=True)
  else:latest.write_bytes(saved)
report={'browser':'native CEF','cases':results,'checkpoint_pointer_restored':True,'atlas_reference_and_clock_unchanged':True,'page_errors':errors}
(ROOT/'evidence/editor-edge-ui-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
