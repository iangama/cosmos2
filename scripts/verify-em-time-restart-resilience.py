"""Fresh boot exact future and actual parent/native partial-save reporting."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import subprocess
import sys
import urllib.request
import uuid
from cef_page import Page
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parents[1];CANDIDATE=ROOT/'output/c212-em-time-product'
STORAGE=CANDIDATE/'c212-em-worker/product'
sys.path[:0]=[str(CANDIDATE/'em'),str(CANDIDATE/'app')]
from em_experiment import Experiment
from em_laboratory import EMLaboratory
import em_time_laboratory as adjunct

destination=ROOT/'evidence/em-time-restart-resilience-check.json';assert not destination.exists()
expected=json.loads((ROOT/'output/c212-em-time-restart-expected.json').read_bytes())
session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert Path(session['serverScript']).resolve()==(CANDIDATE/'app/server.py').resolve()
assert session['started']!=expected['previous_session']['started']
owner=(ROOT/'user/sessions/latest.json').read_bytes();originals={suffix:(STORAGE/('ui-phase'+suffix)).read_bytes()for suffix in expected['files_sha256']}
def current():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/em/state',timeout=10))
def guard(state):return {k:state[k]for k in ('system_id','edit_token','revision','frame')}|{'expected_time_s':state['time_s']}
def request(name,**values):
    req=urllib.request.Request('http://127.0.0.1:4700/api/em/command',data=json.dumps({'command':name,**guard(current()['state']),**values}).encode(),headers={'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(req,timeout=20))
def idle(page):page.wait_for_function('state&&state.paused&&!pending&&nativeState?.confirmation?.metadata.time_s===state.time_s&&!nativeState.error',timeout=30000)

with Page() as page:
    page.goto('http://127.0.0.1:4700/');page.wait_for_function('typeof appState!=="undefined"&&appState!==null')
    page.locator('#em-lab').click();idle(page)
    initial=current()['state'];assert initial['time_s']==0 and initial['requested_model_s_per_wall_s']==1 and not initial['time_preferences']['timestep_changes']
    page.locator('#restore').click();idle(page);restored=current()['state']
    for key in ('experiment','editor','time_preferences','scientific_generation','execution_generation'):assert restored[key]==expected[key],key
    assert page.evaluate('Number(document.getElementById("integration-step").value)')==expected['experiment']['dt_s']
    assert page.evaluate('Number(document.getElementById("model-rate").value)')==expected['time_preferences']['rate']
    program='''import sys,json
sys.path.insert(0,sys.argv[1]);from em_experiment import Experiment
ex=Experiment.from_payload(json.load(sys.stdin));ex.advance(777);print(json.dumps(ex.payload()))
'''
    reference=subprocess.run([sys.executable,'-Xutf8','-c',program,str(ROOT/'output/c212-em-cloud-native-product/em')],input=json.dumps(restored['experiment']),capture_output=True,text=True,encoding='utf-8',check=True)
    for steps in [32]*24+[9]:assert not request('advance',steps=steps).get('display')
    assert current()['state']['experiment']==json.loads(reference.stdout)
    assert current()['state']['editor']==expected['editor'] and current()['state']['time_preferences']==expected['time_preferences']
    request('load',file='ui-phase');page.evaluate('refresh(true)');idle(page)
    page.locator('#native-return').click();page.wait_for_function('location.pathname==="/"')

local=EMLaboratory();view_writer=local._save_view;time_writer=adjunct.save
class Atlas:
    def status(self):return {'mode':'atlas'}
partial=[]
try:
    local.enter(Atlas())
    def command(name,**values):return local.command({'command':name,**guard(local._current()),**values})
    command('set_rate',value=.5,expected_rate=1.)
    original=deepcopy(local._current()['experiment'])
    def failure(*_args,**_kwargs):raise PermissionError('Injected preference write failure')
    for label in ('native_view','timing_preferences'):
        if label=='native_view':local._save_view=failure
        else:adjunct.save=failure
        name='partial-'+uuid.uuid4().hex[:12];result=command('save',file=name)
        assert result['persistence']['state']=='partial' and result['persistence']['scientific_checkpoint_saved']
        assert result['persistence']['native_view_saved']==(label=='timing_preferences') and not result['persistence']['timing_preferences_saved']
        assert not result.get('display') and local.native.error is None
        assert json.loads(json.dumps(Experiment.load(STORAGE/(name+'.json')).payload()))==original
        assert local._current()['experiment']==original
        partial.append({'failed':label,'persistence':result['persistence'],'checkpoint_valid_and_phase_unchanged':True})
        local._save_view=view_writer;adjunct.save=time_writer
    name='complete-'+uuid.uuid4().hex[:12];result=command('save',file=name)
    assert result['persistence']=={'state':'complete','scientific_checkpoint_saved':True,'native_view_saved':True,'timing_preferences_saved':True}
    restored=adjunct.load(STORAGE,name,local._current()['execution_generation']);assert restored['time_preferences']['rate']==.5
finally:
    local._save_view=view_writer;adjunct.save=time_writer
    local.leave();local.close()

with connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.2,ping_interval=None) as ws:
    ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
    ws.send(json.dumps({'topic':1,'type':'luascript','payload':{'script':'return {clean=not openspace.hasSceneGraphNode("C2EMRoot")}','return':True}}))
    assert json.loads(ws.recv(timeout=10))['payload']['1']['clean']
assert (ROOT/'user/sessions/latest.json').read_bytes()==owner
for suffix,raw in originals.items():assert (STORAGE/('ui-phase'+suffix)).read_bytes()==raw
report={'status':'fresh_native_restart_exact_core04_future_and_partial_preference_writes_verified',
        'restart_reference':expected,
        'session':session,'previous_session':expected['previous_session'],'restored_science_editor_timing_and_controls_exact':True,
        'future_steps_exact_against_frozen_core04_process':777,'partial_save_cases':partial,
        'successful_save_acknowledges_all_three_files':True,'scientific_and_auxiliary_saves_preserved':True,
        'no_orphan_native_nodes':True,'owner_pointer_preserved':True,
        'source_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()for p in [
            Path(__file__),CANDIDATE/'em/em_worker.py',CANDIDATE/'em/em_timing.py',CANDIDATE/'app/em_laboratory.py',CANDIDATE/'app/em_time_laboratory.py',CANDIDATE/'app/ui/em/app.js']},
        'scope':'Actual normal boot, native worker and injected preference I/O failures. No formal128/10k throughput or installed promotion.'}
destination.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'partial_cases':len(partial),'future_steps':777}),flush=True)
