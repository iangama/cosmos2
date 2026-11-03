"""Native256 active scene, final identity, archives and owner preservation."""
from pathlib import Path
import copy,hashlib,json,subprocess,time,urllib.request
from cef_page import Page
ROOT=Path(__file__).resolve().parents[1];BASE='http://127.0.0.1:4700/api/'
pointer=ROOT/'user/sessions/latest.json';saved=pointer.read_bytes();errors=[]
def get():return json.load(urllib.request.urlopen(BASE+'state',timeout=65))['physics']
def post(command,**parameters):return json.load(urllib.request.urlopen(urllib.request.Request(BASE+'command',data=json.dumps({'command':command,**parameters}).encode(),headers={'Content-Type':'application/json'}),timeout=65))
def idle(page):page.wait_for_function('!pending',timeout=65000);time.sleep(.1)
try:
 with Page() as page:
  page.on('pageerror',lambda error:errors.append(str(error)));page.goto('http://127.0.0.1:4700/');page.wait_for_function('appState!==null');page.locator('#ui-scale').select_option('1')
  post('enter');page.evaluate('updateState()');idle(page)
  page.locator('#fixture').select_option('256');page.locator('#reset').click();idle(page)
  page.wait_for_function('appState.physics.bodies.length===256')
  p=get();assert p['scientific_generation']['model_version']=='3.12.0' and p['population_contract']['active_mass_count']==256 and p['population_contract']['all_active_masses_gravitate']
  page.evaluate('document.getElementById("body-editor").open=true');page.locator('#edit-body').select_option('p255');page.locator('#prepare-body-edit').click();idle(page)
  assert page.evaluate('bodyEditSnapshot?.body==="p255"&&document.getElementById("edit-body").options.length===256')
  before=get();page.locator('#save').click();idle(page);post('resume');time.sleep(.8);post('pause');post('load');page.evaluate('updateState()');idle(page)
  restored=get();assert restored['bodies']==before['bodies'] and restored['time']==before['time'] and restored['conservation']==before['conservation']
  started=time.perf_counter();post('atlas');post('enter');reentry_s=time.perf_counter()-started;assert get()['bodies']==before['bodies'];page.evaluate('updateState()');idle(page)
  page.evaluate('document.getElementById("body-editor").open=false');page.locator('#lab-home').click();idle(page)
  subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-p256.png'],check=True,capture_output=True)
finally:
 try:post('atlas')
 finally:pointer.write_bytes(saved)
assert not errors,errors
report={'status':'installed_p256_native_verified','active_mass_count':256,'last_identity_selectable':True,'reenter_same_256_scene_wall_s':reentry_s,'save_load_phase_reference_exact':True,'owner_pointer_preserved':pointer.read_bytes()==saved,'page_errors':errors,'scope':'Native scene/UI; formal256 profile separate'}
(ROOT/'evidence/p256-ui-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
