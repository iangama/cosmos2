"""General128-source Lorentz dynamics vs independent adaptive DOP853 and refinement."""
from pathlib import Path
import argparse
import hashlib
import inspect
import json
import math
import sys
import time
import numpy as np
import scipy
from scipy.integrate import solve_ivp
from scipy.integrate._ivp import rk, ivp, dop853_coefficients
from em_cloud_source_fixture import source_model, particles

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--label', required=True)
parser.add_argument('--steps', default='1280000,2560000,5120000')
args = parser.parse_args()
assert args.label.isalnum() and len(args.label)<=20
step_counts = tuple(map(int,args.steps.split(',')))
assert len(step_counts)==3 and min(step_counts)>0 and step_counts[1]==2*step_counts[0] and step_counts[2]==2*step_counts[1]
destination = ROOT/f'evidence/em-cloud-native-source128-intense-{args.label}.json'
assert not destination.exists()
STAGE = ROOT/'output/c212-em-cloud-native-staging'
sys.path.insert(0, str(STAGE))
from cloud_core import System, Phase
from cloud_checkpoint import generation
from em_fields import Model, Source

constants = json.loads((STAGE/'constants.json').read_bytes())
ke = 1/(4*math.pi*constants['vacuum_electric_permittivity_F_m']['value'])
mu4pi = constants['vacuum_magnetic_permeability_N_A2']['value']/(4*math.pi)
model = source_model()
for source in model['sources']:
    source['charge_C'] = (1 if source['charge_C']>0 else -1)*1e-10
source_x = np.array([s['position_m'] for s in model['sources']])
source_q = np.array([s['charge_C'] for s in model['sources']])
source_m = np.array([s['magnetic_moment_A_m2'] for s in model['sources']])
exclusion = np.array([s['exclusion_radius_m'] for s in model['sources']])

def fields(x):
    # Independent full-vector formula: no production field/helper calls, no
    # direction-first grouping or production compensated accumulator.
    d = x[:, None, :]-source_x
    radius = np.sqrt(np.sum(d*d, axis=2))
    assert np.all(radius > exclusion)
    electric = np.sum((ke*source_q/radius**3)[:, :, None]*d, axis=1)+model['uniform_E_V_m']
    magnetic = mu4pi*np.sum(3*d*np.sum(d*source_m, axis=2)[:, :, None]/radius[:, :, None]**5
                           -source_m/radius[:, :, None]**3, axis=1)+model['uniform_B_T']
    return electric, magnetic

def rhs(_time, y):
    x, v = y.reshape(2, 4, 3)
    e, b = fields(x)
    return np.array([v, e+np.cross(v, b)]).reshape(-1)

def energy(x, v):
    radius = np.linalg.norm(x[:, None, :]-source_x, axis=2)
    potential = np.array([math.fsum(ke*q/r for q, r in zip(source_q, row)) for row in radius])
    return .5*np.sum(v*v, axis=1)+potential

x0, v0 = particles()
indices = [0, 1234, 4321, 9999]
x0, v0 = x0[indices], v0[indices]
production = Model(tuple(Source(**s) for s in model['sources']), model['uniform_E_V_m'], model['uniform_B_T'])
e, b = fields(x0)
for k, x in enumerate(x0):
    s = production.evaluate(x)
    assert math.dist(e[k], s['electric_field_V_m'])/s['electric_scale_V_m'] < 1e-13
    assert math.dist(b[k], s['magnetic_field_T'])/s['magnetic_scale_T'] < 1e-13
references = []
duration = 20*math.pi
for tolerance in (1e-12, 2.5e-14):
    start = time.perf_counter()
    solution = solve_ivp(rhs, (0., duration), np.array([x0, v0]).reshape(-1),
                         method='DOP853', rtol=tolerance, atol=tolerance*.1, max_step=.05)
    assert solution.success and solution.t[-1] == duration
    references.append(solution.y[:, -1].reshape(2, 4, 3))
    print(json.dumps({'reference_rtol': tolerance, 'function_evaluations': solution.nfev,
                      'wall_s': time.perf_counter()-start}), flush=True)
reference_change = float(np.max(abs(references[0]-references[1])))
criteria_failures = []
if reference_change >= 1e-8: criteria_failures.append({"criterion":"DOP853 reference refinement <=1e-8","observed":reference_change})
system = System.uniform(production, 4, 1., 1.)
records = []
k0 = energy(x0, v0)
def persist_partial(progress=None):
    partial={'completed':False,'accepted':False,'model':model,'particle_indices_in_10k_fixture':indices,
             'runs':records,'criteria_failures':criteria_failures,'current_progress':progress,
             'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    temporary=destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(partial,indent=2)+'\n');temporary.replace(destination)
persist_partial()
for steps in step_counts:
    phase = Phase(x0, v0)
    dt = duration/steps
    began = time.perf_counter()
    for index in range(steps):
        phase, _ = system.step(phase, dt)
        if (index+1)%64000==0:
            progress={'phase':'intense_refinement','steps':steps,'completed_steps':index+1,'model_time_s':phase.time_s,'wall_s':time.perf_counter()-began}
            destination.with_suffix('.progress.json').write_text(json.dumps(progress)+'\n')
            persist_partial(progress)
            print(json.dumps(progress),flush=True)
    ref = solve_ivp(rhs, (0., phase.time_s), np.array([x0, v0]).reshape(-1),
                    method='DOP853', rtol=2.5e-14, atol=2.5e-15, max_step=.05)
    assert ref.success
    reference = ref.y[:, -1].reshape(2, 4, 3)
    error = max(float(np.max(np.linalg.norm(phase.positions()-reference[0], axis=1))),
                float(np.max(np.linalg.norm(phase.velocities()-reference[1], axis=1))))
    k = energy(phase.positions(), phase.velocities())
    energy_error = float(np.max(abs(k-k0)/np.maximum(abs(k0), .5*np.sum(v0*v0, axis=1))))
    if error >= 1e-3: criteria_failures.append({"steps":steps,"criterion":"native phase error <1e-3","observed":error})
    if energy_error >= 1e-6: criteria_failures.append({"steps":steps,"criterion":"static energy error <1e-6","observed":energy_error})
    records.append({'steps': steps, 'dt_s': dt, 'time_s': phase.time_s,
                    'phase_error_over_initial_Larmor_scale_max': error, 'static_energy_relative_error': energy_error, 'wall_s':time.perf_counter()-began,
                    'endpoint_position_m':phase.positions().tolist(),'endpoint_velocity_m_s':phase.velocities().tolist(),
                    'reference_position_m':reference[0].tolist(),'reference_velocity_m_s':reference[1].tolist(),
                    'initial_energy_J':k0.tolist(),'endpoint_energy_J':k.tolist()})
    persist_partial()
    print(json.dumps(records[-1]), flush=True)
ratios = [a['phase_error_over_initial_Larmor_scale_max']/b['phase_error_over_initial_Larmor_scale_max'] for a,b in zip(records,records[1:])]
if min(ratios)<=3.8:criteria_failures.append({'criterion':'second-order refinement ratios >3.8','observed':ratios})
files = [p for p in STAGE.iterdir() if p.is_file()]+[Path(__file__), ROOT/'scripts/em_cloud_source_fixture.py']
result = {'completed':True,'accepted':not criteria_failures,'criteria_failures':criteria_failures,'convergence_ratios':ratios,'status': 'rejected_source128_dynamics' if criteria_failures else 'charged_dipolar_128source_native_Boris_matches_independent_DOP853_and_second_order_refinement',
          'endpoint_error_normalizing_scales':{'position_m':1.,'velocity_m_s':1.},
          'model': model, 'particle_indices_in_10k_fixture': indices, 'q_C': 1., 'mass_kg': 1.,
          'independent_reference': 'SciPy DOP853, direct full-vector field formula, max_step=.05s, two tolerances',
          'scipy_version': scipy.__version__, 'DOP853_reference_refinement_max_component_change': reference_change,
          'runs': records, 'scientific_generation': generation(),
          'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
          'reference_implementation_sha256': {str(Path(inspect.getfile(m)).relative_to(ROOT)): hashlib.sha256(Path(inspect.getfile(m)).read_bytes()).hexdigest()
                                               for m in (rk, ivp, dop853_coefficients)},
          'scope': 'Only four particles,128static sources at+-1e-10C over10uniform-B periods, with the explicitly tested smaller timesteps. Preserves the previous coarse-step rejection; does not approve dt.002 or native10k throughput in the intense regime, installation or full C2-12.'}
destination.write_text(json.dumps(result, indent=2)+'\n')

if criteria_failures: raise SystemExit(1)
