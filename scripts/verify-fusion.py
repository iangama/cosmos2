"""Independent upstream rates, ODE composition and limiting-case checks."""
from collections import Counter
from pathlib import Path
import copy
import hashlib
import itertools
import json
import math
import sys
import tempfile

import numpy as np
import pynucastro as pyna
from scipy.constants import Avogadro, elementary_charge
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from forces import evaluate, normalize, save_configuration, load_configuration_record
from fusion import DATA, MIXTURES, RADIATIVE, rate_value
from packages import PackageStore

library = pyna.ReacLibLibrary()
rates = {key: library.get_rate_by_name(entry['query']) for key, entry in DATA['rates'].items()}
rate_error = max(abs(rate_value(t, DATA['rates'][key])/float(rate.eval(t))-1)
                 for key, rate in rates.items() for t in (1e7, 3e7, 1e8, 3e8, 1e9))
assert rate_error < 1e-12, rate_error
for key, entry in DATA['rates'].items():
    assert hashlib.sha256((ROOT / 'data/science' / entry['raw_file']).read_bytes()).hexdigest() == entry['sha256']
    assert entry['prefactor'] == rates[key].prefactor == (0.5 if len(set(entry['reactants'])) == 1 else 1)

ode_error = extent_error = balance_error = 0
cases, gates = [], 0
for mixture, spec in MIXTURES.items():
    keys = spec['channels']
    for ratio in (.3, 1, 1 + 1e-12, 3):
        n0, temperature = 1e22, 3e8
        coefficient = {key: float(rates[key].eval(temperature))*1e-6/Avogadro for key in keys}
        duration = 4/(sum(coefficient.values())*n0)
        assert 1e-6 <= duration <= 1e20
        request = {'scenario': 'fusion', 'parameters': {'mixture': mixture, 'temperature_K': temperature,
                   'density_m3': n0, 'partner_ratio': ratio, 'duration_s': duration}}
        run = evaluate(request)
        f = run['result']['fusion']
        names = f['species']
        initial = np.zeros(len(names))
        for name in set(spec['fuels']):
            initial[names.index(name)] = 1 if name == spec['fuels'][0] else ratio
        stoich = np.array([[Counter(DATA['rates'][k]['products'])[name]-Counter(DATA['rates'][k]['reactants'])[name]
                           for k in keys] for name in names])
        def rhs(_, y):
            flux = np.array([coefficient[k]*n0*duration*DATA['rates'][k]['prefactor']
                             * np.prod([y[names.index(n)] for n in DATA['rates'][k]['reactants']]) for k in keys])
            return np.r_[stoich @ flux, flux]
        reference = solve_ivp(rhs, (0, 1), np.r_[initial, np.zeros(len(keys))], method='DOP853',
                              t_eval=np.linspace(0, 1, 241), rtol=2e-12, atol=1e-14)
        assert reference.success
        ode_error = max(ode_error, float(np.max(np.abs(reference.y[:len(names)].T-np.array(f['number_density_m3'])/n0))))
        extent_error = max(extent_error, float(np.max(np.abs(reference.y[len(names):].T-np.array(f['reaction_extents_m3'])/n0))))
        balance_error = max(balance_error, f['baryon_relative_error'], f['charge_relative_error'])
        energy = np.array(f['reaction_extents_m3']) @ np.array([DATA['rates'][k]['Q_MeV'] for k in keys])*1e6*elementary_charge
        np.testing.assert_allclose(energy, f['energy_available_J_m3'], rtol=1e-13, atol=0)
        if mixture == 'dd':
            ext = np.array(f['reaction_extents_m3'])
            np.testing.assert_allclose(ext[1:, 0]/ext[1:, 1], coefficient['ddn']/coefficient['ddp'], rtol=1e-13)
            assert abs(coefficient['ddn']/coefficient['ddp']-1) > .01
        if ratio == 1:
            cases.append({'mixture': mixture, 'duration_s': duration, 'channels': keys,
                          'final_mass_fractions': f['mass_fractions'][-1]})
    # All channel/electromagnetic gates, independently of view controls.
    radiative = bool(set(keys) & RADIATIVE)
    combinations = itertools.product((False, True), repeat=len(keys) + int(radiative))
    base = evaluate({'scenario': 'fusion', 'parameters': {'mixture': mixture}})
    for values in combinations:
        controls = {'strong': {'effects': {'fusion_' + k: v for k, v in zip(keys, values)}}}
        if radiative:
            controls['electromagnetic'] = {'effects': {'fusion_radiative_capture': values[-1]}}
        request = {'scenario': 'fusion', 'parameters': {'mixture': mixture}, 'controls': controls}
        calculated = evaluate(request)
        assert calculated['result']['reference'] == base['result']['reference']
        for force in ('strong', 'electromagnetic'):
            hidden = copy.deepcopy(request)
            hidden['controls'].setdefault(force, {})['visible'] = False
            assert evaluate(hidden)['result'] == calculated['result']
            assert evaluate(hidden)['physics_sha256'] == calculated['physics_sha256']
        if not any(calculated['result']['fusion']['channels'].values()):
            assert not np.any(calculated['result']['fusion']['event_rates_m3_s'])
            assert not np.any(calculated['result']['fusion']['energy_available_J_m3'])
            assert np.max(np.abs(np.array(calculated['result']['fusion']['number_density_m3'])
                                 - np.array(list(calculated['result']['fusion']['initial_density_m3'].values())))) == 0
        gates += 1
    for force, (acting, visible) in itertools.product(('strong', 'electromagnetic'), itertools.product((False, True), repeat=2)):
        request = {'scenario': 'fusion', 'parameters': {'mixture': mixture}, 'controls': {force: {'acting': acting, 'visible': visible}}}
        trial = evaluate(request)
        assert trial['result']['reference'] == base['result']['reference']
        if force == 'strong' and not acting or radiative and force == 'electromagnetic' and not acting:
            assert not any(trial['result']['fusion']['channels'].values())
        gates += 1
assert ode_error < 1e-9 and extent_error < 1e-9 and balance_error < 1e-13

# Tiny exposures must retain nonzero production, even when n_initial-n_final rounds to zero.
tiny = evaluate({'scenario': 'fusion', 'parameters': {'mixture': 'c12alpha', 'temperature_K': 1e7,
                 'density_m3': 1e16, 'duration_s': 1e-6}})['result']['fusion']
assert tiny['reaction_extents_m3'][-1][0] > 0
large_integer = evaluate({'scenario': 'fusion', 'parameters': {'mixture': 'c12alpha',
                         'temperature_K': 300000000, 'density_m3': 10000000000000000000000,
                         'duration_s': 60000000000000000000}})
assert len(large_integer['result']['time_s']) == 241
assert .15 < large_integer['result']['fusion']['mass_fractions'][-1][0]/.75 < .25
limits = []
for mixture in MIXTURES:
    for ratio in (1e-3, 1, 1+1e-12, 1e3):
        for temp, duration in ((1e7, 1e-6), (1e9, 1e20)):
            result = evaluate({'scenario': 'fusion', 'parameters': {'mixture': mixture, 'temperature_K': temp,
                              'density_m3': 1e24, 'partner_ratio': ratio, 'duration_s': duration}})
            f = result['result']['fusion']
            assert np.min(f['number_density_m3']) >= 0
            assert max(f['baryon_relative_error'], f['charge_relative_error']) < 1e-13
            json.dumps(result, allow_nan=False)
            limits.append((mixture, ratio, temp, duration))

# The fixed physical duration means changing temperature/density changes the amount burned.
cold = evaluate({'scenario': 'fusion', 'parameters': {'temperature_K': 1e7}})['result']
hot = evaluate({'scenario': 'fusion', 'parameters': {'temperature_K': 1e8}})['result']
dense = evaluate({'scenario': 'fusion', 'parameters': {'density_m3': 1e22}})['result']
assert cold['time_s'] == hot['time_s'] == dense['time_s']
assert cold['fusion']['mass_fractions'][-1][0] > hot['fusion']['mass_fractions'][-1][0] > dense['fusion']['mass_fractions'][-1][0]

invalid = [{'mixture': 'unknown'}, {'duration_s': 0}, {'duration_s': float('inf')},
           {'partner_ratio': 0}, {'partner_ratio': True}, {'density_m3': -1}, {'temperature_K': 1e6}]
for parameters in invalid:
    try: normalize({'scenario': 'fusion', 'parameters': parameters})
    except ValueError: pass
    else: raise AssertionError('Accepted invalid input')
with tempfile.TemporaryDirectory() as folder:
    request = {'scenario': 'fusion', 'parameters': {'mixture': 'dd'},
               'controls': {'strong': {'effects': {'fusion_ddp': False}}}}
    original = evaluate(request)
    save_configuration(request, folder)
    loaded = load_configuration_record(folder)
    assert loaded['restoration']['status'] == 'same_generation'
    assert evaluate(loaded['configuration']) == original

report = {'ok': True, 'rate_max_relative_error': rate_error, 'channels': 7, 'mixtures': cases,
          'composition_vs_independent_ODE_initial_density': ode_error,
          'extent_vs_independent_ODE_initial_density': extent_error,
          'baryon_charge_max_relative_residual': balance_error, 'gate_combinations': gates,
          'limit_cases': len(limits), 'tiny_exposure_produces_nonzero_products': True,
          'browser_large_integer_JSON_uses_float64': True,
          'temperature_density_change_burn_at_fixed_time': True, 'invalid_inputs_rejected': len(invalid),
          'roundtrip_same_generation_exact_calculated_output': True,
          'scope': 'isolated forward mixtures; no deposition, secondary reactions or thermal feedback'}
(ROOT / 'evidence/fusion-check.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
