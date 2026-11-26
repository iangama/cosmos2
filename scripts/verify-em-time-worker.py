"""Real worker numeric timing, legacy core futures and sealed preference tests."""
from pathlib import Path
from copy import deepcopy
import hashlib
import argparse
import json
import math
import queue
import subprocess
import sys
import threading
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
CANDIDATE=ROOT/'output/c212-em-time-product'
BASE=ROOT/'output/c212-em-cloud-native-product'
sys.path[:0]=[str(CANDIDATE/'em'),str(CANDIDATE/'app')]
from em_experiment import generation
from em_timing import execution_generation
import em_time_laboratory as adjunct

parser=argparse.ArgumentParser();parser.add_argument('--label',default='initial');args=parser.parse_args()
assert args.label.isalnum() and len(args.label)<=20
destination=ROOT/('evidence/em-time-worker-check.json' if args.label=='initial' else 'evidence/em-time-worker-'+args.label+'-check.json');assert not destination.exists()
storage=CANDIDATE/'c212-em-worker'/('timing-test-'+uuid.uuid4().hex[:12]);storage.mkdir()
worker=subprocess.Popen([sys.executable,'-u',str(CANDIDATE/'em/em_worker.py'),'--storage',str(storage)],
                        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
messages=queue.Queue();latest=None;serial=0;refused=[];futures=[]
def reader():
    for line in worker.stdout:messages.put(json.loads(line))
    messages.put({'type':'EOF'})
threading.Thread(target=reader,daemon=True).start()
ready=messages.get(timeout=10);assert ready['type']=='ready' and ready['protocol']==2
latest=messages.get(timeout=10);assert latest['type']=='snapshot'

def stable():
    return {k:deepcopy(latest[k]) for k in ('system_id','edit_token','revision','time_s','paused','experiment','editor','time_preferences','scientific_generation','execution_generation')}
def guard():
    return {k:latest[k]for k in ('system_id','edit_token','revision','frame')}|{'expected_time_s':latest['time_s']}
def command(name,error=False,**values):
    global serial,latest
    serial+=1
    request={'id':serial,'command':name,**(guard() if name not in ('pause','resume','snapshot','quit') else {}),**values}
    if name in ('set_rate','set_timestep'):
        key='expected_rate' if name=='set_rate' else 'expected_dt_s'
        request.setdefault(key,latest['requested_model_s_per_wall_s'] if name=='set_rate' else latest['experiment']['dt_s'])
    worker.stdin.write(json.dumps(request)+'\n');worker.stdin.flush()
    while True:
        value=messages.get(timeout=15)
        if value['type']=='snapshot':latest=value
        elif value.get('id')==serial:
            assert value['type']==('error' if error else 'ack'),value
            return value
        else:assert value['type']!='EOF','Worker stopped: '+worker.stderr.read()

def reference(payload,steps):
    program='''import sys,json
sys.path.insert(0,sys.argv[1])
from em_experiment import Experiment
data=json.load(sys.stdin);ex=Experiment.from_payload(data['experiment']);ex.advance(data['steps']);print(json.dumps(ex.payload(),allow_nan=False))
'''
    result=subprocess.run([sys.executable,'-Xutf8','-c',program,str(BASE/'em')],input=json.dumps({'experiment':payload,'steps':steps}),capture_output=True,text=True,encoding='utf-8',check=True)
    return json.loads(result.stdout)

def advance(steps):
    for count in [32]*(steps//32)+([steps%32] if steps%32 else []):command('advance',steps=count)

owner=(ROOT/'user/sessions/latest.json').read_bytes()
try:
    expected=json.loads((ROOT/'evidence/native-em128-c212mutfixa.json').read_bytes())['scientific_generation']
    assert generation()==expected==latest['scientific_generation']
    assert latest['execution_generation']==execution_generation()
    for preset in ('helix','coulomb','dipole'):
        command('load_preset',preset=preset)
        initial=deepcopy(latest['experiment']);expected_future=reference(initial,777)
        advance(777);assert latest['experiment']==expected_future
        before=stable();command('set_rate',value=.5)
        assert latest['experiment']==before['experiment'] and latest['editor']==before['editor'] and latest['revision']==before['revision']
        before=stable();command('set_timestep',dt_s=.0005)
        assert latest['experiment']['phase']==before['experiment']['phase'] and latest['editor']==before['editor']
        assert latest['revision']==before['revision'] and latest['edit_token']==before['edit_token']
        changed=deepcopy(latest['experiment']);expected_future=reference(changed,777)
        advance(777);assert latest['experiment']==expected_future
        futures.append({'preset':preset,'legacy_steps_exact':777,'changed_timestep_future_exact':777,'phase_editor_and_reference_preserved_on_timestep_change':True})
    for name,key,values in [('set_rate','value',[True,False,0,-1,101,None,'1',float('nan'),float('inf')]),
                            ('set_timestep','dt_s',[True,False,0,-1,2,None,'.001',float('nan'),float('inf'),1e-300])]:
        for value in values:
            before=stable();command(name,error=True,**{key:value});assert stable()==before;refused.append(name+':'+repr(value))
        for key2,value in [('system_id','stale'),('edit_token','stale'),('revision',-1),('frame','wrong'),('expected_time_s',-1),('unknown',0)]:
            before=stable();command(name,error=True,**{key:(1 if name=='set_rate' else .001),key2:value});assert stable()==before;refused.append(name+':'+key2)
        baseline='expected_rate' if name=='set_rate' else 'expected_dt_s'
        before=stable();command(name,error=True,**{key:(1 if name=='set_rate' else .001),baseline:-1});assert stable()==before;refused.append(name+':'+baseline)
    command('load_preset',preset='helix')
    for i in range(71):command('set_timestep',dt_s=.0005 if i%2==0 else .001)
    prefs=deepcopy(latest['time_preferences']);assert len(prefs['timestep_changes'])==64 and prefs['dropped_timestep_changes']==7
    command('set_rate',value=.5);command('save',file='timing');saved=stable();adjunct.save(storage,'timing',latest)
    original=(storage/'timing.timing.json').read_bytes();envelope=json.loads(original)
    invalid=[('rate_bool',lambda b:b['preferences'].update(rate=True)),('negative_rate',lambda b:b['preferences'].update(rate=-1)),
             ('extra_preferences',lambda b:b['preferences'].update(extra=True)),('wrong_generation',lambda b:b['execution_generation'].update(protocol=99)),
             ('wrong_checkpoint',lambda b:b.update(checkpoint_sha256='0'*64)),('wrong_schema',lambda b:b.update(schema=True)),
             ('future_event',lambda b:b['preferences']['timestep_changes'][-1].update(time_s=1e9)),
             ('wrong_dt',lambda b:b['preferences']['timestep_changes'][-1].update(dt_after_s=.03))]
    for label,mutate in invalid:
        bad=deepcopy(envelope);mutate(bad['payload']);bad['sha256']=hashlib.sha256(adjunct.canonical(bad['payload'])).hexdigest();(storage/'timing.timing.json').write_text(json.dumps(bad))
        before=stable()
        try:adjunct.load(storage,'timing',latest['execution_generation'])
        except ValueError:pass
        else:raise AssertionError('Invalid preference accepted: '+label)
        assert stable()==before;refused.append('adjunct:'+label)
    for label,raw in [('not_object',b'[]'),('duplicate',b'{"payload":{},"payload":{},"sha256":"0"}'),('oversized',b' '*32769)]:
        (storage/'timing.timing.json').write_bytes(raw)
        try:adjunct.load(storage,'timing',latest['execution_generation'])
        except ValueError:pass
        else:raise AssertionError('Malformed adjunct accepted: '+label)
        refused.append('adjunct:'+label)
    (storage/'timing.timing.json').write_bytes(original)
    command('set_rate',value=2);command('set_timestep',dt_s=.001)
    preferences=adjunct.load(storage,'timing',latest['execution_generation']);command('load',file='timing',**preferences)
    assert latest['experiment']==saved['experiment'] and latest['editor']==saved['editor'] and latest['time_preferences']==saved['time_preferences']
    command('set_rate',value=2);command('resume');time.sleep(.15)
    before=deepcopy(latest['experiment']['phase']);command('set_rate',value=.5)
    assert latest['requested_model_s_per_wall_s']==.5 and not latest['paused']
    started=time.perf_counter();ack=command('pause');pause_ms=(time.perf_counter()-started)*1000;assert ack['elapsed_ms']<=pause_ms<=250
    command('load',file='timing');assert latest['requested_model_s_per_wall_s']==1 and latest['time_preferences']['timestep_changes']==[] and latest['experiment']==saved['experiment']
    assert (ROOT/'user/sessions/latest.json').read_bytes()==owner
    report={'status':'numeric_timing_real_worker_legacy_futures_and_sealed_preferences_verified',
            'futures':futures,'refusals_without_mutation':refused,'bounded_timestep_history':{'retained':64,'dropped':7},
            'saved_preferences_roundtrip_exact':True,'legacy_checkpoint_default_rate1_and_preserved_dt':True,
            'rate_changed_while_running':True,'pause_wall_ms':pause_ms,'owner_pointer_preserved':True,
            'scientific_generation':generation(),'execution_generation':execution_generation(),
            'source_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in (Path(__file__),CANDIDATE/'em/em_timing.py',CANDIDATE/'em/em_worker.py',CANDIDATE/'app/em_time_laboratory.py')},
            'scope':'Numeric controls only, unchanged core0.4; no CEF, restart, throughput or full C2-12 acceptance.'}
    destination.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'future_cases':len(futures),'refusals':len(refused),'pause_ms':pause_ms}),flush=True)
finally:
    if worker.poll() is None:
        command('quit');worker.wait(timeout=10)
