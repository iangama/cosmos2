"""Bounded source128 CPU profile; no engine or graphics performance claim."""
from pathlib import Path
import hashlib
import json
import math
import statistics
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT/'output/c212-em-cloud-native-staging'
sys.path.insert(0, str(STAGE))
import cloud_native as native
from cloud_core import Phase, System
from cloud_checkpoint import generation
from em_fields import Model, Source

destination = ROOT/'evidence/em-cloud-native-thread-profile-d.json'
assert not destination.exists()
i = np.arange(10000)
a = i*math.pi*(3-math.sqrt(5))
x = np.column_stack((.4*np.cos(a), .4*np.sin(a), .4*(i+.5)/10000-.2))
v = np.column_stack((np.ones(10000), .1*np.sin(a), np.zeros(10000)))
sources = []
for k in range(128):
    z = 1-2*(k+.5)/128
    a = k*math.pi*(3-math.sqrt(5))
    r = math.sqrt(1-z*z)
    sources.append(Source(str(k), (8*r*math.cos(a), 8*r*math.sin(a), 8*z),
                          .02, (-1)**k*1e-10, (1e4, -2e4, 3e4)))
system = System.uniform(Model(tuple(sources), uniform_B_T=(0, 0, 1)), 10000, 1, 1)
runs = []
for count in (1, 2, 4, 6, 8):
    for kind in ('fields', 'complete_immutable_step'):
        phase = Phase(x, v)
        for _ in range(5):
            native.evaluate(system._native_model, phase.positions(), potential=False, thread_count=count)
        costs = []
        began_cpu = time.process_time()
        for _ in range(200):
            start = time.perf_counter()
            if kind == 'fields':
                native.evaluate(system._native_model, phase.positions(), potential=False, thread_count=count)
            else:
                xx, vv, work, kinetic = native.step(system._native_model, phase.positions(), phase.velocities(),
                                                  system.charges(), system.masses(), .002, True, True,
                                                  thread_count=count)
                phase = Phase._internal(xx, vv, phase.time_s+.002)
                native.immutable(work)
                native.immutable(kinetic)
            costs.append(time.perf_counter()-start)
        cpu = time.process_time()-began_cpu
        record = {'threads': count, 'kind': kind, 'wall_samples_s': costs,
                  'mean_wall_ms': math.fsum(costs)/len(costs)*1000, 'median_wall_ms': statistics.median(costs)*1000,
                  'process_CPU_s': cpu, 'model_s_per_wall_s': .002*len(costs)/math.fsum(costs) if kind != 'fields' else None}
        runs.append(record)
        print(json.dumps({k: v for k, v in record.items() if k != 'wall_samples_s'}), flush=True)
result = {'runs': runs, 'scientific_generation': generation(),
          'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in [Path(__file__), *[p for p in STAGE.iterdir() if p.is_file()]]},
          'scope': '200 isolated repetitions per condition. Thread tuning evidence, not native sustained approval.'}
destination.write_text(json.dumps(result, indent=2)+'\n')
