"""AME2020 neutral-atom Q values and fixed-target relativistic kinematics.

Reference instrument only: no cross sections, branching ratios or reaction rates.
Original printed mass excesses are combined as Decimal, with shared variables
consolidated before propagating the explicitly independent mass uncertainties.
"""
from collections import Counter
from decimal import Decimal, InvalidOperation, localcontext
from functools import lru_cache
from pathlib import Path
import copy
import hashlib
import json
import platform

import nuclei

ROOT = Path(__file__).resolve().parents[1]
UC2 = Decimal('931494.10242')  # keV, conversion adopted by AME2020
PHOTON = 'particle:photon'
SAVE_PATH = ROOT / 'user/nuclei/energies-selection.json'


def ident(z, a):
    return f'nucleus:ame2020:{z}:{a}'


N, H, D, T, HE3, HE4 = (ident(z, a) for z, a in ((0, 1), (1, 1), (1, 2), (1, 3), (2, 3), (2, 4)))


def preset(key, label, projectile, target, products, energy):
    return {'id': key, 'label': label, 'configuration': {
        'schema': 1, 'projectile_id': projectile, 'target_id': target,
        'products': [{'id': i, 'count': c} for i, c in products],
        'projectile_energy_MeV': energy, 'separation_id': target}}


PRESETS = [
    preset('dt', 'D + T → He-4 + n', D, T, [(HE4, 1), (N, 1)], .1),
    preset('dd-n', 'D + D → He-3 + n', D, D, [(HE3, 1), (N, 1)], .1),
    preset('dd-p', 'D + D → T + H-1', D, D, [(T, 1), (H, 1)], .1),
    preset('dp', 'D + H-1 → He-3 + γ', D, H, [(HE3, 1), (PHOTON, 1)], .1),
    preset('he3he3', 'He-3 + He-3 → He-4 + 2 H-1', HE3, HE3, [(HE4, 1), (H, 2)], .1),
    preset('li7p', 'H-1 + Li-7 → 2 He-4', H, ident(3, 7), [(HE4, 2)], .1),
    preset('c12alpha', 'He-4 + C-12 → O-16 + γ', HE4, ident(6, 12), [(ident(8, 16), 1), (PHOTON, 1)], 1),
    preset('n14-n2n', 'n + N-14 → N-13 + 2 n', N, ident(7, 14), [(ident(7, 13), 1), (N, 2)], 15),
    preset('c12-photo3alpha', 'γ + C-12 → 3 He-4', PHOTON, ident(6, 12), [(HE4, 3)], 10),
]
GENERATION = {
    'schema': 1, 'model_id': 'cosmos2:ame2020-reaction-energies', 'model_version': '1.0.0',
    'code_sha256': {f'app/{name}': hashlib.sha256((ROOT / 'app' / name).read_bytes()).hexdigest()
                    for name in ('nuclear_energies.py', 'nuclei.py')},
    'data_sha256': {'data/science/ame2020-mass-original.txt': nuclei.EXPECTED_SHA256},
    'runtime': {'python': platform.python_version()},
}
CONTRACT = {
    'model_id': GENERATION['model_id'], 'kind': 'evaluated_mass_reference_and_kinematic_constraint',
    'mass_convention': 'neutral atoms; free neutron; zero photon rest mass; no bare-ion electron-binding correction',
    'states': 'AME2020 reference states; no excited states or isomers',
    'energy_unit': 'keV', 'incident_energy_unit': 'MeV',
    'reference_frame': 'laboratory frame with massive target initially at rest',
    'projectile_energy': 'kinetic for massive projectile; total energy for photon',
    'time': None, 'evolution': None,
    'Q': 'sum(initial mass excesses) - sum(final mass excesses); A and Z conserved',
    'threshold': 'max(0, -Q * (2 * (Ma*c^2 + MT*c^2) - Q) / (2 * MT*c^2))',
    'channel_domain': 'two incident particles; at least two final particles; no weak leptonic channels',
    'uncertainty': 'linear propagation of independent tabulated mass uncertainties; shared nuclide mass consolidated; AME covariances unavailable',
    'conversion_uc2_keV': str(UC2), 'conversion_uncertainty_propagated': False,
    'threshold_uncertainty': 'piecewise linear mass-only propagation; not a complete uncertainty, especially near Q=0',
    'excluded': ['rates', 'cross sections', 'Coulomb transmission', 'selection rules', 'half lives',
                 'neutrino energies', 'classical nuclear trajectories', 'ionization corrections'],
    'provenance': GENERATION,
    'sources': nuclei.SOURCES + [
        {'title': 'UCSD Física 200A · §15.7.3, limiar pelo invariante relativístico',
         'url': 'https://courses.physics.ucsd.edu/2009/Fall/physics200a/LECTURES/CH15.pdf'},
        {'title': 'NNDC QCalc · comparação externa de Q com AME2020, sem covariâncias',
         'url': 'https://www.nndc.bnl.gov/qcalc/'},
    ],
    'external_threshold_comparison': {
        'case': 'n14-n2n', 'NNDC_reported_keV': 11314.175,
        'note': 'NNDC threshold differs from the invariant relativistic result; preserve discrepancy, not a source uncertainty'},
}


@lru_cache(maxsize=1)
def records():
    return {r['id']: r for r in nuclei.catalog()['records']}


def species(key):
    if not isinstance(key, str):
        raise ValueError('O identificador da espécie deve ser texto.')
    if key == PHOTON:
        return {'id': PHOTON, 'label': 'γ', 'A': 0, 'Z': 0, 'source_line': None,
                'quantities': {'mass_excess': {'value': 0, 'uncertainty': 0,
                    'raw_value': '0', 'raw_uncertainty': '0', 'unit': 'keV',
                    'status': 'defined', 'estimated': False, 'uncertainty_estimated': False,
                    'source_resolution': 0}}}
    if key not in records():
        raise ValueError('Espécie ausente no acervo AME2020: ' + key)
    return records()[key]


def configuration(request):
    if not isinstance(request, dict) or request.get('schema', 1) != 1:
        raise ValueError('Configuração de energias nucleares inválida.')
    default = PRESETS[0]['configuration']
    projectile = request.get('projectile_id', default['projectile_id'])
    target = request.get('target_id', default['target_id'])
    species(projectile)
    species(target)
    if target == PHOTON:
        raise ValueError('O alvo em repouso precisa ter massa positiva; γ não pode ser alvo.')
    products = request.get('products', default['products'])
    if not isinstance(products, list) or not 1 <= len(products) <= 8:
        raise ValueError('Informe de um a oito termos de produtos.')
    counts = Counter()
    for product in products:
        if not isinstance(product, dict):
            raise ValueError('Cada produto precisa de espécie e contagem inteira.')
        key, count = product.get('id'), product.get('count')
        species(key)
        if type(count) is not int or not 1 <= count <= 4:
            raise ValueError('A contagem de cada produto deve ser inteira entre 1 e 4.')
        counts[key] += count
    if not 2 <= sum(counts.values()) <= 8 or max(counts.values()) > 4:
        raise ValueError('Este instrumento exige 2–8 partículas finais e até 4 da mesma espécie; 2→1 exige tratamento de ressonância.')
    for quantum in ('A', 'Z'):
        incident = species(projectile)[quantum] + species(target)[quantum]
        final = sum(species(i)[quantum] * c for i, c in counts.items())
        if incident != final:
            raise ValueError(f'A reação não conserva {quantum}: {incident} nos incidentes, {final} nos produtos.')
    energy = request.get('projectile_energy_MeV', default['projectile_energy_MeV'])
    if isinstance(energy, bool) or not isinstance(energy, (int, float, str)) or len(str(energy)) > 40:
        raise ValueError('Energia do projétil inválida.')
    try:
        energy = Decimal(str(energy))
    except InvalidOperation as error:
        raise ValueError('Energia do projétil inválida.') from error
    if not energy.is_finite() or not 0 <= energy <= 100:
        raise ValueError('A energia do projétil deve estar entre 0 e 100 MeV.')
    selected = request.get('separation_id', default['separation_id'])
    species(selected)
    if selected == PHOTON:
        raise ValueError('Selecione um estado AME2020 para as energias de separação.')
    return {'schema': 1, 'projectile_id': projectile, 'target_id': target,
            'products': [{'id': i, 'count': counts[i]} for i in sorted(counts)],
            'projectile_energy_MeV': float(energy), 'separation_id': selected}


def mass_excess(key):
    return nuclei.number(species(key)['quantities']['mass_excess']['raw_value'])[0]


def rest_energy(key):
    excess = mass_excess(key)
    return None if excess is None else Decimal(species(key)['A']) * UC2 + excess


def sigma_independent(gradient):
    variance = Decimal(0)
    for key, coefficient in gradient.items():
        if coefficient == 0:
            continue
        uncertainty = nuclei.number(species(key)['quantities']['mass_excess']['raw_uncertainty'])[0]
        if uncertainty is None:
            return None
        variance += (coefficient * uncertainty) ** 2
    return float(variance.sqrt())


def combination(coefficients):
    coefficients = {key: coefficient for key, coefficient in coefficients.items() if coefficient != 0}
    terms, total, rounding = [], Decimal(0), Decimal(0)
    known, estimated, uncertainty_estimated = True, False, False
    for key, coefficient in sorted(coefficients.items()):
        r = species(key)
        q = r['quantities']['mass_excess']
        value = mass_excess(key)
        known = known and value is not None
        if value is not None:
            total += coefficient * value
        resolution = q['source_resolution']
        if resolution is not None:
            rounding += abs(coefficient) * Decimal(str(resolution)) / 2
        estimated |= q['estimated']
        uncertainty_estimated |= q['uncertainty_estimated']
        terms.append({'id': key, 'label': r['label'], 'coefficient': coefficient,
                      'source_line': r['source_line'], 'mass_excess': copy.deepcopy(q),
                      'contribution_keV': None if value is None else float(coefficient * value)})
    return {'value': float(total) if known else None, 'decimal_keV': str(total) if known else None,
            'unit': 'keV', 'status': 'missing' if not known else 'estimated' if estimated else 'evaluated',
            'estimated': estimated, 'uncertainty_estimated': uncertainty_estimated,
            'standard_uncertainty_independent': sigma_independent(coefficients) if known else None,
            'total_uncertainty': None, 'covariances_included': False,
            'source_print_rounding_bound_keV': float(rounding) if known else None,
            'terms': terms}


def separations(key):
    parent = species(key)
    result = []
    for name, da, dz, emitted, count in (('Sn', 1, 0, N, 1), ('Sp', 1, 1, H, 1),
                                         ('S2n', 2, 0, N, 2), ('Salpha', 4, 2, HE4, 1)):
        daughter = ident(parent['Z'] - dz, parent['A'] - da)
        if daughter not in records():
            result.append({'name': name, 'value': None, 'unit': 'keV', 'status': 'missing_remnant',
                           'daughter_id': daughter, 'reason': 'Remanescente ausente no acervo; energia desconhecida.'})
            continue
        coefficients = Counter({daughter: 1})
        coefficients[emitted] += count
        coefficients[key] -= 1
        result.append({'name': name, 'daughter_id': daughter, **combination(coefficients)})
    return {'parent_id': key, 'parent_label': parent['label'], 'energies': result}


def _evaluate(cfg):
    projectile, target = cfg['projectile_id'], cfg['target_id']
    initial_counts = Counter([projectile, target])
    coefficients = initial_counts.copy()
    for product in cfg['products']:
        coefficients[product['id']] -= product['count']
    q = combination(coefficients)
    ma, mt = rest_energy(projectile), rest_energy(target)
    kinematics = {'status': 'missing_mass', 'threshold_keV': None, 'threshold_NR_keV': None,
                  'available_CM_keV': None, 'accessible_by_energy': None, 'curve': []}
    if q['value'] is not None and ma is not None and mt is not None:
        qd = Decimal(q['decimal_keV'])
        total_rest = ma + mt
        threshold = max(Decimal(0), -qd * (2 * total_rest - qd) / (2 * mt))
        nr = max(Decimal(0), -qd * (1 + ma / mt))
        beam = Decimal(str(cfg['projectile_energy_MeV'])) * 1000

        def available(kinetic):
            invariant = (total_rest * total_rest + 2 * mt * kinetic).sqrt()
            return qd + 2 * mt * kinetic / (invariant + total_rest)

        gradient = {}
        if qd < 0:
            for key in set(coefficients) | set(initial_counts):
                if key == PHOTON:
                    continue  # Photon rest mass is fixed, not an AME mass variable.
                gradient[key] = ((-total_rest + qd) / mt * coefficients[key]
                                 - qd / mt * initial_counts[key]
                                 - threshold / mt * (key == target))
        limit = min(Decimal(100000), max(Decimal(1000), threshold * Decimal('1.3'), beam * Decimal('1.2')))
        curve = [{'projectile_energy_MeV': float(limit * j / 200 / 1000),
                  'available_CM_MeV': float(available(limit * j / 200) / 1000)} for j in range(201)]
        kinematics = {'status': 'calculated', 'projectile_rest_keV': float(ma), 'target_rest_keV': float(mt),
                      'threshold_keV': float(threshold), 'threshold_decimal_keV': str(threshold),
                      'threshold_NR_keV': float(nr),
                      'threshold_standard_uncertainty_independent_keV': sigma_independent(gradient),
                      'threshold_uncertainty_gradient': {key: float(value) for key, value in gradient.items()},
                      'available_CM_keV': float(available(beam)),
                      'accessible_by_energy': beam >= threshold,
                      'curve': curve}
    initial_label = ' + '.join(species(i)['label'] for i in (projectile, target))
    final_label = ' + '.join((str(p['count']) + ' ' if p['count'] != 1 else '') + species(p['id'])['label'] for p in cfg['products'])
    return {'schema': 1, 'configuration': cfg, 'reaction_label': initial_label + ' → ' + final_label,
            'generation': GENERATION, 'scientific_contract': CONTRACT,
            'reaction_sha256': nuclei.digest({'projectile': projectile, 'target': target,
                'products': cfg['products'], 'generation': GENERATION}),
            'configuration_sha256': nuclei.digest({'configuration': cfg, 'generation': GENERATION}),
            'Q': q, 'kinematics': kinematics, 'separation': separations(cfg['separation_id']),
            'conservation': {name: {'initial': sum(species(i)[name] for i in (projectile, target)),
                                   'final': sum(species(p['id'])[name] * p['count'] for p in cfg['products'])}
                             for name in ('A', 'Z')}}


def evaluate(request):
    with localcontext() as ctx:
        ctx.prec = 40
        return _evaluate(configuration(request))


def catalog():
    return {'schema': 1, 'generation': GENERATION, 'scientific_contract': CONTRACT, 'presets': PRESETS,
            'species': [{k: r[k] for k in ('id', 'label', 'A', 'Z')} for r in [*records().values(), species(PHOTON)]]}


def save(request, path=None):
    body = {'schema': 1, 'configuration': configuration(request), 'generation': GENERATION}
    return nuclei.write_atomic(path or SAVE_PATH, {**body, 'sha256': nuclei.digest(body)})


def load(path=None):
    path = Path(path or SAVE_PATH)
    if path.stat().st_size > 8192:
        raise ValueError('Arquivo de energias nucleares excede o limite.')
    envelope = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(envelope, dict) or envelope.get('schema') != 1:
        raise ValueError('Formato de energias nucleares inválido.')
    body = {key: envelope.get(key) for key in ('schema', 'configuration', 'generation')}
    if envelope.get('sha256') != nuclei.digest(body) or not isinstance(body['generation'], dict):
        raise ValueError('Integridade ou geração de energias nucleares inválida.')
    return {'configuration': configuration(body['configuration']), 'saved_generation': body['generation'],
            'current_generation': GENERATION,
            'compatibility': 'same_generation' if body['generation'] == GENERATION else 'changed_generation'}
