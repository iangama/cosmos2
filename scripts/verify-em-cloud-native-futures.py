"""Separate-process NumPy/native comparisons of every phase/work/time snapshot."""
from pathlib import Path
import hashlib
import json
import math
import subprocess
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
STAGES = (ROOT/'output/c212-em-cloud-product/em-cloud', ROOT/'output/c212-em-cloud-native-staging')
OUTPUT = ROOT/'output/em-cloud-native-e-future-comparison'

def child(stage, case, target):
    sys.path.insert(0, str(stage))
    from cloud_core import System, Phase
    from em_fields import Model, Source
    n, steps, count, acting_e, acting_b = case
    rng = np.random.default_rng(201026+n)
    x = rng.normal(size=(n, 3))*.2
    v = rng.normal(size=(n, 3))*.1
    sources = []
    for j in range(count):
        z = 1-2*(j+.5)/count
        a = j*math.pi*(3-math.sqrt(5))
        r = math.sqrt(1-z*z)
        sources.append(Source(str(j), (8*r*math.cos(a), 8*r*math.sin(a), 8*z),
                              .02, (-1)**j*1e-10, (1e4, -2e4, 3e4)))
    system = System(Model(tuple(sources), (.1, -.2, .3), (.2, .1, 1.)),
                    rng.uniform(-1, 1, n), rng.uniform(.5, 2, n))
    phase = Phase(x, v)
    phases, work, energy, times = [], [], [], []
    for _ in range(steps):
        phase, d = system.step(phase, .002, electric_acting=acting_e, magnetic_acting=acting_b)
        phases.append(np.column_stack((phase.positions(), phase.velocities())))
        work.append(d['electric_work_J'])
        energy.append(d['kinetic_change_J'])
        times.append([phase.time_s, d['sample_time_s']])
    np.savez(target, phase=np.array(phases), work=np.array(work), energy=np.array(energy), time=np.array(times))

if len(sys.argv) > 1:
    child(Path(sys.argv[1]), json.loads(sys.argv[2]), Path(sys.argv[3]))
else:
    assert not OUTPUT.exists()
    OUTPUT.mkdir()
    cases = []
    for n, steps, count in ((1, 777, 0), (16, 777, 2), (128, 64, 128), (10000, 8, 128)):
        for acting_e, acting_b in ((False, False), (True, False), (False, True), (True, True)):
            case = [n, steps, count, acting_e, acting_b]
            paths = []
            for implementation, stage in enumerate(STAGES):
                path = OUTPUT/(str(len(cases))+'-'+str(implementation)+'.npz')
                subprocess.run([sys.executable, str(Path(__file__).resolve()), str(stage),
                                json.dumps(case), str(path)], check=True, capture_output=True)
                paths.append(path)
            errors = {}
            with np.load(paths[0], allow_pickle=False) as old, np.load(paths[1], allow_pickle=False) as new:
                assert np.array_equal(old['time'], new['time'])
                for key in ('phase', 'work', 'energy'):
                    error = float(np.max(abs(old[key]-new[key])))/max(1., float(np.max(abs(old[key]))))
                    assert error <= 1e-11, (case, key, error)
                    errors[key+'_normalized_max_error'] = error
            record = {'case': case, **errors, 'time_and_sample_time_bit_exact': True,
                      'all_steps_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
            cases.append(record)
            print(json.dumps(record), flush=True)
    files = [p for stage in STAGES for p in stage.iterdir() if p.is_file()]+[Path(__file__)]
    result = {'status': 'NumPy_and_native_separate_process_full_phase_work_time_futures_agree_within_frozen_tolerance',
              'cases': cases, 'tolerance': 1e-11,
              'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
              'scope': 'Every saved collective step of listed fixtures. Numeric comparison, not a bitwise cross-implementation/migration or native performance claim.'}
    (ROOT/'evidence/em-cloud-native-e-futures-check.json').write_text(json.dumps(result, indent=2)+'\n')
