"""Uninstalled C2-11 probe definitions and read-only field snapshots.

Configuration has its own revision and tombstones. Follow offsets are in the
simulation's inertial axes; there is no quaternion rotation or backreaction.
"""
import copy
import math
import re
import uuid

from physics import PHYSICAL_SCALE

MAX_PROBES = 16
MAX_ISSUED = 1024
MAX_EVENTS = 4096
ID = re.compile(r'probe:[0-9a-f]{32}')


def empty():
    return {'schema': 1, 'revision': 0, 'probes': [], 'issued_ids': [], 'events': []}


def public(configuration):
    return {'schema': 1, 'revision': configuration['revision'],
            'probes': copy.deepcopy(configuration['probes']), 'maximum_probes': MAX_PROBES}


def restore(manifest, known_body_ids):
    if 'instruments' in manifest:
        return validate(manifest['instruments'], known_body_ids)
    if manifest.get('saved_generation', {}).get('model_version') == '3.5.0':
        raise ValueError('Definições dos instrumentos ausentes no checkpoint3.5.')
    return empty()


def vector(value):
    if (not isinstance(value, list) or len(value) != 3
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in value)
            or math.hypot(*value) > 1e17):
        raise ValueError('Posição/deslocamento: use três coordenadas SI finitas no domínio do editor.')
    return list(value)


def definition(value, known_body_ids):
    if not isinstance(value, dict):
        raise ValueError('Definição de sonda inválida.')
    mode = value.get('mode')
    keys = {'id', 'name', 'mode'}
    if mode == 'fixed':
        keys |= {'position_m'}
    elif mode == 'follow':
        keys |= {'body_id', 'offset_m', 'exclude_followed_source'}
    else:
        raise ValueError('Sonda deve ser fixa ou seguir um corpo em eixos inerciais.')
    if set(value) != keys or not isinstance(value.get('id'), str) or not ID.fullmatch(value['id']):
        raise ValueError('Campos ou identidade da sonda inválidos.')
    label = value.get('name')
    if (not isinstance(label, str) or not 1 <= len(label) <= 80 or label != label.strip()
            or any(ord(c) < 32 or ord(c) == 127 for c in label)):
        raise ValueError('Nome da sonda deve ter 1–80 caracteres sem controles.')
    if mode == 'fixed':
        vector(value['position_m'])
    else:
        body = value['body_id']
        if not isinstance(body, str) or body not in known_body_ids:
            raise ValueError('Fonte seguida não pertence ao histórico deste sistema.')
        vector(value['offset_m'])
        if type(value['exclude_followed_source']) is not bool:
            raise ValueError('A exclusão da própria fonte deve ser explícita.')
    return copy.deepcopy(value)


def validate(value, known_body_ids):
    if (not isinstance(value, dict) or set(value) != {'schema', 'revision', 'probes', 'issued_ids', 'events'}
            or type(value.get('schema')) is not int or value['schema'] != 1):
        raise ValueError('Formato dos instrumentos incompatível.')
    rows, issued, revision = value['probes'], value['issued_ids'], value['revision']
    if (not isinstance(rows, list) or len(rows) > MAX_PROBES
            or not isinstance(issued, list) or len(issued) > MAX_ISSUED
            or any(not isinstance(v, str) or not ID.fullmatch(v) for v in issued)
            or len(issued) != len(set(issued))
            or type(revision) is not int or not 0 <= revision <= MAX_EVENTS
            or revision < 2 * len(issued) - len(rows)):
        raise ValueError('Revisão, população ou histórico dos instrumentos inválido.')
    checked = [definition(row, known_body_ids) for row in rows]
    ids = [row['id'] for row in checked]
    if len(ids) != len(set(ids)) or any(v not in issued for v in ids):
        raise ValueError('Sonda duplicada ou identidade não emitida.')
    events = value['events']
    if not isinstance(events, list) or len(events) != revision:
        raise ValueError('Histórico de configuração inválido.')
    active, emitted = [], []
    for index, event in enumerate(events, 1):
        if not isinstance(event, dict) or type(event.get('revision')) is not int or event['revision'] != index:
            raise ValueError('Sequência do histórico dos instrumentos inválida.')
        operation = event.get('operation')
        if operation in ('create', 'update'):
            if set(event) != {'revision', 'operation', 'definition'}:
                raise ValueError('Evento de configuração inválido.')
            row = definition(event['definition'], known_body_ids)
            current_ids = [r['id'] for r in active]
            if operation == 'create':
                if row['id'] in emitted or len(active) >= MAX_PROBES:
                    raise ValueError('Identidade reutilizada ou população histórica inválida.')
                active.append(row)
                emitted.append(row['id'])
            else:
                if row['id'] not in current_ids:
                    raise ValueError('Alteração histórica de sonda inativa.')
                active[current_ids.index(row['id'])] = row
        elif operation == 'remove':
            if set(event) != {'revision', 'operation', 'id'} or event['id'] not in [r['id'] for r in active]:
                raise ValueError('Remoção histórica de sonda inativa.')
            active = [r for r in active if r['id'] != event['id']]
        else:
            raise ValueError('Operação histórica de instrumentos inválida.')
    if active != checked or emitted != issued:
        raise ValueError('Definições não correspondem ao histórico dos instrumentos.')
    return copy.deepcopy(value)


def configure(current, request, active_body_ids, known_body_ids):
    result = validate(current, known_body_ids)
    if not isinstance(request, dict):
        raise ValueError('Comando de instrumentos inválido.')
    revision = request.get('instruments_revision')
    if type(revision) is not int or revision != result['revision']:
        raise ValueError('Os instrumentos mudaram; carregue novamente o formulário.')
    if revision >= MAX_EVENTS:
        raise ValueError('Limite de alterações dos instrumentos atingido neste sistema.')
    operation = request.get('operation')
    if operation in ('create', 'update'):
        if not isinstance(request.get('definition'), dict):
            raise ValueError('Definição de sonda ausente.')
        proposed = copy.deepcopy(request['definition'])
        if operation == 'create':
            if 'id' in proposed or len(result['probes']) >= MAX_PROBES or len(result['issued_ids']) >= MAX_ISSUED:
                raise ValueError('Limite de sondas/histórico atingido ou ID informado na criação.')
            identifier = 'probe:' + uuid.uuid4().hex
            while identifier in result['issued_ids']:
                identifier = 'probe:' + uuid.uuid4().hex
            proposed['id'] = identifier
        proposed = definition(proposed, known_body_ids)
        if proposed['mode'] == 'follow' and proposed['body_id'] not in active_body_ids:
            raise ValueError('Selecione um corpo ativo para seguir.')
        if operation == 'create':
            result['probes'].append(proposed)
            result['issued_ids'].append(proposed['id'])
        else:
            ids = [row['id'] for row in result['probes']]
            if proposed['id'] not in ids:
                raise ValueError('Sonda removida ou desconhecida.')
            result['probes'][ids.index(proposed['id'])] = proposed
    elif operation == 'remove':
        identifier = request.get('id')
        if not isinstance(identifier, str) or identifier not in [row['id'] for row in result['probes']]:
            raise ValueError('Sonda removida ou desconhecida.')
        result['probes'] = [row for row in result['probes'] if row['id'] != identifier]
    else:
        raise ValueError('Operação de instrumentos desconhecida.')
    result['revision'] += 1
    event = {'revision': result['revision'], 'operation': operation}
    if operation == 'remove':
        event['id'] = identifier
    else:
        event['definition'] = copy.deepcopy(proposed)
    result['events'].append(event)
    return validate(result, known_body_ids)


def resolve(row, bodies):
    if row['mode'] == 'fixed':
        return list(row['position_m'])
    source = next((body for body in bodies if body['id'] == row['body_id']), None)
    if source is None:
        raise ValueError('Corpo seguido removido; identidade original preservada.')
    length = PHYSICAL_SCALE['length_unit_m']
    return vector([source['position'][k] * length + row['offset_m'][k] for k in range(3)])


def sample(configuration, physical_state, evaluator):
    """All readings use one already-confirmed physical snapshot and evaluator."""
    bodies = physical_state['bodies']
    stamp = {key: copy.deepcopy(physical_state[key]) for key in
             ('system_id', 'edit_token', 'revision', 'time', 'scientific_generation')}
    stamp['frame'] = physical_state['contract']['frame']
    stamp['instruments_revision'] = configuration['revision']
    readings = []
    for row in configuration['probes']:
        reading = {'id': row['id'], 'definition': copy.deepcopy(row), 'available': False}
        try:
            point = resolve(row, bodies)
            excluded = row['body_id'] if row['mode'] == 'follow' and row['exclude_followed_source'] else None
            sources = [body for body in bodies if body['id'] != excluded]
            evaluated = dict(evaluator(sources, point))
            contributions = evaluated.pop('sources')
            reading.update(evaluated, available=True, source_count=len(contributions),
                           nearest_included_source_distance_m=min((s['distance_m'] for s in contributions), default=None),
                           excluded_source_ids=[] if excluded is None else [excluded])
        except ValueError as error:
            reading['reason'] = str(error)
        readings.append(reading)
    length = PHYSICAL_SCALE['length_unit_m']
    gm = PHYSICAL_SCALE['nominal_GM_unit_m3_s2']
    source_snapshot = [{'id': b['id'], 'GM_m3_s2': b['mass'] * gm,
                        'position_m': [v * length for v in b['position']]} for b in bodies]
    return {**stamp, 'readings': readings, 'source_ids': [body['id'] for body in bodies],
            'source_snapshot_si': source_snapshot,
            'offset_axes': 'simulation inertial axes; no body co-rotation',
            'policy': 'read-only probes; no mass, force feedback or integrator reset'}
