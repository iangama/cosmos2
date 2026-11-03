"""Exercise actual SIMD fields, exclusions, fixed source order and thread determinism."""
from pathlib import Path
import hashlib
import json
import math
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT/'output/c212-em-cloud-native-staging'
sys.path.insert(0, str(STAGE))
import cloud_native as native
from cloud_core import Phase, System
from cloud_fields import evaluate, drift_domain
from cloud_checkpoint import generation
from em_fields import Model, Source, SPEED_LIMIT_M_S
from em_particles import DomainExit

rng = np.random.default_rng(20261020)
x = rng.normal(size=(1025, 3))*.4
sources = []
for j in range(128):
    z = 1-2*(j+.5)/128
    a = j*math.pi*(3-math.sqrt(5))
    r = math.sqrt(1-z*z)
    sources.append(Source(str(j), (8*r*math.cos(a), 8*r*math.sin(a), 8*z),
                          .02, (-1)**j*1e-9, (1e5, -2e5, 3e5)))
field_error = 0.
field_cases = 0
for count in (0, 1, 3, 4, 16, 128):
    model = Model(tuple(sources[:count]), (.1, -.2, .3), (.2, .1, 1.))
    reference = evaluate(model, x)
    readings = [native.evaluate(native.pack(model), x, thread_count=t) for t in (1, 4, 6, 8)]
    for value in readings[1:]:
        assert all(np.array_equal(a, b) for a, b in zip(value, readings[0]))
    e, b, phi = readings[0]
    for k in range(0, len(x), 13):
        scalar = model.evaluate(x[k])
        for actual, expected, scale in ((e[k], scalar['electric_field_V_m'], scalar['electric_scale_V_m']),
                                         (b[k], scalar['magnetic_field_T'], scalar['magnetic_scale_T'])):
            error = math.dist(actual, expected)/max(scale, 1e-300)
            assert error < 1e-13, (count, k, error)
            field_error = max(field_error, error)
        assert math.isclose(phi[k], scalar['electric_potential_V'], rel_tol=1e-13, abs_tol=1e-13)
    for value, old in zip(readings[0], reference):
        assert np.allclose(value, old, rtol=1e-13, atol=1e-13)
    field_cases += 1

model = Model(tuple(sources), (.1, -.2, .3), (.2, .1, 1.))
system = System(model, rng.uniform(-1, 1, len(x)), rng.uniform(.5, 2, len(x)))
initial = Phase(x, rng.normal(size=x.shape)*.1)
thread_futures = []
for thread_count in (1, 4, 6, 8):
    phase = initial
    digest = hashlib.sha256()
    for _ in range(64):
        xx, vv, work, kinetic = native.step(system._native_model, phase.positions(), phase.velocities(),
                                          system.charges(), system.masses(), .002, True, True,
                                          thread_count=thread_count)
        phase = Phase(xx, vv, phase.time_s+.002)
        for a in (phase._x, phase._v, work.tobytes(), kinetic.tobytes()):
            digest.update(a)
    thread_futures.append(digest.hexdigest())
assert len(set(thread_futures)) == 1

refusals = []
# Fast bounding-box rejection must never discard grazing/axis-skew crossings.
for center, radius, start, velocity in (
    ((0, 0, 0), .1, (-1, 0, 0), (4, 0, 0)),
    ((0, 0, 0), .1, (-1, .099999, 0), (4, 0, 0)),
    ((.2, -.3, .4), .1, (-.8, -1.3, -.6), (4, 4, 4)),
    ((0, 0, 0), 1e-310, (-1e-300, 0, 0), (4e-300, 0, 0)),
):
    obstacle = System.uniform(Model((Source('excluded', center, radius, 0.),)), 1, 1, 1)
    phase = Phase([start], [velocity])
    before = phase._x, phase._v, phase.time_s
    for control in ((False, False), (False, True), (True, False), (True, True)):
        try:
            obstacle.step(phase, 1., electric_acting=control[0], magnetic_acting=control[1])
        except DomainExit:
            refusals.append([center, radius, control])
        else:
            raise AssertionError('Drift tunneled through excluded source')
        assert (phase._x, phase._v, phase.time_s) == before

# Force SIMD fallback at subnormal radii, then test the declared speed boundary.
tiny_model = Model(tuple(Source(str(i), (0, 0, 0), 1e-310, 0.) for i in range(4)))
tiny_x = np.array([[1e-300, 0, 0]]*4)
assert all(np.array_equal(a, b) for a, b in zip(native.evaluate(native.pack(tiny_model), tiny_x), evaluate(tiny_model, tiny_x)))
speed_admission = []
for value in (np.nextafter(SPEED_LIMIT_M_S, 0.), SPEED_LIMIT_M_S, np.nextafter(SPEED_LIMIT_M_S, math.inf)):
    try:
        phase = Phase([[0, 0, 0]], [[float(value), 0, 0]])
        System.uniform(Model(), 1, 1, 1).step(phase, .002)
    except DomainExit:
        speed_admission.append(False)
    else:
        speed_admission.append(True)
assert speed_admission == [True, True, False]

box_cases, box_refusals = 0, 0
for trial in range(200):
    n = (1, 4, 513)[trial % 3]
    start = rng.uniform(-2, 2, size=(n, 3))
    velocity = rng.uniform(-8, 8, size=(n, 3))
    if trial % 2:
        start[:, 1:] = 0
        velocity[:, 1:] = 0
    if trial % 10 == 0:
        start[0] = [-1, np.nextafter(.1, 0.), 0]
        velocity[0] = [4, 0, 0]
    if trial % 10 == 1:
        start[0] = [-1, np.nextafter(.1, math.inf), 0]
        velocity[0] = [4, 0, 0]
    source_model = Model((Source('origin', (0, 0, 0), .1, 0.),
                          Source('skew', (.4, -.2, .7), .05, 0.),
                          Source('far', (1e17, -1e17, 1e17), .01, 0.)))
    mid = start+.5*velocity
    end = mid+.5*velocity
    expected = True
    try:
        drift_domain(source_model, start, mid)
        evaluate(source_model, mid, potential=False)
        drift_domain(source_model, mid, end)
    except DomainExit:
        expected = False
    phase = Phase(start, velocity)
    before = phase._x, phase._v
    try:
        System.uniform(source_model, n, 1, 1).step(phase, 1.)
    except DomainExit:
        observed = False
    else:
        observed = True
    assert observed is expected, trial
    assert (phase._x, phase._v) == before
    box_cases += 1
    box_refusals += not expected

paths = [p for p in STAGE.iterdir() if p.is_file()]+[Path(__file__)]
result = {'status': 'actual_native_SIMD_fields_source128_exclusions_and_thread_determinism_verified',
          'field_cases': field_cases, 'particles_each': len(x), 'scalar_field_normalized_error_max': field_error,
          'threads_tested': [1, 4, 6, 8], 'thread_future_steps_each': 64, 'thread_future_sha256': thread_futures,
          'crossing_refusals_and_unchanged_inputs': len(refusals), 'subnormal_field_fallback_exact': True,
          'speed_boundary_admission': speed_admission, 'scientific_generation': generation(),
          'conservative_batch_box_cases_vs_reference': box_cases, 'batch_box_refusals': box_refusals,
          'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
          'scope': 'Isolated helper only; no checkpoint migration,10k/native throughput, installation or complete C2-12 approval.'}
(ROOT/'evidence/em-cloud-native-contract-e-check.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({k: v for k, v in result.items() if k not in ('source_sha256', 'scientific_generation')}, indent=2))
