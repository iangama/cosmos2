"""Versioned four-center import, independent of the legacy three-body parser."""
from pathlib import Path
import copy
import math
import platform
import re
import uuid
import rebound

from atlas_import import digest
from physics import PHYSICAL_SCALE
from solar_contract import ROOT, FRAME, EXCLUDED, sha, validate_catalog

KIND = 'solar_four_physical_centers'


def _typed_equal(actual, expected):
    if type(expected) in (int, float):
        return type(actual) in (int, float) and actual == expected
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(_typed_equal(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(_typed_equal(a, b) for a, b in zip(actual, expected))
    return actual == expected


def generation():
    folder = Path(__file__).parent
    return {'schema': 1, 'model_id': 'cosmos2:reduced-sun-earth-moon-jupiter599-newton',
            'model_version': '1.0.0-candidate',
            'code_sha256': {p: sha(folder / p) for p in
                           ['solar_contract.py', 'solar_catalog.py', 'solar_import.py', 'import_dispatch.py',
                            'session.py', 'body_registry.py', 'physics.py', 'solar_tides.py', 'earth_magnetism.py', 'geomagnetism.py', 'jupiter_magnetism.py', 'jrm33.py']},
            'runtime': {'python': platform.python_version(), 'rebound': rebound.__version__},
            'data_sha256': {'canonical-units.json': sha(ROOT / 'data/science/canonical-units.json'), 'igrf14coeffs.txt': sha(ROOT / 'data/science/igrf14coeffs.txt'), 'earth_EOP_PCK': sha(ROOT / 'output/is3-earth-orientation-staging/earth_000101_270118_261022.bpc'), 'earth_EOP_receipt': sha(ROOT / 'evidence/is3-earth-orientation-acquisition-20261023.json'), 'JRM33_coefficients': sha(folder / 'jrm33-coefficients.json'), 'Jupiter_orientation_receipt': sha(ROOT / 'evidence/is3-jupiter-orientation-acquisition-20261023b.json'), 'PCK00011': sha(ROOT / 'data/spice/pck00011.tpc'), 'LSK': sha(ROOT / 'data/spice/naif0012.tls')}}


def _assemble(catalog, branch, source_generation):
    bodies = []
    total = math.fsum(b['GM']['value'] for b in catalog['bodies'])
    center = [math.fsum(b['GM']['value'] * b['position_m'][k] for b in catalog['bodies']) / total for k in range(3)]
    velocity = [math.fsum(b['GM']['value'] * b['velocity_m_s'][k] for b in catalog['bodies']) / total for k in range(3)]
    for source in catalog['bodies']:
        target = source['naif_id']
        bodies.append({'id': f'exp:{branch}:naif:{target}', 'reference_id': source['id'],
                       'naif_id': target, 'name': source['name'], 'entity_kind': 'physical_body',
                       'source_GM': copy.deepcopy(source['GM']),
                       'source_position_m': list(source['position_m']), 'source_velocity_m_s': list(source['velocity_m_s']),
                       'source_uncertainty': {'position_m': None, 'velocity_m_s': None},
                       'shape_reference': None, 'reference_properties': [],
                       'mass': source['GM']['value'] / PHYSICAL_SCALE['nominal_GM_unit_m3_s2'],
                       'position': [(x - c) / PHYSICAL_SCALE['length_unit_m'] for x, c in zip(source['position_m'], center)],
                       'velocity': [(x - c) / PHYSICAL_SCALE['velocity_unit_m_s'] for x, c in zip(source['velocity_m_s'], velocity)]})
    return {
        'schema': 2, 'kind': KIND, 'version': '1.0.0', 'branch_id': branch,
        'contract': {'schema': 2, 'frame': FRAME, 'units': {'system': 'canonical', 'G': 1.0},
                     'model': 'newtonian_point_masses', 'collisions': 'disabled', 'integrator': 'IAS15', 'epsilon': 1e-9,
                     'epoch': copy.deepcopy(catalog['epoch']),
                     'time': 'elapsed model time; epoch_et_tdb_s + t*time_unit_s; not a replacement for JPL ephemerides',
                     'jupiter_representation': 'physical center599 and planet GM; no independent barycenter5 particle',
                     'excluded_influences': list(EXCLUDED)},
        'physical_scale': copy.deepcopy(PHYSICAL_SCALE),
        'source': {k: copy.deepcopy(catalog[k]) for k in ['model', 'epoch', 'frame', 'center_naif_id', 'aberration', 'provenance']},
        'reference_catalog': copy.deepcopy(catalog),
        'initial_ssb_origin_m': center, 'inertial_origin_velocity_m_s': velocity,
        'render_frame': catalog['render_frame'], 'j2000_to_render_frame': copy.deepcopy(catalog['j2000_to_render_frame']),
        'generation': copy.deepcopy(source_generation), 'bodies': bodies,
    }


def prepare(catalog):
    catalog = validate_catalog(catalog)
    result = _assemble(catalog, uuid.uuid4().hex, generation())
    result['initial_state_sha256'] = digest(result)
    return validate(result)


def validate(value):
    if not isinstance(value, dict) or type(value.get('schema')) is not int or value['schema'] != 2 or value.get('kind') != KIND or value.get('version') != '1.0.0':
        raise ValueError('Formato da cópia solar de quatro centros incompatível.')
    body = {k: v for k, v in value.items() if k != 'initial_state_sha256'}
    if digest(body) != value.get('initial_state_sha256'):
        raise ValueError('Integridade da cópia solar inválida.')
    branch = value.get('branch_id')
    if not isinstance(branch, str) or not re.fullmatch('[0-9a-f]{32}', branch):
        raise ValueError('Ramificação solar inválida.')
    catalog = validate_catalog(value.get('reference_catalog'))
    saved_generation = value.get('generation')
    if not isinstance(saved_generation, dict) or saved_generation.get('model_id') != 'cosmos2:reduced-sun-earth-moon-jupiter599-newton' or saved_generation.get('model_version') != '1.0.0-candidate':
        raise ValueError('Geração científica solar incompatível.')
    expected = _assemble(catalog, branch, saved_generation)
    if not _typed_equal(body, expected):
        raise ValueError('Cópia solar não corresponde aos estados, GM, referencial ou operadores declarados.')
    # Booleans can compare equal to numbers in Python; explicitly reject them.
    for row in value['bodies']:
        if type(row.get('mass')) not in (int, float):
            raise ValueError('Massa canônica inválida.')
        for key in ['position', 'velocity']:
            if any(type(x) not in (int, float) for x in row[key]):
                raise ValueError('Fase canônica inválida.')
    for row in expected['bodies']:
        for key, scale, origin, original, limit in [
            ('position', PHYSICAL_SCALE['length_unit_m'], 'initial_ssb_origin_m', 'source_position_m', .001),
            ('velocity', PHYSICAL_SCALE['velocity_unit_m_s'], 'inertial_origin_velocity_m_s', 'source_velocity_m_s', 1e-8),
        ]:
            if max(abs(x * scale + c - y) for x, c, y in zip(row[key], value[origin], row[original])) > limit:
                raise ValueError('Ida/volta SI/canônica solar inconsistente.')
    return copy.deepcopy(value)
