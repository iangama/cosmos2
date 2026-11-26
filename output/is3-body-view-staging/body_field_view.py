"""Validate a portable frozen magnetic view before an atomic checkpoint commit."""
import copy
import math

from body_field_geometry import build
from physics import PHYSICAL_SCALE


def numeric(value, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError('Parâmetro de exibição fora do domínio adotado.')
    return value


def configuration(value, body_ids):
    if not isinstance(value, dict) or set(value) != {'selected_body_id', 'representation', 'earth', 'jupiter'}:
        raise ValueError('Configuração visual magnética incompatível.')
    if value['selected_body_id'] not in body_ids or value['representation'] not in ('vector', 'lines'):
        raise ValueError('Seleção ou representação magnética incompatível.')
    earth, jupiter = value['earth'], value['jupiter']
    if not isinstance(earth, list) or len(earth) != 3 or not isinstance(jupiter, list) or len(jupiter) != 4:
        raise ValueError('Formulários magnéticos incompletos.')
    for v, limits in zip(earth, [(-90, 90), (-180, 180), (0, 1e6)]):
        numeric(v, *limits)
    for v, limits in zip(jupiter[:3], [(71492000., 20*71492000.), (-90, 90), (0, 360)]):
        numeric(v, *limits)
    if type(jupiter[3]) is not int or jupiter[3] not in (1, 13, 18):
        raise ValueError('Grau joviano visual incompatível.')
    return copy.deepcopy(value)


def compare(value, expected, key=''):
    """Compare a replayed provider, keeping units in the error tolerances."""
    if isinstance(expected, dict):
        if not isinstance(value, dict) or set(value) != set(expected):
            raise ValueError('Estrutura da leitura magnética arquivada divergiu: '+key)
        for k in expected:
            compare(value[k], expected[k], k)
    elif isinstance(expected, list):
        if not isinstance(value, list) or len(value) != len(expected):
            raise ValueError('Componentes da leitura magnética arquivada divergiram: '+key)
        for v, e in zip(value, expected):
            compare(v, e, key)
    elif type(expected) in (int, float):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError('Componente arquivada não finita: '+key)
        if key.endswith('_T') or key == 'field_norm_T':
            tolerance = 2e-18
        elif key.endswith('_m') or key == 'relative_point_J2000_m':
            tolerance = .001
        elif key == 'et_tdb_s':
            tolerance = 1e-6
        else:
            tolerance = 1e-12
        if abs(value-expected) > tolerance:
            raise ValueError('Leitura arquivada divergiu do provedor fixado: '+key)
    elif type(value) is not type(expected) or value != expected:
        raise ValueError('Metadado magnético arquivado divergiu: '+key)


def validate(value, *, system_id, fixture_sha256, bodies, time, revision, initial):
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {'schema', 'system_id', 'fixture_sha256', 'configuration', 'layer'}:
        raise ValueError('Arquivo visual magnético incompatível.')
    if type(value['schema']) is not int or value['schema'] != 1 or value['system_id'] != system_id or value['fixture_sha256'] != fixture_sha256:
        raise ValueError('Origem do arquivo visual magnético incompatível.')
    ids = [b['id'] for b in bodies]
    configuration(value['configuration'], ids)
    layer = value['layer']
    if layer is not None:
        if not isinstance(layer, dict) or set(layer) != {'reading', 'representation', 'visible'}:
            raise ValueError('Camada magnética arquivada incompatível.')
        if type(layer['visible']) is not bool or layer['representation'] not in ('vector', 'lines'):
            raise ValueError('Estado visual magnético incompatível.')
        reading = layer['reading']
        if not isinstance(reading, dict) or reading.get('system_id') != system_id or reading.get('body_id') not in ids:
            raise ValueError('Corpo/sistema da amostra arquivada incompatíveis.')
        if not isinstance(initial, dict) or initial.get('kind') != 'solar_four_physical_centers':
            raise ValueError('Origem solar da amostra arquivada ausente.')
        numeric(reading.get('time'), 0, time)
        if type(reading.get('revision')) is not int or not 0 <= reading['revision'] <= revision:
            raise ValueError('Revisão da amostra arquivada incompatível.')
        if not isinstance(reading.get('edit_token'), str) or len(reading['edit_token']) != 32 or any(c not in '0123456789abcdef' for c in reading['edit_token']):
            raise ValueError('Identidade temporal da amostra arquivada incompatível.')
        body = next(b for b in bodies if b['id'] == reading['body_id'])
        if body.get('reference_id') != reading.get('body_reference_id'):
            raise ValueError('Fonte corporal da amostra arquivada incompatível.')
        geometry = build(reading)
        center_key = 'earth_center_inertial_m' if geometry['model'] == 'IGRF14' else 'jupiter_center_inertial_m'
        snapshot = {k: copy.deepcopy(reading[k]) for k in ['system_id', 'edit_token', 'revision', 'time']}
        snapshot.update(atlas_initial=initial, contract={'frame': reading['frame']}, physical_scale=PHYSICAL_SCALE,
                        bodies=[{'id': body['id'], 'reference_id': body['reference_id'],
                                 'position': [v/PHYSICAL_SCALE['length_unit_m'] for v in reading[center_key]]}])
        c = reading['coordinates']
        if geometry['model'] == 'IGRF14':
            from earth_magnetism import read
            expected = read(snapshot, body['id'], c['latitude_deg'], c['longitude_deg'], c['altitude_m'])
        else:
            from jupiter_magnetism import read
            expected = read(snapshot, body['id'], c['radius_m'], c['latitude_planetocentric_deg'], c['longitude_east_deg'], reading['degree'])
        # Keep the complete original generation as provenance; renderer changes
        # alone must not relabel the historical provider as a new field query.
        generation = reading.get('scientific_generation')
        if not isinstance(generation, dict) or generation.get('candidate_extension', {}).get('id') != 'is3-body-fields':
            raise ValueError('Geração original da leitura magnética ausente.')
        compare({k: v for k, v in reading.items() if k != 'scientific_generation'}, expected)
    return copy.deepcopy(value)


def capture(state, selected_configuration, preview):
    value = {'schema': 1, 'system_id': state['system_id'], 'fixture_sha256': state['fixture_sha256'],
             'configuration': selected_configuration,
             'layer': None if preview is None else {
                 'reading': preview['reading'], 'representation': preview['representation'],
                 'visible': preview.get('visible', True)}}
    return validate(value, system_id=state['system_id'], fixture_sha256=state['fixture_sha256'],
                    bodies=state['bodies'], time=state['time'], revision=state['revision'], initial=state.get('atlas_initial'))
