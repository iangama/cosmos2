"""Trace unchanged H slice stages with a separate real worker and storage."""
from pathlib import Path
from copy import deepcopy
import argparse
import os
import hashlib
import json
import sys
import time

ROOT=Path(__file__).resolve().parents[1];H=ROOT/'output/c212-em-cloud-editor-product'
sys.path.insert(0,str(H/'app'));sys.path.insert(0,str(H/'em'))
import em_laboratory
import em_slice
from em_experiment import Experiment
parser=argparse.ArgumentParser();parser.add_argument('--label',default='release2');args=parser.parse_args();assert args.label.isalnum()
destination=ROOT/f'evidence/em-cloud-editor-potential-sampling-{args.label}-diagnostic.json';assert not destination.exists()
os.environ['PYTHONUTF8']='1'
owner=(ROOT/'user/sessions/latest.json').read_bytes()
fixture=json.loads((ROOT/'evidence/native-em128-c212hpotb.json').read_bytes())['fixture']
storage=H/('c212-em-worker/sampling-'+args.label+'-diagnostic');assert not storage.exists();storage.mkdir()
em_laboratory.STORAGE=storage
ex=Experiment.from_payload(fixture);ex.save(storage/'fixture.json')
lab=em_laboratory.EMLaboratory();runs=[];original=em_slice.contours;stages=[]
def guarded():
    s=lab._current();return {k:s[k] for k in ('system_id','edit_token','revision','frame')}|{'expected_time_s':s['time_s']}
def geometry(*args,**kwargs):
    began=time.perf_counter();cpu=time.process_time();result=original(*args,**kwargs)
    stages.append({'stage':'contours','wall_ms':(time.perf_counter()-began)*1000,'parent_cpu_ms':(time.process_time()-cpu)*1000,'segments':len(result['segments'])});return result
em_slice.contours=geometry
try:
    with lab.command_lock:
        lab._start();lab._worker({'command':'load','file':'fixture',**guarded()})
        for i in range(64):
            s=lab._current();lab._worker({'command':'set_timestep',**guarded(),'dt_s':.0005 if i%2==0 else .001,'expected_dt_s':s['experiment']['dt_s']})
        before=lab._current()
        axis=[-3+6*i/32 for i in range(33)];grid={'x_m':axis,'y_m':axis,'z_m':0.}
        for repeat in range(3):
            stages=[];began=time.perf_counter();cpu=time.process_time()
            def query(value):
                start=time.perf_counter();result=lab._worker(value)
                stages.append({'stage':'worker_batch','points':len(value['points_m']),'wall_ms':(time.perf_counter()-start)*1000,'worker_elapsed_ms':result['elapsed_ms']});return result
            try:
                layer=em_slice.sample_slice(lab._current,query,lab.command_lock,grid,None)
                outcome={'completed':True,'numeric_ms':layer['batch_protocol']['elapsed_wall_ms'],'segments':len(layer['geometry']['segments'])}
            except (ValueError,TimeoutError) as error:outcome={'completed':False,'error':type(error).__name__+': '+str(error)}
            outcome.update(repeat=repeat+1,wall_ms=(time.perf_counter()-began)*1000,parent_cpu_ms=(time.process_time()-cpu)*1000,stages=deepcopy(stages));runs.append(outcome)
            print(json.dumps(outcome),flush=True)
            assert lab._current()['experiment']==before['experiment']
finally:
    em_slice.contours=original
    try:lab.close()
    except Exception as error:
        runs.append({'cleanup_error':type(error).__name__+': '+str(error)})
        if lab.worker is not None and lab.worker.poll() is None:lab.worker.terminate();lab.worker.wait(timeout=5)
    assert (ROOT/'user/sessions/latest.json').read_bytes()==owner
    report={'status':'H_unchanged_slice_separate_real_worker_stage_diagnostic','runs':runs,'owner_pointer_preserved':True,
            'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),H/'app/em_slice.py',H/'app/em_potential.py',H/'app/em_laboratory.py',H/'em/em_worker.py']},
            'scope':'Separate worker/storage, same128fixture/64timing records/33grid and original2s budget. Contour wrapper records time only; no native/CEF throughput acceptance or retrospective cause for A.'}
    destination.write_text(json.dumps(report,indent=2)+'\n')
