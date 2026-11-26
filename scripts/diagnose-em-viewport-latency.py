"""Bounded J latency diagnostic: original fixture,33²/128sources/64timing/2s.

Measure client guard/headers/transfer/parse and actual product CPU counters.
No product-source edits, sampling-limit changes or retrospective causation.
Run only after formal captures end.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import sys
import time
import urllib.request
import urllib.error
import psutil
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
J=ROOT/'output/c212-em-viewport-product'
parser=argparse.ArgumentParser();parser.add_argument('--label',required=True)
args=parser.parse_args();assert args.label.isalnum()
DEST=ROOT/f'evidence/em-viewport-latency-{args.label}-diagnostic.json';assert not DEST.exists()
session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert session['emViewportCandidate']
raw=json.loads((ROOT/'evidence/native-em128-c212jpota.json').read_bytes())
for name,digest in raw['configuration_sha256'].items():
    if name.startswith('output/c212-em-viewport-product/'):
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
sys.path.insert(0,str(J/'em'))
from em_experiment import Experiment
file='latency-'+args.label
Experiment.from_payload(raw['fixture']).save(J/'c212-em-worker/product'/(file+'.json'))
owner=(ROOT/'user/sessions/latest.json').read_bytes()
report={'completed':False,'session':session,'runs':[],'setup':{},'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def state():
    return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/em/state',timeout=10))['state']


def cpu():
    processes={}
    for pid in (session['app'],session['server']):
        root=psutil.Process(pid)
        for process in [root,*root.children(recursive=True)]:
            try:
                value=process.cpu_times()
                processes[str(process.pid)]={'name':process.name(),'cpu_s':value.user+value.system}
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    return {'utc':datetime.now(timezone.utc).isoformat(),'wall_s':time.perf_counter(),
            'processors':psutil.cpu_count(),'system':dict(psutil.cpu_times()._asdict()),'processes':processes}


def command(name,**values):
    start=time.perf_counter();s=state();guard_done=time.perf_counter()
    g={k:s[k] for k in ('system_id','edit_token','revision','frame')}|{'expected_time_s':s['time_s']}
    request=urllib.request.Request('http://127.0.0.1:4700/api/em/command',data=json.dumps({'command':name,**g,**values}).encode(),headers={'Content-Type':'application/json'})
    try:response=urllib.request.urlopen(request,timeout=20)
    except urllib.error.HTTPError as error:response=error
    headers=time.perf_counter();body=response.read();read=time.perf_counter();value=json.loads(body);parsed=time.perf_counter()
    return value,{'status':response.status,'total_with_guard_ms':(parsed-start)*1000,'guard_ms':(guard_done-start)*1000,
                  'request_to_headers_ms':(headers-guard_done)*1000,'body_transfer_ms':(read-headers)*1000,
                  'JSON_parse_ms':(parsed-read)*1000,'response_bytes':len(body)}


try:
    with Page() as page:
        page.goto('http://127.0.0.1:4700/')
        page.wait_for_function('typeof appState!=="undefined"&&appState')
        page.locator('#em-lab').click()
        page.wait_for_function('state&&state.paused&&!pending&&nativeState.active',timeout=30000)
        assert command('load',file=file)[1]['status']==200
        for index in range(64):
            assert command('set_timestep',dt_s=.0005 if index%2==0 else .001,expected_dt_s=state()['experiment']['dt_s'])[1]['status']==200
        page.wait_for_function('state.experiment.mode==="mutual_electrostatic"&&state.experiment.system.ids.length===128')
        page.locator('#interface-scale').select_option('1')
        if page.evaluate('workspacePanel')!='layers':page.locator('[data-panel="layers"]').click()
        page.locator('#measure').click();page.wait_for_function('!pending&&map?.samples.length===97',timeout=30000)
        original=state();assert len(original['time_preferences']['timestep_changes'])==64
        for repeat,visible in enumerate((True,False,True),1):
            assert command('configure_potential',changes={'visible':visible,'count_axis':33,'levels_V':None})[1]['status']==200
            before=cpu();value,timing=command('sample_potential');after=cpu()
            if timing['status']==200:
                layer=value['result'];assert len(layer['measurement']['samples'])==1089
                timing.update(numeric_ms=layer['batch_protocol']['elapsed_wall_ms'],display=value.get('display'),
                              batch_protocol=layer['batch_protocol'],layer_id=value['native_potential']['layer_id'])
            else:timing['error']=value
            assert state()['experiment']==original['experiment']
            timing.update(repeat=repeat,potential_visible=visible,host_before=before,host_after=after)
            report['runs'].append(timing)
            DEST.write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps({k:v for k,v in timing.items() if k not in ('host_before','host_after','batch_protocol','layer_id')}),flush=True)
        page.locator('#native-return').click();page.wait_for_function('location.pathname==="/"')
        assert owner==(ROOT/'user/sessions/latest.json').read_bytes()
        report.update(completed=True,scientific_phase_and_owner_preserved=True,
                      scope='Three bounded measurements with exact rejected J fixture/settings. CPU counters provide concurrent context only, not proof of cause for the earlier rejection or formal performance acceptance.')
finally:
    DEST.write_text(json.dumps(report,indent=2)+'\n')
