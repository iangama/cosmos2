"""Forward isolated binary mixtures, exact depletion and competing D+D channels.

Products are counted without secondary reactions. Temperature and volume are
prescribed; available Q energy is neither deposited heat nor luminosity.
"""
from collections import Counter
from pathlib import Path
import json
import math

import numpy as np
from scipy.constants import Avogadro, elementary_charge
import nuclear_energies as energies

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'data/science/fusion.json').read_text(encoding='utf-8'))
MIXTURES = {
    'dt': {'label': 'D + T → He-4 + n', 'fuels': ['d', 't'], 'channels': ['dt']},
    'dd': {'label': 'D + D · ramos He-3 + n e T + p', 'fuels': ['d', 'd'], 'channels': ['ddn', 'ddp']},
    'dp': {'label': 'D + p → He-3 + γ', 'fuels': ['d', 'p'], 'channels': ['dp']},
    'he3he3': {'label': 'He-3 + He-3 → He-4 + 2p', 'fuels': ['he3', 'he3'], 'channels': ['he3he3']},
    'li7p': {'label': 'Li-7 + p → 2 He-4', 'fuels': ['li7', 'p'], 'channels': ['li7p']},
    'c12alpha': {'label': 'C-12 + He-4 → O-16 + γ', 'fuels': ['c12', 'he4'], 'channels': ['c12alpha']},
}
CHANNEL_LABELS = {
    'dt': 'D + T → He-4 + n', 'ddn': 'D + D → He-3 + n', 'ddp': 'D + D → T + p',
    'dp': 'D + p → He-3 + γ', 'he3he3': 'He-3 + He-3 → He-4 + 2p',
    'li7p': 'Li-7 + p → 2 He-4', 'c12alpha': 'C-12 + He-4 → O-16 + γ',
}
RADIATIVE = {'dp', 'c12alpha'}


def rate_value(temperature, entry):
    t = temperature / 1e9
    basis = (1, 1/t, t**(-1/3), t**(1/3), t, t**(5/3), math.log(t))
    return math.fsum(math.exp(math.fsum(a*b for a, b in zip(s, basis))) for s in entry['sets'])


def effect_keys(mixture):
    keys = {'strong': ['fusion_' + c for c in MIXTURES[mixture]['channels']]}
    if set(MIXTURES[mixture]['channels']) & RADIATIVE:
        keys['electromagnetic'] = ['fusion_radiative_capture']
    return keys


def evolve(mixture, density, ratio, times, coefficients):
    """Densities/extents without subtractive loss at either depletion limit."""
    # Browser JSON can spell 1e20 as a large integer. Keep the numerical
    # arrays float64 instead of NumPy object arrays for such valid inputs.
    density, ratio = float(density), float(ratio)
    times = np.asarray(times, dtype=float)
    fuel_a, fuel_b = MIXTURES[mixture]['fuels']
    keys = MIXTURES[mixture]['channels']
    species = list(dict.fromkeys([fuel_a, fuel_b, *[n for k in keys for n in DATA['rates'][k]['products']]]))
    initial = {n: 0.0 for n in species}
    initial[fuel_a] = density
    if fuel_a != fuel_b:
        initial[fuel_b] = density * ratio
    n0 = np.array([initial[n] for n in species])
    k = math.fsum(coefficients.values())
    extent = np.zeros((len(times), len(keys)))
    densities = np.tile(n0, (len(times), 1))
    if k:
        if fuel_a == fuel_b:
            exposure = k * density * times
            remaining = density / (1 + exposure)
            total_events = .5 * density * (exposure / (1 + exposure))
        else:
            low, high = sorted((initial[fuel_a], initial[fuel_b]))
            delta = high - low
            if delta == 0:
                exposure = k * low * times
                remaining = low / (1 + exposure)
                total_events = low * (exposure / (1 + exposure))
            else:
                exposure = k * delta * times
                lost = -np.expm1(-exposure)
                denominator = delta + low * lost
                remaining = low * (delta / denominator) * np.exp(-exposure)
                total_events = low * (high / denominator) * lost
        for j, key in enumerate(keys):
            extent[:, j] = total_events * (coefficients[key] / k)
            for product, count in Counter(DATA['rates'][key]['products']).items():
                densities[:, species.index(product)] += count * extent[:, j]
        if fuel_a == fuel_b:
            densities[:, species.index(fuel_a)] = remaining
        else:
            lower = fuel_a if initial[fuel_a] <= initial[fuel_b] else fuel_b
            higher = fuel_b if lower == fuel_a else fuel_a
            densities[:, species.index(lower)] = remaining
            densities[:, species.index(higher)] = remaining + abs(initial[fuel_a] - initial[fuel_b])
    event_rates = np.column_stack([
        DATA['rates'][key]['prefactor'] * coefficients[key]
        * densities[:, species.index(fuel_a)] * densities[:, species.index(fuel_b)] for key in keys])
    atomic_a = np.array([DATA['nuclides'][n]['A'] for n in species])
    atomic_z = np.array([DATA['nuclides'][n]['Z'] for n in species])
    baryons = float(n0 @ atomic_a)
    charge = float(n0 @ atomic_z)
    mass_fractions = densities * atomic_a / baryons
    q = np.array([DATA['rates'][key]['Q_MeV'] for key in keys])
    energy = extent @ q * 1e6 * elementary_charge
    photons = sum((extent[:, j] for j, key in enumerate(keys) if key in RADIATIVE), np.zeros(len(times)))
    return {'species': species, 'initial_density_m3': initial, 'baryon_density_m3': baryons,
            'number_density_m3': densities.tolist(), 'mass_fractions': mass_fractions.tolist(),
            'event_rates_m3_s': event_rates.tolist(), 'reaction_extents_m3': extent.tolist(),
            'energy_available_J_m3': energy.tolist(), 'photon_count_m3': photons.tolist(),
            'baryon_relative_error': float(np.max(np.abs(densities @ atomic_a / baryons - 1))),
            'charge_relative_error': float(np.max(np.abs(densities @ atomic_z / charge - 1)))}


def experiment(params, controls):
    mixture = params['mixture']
    keys = MIXTURES[mixture]['channels']
    times = np.linspace(0.0, float(params['duration_s']), 241)
    coefficients = {key: rate_value(params['temperature_K'], DATA['rates'][key]) * 1e-6 / Avogadro for key in keys}
    channels = {key: controls['strong']['acting'] and controls['strong']['effects']['fusion_' + key]
                and (key not in RADIATIVE or (controls['electromagnetic']['acting']
                     and controls['electromagnetic']['effects']['fusion_radiative_capture'])) for key in keys}
    reference = evolve(mixture, params['density_m3'], params['partner_ratio'], times, coefficients)
    actual = reference if all(channels.values()) else evolve(mixture, params['density_m3'], params['partner_ratio'], times,
                                                             {k: v if channels[k] else 0 for k, v in coefficients.items()})
    source_channels = {}
    for key in keys:
        entry = DATA['rates'][key]
        terms = Counter(entry['reactants'])
        terms.subtract(entry['products'])
        q_ame = energies.combination({DATA['nuclides'][n]['ame2020_id']: c for n, c in terms.items()})
        source_channels[key] = {'label': CHANNEL_LABELS[key], 'Q_MeV': entry['Q_MeV'],
                                'Q_AME_keV': q_ame, 'rate_cm3_mol_s': coefficients[key] * Avogadro * 1e6,
                                'sigma_v_m3_s': coefficients[key], 'prefactor': entry['prefactor'],
                                'source': entry['source'], 'fit_label': entry['label'],
                                'radiative': key in RADIATIVE, 'fit_uncertainty': None}
    species = actual['species']
    ids = [DATA['nuclides'][n]['ame2020_id'] for n in species]
    records = [energies.species(i) for i in ids]
    initial_total_rate = math.fsum(reference['event_rates_m3_s'][0])
    dependencies = ('Atuação forte controla cada canal; capturas radiativas exigem forte e EM. '
                    'Barreira Coulomb e núcleos das taxas são preservados ao suprimir operadores: hipótese contrafactual.')
    return {'model': MIXTURES[mixture]['label'] + '; taxas REACLIB e consumo analítico por estequiometria.',
            'domain': 'Zona homogênea Maxwelliana, T e volume prescritos; 10–1000 MK. '
                      'Sem screening, reações inversas ou secundárias dos produtos, confinamento, transporte ou realimentação térmica. '
                      'Energia disponível não significa calor depositado ou luminosidade. Incertezas dos fits ausentes no recorte; não são zero.',
            'parameter_note': ('Há uma só densidade de combustível; razão entre combustíveis não se aplica.'
                               if MIXTURES[mixture]['fuels'][0] == MIXTURES[mixture]['fuels'][1]
                               else 'Razão segundo/primeiro define as densidades iniciais; duração física permanece fixa.'),
            'influences': ['strong', 'electromagnetic'] if set(keys) & RADIATIVE else ['strong'],
            'time_s': times.tolist(), 'curve_axis': 'fração mássica convencional A·n / bárions iniciais',
            'probe_kind': 'composition',
            'curves': [{'name': r['label'], 'values': [row[i] for row in actual['mass_fractions']]}
                       for i, r in enumerate(records)],
            'reference_curve': [row[0] for row in reference['mass_fractions']],
            'reference': {'channels': source_channels, 'channel_dependencies': dependencies,
                          'reference_curve_species': records[0]['label'], 'initial_total_rate_m3_s': initial_total_rate,
                          'composition': reference},
            'fusion': {**actual, 'mixture': mixture, 'channels': channels, 'channel_order': keys,
                       'species_ids': ids, 'species_labels': [r['label'] for r in records],
                       'binding_AME': [{'id': r['id'], 'label': r['label'], 'A': r['A'],
                                        'binding_per_nucleon': r['quantities']['binding_per_nucleon']} for r in records],
                       'time_sampling': '241 uniform physical instants; no adaptive time compression',
                       'energy_deposited_J_m3': None, 'neutrino_count_m3': 0},
            'measurements': [
                {'label': 'Taxa total aplicada no início', 'value': math.fsum(actual['event_rates_m3_s'][0]), 'unit': 'reações/(m³·s)'},
                {'label': 'Energia disponível ao final', 'value': actual['energy_available_J_m3'][-1], 'unit': 'J/m³'},
                {'label': 'Duração física calculada', 'value': params['duration_s'], 'unit': 's'},
                {'label': 'Resíduo relativo de bárions', 'value': actual['baryon_relative_error'], 'unit': 'relativo'}],
            'sources': list(dict.fromkeys([*DATA['sources'], energies.nuclei.SOURCES[2]['url'],
                                           *[DATA['rates'][k]['source']['URL'] for k in keys]]))}
