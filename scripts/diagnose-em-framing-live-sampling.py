"""Two paused potential measurements in fresh I, same formal fixture."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time
import urllib.request
import urllib.error
from cef_page import Page
ROOT=Path(__file__).resolve().parents[1];H=ROOT/'output/c212-em-framing-product'
sys.path.insert(0,str(H/'em'));from em_experiment import Experiment
parser=argparse.ArgumentParser();parser.add_argument('--label',default='provider1');args=parser.parse_args();assert args.label.isalnum()
dest=ROOT/f'evidence/em-framing-potential-{args.label}-live-diagnostic.json';assert not dest.exists()
fixture=json.loads((ROOT/'evidence/native-em128-c212hpotb.json').read_bytes())['fixture']
Experiment.from_payload(fixture).save(H/'c212-em-worker/product'/('sampling-'+args.label+'.json'))
session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'));assert session['emFramingCandidate']
owner=(ROOT/'user/sessions/latest.json').read_bytes();runs=[]
def state():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/em/state',timeout=10))['state']
def command(name,**values):
    s=state();g={k:s[k] for k in ('system_id','edit_token','revision','frame')}|{'expected_time_s':s['time_s']}
    request=urllib.request.Request('http://127.0.0.1:4700/api/em/command',data=json.dumps({'command':name,**g,**values}).encode(),headers={'Content-Type':'application/json'})
    began=time.perf_counter()
    try:return {'status':200,'response':json.load(urllib.request.urlopen(request,timeout=20)),'wall_ms':(time.perf_counter()-began)*1000}
    except urllib.error.HTTPError as e:return {'status':e.code,'error':json.load(e),'wall_ms':(time.perf_counter()-began)*1000}
with Page() as p:
    p.goto('http://127.0.0.1:4700/em.html');p.wait_for_function('state&&state.paused&&!pending&&nativeState.active',timeout=30000)
    assert command('load',file='sampling-'+args.label)['status']==200
    for i in range(64):assert command('set_timestep',dt_s=.0005 if i%2==0 else .001,expected_dt_s=state()['experiment']['dt_s'])['status']==200
    p.wait_for_function('state.experiment.mode==="mutual_electrostatic"&&state.experiment.system.ids.length===128')
    p.locator('[data-panel="layers"]').click();p.locator('#measure').click();p.wait_for_function('!pending&&map?.samples.length===97',timeout=30000)
    assert command('configure_potential',changes={'visible':True,'count_axis':33,'levels_V':None})['status']==200
    before=state()
    for i in range(2):
        r=command('sample_potential')
        if r['status']==200:
            response=r.pop('response');r.update(numeric_ms=response['result']['batch_protocol']['elapsed_wall_ms'],display=response.get('display'))
        assert state()['experiment']==before['experiment'];r['repeat']=i+1;runs.append(r);print(json.dumps(r),flush=True)
    p.locator('#native-return').click();p.wait_for_function('location.pathname==="/"')
assert owner==(ROOT/'user/sessions/latest.json').read_bytes()
dest.write_text(json.dumps({'status':'I_initial_same_fixture_sampling_diagnostic','session':session,'runs':runs,'scientific_phase_preserved':True,'owner_pointer_preserved':True,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scope':'Original33x33/128source/64timing/2s settings with97native arrows in fresh I with exact exclusion-mask optimization. Diagnostic only, no formal frames or A attribution.'},indent=2)+'\n')
