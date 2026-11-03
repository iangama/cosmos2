"""Pinned evaluated branches, analytical lifetimes and independent ODE checks."""
from pathlib import Path
import copy
import csv
import hashlib
import itertools
import json
import math
import sys
import tempfile

import numpy as np
from scipy.integrate import solve_ivp
from scipy.constants import elementary_charge

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from forces import evaluate, normalize, save_configuration, load_configuration_record
from decays import DATA, CASES, channel_keys

receipt = json.loads((ROOT / 'evidence/decay-data.json').read_text())
assert hashlib.sha256((ROOT / receipt['dataset']).read_bytes()).hexdigest() == receipt['sha256']
for entry in receipt['files']:
    raw = (ROOT / entry['path']).read_bytes()
    assert len(raw) == entry['bytes'] and hashlib.sha256(raw).hexdigest() == entry['sha256']
for parent in DATA['parents'].values():
    gs = parent['ENSDF_ground_state']
    assert parent['half_life_s'] == float(gs['half_life_sec'])
    assert parent['half_life_uncertainty_s'] == float(gs['unc_hls'])
for key, channel in DATA['channels'].items():
    rows = list(csv.DictReader((ROOT / channel['source_file']).open()))
    row = rows[channel['source_line']-2]
    assert row == channel['source_row'] and float(row['p_energy']) == 0 and not row['p_energy_shift']
    field = 'intensity_ec' if channel['mode'] == 'electron_capture' else 'intensity_beta'
    assert channel['printed_intensity_percent'] == float(row[field])
    assert channel['Q']['value'] == float(row['q'])
assert len(DATA['parents']) == 10 and len(DATA['channels']) == 19
assert DATA['parents']['n']['half_life_s'] == 613.9
assert DATA['parents']['n']['NUBASE2020_comparison']['half_life_s'] == 609.8
assert DATA['parents']['n13']['half_life_s'] == 597.504
assert DATA['parents']['n13']['NUBASE2020_comparison']['half_life_s'] == 597.9
assert DATA['parents']['na22']['printed_total_intensity_percent'] == 99.996
assert DATA['parents']['na22']['branch_normalization_factor'] > 1
assert DATA['channels']['f18_beta_plus_0']['probability'] == .9673
assert DATA['channels']['f18_electron_capture_0']['probability'] == .0327
assert DATA['channels']['c14_beta_minus_0']['independent_source_energy_residual_keV'] < -.2
assert all(float(DATA['channels'][k]['source_row']['p_energy']) == 0 for k in DATA['parents']['y90']['channels'])

ode_error = counts_error = balance = half_error = 0
cases = []
for case in CASES:
    request = {'scenario': 'decays', 'parameters': {'parent_case': case}}
    result = evaluate(request)
    r, d = result['result'], result['result']['decays']
    half_error = max(half_error, abs(d['population_fractions'][60][0] - .5))
    nodes, keys = d['node_ids'], d['channel_order']
    initial = np.zeros(len(nodes)+len(keys));initial[0] = 1
    scale = DATA['parents'][case]['half_life_s']
    coeff = [math.log(2)/DATA['parents'][DATA['channels'][k]['parent']]['half_life_s']
             * DATA['channels'][k]['probability'] * scale for k in keys]
    def rhs(_, state):
        dy = np.zeros_like(state)
        for j, key in enumerate(keys):
            c = DATA['channels'][key]
            rate = coeff[j] * state[nodes.index(c['parent_node'])]
            dy[nodes.index(c['parent_node'])] -= rate
            dy[nodes.index(c['daughter_node'])] += rate
            dy[len(nodes)+j] = rate
        return dy
    reference = solve_ivp(rhs, (0, 4), initial, t_eval=np.linspace(0, 4, 241),
                          method='Radau', rtol=2e-11, atol=2e-13)
    assert reference.success
    ode_error = max(ode_error, float(np.max(np.abs(reference.y[:len(nodes)].T - d['population_fractions']))))
    counts_error = max(counts_error, float(np.max(np.abs(reference.y[len(nodes):].T - np.array(d['channel_event_counts'])/1e6))))
    balance = max(balance, d['baryon_relative_error'], d['charge_residual_per_initial_nucleus'],
                  d['energy_balance_relative_error'], d['population_sum_error'])
    counts = np.array(d['channel_event_counts'])
    plus = sum(counts[:, j] for j, k in enumerate(keys) if DATA['channels'][k]['mode'] == 'beta_plus') if any(DATA['channels'][k]['mode'] == 'beta_plus' for k in keys) else np.zeros(241)
    capture = sum(counts[:, j] for j, k in enumerate(keys) if DATA['channels'][k]['mode'] == 'electron_capture') if any(DATA['channels'][k]['mode'] == 'electron_capture' for k in keys) else np.zeros(241)
    np.testing.assert_allclose(d['electron_neutrino_count'], plus+capture, rtol=1e-13, atol=1e-12)
    np.testing.assert_allclose(d['positron_count'], plus, rtol=1e-13, atol=1e-12)
    q = np.array([DATA['channels'][k]['Q']['value'] for k in keys])
    np.testing.assert_allclose(counts @ q*1000*elementary_charge, d['energy_available_J'], rtol=1e-13, atol=0)
    assert d['energy_deposited_J'] is None
    cases.append({'case': case, 'half_life_s': DATA['parents'][case]['half_life_s'],
                  'channels': len(keys), 'final_population_fractions': d['population_fractions'][-1]})
assert half_error < 1e-12 and ode_error < 1e-9 and counts_error < 1e-9 and balance < 1e-11

# Bateman's independent two-link closed form, including initial daughter.
bateman_error = 0
for initial_daughter in (0, .4, 1):
    r = evaluate({'scenario': 'decays', 'parameters': {'parent_case': 'sr90',
                  'initial_daughter_fraction': initial_daughter}})['result']
    t = np.array(r['time_s']);d = r['decays']
    a = math.log(2)/DATA['parents']['sr90']['half_life_s']
    b = math.log(2)/DATA['parents']['y90']['half_life_s']
    parent = (1-initial_daughter)*np.exp(-a*t)
    daughter = initial_daughter*np.exp(-b*t)+(1-initial_daughter)*a/(b-a)*(np.exp(-a*t)-np.exp(-b*t))
    expected = np.column_stack([parent, daughter, 1-parent-daughter])
    bateman_error = max(bateman_error, float(np.max(np.abs(expected-d['population_fractions']))))
assert bateman_error < 1e-12

gate_count = 0
for case in CASES:
    baseline = evaluate({'scenario': 'decays', 'parameters': {'parent_case': case}})
    keys = channel_keys(case)
    for switches in itertools.product((False, True), repeat=len(keys)):
        request = {'scenario': 'decays', 'parameters': {'parent_case': case},
                   'controls': {'weak': {'effects': {'decay_'+k: v for k, v in zip(keys, switches)}}}}
        calculated = evaluate(request)
        d = calculated['result']['decays']
        assert calculated['result']['reference'] == baseline['result']['reference']
        hidden = copy.deepcopy(request);hidden['controls']['weak']['visible'] = False
        assert evaluate(hidden)['result'] == calculated['result']
        assert evaluate(hidden)['physics_sha256'] == calculated['physics_sha256']
        for j, on in enumerate(switches):
            if not on:
                assert np.max(np.abs(np.array(d['channel_event_counts'])[:, j])) == 0
        if not any(switches):
            assert d['population_fractions'][-1] == d['population_fractions'][0]
            assert d['energy_available_J'][-1] == 0
        elif case != 'sr90' or switches[0]:
            assert d['energy_available_J'][-1] > 0
        else:
            # An active daughter width cannot act without a daughter population.
            assert d['energy_available_J'][-1] == 0
        assert d['minimum_population_fraction'] >= -1e-12
        assert d['charge_residual_per_initial_nucleus'] < 1e-11
        gate_count += 1
    for acting, visible in itertools.product((False, True), repeat=2):
        trial = evaluate({'scenario': 'decays', 'parameters': {'parent_case': case},
                          'controls': {'weak': {'acting': acting, 'visible': visible}}})
        assert trial['result']['reference'] == baseline['result']['reference']
        if not acting: assert trial['result']['decays']['energy_available_J'][-1] == 0
        gate_count += 1

# Partial widths are removed, never renormalized after intervention.
f = evaluate({'scenario': 'decays', 'parameters': {'parent_case': 'f18'},
              'controls': {'weak': {'effects': {'decay_f18_beta_plus_0': False}}}})['result']
expected_parent = np.exp(-math.log(2)*.0327*np.array(f['time_s'])/DATA['parents']['f18']['half_life_s'])
np.testing.assert_allclose(np.array(f['decays']['population_fractions'])[:, 0], expected_parent, rtol=1e-13, atol=1e-14)
assert f['decays']['positron_count'][-1] == 0 and f['decays']['captured_electron_count'][-1] > 0
held = evaluate({'scenario': 'decays', 'parameters': {'parent_case': 'sr90'},
                 'controls': {'weak': {'effects': {'decay_'+k: False for k in DATA['parents']['y90']['channels']}}}})['result']['decays']
assert math.isclose(held['populations'][-1][1], 937500, rel_tol=1e-13) and held['populations'][-1][2] == 0

limit_count = 0
for case, duration, population in itertools.product(CASES, (.001, 20), (1, 1e12)):
    r = evaluate({'scenario': 'decays', 'parameters': {'parent_case': case,
                  'duration_half_lives': duration, 'initial_population': population}})
    d = r['result']['decays']
    assert d['minimum_population_fraction'] >= -1e-12
    assert max(d['population_sum_error'], d['charge_residual_per_initial_nucleus']) < 1e-11
    json.dumps(r, allow_nan=False);limit_count += 1

for p in ({'parent_case': 'missing'}, {'duration_half_lives': 0}, {'duration_half_lives': 21},
          {'initial_population': True}, {'initial_population': 0}, {'initial_daughter_fraction': 1.1},
          {'duration_half_lives': float('nan')}):
    try: normalize({'scenario': 'decays', 'parameters': p})
    except ValueError: pass
    else: raise AssertionError('Invalid configuration accepted')
with tempfile.TemporaryDirectory() as folder:
    original = {'scenario': 'decays', 'parameters': {'parent_case': 'na22'},
                'controls': {'weak': {'effects': {'decay_na22_beta_plus_0': False}}}}
    save_configuration(original, folder)
    loaded = load_configuration_record(folder)
    assert loaded['restoration']['status'] == 'same_generation'
    assert evaluate(loaded['configuration']) == evaluate(original)

report = {'ok': True, 'parents': cases, 'evaluated_channels': len(DATA['channels']),
          'source_files_SHA256_and_raw_rows_verified': True, 'isomer_rows_excluded': True,
          'ENSDF_and_NUBASE_differences_preserved': True, 'printed_branch_normalization_explicit': True,
          'source_energy_discrepancies_preserved': True, 'half_life_max_error_initial_population': half_error,
          'composition_vs_independent_Radau_initial_population': ode_error,
          'event_counts_vs_independent_Radau_initial_population': counts_error,
          'Sr_Y_Bateman_max_error_initial_population': bateman_error,
          'baryon_charge_energy_max_residual': balance, 'gate_combinations': gate_count, 'limit_cases': limit_count,
          'partial_width_suppression_no_renormalization': True, 'daughter_feeding_when_decay_suppressed': True,
          'population_lepton_charge_energy_balances': True, 'save_load_generation': True,
          'scope': 'Expected populations, linear decay, evaluated atomic reference environment; no spectra or transport'}
(ROOT / 'evidence/decays-check.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
