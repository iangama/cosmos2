"""Clone geometric JPL states into a declared reduced Newtonian experiment.

No SPICE/numpy dependency in the worker. It receives validated original SI
states, subset barycenter, units and a display-only frame transformation.
"""
from functools import lru_cache
from pathlib import Path
from decimal import Decimal
import copy
import hashlib
import json
import math
import platform
import uuid
import rebound
from physics import PHYSICAL_SCALE

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
TARGETS = [('10', 'Sol', 'GMS'), ('399', 'Terra', 'GM3'), ('301', 'Lua', 'GMM')]
FRAME = 'initial_subset_barycenter_inertial_axes_J2000'
EXCLUDED = ['demais planetas e luas', 'asteroides e outros corpos menores',
            'relatividade', 'J2 e deformações de maré', 'radiação e processos estelares', 'colisões']


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()).hexdigest()


@lru_cache(maxsize=1)
def gm_data():
    path = ROOT / 'data/spice/de442_tech-comments.txt'
    receipt = json.loads((ROOT / 'evidence/atlas-kernels-acquisition.json').read_text(encoding='utf-8'))
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != receipt['files'][path.name]['sha256']:
        raise ValueError('Comentários DE442 diferem do recibo de aquisição.')
    values = {}
    for i, line in enumerate(raw.decode('ascii').splitlines(), 1):
        tokens = line.split()
        if len(tokens) == 4 and tokens[0] in ('GMS', 'GM3', 'GMM'):
            if tokens[0] in values:
                raise ValueError('GM duplicado nos comentários DE442.')
            number = Decimal(tokens[3])
            values[tokens[0]] = {'value': float(number * Decimal(1000000000)),
                                'unit': 'm^3/s^2', 'uncertainty': None,
                                'origin': 'JPL DE442 published model parameter, printed SI conversion',
                                'raw_value_km3_s2': tokens[3], 'source_line': i,
                                'source': receipt['files'][path.name]['url'], 'source_sha256': sha,
                                'source_resolution_m3_s2': float(Decimal(10) ** number.as_tuple().exponent * Decimal(1000000000))}
    if set(values) != {'GMS', 'GM3', 'GMM'}:
        raise ValueError('GM Sol/Terra/Lua ausente.')
    return values


@lru_cache(maxsize=1)
def generation():
    code = ['app/physics.py', 'app/session.py', 'app/worker.py', 'app/atlas_import.py']
    data = ['data/science/canonical-units.json', 'data/spice/de442_tech-comments.txt',
            'data/spice/de442s.bsp', 'data/spice/naif0012.tls', 'data/spice/pck00011.tpc']
    return {'schema': 1, 'model_id': 'cosmos2:reduced-sun-earth-moon-newton', 'model_version': '1.1.0',
            'code_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in code},
            'data_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in data},
            'runtime': {'python': platform.python_version(), 'rebound': rebound.__version__}}


def vector(value):
    if not isinstance(value, list) or len(value) != 3 or any(type(v) not in (int, float) or not math.isfinite(v) for v in value):
        raise ValueError('Vetor SI inválido na cópia do Atlas.')
    return list(value)


def render_transform(value, frame):
    transform = value
    if frame != 'GALACTIC' or not isinstance(transform, list) or len(transform) != 3:
        raise ValueError('Transformação gráfica GALACTIC ausente.')
    transform = [vector(row) for row in transform]
    if max(abs(sum(transform[i][k] * transform[j][k] for k in range(3)) - (1 if i == j else 0)) for i in range(3) for j in range(3)) > 1e-12:
        raise ValueError('Transformação gráfica não é ortogonal.')
    determinant = (transform[0][0] * (transform[1][1] * transform[2][2] - transform[1][2] * transform[2][1])
                   - transform[0][1] * (transform[1][0] * transform[2][2] - transform[1][2] * transform[2][0])
                   + transform[0][2] * (transform[1][0] * transform[2][1] - transform[1][1] * transform[2][0]))
    if abs(determinant - 1) > 1e-12:
        raise ValueError('Transformação gráfica altera a orientação dos eixos.')
    return transform


def experiment_subset(atlas):
    """Explicit copy boundary: Saturn remains an excluded external influence."""
    result=copy.deepcopy(atlas)
    bodies=result.get('bodies',[])
    if not isinstance(bodies,list) or len({b.get('naif_id') for b in bodies if isinstance(b,dict)})!=len(bodies):
        raise ValueError('Corpos ausentes ou duplicados no Atlas.')
    result['bodies']=[b for b in bodies if b.get('naif_id') in {t[0] for t in TARGETS}]
    return result


def prepare(atlas):
    if not isinstance(atlas, dict) or atlas.get('schema') != 1 or atlas.get('frame') != 'J2000/ICRF' or atlas.get('center_naif_id') != '0' or atlas.get('aberration') != 'NONE':
        raise ValueError('A cópia exige estado geométrico SSB/J2000 do Atlas.')
    if atlas.get('position_unit') != 'm' or atlas.get('velocity_unit') != 'm/s':
        raise ValueError('Unidades do Atlas incompatíveis.')
    epoch = atlas.get('epoch', {})
    if not isinstance(epoch.get('utc'), str) or type(epoch.get('et_tdb_s')) not in (int, float) or not math.isfinite(epoch['et_tdb_s']):
        raise ValueError('Época UTC/TDB ausente na cópia do Atlas.')
    source_bodies = atlas.get('bodies', [])
    if not isinstance(source_bodies, list) or len(source_bodies) != 3:
        raise ValueError('Copie o subconjunto completo Sol/Terra/Lua.')
    by_id = {b.get('naif_id'): b for b in source_bodies if isinstance(b, dict)}
    if set(by_id) != {t[0] for t in TARGETS}:
        raise ValueError('IDs do Atlas incompatíveis.')
    parameters = gm_data()
    bodies = []
    branch = uuid.uuid4().hex
    for target, name, label in TARGETS:
        b = by_id[target]
        if b.get('id') != 'sol:naif:' + target:
            raise ValueError('ID de referência do Atlas inválido.')
        pos, vel = vector(b.get('position_m')), vector(b.get('velocity_m_s'))
        coverage = b.get('coverage_et_s', [])
        if not any(isinstance(pair, list) and len(pair) == 2 and pair[0] <= epoch['et_tdb_s'] <= pair[1] for pair in coverage):
            raise ValueError('Época fora da cobertura do corpo: ' + name)
        gm = copy.deepcopy(parameters[label])
        bodies.append({'id': f'exp:{branch}:naif:{target}', 'reference_id': b['id'], 'name': name,
                       'naif_id': target, 'source_GM': gm,
                       'source_position_m': pos, 'source_velocity_m_s': vel,
                       'source_uncertainty': {'position_m': None, 'velocity_m_s': None},
                       'shape_reference': copy.deepcopy(b.get('shape')),
                       'reference_properties': copy.deepcopy(b.get('properties', [])),
                       'mass_kg_reference': {'value': gm['value'] / PHYSICAL_SCALE['G_m3_kg_s2'],
                                             'origin': 'GM/G conversion of a model parameter', 'unit': 'kg',
                                             'uncertainty': None,
                                             'relative_uncertainty_from_G_only': PHYSICAL_SCALE['G_standard_uncertainty'] / PHYSICAL_SCALE['G_m3_kg_s2']}})
    total = math.fsum(b['source_GM']['value'] for b in bodies)
    center = [math.fsum(b['source_GM']['value'] * b['source_position_m'][k] for b in bodies) / total for k in range(3)]
    velocity = [math.fsum(b['source_GM']['value'] * b['source_velocity_m_s'][k] for b in bodies) / total for k in range(3)]
    for b in bodies:
        b['mass'] = b['source_GM']['value'] / PHYSICAL_SCALE['nominal_GM_unit_m3_s2']
        b['position'] = [(p - c) / PHYSICAL_SCALE['length_unit_m'] for p, c in zip(b['source_position_m'], center)]
        b['velocity'] = [(v - c) / PHYSICAL_SCALE['velocity_unit_m_s'] for v, c in zip(b['source_velocity_m_s'], velocity)]
    transform = render_transform(atlas.get('j2000_to_render_frame'), atlas.get('render_frame'))
    contract = {'schema': 1, 'frame': FRAME, 'units': {'system': 'canonical', 'G': 1.0},
                'model': 'newtonian_point_masses', 'collisions': 'disabled', 'integrator': 'IAS15', 'epsilon': 1e-9,
                'epoch': copy.deepcopy(epoch), 'time': 'elapsed model time; epoch_et_tdb_s + t*time_unit_s is a coordinate-time association, not a new JPL ephemeris',
                'excluded_influences': list(EXCLUDED)}
    source = {k: copy.deepcopy(atlas[k]) for k in ('model', 'epoch', 'frame', 'center_naif_id', 'aberration', 'provenance', 'application_coverage_utc')}
    for key in ('observer', 'packages_manifest_sha256'):
        if key in atlas:
            source[key] = copy.deepcopy(atlas[key])
    result = {'schema': 1, 'kind': 'atlas_sun_earth_moon', 'branch_id': branch,
              'contract': contract, 'physical_scale': PHYSICAL_SCALE, 'source': source,
              'initial_ssb_origin_m': center, 'inertial_origin_velocity_m_s': velocity,
              'render_frame': 'GALACTIC', 'j2000_to_render_frame': transform,
              'generation': generation(), 'bodies': bodies}
    result['initial_state_sha256'] = digest(result)
    validate(result)
    return result


def validate(prepared):
    if not isinstance(prepared, dict) or prepared.get('kind') != 'atlas_sun_earth_moon' or prepared.get('schema') != 1:
        raise ValueError('Estado inicial do Atlas inválido.')
    body = {k: v for k, v in prepared.items() if k != 'initial_state_sha256'}
    if digest(body) != prepared.get('initial_state_sha256'):
        raise ValueError('Integridade do estado inicial do Atlas inválida.')
    if not isinstance(prepared.get('contract'), dict) or prepared.get('physical_scale') != PHYSICAL_SCALE or prepared['contract'].get('frame') != FRAME:
        raise ValueError('Escala/referencial do experimento incompatível.')
    render_transform(prepared.get('j2000_to_render_frame'), prepared.get('render_frame'))
    contract = prepared['contract']
    expected = {'schema': 1, 'units': {'system': 'canonical', 'G': 1.0},
                'model': 'newtonian_point_masses', 'collisions': 'disabled',
                'integrator': 'IAS15', 'epsilon': 1e-9, 'excluded_influences': EXCLUDED}
    if any(contract.get(k) != v for k, v in expected.items()):
        raise ValueError('Operadores/solver do experimento incompatíveis.')
    source = prepared.get('source', {})
    if not isinstance(source, dict) or source.get('frame') != 'J2000/ICRF' or source.get('center_naif_id') != '0' or source.get('aberration') != 'NONE' or source.get('epoch') != contract.get('epoch'):
        raise ValueError('Época/referencial da origem do experimento incompatíveis.')
    observer = source.get('observer')
    if observer is not None and (not isinstance(observer, dict) or observer.get('kind') != 'geometric_simultaneous_coordinate_state' or
                                observer.get('coordinate_origin_naif_id') != '0' or observer.get('aberration') != 'NONE' or
                                observer.get('light_time_applied') is not False or observer.get('emission_et_tdb_s') is not None or
                                observer.get('reception_et_tdb_s') is not None or observer.get('state_epoch_et_tdb_s') != source['epoch']['et_tdb_s']):
        raise ValueError('A cópia exige estado geométrico simultâneo, sem observador aparente.')
    branch = prepared.get('branch_id')
    if not isinstance(branch, str) or len(branch) != 32 or any(c not in '0123456789abcdef' for c in branch):
        raise ValueError('ID da ramificação inválido.')
    bodies = prepared.get('bodies', [])
    if not isinstance(bodies, list) or len(bodies) != 3 or any(not isinstance(b, dict) for b in bodies):
        raise ValueError('Subconjunto do experimento incompleto.')
    for b, (target, _, label) in zip(bodies, TARGETS):
        if b.get('id') != f'exp:{branch}:naif:{target}' or b.get('reference_id') != 'sol:naif:' + target:
            raise ValueError('IDs de corpos do experimento inválidos.')
        gm = b.get('source_GM')
        if gm != gm_data()[label] or b.get('mass') != gm['value'] / PHYSICAL_SCALE['nominal_GM_unit_m3_s2']:
            raise ValueError('GM/massa incompatível com a fonte publicada.')
        for key in ('position', 'velocity', 'source_position_m', 'source_velocity_m_s'):
            vector(b.get(key))
        properties = b.get('reference_properties', [])
        if properties:
            if not isinstance(properties, list) or len(properties) != 7 or any(not isinstance(p, dict) for p in properties) or {p.get('id') for p in properties} != {'position', 'velocity', 'GM', 'mass', 'shape', 'orientation', 'texture'}:
                raise ValueError('Propriedades de referência incompletas ou duplicadas.')
            by_id = {p['id']: p for p in properties}
            for key, value, unit in [('position', b['source_position_m'], 'm'), ('velocity', b['source_velocity_m_s'], 'm/s'),
                                     ('GM', gm['value'], 'm³/s²'), ('mass', gm['value']/PHYSICAL_SCALE['G_m3_kg_s2'], 'kg')]:
                if by_id[key].get('value') != value or by_id[key].get('unit') != unit or by_id[key].get('uncertainty', {}).get('value') is not None:
                    raise ValueError('Propriedade não corresponde ao estado de origem.')
            if any(by_id[key].get('epoch') != source['epoch'] or by_id[key].get('frame') != 'SSB / J2000-ICRF' for key in ('position', 'velocity')):
                raise ValueError('Época/referencial da propriedade incompatível.')
        for key, scale, origin, original, tolerance in [
            ('position', PHYSICAL_SCALE['length_unit_m'], 'initial_ssb_origin_m', 'source_position_m', .001),
            ('velocity', PHYSICAL_SCALE['velocity_unit_m_s'], 'inertial_origin_velocity_m_s', 'source_velocity_m_s', 1e-8),
        ]:
            offset = vector(prepared.get(origin))
            if max(abs(v * scale + c - x) for v, c, x in zip(b[key], offset, b[original])) > tolerance:
                raise ValueError('Transformação inversa do Atlas inconsistente.')
    for i, b in enumerate(bodies):
        for other in bodies[i + 1:]:
            if math.dist(b['position'], other['position']) <= 1e-6:
                raise ValueError('Corpos coincidentes na condição inicial.')
    total = math.fsum(b['mass'] for b in bodies)
    for key in ('position', 'velocity'):
        if max(abs(math.fsum(b['mass'] * b[key][k] for b in bodies) / total) for k in range(3)) > 1e-12:
            raise ValueError('Baricentro inicial do subconjunto inconsistente.')
    return copy.deepcopy(prepared)
