"""Independent numerical/reference checks for the first four force scenarios."""
from pathlib import Path
import copy
import hashlib
import itertools
import json
import math
import sys
import tempfile
import numpy as np
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'app'))
from forces import evaluate, normalize, SCENARIOS, FORCES, DATA, point_gravity, reaclib_rate, save_configuration, load_configuration

report = {'platform': sys.platform, 'scope': 'bounded initial scenarios; not full four-force certification'}
combinations = 0
for name in FORCES:
    baseline = evaluate({'scenario': name})['result']
    for acting, visible in itertools.product((False, True), repeat=2):
        config = {'scenario': name, 'controls': {name: {'acting': acting, 'visible': visible}}}
        result = evaluate(config)['result']
        assert result['reference'] == baseline['reference']
        other = copy.deepcopy(config)
        other['controls'][name]['visible'] = not visible
        assert result == evaluate(other)['result'], 'Visibility changed physical output'
        if not acting:
            assert result['measurements'][1]['value'] == 0
        combinations += 1
report['independent_control_combinations'] = combinations

# Directions cover 3D, not just one orbital plane. Force magnitudes obey inverse square.
directions = [(1,0,0),(0,1,0),(0,0,1),(-1,0,0),(0,-1,0),(0,0,-1),(1,2,3)]
for direction in directions:
    a = np.array(point_gravity(direction, 3.0))
    b = np.array(point_gravity([2*x for x in direction], 3.0))
    assert np.dot(a, direction) < 0
    assert np.linalg.norm(np.cross(a, direction)) < 1e-14
    assert np.allclose(b, a/4, rtol=1e-14, atol=1e-16)
g = evaluate({'scenario':'gravity'})['result']
err = float(np.max(np.linalg.norm(np.array(g['positions'])-np.array(g['reference_positions']), axis=1)))
assert err < 1e-8
off = evaluate({'scenario':'gravity', 'controls':{'gravity':{'acting':False}}})['result']
steps = np.diff(off['positions'], axis=0)
assert np.max(np.abs(steps-steps[0])) < 1e-14
report['gravity_max_orbit_error_initial_radius'] = err
report['gravity_3d_directions'] = len(directions)

# An independently integrated Lorentz ODE checks signs, phase and E work of the analytic solution.
from scipy.constants import elementary_charge, proton_mass
em_error = 0
for sign in (-1,1):
    for electric in (-1,0,1):
        result = evaluate({'scenario':'electromagnetic','parameters':{'charge_sign':sign,'E_Vm':electric}})['result']
        q_m = sign*elementary_charge/proton_mass
        def rhs(t,y):
            return np.r_[y[3:], q_m*(np.array([electric,0,0])+np.cross(y[3:], [0,0,.001]))]
        times = result['time_s']
        reference = solve_ivp(rhs,(0,times[-1]),[0,0,0,1e4,0,3e3],t_eval=times,method='DOP853',rtol=1e-11,atol=1e-13)
        error = float(np.max(np.abs(reference.y[:3].T/result['position_unit_m']-result['positions'])))
        em_error = max(error, em_error)
assert em_error < 1e-8
report['lorentz_max_error_larmor_units'] = em_error
effect_error = 0
for electric_on, magnetic_on in itertools.product((False, True), repeat=2):
    request = {'scenario': 'electromagnetic', 'parameters': {'E_Vm': 1},
               'controls': {'electromagnetic': {'effects': {
                   'electric_acceleration': electric_on, 'magnetic_deflection': magnetic_on}}}}
    result = evaluate(request)['result']
    electric, magnetic = int(electric_on), .001*int(magnetic_on)
    q_m = elementary_charge/proton_mass
    def rhs(t, y):
        return np.r_[y[3:], q_m*(np.array([electric, 0, 0])+np.cross(y[3:], [0, 0, magnetic]))]
    reference = solve_ivp(rhs, (0, result['time_s'][-1]), [0,0,0,1e4,0,3e3],
                          t_eval=result['time_s'], method='DOP853', rtol=1e-11, atol=1e-13)
    effect_error = max(effect_error, float(np.max(np.abs(reference.y[:3].T/result['position_unit_m']-result['positions']))))
    assert result['reference']['B_T'] == .001 and result['reference']['E_Vm'] == 1
    assert result['applied_fields'] == {'B_T': magnetic, 'E_Vm': electric}
    assert result['measurements'][3]['value'] < 1e-12
assert effect_error < 1e-8
report['lorentz_effect_combinations'] = 4
report['lorentz_effect_max_error_larmor_units'] = effect_error

# Frozen reference values were produced by upstream pynucastro, not this evaluator.
rate_error = max(abs(reaclib_rate(float(t))/v-1) for t,v in DATA['reference_rates'].items())
assert rate_error < 1e-12
s = evaluate({'scenario':'strong'})['result']
# Independent integration in dimensionless time u=<sigma v>*n0*t.
numeric = solve_ivp(lambda t,y:[-y[0]*y[0]], (0,4), [1],t_eval=np.linspace(0,4,241),rtol=1e-11,atol=1e-13)
reaction_error = float(np.max(np.abs(numeric.y[0]-s['curves'][0]['values'])))
assert reaction_error < 1e-9
for rem, product in zip(s['curves'][0]['values'],s['curves'][1]['values']):
    # D(A2,Z1)+T(A3,Z1) -> He4(A4,Z2)+n(A1,Z0)
    assert abs(5*rem + 5*product - 5) < 1e-14
    assert abs(2*rem + 2*product - 2) < 1e-14
report['reaclib_relative_error'] = rate_error
report['nuclear_consumption_vs_ode'] = reaction_error
w = evaluate({'scenario':'weak'})['result']
assert math.isclose(w['curves'][0]['values'][60], .5, rel_tol=1e-14)
assert math.isclose(w['curves'][0]['values'][-1], 1/16, rel_tol=1e-14)
assert w['reference']['half_life_s'] == 609.8  # NUBASE2020 pinned dataset
report['weak_half_life_s'] = w['reference']['half_life_s']
half_lives = {}
for species in ('n', 't', 'c14', 'be7'):
    result = evaluate({'scenario': 'weak', 'parameters': {'species': species}})['result']
    assert math.isclose(result['curves'][0]['values'][60], .5, rel_tol=1e-14)
    assert result['reference']['parent_A'] == result['reference']['daughter_A']
    capture = species == 'be7'
    assert result['reference']['parent_Z'] == result['reference']['daughter_Z']+(1 if capture else -1)
    half_lives[species] = result['reference']['half_life_s']
    off = evaluate({'scenario': 'weak', 'parameters': {'species': species},
                    'controls': {'weak': {'effects': {'electron_capture' if capture else 'beta_decay': False}}}})
    assert off['result']['curves'][0]['values'] == [1.0]*241
    assert off['result']['measurements'][3]['value'] == 0
    assert off['result']['reference'] == result['reference']
report['weak_evaluated_species_half_lives_s'] = half_lives

# pp-I: rates checked against upstream's frozen evaluations; composition and
# energy must converge and conserve baryons for supported channel switches.
from stellar import integrate_zone, rate_value, DATA as stellar_data, YEAR_S, STOICHIOMETRY
stellar_rate_error = max(abs(rate_value(float(t), entry)/value-1)
                         for entry in stellar_data['rates'].values()
                         for t, value in entry['reference_rates'].items())
assert stellar_rate_error < 1e-12
assert np.allclose(np.array([1,2,3,4]) @ STOICHIOMETRY, 0)
zone = integrate_zone(1.5e7, 1.5e5, .35, 1e8*YEAR_S)
refined = integrate_zone(1.5e7, 1.5e5, .35, 1e8*YEAR_S, tolerance=1e-10)
composition_error = float(np.max(np.abs(np.array(zone['mass_fractions'])-refined['mass_fractions'])))
energy_error = abs(zone['energy_deposited_J_m3'][-1]/refined['energy_deposited_J_m3'][-1]-1)
assert composition_error < 1e-9 and energy_error < 1e-8
for pp, dp, he3 in itertools.product((False,True), repeat=3):
    run = integrate_zone(1.5e7,1.5e5,.35,1e8*YEAR_S,channels={'pp':pp,'dp':dp,'he3he3':he3})
    assert run['baryon_error'] < 1e-10
    assert run['minimum_abundance'] >= -1e-20
    assert np.allclose(np.array(run['energy_available_J_m3'])-run['energy_neutrinos_J_m3'],
                       run['energy_deposited_J_m3'], rtol=1e-14, atol=1e-12)
    if not pp:
        assert run['neutrino_count_m3'][-1] == 0 and run['energy_available_J_m3'][-1] == 0
    if not dp:
        assert run['mass_fractions'][-1][2] == 0
report['stellar_pp1'] = {'rate_relative_error':stellar_rate_error,'channel_combinations':8,
                         'composition_refinement_error':composition_error,'energy_refinement_relative_error':energy_error,
                         'baryon_error':zone['baryon_error'],'source_mean_neutrino_MeV':stellar_data['pp_neutrino_mean_MeV'],
                         'scope':'fixed T/rho; forward pp-I; does not validate full solar evolution'}

rejected = 0
for request in ({'scenario':'invalid'}, {'parameters':{'mass_solar':float('nan')}},
                {'parameters':{'mass_solar':True}}, {'controls':{'gravity':{'acting':'false'}}},
                {'scenario':'electromagnetic','parameters':{'charge_sign':0}},
                {'scenario':'strong','parameters':{'temperature_K':1e30}}):
    try: normalize(request)
    except ValueError: rejected += 1
    else: raise AssertionError(f'Accepted invalid request {request}')
report['invalid_requests_rejected'] = rejected
with tempfile.TemporaryDirectory(prefix='cosmos2-forces-') as folder:
    config = {'scenario':'weak','controls':{'weak':{'acting':False,'visible':True}}}
    save_configuration(config, folder)
    assert normalize(config) == load_configuration(folder)
    assert evaluate(config) == evaluate(load_configuration(folder))
    manifest = Path(folder)/'latest.json'
    damaged = json.loads(manifest.read_text())
    damaged['configuration']['controls']['weak']['acting'] = True
    manifest.write_text(json.dumps(damaged))
    try: load_configuration(folder)
    except ValueError: pass
    else: raise AssertionError('Accepted modified configuration')
    legacy = {'scenario': 'weak', 'parameters': {'initial_population': 1000},
              'controls': {force: {'acting': True, 'visible': True} for force in FORCES}}
    digest = hashlib.sha256(json.dumps(legacy, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    manifest.write_text(json.dumps({'schema': 1, 'configuration': legacy, 'sha256': digest}))
    restored = load_configuration(folder)
    assert restored['parameters']['species'] == 'n'
    assert restored['controls']['weak']['effects']['beta_decay'] is True
report['persistence_and_corruption'] = 'passed'
report['legacy_configuration_migration'] = 'passed'
(ROOT/'evidence/forces-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
