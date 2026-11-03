"""Real child process, five presets, controls, pause, guarded persistence and probes."""
from pathlib import Path
import hashlib
import json
import queue
import subprocess
import sys
import threading
import time
import uuid

ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/c212-em-staging'
owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes()
storage=ROOT/'output/c212-em-worker'/('test-'+uuid.uuid4().hex)
process=subprocess.Popen([sys.executable,'-u',str(STAGE/'em_worker.py'),'--storage',str(storage)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
messages=queue.Queue();latest=None;serial=0
def reader():
    for line in process.stdout:
        try:messages.put(json.loads(line))
        except ValueError:messages.put({'type':'invalid_output','line':line})
    messages.put({'type':'closed'})
threading.Thread(target=reader,daemon=True).start()
def read(timeout=10):
    global latest
    value=messages.get(timeout=timeout)
    assert value['type'] not in ('invalid_output','closed'),value
    if value['type']=='snapshot':latest=value
    return value
def call(name,error=False,**args):
    global serial
    serial+=1;start=time.perf_counter()
    process.stdin.write(json.dumps({'id':serial,'command':name,**args},allow_nan=False)+'\n');process.stdin.flush()
    deadline=time.perf_counter()+10
    while time.perf_counter()<deadline:
        value=read()
        if value.get('id')==serial:
            assert value['type']==('error' if error else 'ack'),value
            return value,(time.perf_counter()-start)*1000
    raise TimeoutError(name)
def guard():
    return {k:latest[k] for k in ('system_id','edit_token','revision','frame')}|{'expected_time_s':latest['time_s']}
cases=[];pauses=[];rejections=[]
try:
    ready=read();assert ready['type']=='ready' and ready['protocol']==1
    while latest is None:read()
    for preset in ready['presets']:
        call('load_preset',**guard(),preset=preset)
        assert latest['paused'] and latest['time_s']==0
        ack,_=call('probe',**guard(),position_m=[10,0,0]);assert ack['result']['valid']
        baseline=ack['result'];before=latest['experiment']['phase']
        controls={'acting':False} if preset=='coulomb' else {'electric_acting':False,'magnetic_acting':False}
        call('set_controls',**guard(),controls=controls)
        assert latest['experiment']['phase']==before
        ack,_=call('probe',**guard(),position_m=[10,0,0]);assert ack['result']==baseline
        controls={k:True for k in controls};call('set_controls',**guard(),controls=controls)
        for _ in range(4):
            start=latest['time_s'];dt=latest['experiment']['dt_s'];call('resume')
            deadline=time.perf_counter()+10
            while latest['time_s']<start+5*dt:
                assert time.perf_counter()<deadline,'Worker did not advance'
                read()
            _,wall=call('pause');pauses.append(wall);assert latest['paused'] and wall<250
        call('save',**guard(),file=preset);saved=latest['experiment'];old_guard=guard()
        call('advance',**guard(),steps=32);assert latest['time_s']>saved['phase']['time_s']
        call('load',**guard(),file=preset);assert latest['experiment']==saved
        assert latest['edit_token']!=old_guard['edit_token']
        before=latest['experiment'];call('advance',error=True,**old_guard,steps=1);assert latest['experiment']==before
        rejections.append(preset+' stale token')
        cases.append({'preset':preset,'live_advancement':True,'four_pauses':True,'controls_preserve_reference_and_phase':True,'probe_valid':True,'save_advance_load_exact':True})
        print('worker '+preset+' passed',flush=True)
    if '--with-128' in sys.argv:
        sys.path.insert(0,str(STAGE))
        import math
        import itertools
        import numpy as np
        from em_fields import K_E
        from em_mutual import System,Phase
        from em_experiment import Experiment
        positions=tuple(itertools.islice(itertools.product((-4,-2,0,2,4),repeat=3),125))+((-6,0,0),(6,0,0),(0,6,0))
        charge=.1*math.sqrt(1/K_E)
        system=System(tuple(map(str,range(128))),tuple(charge*(-1)**k for k in range(128)),tuple([1.]*128),tuple([.01]*128))
        phase=Phase(positions,tuple([(0.,0.,0.)]*128));initial_d=system.diagnostics(phase)
        experiment=Experiment('mutual_electrostatic',system,phase,.001,{'acting':True})
        experiment.save(storage/'population128.json');call('load',**guard(),file='population128')
        rates=[]
        for _ in range(5):
            start=latest['time_s'];began=time.perf_counter();call('resume')
            deadline=time.perf_counter()+10
            while latest['time_s']<start+.005:
                assert time.perf_counter()<deadline,'128 charges did not advance'
                read()
            _,wall=call('pause');pauses.append(wall);assert wall<250
            rates.append((latest['time_s']-start)/(time.perf_counter()-began))
        final=Phase(**latest['experiment']['phase']);d=system.diagnostics(final)
        error=abs(d['energy_J']-initial_d['energy_J'])/initial_d['energy_scale_J'];assert error<1e-6
        assert len(final.position_m)==128 and final.position_m!=phase.position_m
        cases.append({'preset':'128 synthetic mutually interacting charges','five_pauses':True,'live_advancement':True,
            'elapsed_model_s':final.time_s,'energy_error_over_initial_K_plus_abs_U':error,
            'observed_model_s_per_wall_s_min':min(rates),'formal_frame_or_real_time_rate_acceptance':False})
        print('worker128 active charges passed',flush=True)
    for name,args in [('save',{'file':'../outside'}),('advance',{'steps':4096}),('load_preset',{'preset':'unknown'})]:
        before=latest['experiment'];call(name,error=True,**guard(),**args);assert latest['experiment']==before;rejections.append(name+' invalid input')
    call('resume');call('save',error=True,**guard(),file='running');rejections.append('save while running');call('pause')
    assert not (storage/'running.json').exists()
    call('quit');process.wait(timeout=5);assert process.returncode==0
    stderr=process.stderr.read();assert not stderr,stderr
    assert owner.read_bytes()==original
    report={'status':'isolated_EM_worker_five_presets_verified_not_installed','child_pid':process.pid,
        'cases':cases,'pause_samples':len(pauses),'pause_API_wall_max_ms':max(pauses),
        'rejected_without_replacing_state':rejections,'bounded_input_commands':32,'integration_quantum_steps':32,
        'stderr_empty':True,'clean_exit':True,'owner_pointer_preserved':True,'storage':str(storage),
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (STAGE/'em_worker.py',STAGE/'em_presets.py',STAGE/'em_experiment.py',STAGE/'em_fields.py',STAGE/'em_particles.py',STAGE/'em_mutual.py',STAGE/'constants.json',Path(__file__))},
        'scope':'Actual isolated worker IPC with continuously drained stdout; optional128-charge case proves evolution/conservation/pause on that fixture, not a formal native frame or requested-rate profile. No10k EM particles or body-catalogue acceptance.'}
    (ROOT/'evidence/em-worker-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
finally:
    if process.poll() is None:process.terminate();process.wait(timeout=5)
    assert owner.read_bytes()==original
