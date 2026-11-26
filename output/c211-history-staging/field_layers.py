"""Bounded, persisted gravity maps sampled from one confirmed physical state."""
import copy
import math
import time

from physics import PHYSICAL_SCALE
from gravity_instruments import vector
from field_geometry import shell, arrows
from field_sections import plane, equipotentials

MAX_EVENTS = 4096


def defaults():
    return {'center_mode': 'fixed', 'center_m': [0., 0., 0.], 'body_id': None,
            'shell_enabled': True, 'shell_radius_m': 2e10, 'shell_count': 96,
            'cut_enabled': True, 'cut_half_width_m': 3e10, 'cut_resolution': 17,
            'cut_orientation_deg': [0., 0., 0.], 'cut_offset_m': 0.,
            'magnitude_scale': 'log', 'potential_levels_J_kg': []}


def empty():
    return {'schema': 1, 'revision': 0, 'settings': defaults(), 'events': []}


def settings(value, known_body_ids):
    if not isinstance(value, dict) or set(value) != set(defaults()):
        raise ValueError('Configuração do mapa de campo incompatível.')
    vector(value['center_m'])
    if value['center_mode'] not in ('fixed', 'follow'):
        raise ValueError('Centro do mapa deve ser fixo ou seguir um corpo.')
    if value['center_mode'] == 'follow':
        if not isinstance(value['body_id'], str) or value['body_id'] not in known_body_ids:
            raise ValueError('Corpo central não pertence ao histórico deste sistema.')
    elif value['body_id'] is not None:
        raise ValueError('Centro fixo não recebe identidade de corpo.')
    if any(type(value[k]) is not bool for k in ('shell_enabled', 'cut_enabled')):
        raise ValueError('Escolha explicitamente as camadas de campo.')
    if not value['shell_enabled'] and not value['cut_enabled']:
        raise ValueError('Ative a casca 3D ou o corte.')
    for key in ('shell_radius_m', 'cut_half_width_m'):
        if type(value[key]) not in (int, float) or not math.isfinite(value[key]) or not .001 <= value[key] <= 1e17:
            raise ValueError('Extensão do campo fora do domínio SI do editor.')
    if type(value['shell_count']) is not int or value['shell_count'] not in (48, 96, 128):
        raise ValueError('A casca usa 48, 96 ou 128 pontos.')
    if type(value['cut_resolution']) is not int or value['cut_resolution'] not in (17, 21):
        raise ValueError('O corte usa resolução 17 ou 21.')
    angle = value['cut_orientation_deg']
    if not isinstance(angle, list) or len(angle) != 3 or any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 360 for v in angle):
        raise ValueError('Orientação: três ângulos finitos entre −360 e 360 graus.')
    offset = value['cut_offset_m']
    if type(offset) not in (int, float) or not math.isfinite(offset) or abs(offset) > 1e17:
        raise ValueError('Deslocamento do corte fora do domínio SI.')
    if value['magnitude_scale'] not in ('linear', 'log'):
        raise ValueError('Magnitude usa escala linear ou logarítmica.')
    levels = value['potential_levels_J_kg']
    if not isinstance(levels, list) or len(levels) > 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in levels) or len(set(levels)) != len(levels):
        raise ValueError('Use até quatro potenciais SI distintos, ou deixe a escolha automática.')
    return copy.deepcopy(value)


def validate(value, known_body_ids, physical_time):
    if not isinstance(value, dict) or set(value) != {'schema', 'revision', 'settings', 'events'} or type(value['schema']) is not int or value['schema'] != 1:
        raise ValueError('Formato do mapa de campo inválido.')
    revision = value['revision']
    if type(revision) is not int or not 0 <= revision <= MAX_EVENTS or not isinstance(value['events'], list) or len(value['events']) != revision:
        raise ValueError('Histórico do mapa de campo inválido.')
    checked = settings(value['settings'], known_body_ids)
    previous_time = 0.
    last = defaults()
    for index, event in enumerate(value['events'], 1):
        if not isinstance(event, dict) or set(event) != {'revision', 'time', 'settings'} or type(event['revision']) is not int or event['revision'] != index:
            raise ValueError('Sequência do mapa de campo inválida.')
        stamp = event['time']
        if type(stamp) not in (int, float) or not math.isfinite(stamp) or not previous_time <= stamp <= physical_time:
            raise ValueError('Instante do histórico do campo inválido.')
        last = settings(event['settings'], known_body_ids)
        previous_time = stamp
    if checked != last:
        raise ValueError('Configuração do campo não corresponde ao histórico.')
    return copy.deepcopy(value)


def restore(manifest, known_body_ids, physical_time):
    if 'field_layers' in manifest:
        return validate(manifest['field_layers'], known_body_ids, physical_time)
    if manifest['saved_generation']['model_version'] in ('3.6.0','3.7.0'):
        raise ValueError('Definições do mapa ausentes no checkpoint 3.6.')
    return empty()


def public(configuration):
    return {k: copy.deepcopy(configuration[k]) for k in ('schema', 'revision', 'settings')}


def configure(current, request, active_body_ids, physical_time):
    if current['revision'] >= MAX_EVENTS:
        raise ValueError('Limite do histórico de mapas atingido.')
    proposed = settings(request.get('settings'), active_body_ids)
    revision = current['revision'] + 1
    result = copy.deepcopy(current)
    result.update(revision=revision, settings=proposed)
    result['events'].append({'revision': revision, 'time': physical_time, 'settings': copy.deepcopy(proposed)})
    return result


def axes(angles_deg):
    """Rz(yaw) Ry(pitch) Rx(roll), columns u/v/normal in inertial axes."""
    x, y, z = [math.radians(v) for v in angles_deg]
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    return [[cz * cy, sz * cy, -sy],
            [cz * sy * sx - sz * cx, sz * sy * sx + cz * cx, cy * sx],
            [cz * sy * cx + sz * sx, sz * sy * cx - cz * sx, cy * cx]]


def center(settings_value, bodies):
    point = list(settings_value['center_m'])
    if settings_value['center_mode'] == 'follow':
        body = next((b for b in bodies if b['id'] == settings_value['body_id']), None)
        if body is None:
            raise ValueError('Corpo central removido; identidade original do mapa preservada.')
        point = [point[k] + body['position'][k] * PHYSICAL_SCALE['length_unit_m'] for k in range(3)]
    return vector(point)


def _compact(samples):
    for sample in samples:
        if sample['valid']:
            sources = sample.pop('sources')
            sample['nearest_source_distance_m'] = min((s['distance_m'] for s in sources), default=None)
    return samples


def sample(configuration, physical_state, evaluator):
    started = time.perf_counter()
    cfg, bodies = configuration['settings'], physical_state['bodies']
    origin = center(cfg, bodies)
    stamp = {key: copy.deepcopy(physical_state[key]) for key in ('system_id', 'edit_token', 'revision', 'time', 'scientific_generation')}
    stamp.update(frame=physical_state['contract']['frame'], fields_revision=configuration['revision'])
    result = {**stamp, 'settings': copy.deepcopy(cfg), 'center_m': origin, 'shell': None, 'cut': None,
              'source_ids': [b['id'] for b in bodies],
              'source_snapshot_si': [{'id': b['id'], 'GM_m3_s2': b['mass'] * PHYSICAL_SCALE['nominal_GM_unit_m3_s2'],
                                      'position_m': [v * PHYSICAL_SCALE['length_unit_m'] for v in b['position']]} for b in bodies],
              'policy': 'frozen read-only map; all active sources included; no integrator reset or backreaction'}
    if cfg['shell_enabled']:
        points = shell(origin, cfg['shell_radius_m'], cfg['shell_count'])
        readings = _compact(evaluator(bodies, points))
        result['shell'] = {'samples': readings, 'geometry': arrows(readings, .16 * cfg['shell_radius_m'])}
    if cfg['cut_enabled']:
        u, v, normal = axes(cfg['cut_orientation_deg'])
        cut_center = [origin[k] + normal[k] * cfg['cut_offset_m'] for k in range(3)]
        grid = plane(cut_center, cfg['cut_half_width_m'], u, v, cfg['cut_resolution'])
        readings = _compact(evaluator(bodies, grid['points_m']))
        levels = list(cfg['potential_levels_J_kg'])
        if not levels:
            potentials = sorted(s['potential_J_kg'] for s in readings if s['valid'])
            if potentials:
                levels = sorted(set(potentials[round((len(potentials) - 1) * q)] for q in (.2, .5, .8)))
        contours = equipotentials(grid, readings, levels) if levels else {'contours': [], 'invalid_cells': list(range((grid['resolution'] - 1) ** 2)), 'plateau_cells': [], 'interpolation': 'no valid potential samples'}
        # The full physical grid remains available; directions are visibly decimated.
        stride = 2 if grid['resolution'] == 17 else 3
        sites = [s for s in readings if s['index'] % grid['resolution'] % stride == 0 and s['index'] // grid['resolution'] % stride == 0]
        corners = [[cut_center[k] + cfg['cut_half_width_m'] * (a * u[k] + b * v[k]) for k in range(3)] for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1))]
        result['cut'] = {'grid': {k: value for k, value in grid.items() if k != 'points_m'},
                         'samples': readings, 'normal': normal, 'outline_m': corners,
                         'geometry': arrows(sites, .07 * cfg['cut_half_width_m']),
                         'arrow_grid_stride': stride, 'equipotentials': contours,
                         'level_policy': 'explicit SI levels' if cfg['potential_levels_J_kg'] else 'sample quantiles 20/50/80 percent; actual levels listed'}
    magnitudes = [s['acceleration_norm_m_s2'] for layer in (result['shell'], result['cut']) if layer for s in layer['samples'] if s['valid']]
    positive = [v for v in magnitudes if v > 0]
    result['magnitude_legend'] = {'scale': cfg['magnitude_scale'], 'unit': 'm/s^2', 'minimum': min(magnitudes, default=None),
                                 'maximum': max(magnitudes, default=None), 'minimum_positive': min(positive, default=None),
                                 'zero_policy': 'zero direction undefined; zero excluded from logarithm',
                                 'arrows': 'uniform graphic length shows direction; color shows |g|'}
    result['sample_count'] = len(magnitudes) + sum(not s['valid'] for layer in (result['shell'], result['cut']) if layer for s in layer['samples'])
    result['evaluation_ms'] = (time.perf_counter() - started) * 1000
    return result
