"""Evaluated linear decays with partial-width suppression and Sr90 feeding.

ENSDF/LiveChart is the operational generation. NUBASE is a labelled reference
comparison. Daughter excited levels are aggregated by A/Z, not time-evolved.
"""
from pathlib import Path
import json
import math

import numpy as np
from scipy.constants import elementary_charge
from scipy.linalg import expm

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'data/science/decays.json').read_text(encoding='utf-8'))
MODE_LABELS = {'beta_minus': 'β−', 'beta_plus': 'β+', 'electron_capture': 'Captura eletrônica'}
CASES = {k: p['label'] + (' → Y-90 → Zr-90' if k == 'sr90' else '') for k, p in DATA['parents'].items()}


def channel_label(channel):
    p = DATA['parents'][channel['parent']]
    return (p['label'] + ' → ' + channel['daughter_label'] + ' · ' + MODE_LABELS[channel['mode']]
            + ' · nível ' + format(channel['daughter_excitation_keV'], '.8g') + ' keV')


def parent_keys(case):
    return ['sr90', 'y90'] if case == 'sr90' else [case]


def channel_keys(case):
    return [c for p in parent_keys(case) for c in DATA['parents'][p]['channels']]


EFFECT_LABELS = {'decay_' + k: channel_label(c) for k, c in DATA['channels'].items()}


def evolve(case, initial_population, initial_daughter_fraction, scaled_times, channels):
    parents = parent_keys(case)
    keys = channel_keys(case)
    p = DATA['parents'][case]
    time_scale = p['half_life_s']
    nodes = list(dict.fromkeys([*[DATA['parents'][k]['node_id'] for k in parents],
                                *[DATA['channels'][k]['daughter_node'] for k in keys]]))
    n, m = len(nodes), len(parents)
    generator = np.zeros((n+m, n+m))
    coefficients = {key: math.log(2)/DATA['parents'][DATA['channels'][key]['parent']]['half_life_s']
                         * DATA['channels'][key]['probability'] * time_scale * bool(channels[key]) for key in keys}
    for key in keys:
        c = DATA['channels'][key]
        source, destination = nodes.index(c['parent_node']), nodes.index(c['daughter_node'])
        generator[source, source] -= coefficients[key]
        generator[destination, source] += coefficients[key]
    for i, parent in enumerate(parents):
        generator[n+i, nodes.index(DATA['parents'][parent]['node_id'])] = 1
    initial = np.zeros(n+m)
    initial[nodes.index(p['node_id'])] = 1 - initial_daughter_fraction if case == 'sr90' else 1
    if case == 'sr90':
        initial[nodes.index(DATA['parents']['y90']['node_id'])] = initial_daughter_fraction
    states = np.array([expm(generator * float(t)) @ initial for t in scaled_times])
    populations = states[:, :n] * initial_population
    counts = np.column_stack([states[:, n+parents.index(DATA['channels'][key]['parent'])]
                              * coefficients[key] * initial_population for key in keys])
    event_rates = np.column_stack([populations[:, nodes.index(DATA['channels'][key]['parent_node'])]
                                   * coefficients[key]/time_scale for key in keys])
    q = np.array([DATA['channels'][k]['Q']['value'] for k in keys])
    nu = np.array([DATA['channels'][k]['neutrino_energy']['value'] for k in keys])
    energy = counts @ q * (1000*elementary_charge)
    neutrino_energy = counts @ nu * (1000*elementary_charge)
    non_neutrino = counts @ (q-nu) * (1000*elementary_charge)
    by_mode = {mode: np.sum(counts[:, [i for i, k in enumerate(keys) if DATA['channels'][k]['mode'] == mode]], axis=1)
               for mode in MODE_LABELS}
    a = np.array([DATA['nodes'][i]['A'] for i in nodes])
    z = np.array([DATA['nodes'][i]['Z'] for i in nodes])
    baryon_initial = float(initial[:n] @ a) * initial_population
    charge_initial = float(initial[:n] @ z) * initial_population
    charge = populations @ z - by_mode['beta_minus'] + by_mode['beta_plus'] + by_mode['electron_capture']
    activities = np.column_stack([np.sum(event_rates[:, [i for i, k in enumerate(keys)
                                                         if DATA['channels'][k]['parent'] == p]], axis=1) for p in parents])
    return {'node_ids': nodes, 'labels': [DATA['nodes'][i]['label'] for i in nodes],
            'parents': parents, 'channel_order': keys, 'channels': dict(channels),
            'populations': populations.tolist(), 'population_fractions': (populations/initial_population).tolist(),
            'event_rates_s': event_rates.tolist(), 'channel_event_counts': counts.tolist(),
            'activity_s': activities.tolist(), 'total_activity_s': np.sum(event_rates, axis=1).tolist(),
            'electron_count': by_mode['beta_minus'].tolist(), 'positron_count': by_mode['beta_plus'].tolist(),
            'captured_electron_count': by_mode['electron_capture'].tolist(),
            'electron_neutrino_count': (by_mode['beta_plus']+by_mode['electron_capture']).tolist(),
            'electron_antineutrino_count': by_mode['beta_minus'].tolist(),
            'energy_available_J': energy.tolist(), 'energy_neutrino_J': neutrino_energy.tolist(),
            'energy_non_neutrino_available_J': non_neutrino.tolist(),
            'energy_deposited_J': None,
            'baryon_relative_error': float(np.max(np.abs(populations @ a/baryon_initial-1))),
            'charge_residual_per_initial_nucleus': float(np.max(np.abs(charge-charge_initial))/initial_population),
            'population_sum_error': float(np.max(np.abs(np.sum(populations, axis=1)/initial_population-1))),
            'minimum_population_fraction': float(np.min(populations)/initial_population),
            'energy_balance_relative_error': float(np.max(np.abs(energy-neutrino_energy-non_neutrino))
                                                    / max(float(np.max(energy)), 1e-300))}


def experiment(params, controls):
    case = params['parent_case']
    keys = channel_keys(case)
    active = {k: controls['weak']['acting'] and controls['weak']['effects']['decay_' + k] for k in keys}
    scaled_times = np.linspace(0.0, float(params['duration_half_lives']), 241)
    number = float(params['initial_population'])
    daughter_fraction = float(params['initial_daughter_fraction'])
    full = evolve(case, number, daughter_fraction, scaled_times, dict.fromkeys(keys, True))
    actual = full if all(active.values()) else evolve(case, number, daughter_fraction, scaled_times, active)
    parent = DATA['parents'][case]
    # Use convenient display units while the exported clock remains elapsed SI seconds.
    end = float(scaled_times[-1]*parent['half_life_s'])
    unit, factor = ('s', 1) if end < 3600 else ('h', 3600) if end < 172800 else ('d', 86400) if end < 63113852 else ('anos tropicais', 31556926)
    reference = {'evaluation': DATA['source'], 'parents': {p: DATA['parents'][p] for p in parent_keys(case)},
                 'channels': {k: DATA['channels'][k] for k in keys}, 'full_evolution': full,
                 'channel_dependencies': 'Interação fraca por largura parcial. Suprimir um ramo não renormaliza os demais. '
                                         'Ambiente atômico EC preservado; sem relaxação EM ou transporte de neutrinos calculados.',
                 'normalization_note': DATA['normalization'], 'reference_curve_species': parent['label']}
    return {'model': CASES[case] + '; populações esperadas por exponencial de matriz, avaliação ENSDF/LiveChart fixada.',
            'domain': 'Estados iniciais fundamentais; filhos agregados por A/Z e excitações identificadas nos ramos. '
                      'EC usa o ambiente atômico da avaliação, sem prever plasma ionizado. Sem espectros, oscilação, transporte, '
                      'relaxação gamma ou aniquilação temporal. NUBASE2020 é comparação distinta, sem substituir os valores ENSDF.',
            'parameter_note': 'Duração expressa em meias-vidas ENSDF de referência do pai inicial, inclusive quando um canal é suprimido. '
                              'Q−energiaν é o restante disponível, sem assumir calor depositado. EC usa energy_ec como energia nominal aproximada.',
            'influences': ['weak'], 'time_s': (scaled_times*parent['half_life_s']).tolist(),
            'time_display': {'unit': unit, 'seconds_per_unit': factor},
            'curve_axis': 'população esperada / população nuclear inicial total', 'probe_kind': 'composition',
            'curves': [{'name': label, 'values': [row[i] for row in actual['population_fractions']]}
                       for i, label in enumerate(actual['labels'])],
            'reference_curve': [row[0] for row in full['population_fractions']],
            'decays': actual, 'reference': reference,
            'measurements': [
                {'label': 'Meia-vida ENSDF de referência', 'value': parent['half_life_s'], 'unit': 's'},
                {'label': 'Atividade total aplicada no início', 'value': actual['total_activity_s'][0], 'unit': 'Bq'},
                {'label': 'Energia disponível ao final', 'value': actual['energy_available_J'][-1], 'unit': 'J'},
                {'label': 'Resíduo de carga / núcleo inicial', 'value': actual['charge_residual_per_initial_nucleus'], 'unit': 'relativo'}],
            'sources': DATA['sources']}
