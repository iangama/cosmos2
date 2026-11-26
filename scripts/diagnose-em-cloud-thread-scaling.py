"""Controlled thread-count diagnostic using unchanged F helper and fixed fixture."""
from pathlib import Path
import argparse
import functools
import hashlib
import json
import statistics
import sys
import time
import psutil

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--label',required=True)
parser.add_argument('--profile',default='c212timesrcb');args=parser.parse_args()
assert args.label.isalnum() and args.profile.isalnum()
destination=ROOT/f'evidence/em-cloud-thread-scaling-{args.label}.json';assert not destination.exists()
CANDIDATE=ROOT/'output/c212-em-time-product'
sys.path.insert(0,str(CANDIDATE/'em-cloud'))
from cloud_checkpoint import load, generation
import cloud_native
raw=json.loads((ROOT/f'evidence/native-emcloud-{args.profile}.json').read_bytes())
system,seed,dt,acting=load(ROOT/raw['fixture_checkpoint'])
assert seed.count==10000 and dt==.002 and len(system.model.sources)==128
original=cloud_native.step;process=psutil.Process();owner=(ROOT/'user/sessions/latest.json').read_bytes()
reference=None
result={'scope':'Isolated fixed256-step thread-count diagnostic, not native throughput acceptance or a product configuration change.',
        'candidate':str(CANDIDATE.relative_to(ROOT)),'profile':args.profile,
        'scientific_generation':generation(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'thread_order':[8,6,4,2,1,1,2,4,6,8],'runs':[],'completed':False}
try:
    for index,threads in enumerate(result['thread_order']):
        cloud_native.step=functools.partial(original,thread_count=threads)
        phase=seed
        for _ in range(16):phase,_=system.step(phase,dt,**acting)
        phase=seed;values=[];psutil.cpu_percent(percpu=True)
        cpu0=process.cpu_times();began=time.perf_counter()
        for _ in range(256):
            step_start=time.perf_counter();phase,work=system.step(phase,dt,**acting)
            values.append((time.perf_counter()-step_start)*1000)
        elapsed=time.perf_counter()-began;cpu1=process.cpu_times()
        digest=hashlib.sha256(phase._x+phase._v+work['electric_work_J'].tobytes()+work['kinetic_change_J'].tobytes()).hexdigest()
        if reference is None:reference=digest
        assert digest==reference,(index,threads)
        values.sort()
        row={'run':index+1,'threads':threads,'steps':256,'elapsed_s':elapsed,
             'model_s_per_wall_s':256*dt/elapsed,'median_step_ms':statistics.median(values),
             'p95_step_ms':values[int(.95*(len(values)-1))],'max_step_ms':max(values),
             'process_CPU_seconds':cpu1.user+cpu1.system-cpu0.user-cpu0.system,
             'total_CPU_percent_per_logical_processor':psutil.cpu_percent(percpu=True),
             'final_phase_and_work_sha256':digest,'exact_across_thread_counts':True}
        result['runs'].append(row)
        destination.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(row),flush=True)
    result.update(completed=True,owner_pointer_preserved=(ROOT/'user/sessions/latest.json').read_bytes()==owner)
finally:
    cloud_native.step=original
    destination.write_text(json.dumps(result,indent=2)+'\n')
