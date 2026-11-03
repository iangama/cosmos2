"""Isolated cost of direct prescribed sources; never a native acceptance."""
from pathlib import Path
import hashlib
import json
import math
import os
import platform
import statistics
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'output/c212-em-cloud-native-staging'
sys.path.insert(0, str(SOURCE))
from cloud_core import Phase, System
from cloud_checkpoint import generation
from em_fields import Model, Source

destination = ROOT/'evidence/em-cloud-prescribed-sources-cost-native4.json'
assert not destination.exists()
i = np.arange(10000)
angle = i*math.pi*(3-math.sqrt(5))
x = np.column_stack((.4*np.cos(angle), .4*np.sin(angle), .4*(i+.5)/10000-.2))
v = np.column_stack((np.ones(10000), .1*np.sin(angle), np.zeros(10000)))
records = []
for count in (0, 1, 16, 128):
    sources = []
    for k in range(count):
        z = 1-2*(k+.5)/max(count, 1)
        a = k*math.pi*(3-math.sqrt(5))
        radius = math.sqrt(1-z*z)
        sources.append(Source(str(k), (8*radius*math.cos(a), 8*radius*math.sin(a), 8*z),
                              .02, (-1)**k*1e-10, (1e4, -2e4, 3e4)))
    system = System.uniform(Model(tuple(sources), uniform_B_T=(0, 0, 1)), 10000, 1., 1.)
    phase = Phase(x, v)
    for _ in range(2):
        phase, _ = system.step(phase, .002)
    costs = []
    for _ in range(20):
        start = time.perf_counter()
        phase, _ = system.step(phase, .002)
        costs.append(time.perf_counter()-start)
    record = {'prescribed_sources': count, 'particles': 10000, 'dt_s': .002,
              'step_wall_s': costs, 'model_s_per_wall_s': .04/math.fsum(costs),
              'median_step_ms': statistics.median(costs)*1000,
              'final_phase_sha256': hashlib.sha256(phase._x+phase._v).hexdigest()}
    records.append(record)
    print(json.dumps(record), flush=True)

result = {'scope': 'Isolated CPU diagnostic,20steps after2warmup; not a sustained/native performance approval. '
                   'Same10k q=m=1 cloud anddt.002; static shell sources carry charge and dipole, uniform B=1T.',
          'generation': generation(), 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'logical_processors': os.cpu_count(), 'processor': platform.processor(), 'runs': records}
destination.write_text(json.dumps(result, indent=2)+'\n')
