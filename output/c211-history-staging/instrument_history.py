"""Bounded confirmed measurements, collected independently of integrator steps."""
import copy
import math

import gravity_instruments
import gravity_field
import orbital_diagnostics
from physics import PHYSICAL_SCALE as U

MAX_SAMPLES = 128


def empty():
    return {'schema': 1, 'revision': 0, 'recording': False, 'cadence_wall_s': 1.,
            'samples': [], 'dropped': 0, 'next_sequence': 0}


def public(value):
    return {k: copy.deepcopy(value[k]) for k in ('schema', 'revision', 'recording', 'cadence_wall_s', 'dropped', 'next_sequence')} | {
        'sample_count': len(value['samples']), 'maximum_samples': MAX_SAMPLES,
        'first_time': value['samples'][0]['reading']['time'] if value['samples'] else None,
        'last_time': value['samples'][-1]['reading']['time'] if value['samples'] else None,
        'cadence_policy': 'wall cadence at confirmed worker snapshots; actual physical timestamps retained; no integrator substep or interpolation'}


def configure(value, request):
    recording, cadence = request.get('recording'), request.get('cadence_wall_s')
    if type(recording) is not bool or type(cadence) not in (int, float) or not math.isfinite(cadence) or not .25 <= cadence <= 5.:
        raise ValueError('Gravação explícita e cadência entre0,25e5segundos reais.')
    if value['revision'] >= 4096:
        raise ValueError('Limite de configurações do histórico atingido.')
    result = copy.deepcopy(value)
    result.update(revision=value['revision'] + 1, recording=recording, cadence_wall_s=cadence)
    return result


def clear(value):
    if value['revision'] >= 4096:
        raise ValueError('Limite de configurações do histórico atingido.')
    return {**empty(), 'revision': value['revision'] + 1, 'recording': value['recording'], 'cadence_wall_s': value['cadence_wall_s']}


def append(value, instruments, physical_state, wall_elapsed_s):
    reading = gravity_instruments.sample(instruments, physical_state, gravity_field.evaluate)
    for source, body in zip(reading['source_snapshot_si'], physical_state['bodies']):
        source['velocity_m_s'] = [v * U['velocity_unit_m_s'] for v in body['velocity']]
    prior = value['samples'][-1] if value['samples'] else None
    # Split traces at interventions/config changes, restoration, and missed wall
    # cadence. Samples are never silently connected across a singular reading.
    breaks = []
    if prior:
        last = prior['reading']
        if any(last[k] != reading[k] for k in ('system_id', 'edit_token', 'revision', 'instruments_revision')):
            breaks.append('state_or_instrument_definition_changed')
        if wall_elapsed_s > 1.5 * value['cadence_wall_s']:
            breaks.append('cadence_gap')
        if reading['time'] <= last['time']:
            breaks.append('physical_time_did_not_increase')
    energy_unit = U['mass_unit_kg'] * U['velocity_unit_m_s'] ** 2
    conservation = physical_state['conservation']
    current = conservation['current']
    record = {'sequence': value['next_sequence'], 'reading': reading, 'cadence_wall_s': value['cadence_wall_s'],
              'wall_elapsed_s': wall_elapsed_s, 'break_before': breaks,
              'integrals': {'energy_J': current['energy'] * energy_unit,
                            'momentum_kg_m_s': [v * U['mass_unit_kg'] * U['velocity_unit_m_s'] for v in current['momentum']],
                            'angular_momentum_kg_m2_s': [v * U['mass_unit_kg'] * U['velocity_unit_m_s'] * U['length_unit_m'] for v in current['angular_momentum']],
                            'energy_error': physical_state['energy_error'],
                            'energy_error_absolute_J': physical_state['energy_error_absolute'] * energy_unit,
                            'momentum_error_normalized': conservation['momentum_error_normalized'],
                            'angular_momentum_error_normalized': conservation['angular_momentum_error_normalized']}}
    result = dict(value)
    result['samples'] = value['samples'] + [record]
    result['next_sequence'] += 1
    if len(result['samples']) > MAX_SAMPLES:
        result['samples'] = result['samples'][-MAX_SAMPLES:]
        result['dropped'] += 1
    return result


def curves(value):
    # Plot payload omits global source snapshots/tensors. Selecting a point and
    # exporting the full series retrieves the original confirmed record.
    result = []
    for record in value['samples']:
        r = record['reading']
        result.append({'sequence': record['sequence'], 'time_s': r['time'] * U['time_unit_s'],
                       'revision': r['revision'], 'instruments_revision': r['instruments_revision'],
                       'break_before': record['break_before'], 'integrals': record['integrals'],
                       'probes': [{'id': p['id'], 'name': p['definition']['name'], 'available': p['available'],
                                   **({'acceleration_norm_m_s2': p['acceleration_norm_m_s2'], 'potential_J_kg': p['potential_J_kg'],
                                       'tidal_xx_s_2': p['tidal_tensor_s_2'][0][0]} if p['available'] else {'reason': p['reason']})}
                                  for p in r['readings']]})
    return {**public(value), 'samples': result}


def _finite(value, label, allow_none=False):
    if allow_none and value is None:
        return
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Grandeza inválida no histórico: ' + label)


def _close(a, b, scale):
    return abs(a - b) <= 2e-11 * max(scale, 1e-300)


def validate(value, known_body_ids, physical_time, system_id, current_revision, current_instruments_revision, frame):
    if not isinstance(value, dict) or set(value) != set(empty()) or type(value.get('schema')) is not int or value['schema'] != 1:
        raise ValueError('Formato do histórico incompatível.')
    checked = configure({**value, 'revision': 0}, {'recording': value['recording'], 'cadence_wall_s': value['cadence_wall_s']})
    del checked
    if type(value['revision']) is not int or not 0 <= value['revision'] <= 4096:
        raise ValueError('Revisão do histórico inválida.')
    rows, dropped, following = value['samples'], value['dropped'], value['next_sequence']
    if not isinstance(rows, list) or len(rows) > MAX_SAMPLES or type(dropped) is not int or dropped < 0 or type(following) is not int or following != dropped + len(rows):
        raise ValueError('Janela/contagem do histórico inválida.')
    prior_time = -1.
    for index, record in enumerate(rows, dropped):
        if not isinstance(record, dict) or set(record) != {'sequence', 'reading', 'cadence_wall_s', 'wall_elapsed_s', 'break_before', 'integrals'} or type(record['sequence']) is not int or record['sequence'] != index:
            raise ValueError('Sequência da curva inválida.')
        for key in ('cadence_wall_s', 'wall_elapsed_s'):
            _finite(record[key], key)
        if not .25 <= record['cadence_wall_s'] <= 5 or record['wall_elapsed_s'] < 0:
            raise ValueError('Cadência histórica inválida.')
        if not isinstance(record['break_before'], list) or len(record['break_before']) != len(set(record['break_before'])) or any(v not in ('state_or_instrument_definition_changed', 'cadence_gap', 'physical_time_did_not_increase') for v in record['break_before']):
            raise ValueError('Lacunas históricas inválidas.')
        r = record['reading']
        if not isinstance(r, dict) or r.get('system_id') != system_id or r.get('frame') != frame:
            raise ValueError('Origem do histórico incompatível.')
        _finite(r.get('time'), 'time')
        if not prior_time <= r['time'] <= physical_time:
            raise ValueError('Instante histórico fora da fase salva.')
        prior_time = r['time']
        if type(r.get('revision')) is not int or not 0 <= r['revision'] <= current_revision or type(r.get('instruments_revision')) is not int or not 0 <= r['instruments_revision'] <= current_instruments_revision:
            raise ValueError('Revisão física/instrumental histórica inválida.')
        if not isinstance(r.get('edit_token'), str) or len(r['edit_token']) != 32 or any(c not in '0123456789abcdef' for c in r['edit_token']):
            raise ValueError('Identidade da leitura histórica inválida.')
        sources = r.get('source_snapshot_si')
        if not isinstance(sources, list) or not 1 <= len(sources) <= 128:
            raise ValueError('Fontes históricas inválidas.')
        bodies, source_ids = [], []
        for source in sources:
            if not isinstance(source, dict) or set(source) != {'id', 'GM_m3_s2', 'position_m', 'velocity_m_s'} or source['id'] not in known_body_ids:
                raise ValueError('Fonte histórica desconhecida.')
            _finite(source['GM_m3_s2'], 'GM')
            if not 0 < source['GM_m3_s2'] <= 100 * U['nominal_GM_unit_m3_s2']:
                raise ValueError('GM histórico fora do domínio.')
            gravity_instruments.vector(source['position_m'])
            if not isinstance(source['velocity_m_s'], list) or len(source['velocity_m_s']) != 3:
                raise ValueError('Velocidade histórica inválida.')
            for v in source['velocity_m_s']:
                _finite(v, 'velocity')
            bodies.append({'id': source['id'], 'mass': source['GM_m3_s2'] / U['nominal_GM_unit_m3_s2'],
                           'position': [v / U['length_unit_m'] for v in source['position_m']],
                           'velocity': [v / U['velocity_unit_m_s'] for v in source['velocity_m_s']]})
            source_ids.append(source['id'])
        if len(source_ids) != len(set(source_ids)) or r.get('source_ids') != source_ids:
            raise ValueError('Lista de fontes históricas incoerente.')
        readings = r.get('readings')
        if not isinstance(readings, list) or not 1 <= len(readings) <= 16:
            raise ValueError('Sondas históricas inválidas.')
        ids = []
        for p in readings:
            if not isinstance(p, dict) or type(p.get('available')) is not bool:
                raise ValueError('Amostra histórica inválida.')
            definition = gravity_instruments.definition(p.get('definition'), known_body_ids)
            if p.get('id') != definition['id']:
                raise ValueError('Identidade histórica da sonda incoerente.')
            ids.append(p['id'])
            excluded = [definition['body_id']] if definition['mode'] == 'follow' and definition['exclude_followed_source'] else []
            try:
                point = gravity_instruments.resolve(definition, bodies)
                expected = gravity_field.evaluate([b for b in bodies if b['id'] not in excluded], point)
            except ValueError:
                if p['available'] or not isinstance(p.get('reason'), str) or not p['reason']:
                    raise ValueError('Lacuna histórica perdeu o motivo.')
                continue
            if not p['available'] or p.get('excluded_source_ids') != excluded:
                raise ValueError('Disponibilidade/fontes da leitura histórica incoerentes.')
            gravity_instruments.vector(p.get('position_m'))
            if any(not _close(a, b, max(math.hypot(*point), 1.)) for a, b in zip(p['position_m'], point)):
                raise ValueError('Posição histórica não corresponde à definição.')
            gscale = max(expected['acceleration_norm_m_s2'], sum(math.hypot(*s['acceleration_m_s2']) for s in expected['sources']))
            for key, scale in [('potential_J_kg', abs(expected['potential_J_kg'])), ('acceleration_norm_m_s2', gscale)]:
                _finite(p.get(key), key)
                if not _close(p[key], expected[key], scale):
                    raise ValueError('Campo histórico não corresponde às fontes SI.')
            for key in ('acceleration_m_s2', 'tidal_tensor_s_2'):
                expected_flat = expected[key] if key == 'acceleration_m_s2' else [v for row in expected[key] for v in row]
                stored = p.get(key)
                if key == 'tidal_tensor_s_2':
                    if not isinstance(stored, list) or len(stored) != 3 or any(not isinstance(row, list) or len(row) != 3 for row in stored):
                        raise ValueError('Tensor histórico inválido.')
                    stored = [v for row in stored for v in row]
                if not isinstance(stored, list) or len(stored) != len(expected_flat):
                    raise ValueError('Vetor histórico inválido.')
                scale = gscale if key == 'acceleration_m_s2' else sum(abs(v) for v in expected_flat)
                for a, b in zip(stored, expected_flat):
                    _finite(a, key)
                    if not _close(a, b, scale):
                        raise ValueError('Vetor/tensor histórico não corresponde às fontes SI.')
        if len(ids) != len(set(ids)):
            raise ValueError('Sonda histórica duplicada.')
        integrals = record['integrals']
        if not isinstance(integrals, dict) or set(integrals) != {'energy_J', 'momentum_kg_m_s', 'angular_momentum_kg_m2_s', 'energy_error', 'energy_error_absolute_J', 'momentum_error_normalized', 'angular_momentum_error_normalized'}:
            raise ValueError('Balanços históricos inválidos.')
        for key in ('energy_J', 'energy_error', 'energy_error_absolute_J', 'momentum_error_normalized', 'angular_momentum_error_normalized'):
            _finite(integrals[key], key, key in ('energy_error','momentum_error_normalized','angular_momentum_error_normalized'))
            if key != 'energy_J' and integrals[key] is not None and integrals[key] < 0:
                raise ValueError('Erro histórico deve ser não negativo.')
        for key in ('momentum_kg_m_s', 'angular_momentum_kg_m2_s'):
            if not isinstance(integrals[key], list) or len(integrals[key]) != 3:
                raise ValueError('Momento histórico inválido.')
            for v in integrals[key]:
                _finite(v, key)
        expected_integrals = orbital_diagnostics.integrals(bodies, r['time'])
        eunit = U['mass_unit_kg'] * U['velocity_unit_m_s'] ** 2
        escale = (expected_integrals['kinetic_energy'] + abs(expected_integrals['potential_energy'])) * eunit
        if not _close(integrals['energy_J'], expected_integrals['energy'] * eunit, escale):
            raise ValueError('Energia histórica não corresponde à fase SI.')
        for key, model_key, unit, scale_key in [('momentum_kg_m_s', 'momentum', U['mass_unit_kg'] * U['velocity_unit_m_s'], 'momentum_scale'),
                                                ('angular_momentum_kg_m2_s', 'angular_momentum', U['mass_unit_kg'] * U['velocity_unit_m_s'] * U['length_unit_m'], 'angular_momentum_scale')]:
            for stored, expected in zip(integrals[key], expected_integrals[model_key]):
                if not _close(stored, expected * unit, expected_integrals[scale_key] * unit):
                    raise ValueError('Momento histórico não corresponde à fase SI.')
    return copy.deepcopy(value)
