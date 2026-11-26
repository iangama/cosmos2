"""Independent quadrature, limits, invariants and control checks for null rays."""
from pathlib import Path
import copy
import itertools
import json
import math
import sys
import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'app'))
from relativity import trace_ray, CRITICAL_B
from forces import evaluate


def scattering_angle(b):
    # Independent first-integral quadrature in u=r_s/r. A squared change of
    # variable removes the turning-point singularity and avoids cancellation.
    turn = brentq(lambda u: 1/b**2-u*u+u**3, 0, 2/3, xtol=1e-15, rtol=1e-14)
    def integrand(s):
        u = turn*(1-s*s)
        q = u+turn-(u*u+u*turn+turn*turn)
        return 2*math.sqrt(turn/q)
    return 2*quad(integrand, 0, 1, epsabs=1e-12, epsrel=1e-12)[0]-math.pi, 1/turn


checks = []
for impact in (2.60, 3.2, 10, 100, 1000, 1e6):
    result = trace_ray(impact)
    angle, closest = scattering_angle(impact)
    assert result['status'] == 'escaped'
    error = abs(result['deflection_rad']-angle)
    assert error < 5e-9
    assert abs(result['minimum_radius_rs']/closest-1) < 1e-8
    assert result['invariant_error'] < 1e-9
    checks.append({'impact_rs': impact, 'deflection_rad': result['deflection_rad'],
                   'quadrature_error_rad': error, 'invariant_error': result['invariant_error']})
assert abs(trace_ray(1e6)['deflection_rad']/(2/1e6)-1) < 1e-5
for impact in (1.2, 2.59):
    assert trace_ray(impact)['status'] == 'captured'
assert trace_ray(CRITICAL_B)['status'] == 'near_critical_unresolved'

baseline = evaluate({'scenario': 'relativity'})['result']
for acting, bending, clock in itertools.product((False, True), repeat=3):
    request = {'scenario': 'relativity', 'controls': {'gravity': {
        'acting': acting, 'effects': {'ray_bending': bending, 'static_clock_rate': clock}}}}
    result = evaluate(request)['result']
    assert result['reference'] == baseline['reference']
    assert result['metric_probes'] == baseline['metric_probes']
    visible = copy.deepcopy(request)
    visible['controls']['gravity']['visible'] = False
    assert result == evaluate(visible)['result']
    assert result['ray']['curvature_term_applied'] == (acting and bending)
    expected_clock = math.sqrt(2/3) if acting and clock else 1
    assert result['measurements'][1]['value'] == expected_clock
    if not (acting and bending):
        position = np.array(result['positions'])
        steps = np.diff(position, axis=0)
        assert np.max(np.abs(steps-steps[0])) < 1e-12
        assert result['measurements'][3]['value'] == 0

# Metric radii/clock ratios depend on r/r_s, while SI curvature scales M^-4.
heavy = evaluate({'scenario': 'relativity', 'parameters': {'mass_solar': 100}})['result']
assert np.array_equal(baseline['positions'], heavy['positions'])
assert math.isclose(heavy['reference']['schwarzschild_radius_m'], 10*baseline['reference']['schwarzschild_radius_m'], rel_tol=1e-14)
assert math.isclose(heavy['reference']['kretschmann_m_minus4'], baseline['reference']['kretschmann_m_minus4']/1e4)
json.dumps(evaluate({'scenario': 'relativity', 'parameters': {'impact_rs': 1.2}}), allow_nan=False)
report = {'platform': sys.platform, 'independent_quadrature': checks, 'control_combinations': 8,
          'capture_below_critical': True, 'critical_classification_bounded': True,
          'metric_visibility_does_not_change_physics': True, 'mass_scaling': True,
          'scope': 'Exterior Schwarzschild null rays and static clocks; no Kerr/full image/stellar structure'}
(ROOT/'evidence/relativity-check.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
