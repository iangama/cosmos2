"""Pure scenario/identity/raw-PDH admission for the expanded native residency experiment."""
import copy
import datetime as dt
import hashlib
import json
import math

import gpu_pdh_audit_dynamics16_base as raw_gpu
import expanded_residency_history_audit_v2 as history_audit

LIMITS = dict(median_ms=16.7, p95_ms=25., p99_ms=50., over_100ms=0,
              RAM_bytes=8 * 2**30, GPU_bytes=5.5 * 2**30)
WINDOWS = [
    dict(name='atlas_earth', mode='atlas', instrument=None, body='399'),
    dict(name='sixteen_system', mode='experiment', instrument=None, bodies=16),
    dict(name='earth_mesh', mode='experiment', instrument='spatial', bodies=4, body='399'),
    dict(name='earth_pair', mode='experiment', instrument='layers', bodies=4, body='399'),
    dict(name='earth_proton', mode='experiment', instrument='particles', bodies=4, body='399'),
    dict(name='jupiter_mesh', mode='experiment', instrument='spatial', bodies=4, body='599'),
    dict(name='jupiter_pair', mode='experiment', instrument='layers', bodies=4, body='599'),
    dict(name='jupiter_electron', mode='experiment', instrument='particles', bodies=4, body='599'),
    dict(name='solar_zone', mode='experiment', instrument='solar-zone', bodies=4),
    dict(name='sixteen_titan_restored', mode='experiment', instrument=None, bodies=16, body='606'),
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False).encode('utf8')


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def physical(phase):
    if phase is None:
        return None
    keys = ['system_id', 'edit_token', 'revision', 'time', 'paused', 'contract', 'physical_scale']
    result = {key: copy.deepcopy(phase[key]) for key in keys}
    result['bodies'] = [{key: copy.deepcopy(body[key]) for key in [
        'id', 'reference_id', 'mass', 'applied_GM_m3_s2', 'position', 'velocity'] if key in body}
        for body in phase['bodies']]
    result['atlas_initial_sha256'] = digest(phase['atlas_initial'])
    result['interventions_sha256'] = digest(phase['interventions'])
    result['dynamics16'] = copy.deepcopy(phase['dynamics16'])
    return result


def scenario(state, modules, navigation=None):
    require(state['mode'] in ['atlas', 'experiment'], 'Unknown laboratory mode')
    result = dict(mode=state['mode'], renderer_confirmed=state.get('engine_connected') is True,
                  physics=physical(state.get('physics')), modules={})
    if result['mode'] == 'atlas':
        require(navigation is not None, 'Atlas navigation witness required')
        result['atlas_epoch_et_tdb_s'] = navigation['et']
        result['atlas_anchor'] = navigation['navigation']['Anchor']
        result['renderer_confirmed'] = bool(result['atlas_anchor'] and len(navigation['camera']['position_render_m']) == 3)
    for name in ['spatial', 'layers', 'particles', 'solar-zone']:
        source = modules[name]
        value = dict(active=source['active'], busy=bool(source.get('busy')), error=source.get('error'),
                     recovery_required=bool(source.get('recovery_required')))
        if name in ['spatial', 'layers']:
            value.update(guard=copy.deepcopy(source['guard']), artifact=copy.deepcopy(source.get('artifact')), scene=copy.deepcopy(source.get('scene')))
        elif name == 'particles' and source['active']:
            worker, view = source['worker'], source['view']
            value.update(worker_id=worker['worker_id'], paused=worker['paused'], experiment=copy.deepcopy(worker['experiment']),
                         view={key: copy.deepcopy(view[key]) for key in ['physical_unit_m', 'visible', 'native_nodes', 'confirmed_phase']})
            value['experiment'].pop('native_confirmation', None)
        elif name == 'solar-zone':
            worker = source.get('worker')
            value.update(playing=bool(source.get('playing')), scene=copy.deepcopy(source.get('scene')),
                         worker=None if worker is None else {key: copy.deepcopy(worker[key]) for key in [
                             'worker_id', 'artifact_id', 'artifact_sha256', 'edit_token', 'revision', 'source', 'configuration', 'sample', 'view']})
        result['modules'][name] = value
    encoded(result)
    return result


def admit_scenario(value, recipe, expected=None):
    require(value['renderer_confirmed'] is True and value['mode'] == recipe['mode'], 'Renderer/mode differs from window')
    active = {name for name, module in value['modules'].items() if module['active']}
    require(active == ({recipe['instrument']} if recipe['instrument'] else set()), 'Instrument scene owner differs')
    require(all(not module['busy'] and not module['recovery_required'] and not module['error'] for module in value['modules'].values()),
            'Instrument busy, faulted or recovering in a stable window')
    phase = value['physics']
    if recipe['mode'] == 'atlas':
        require(phase is None, 'Orbital phase is exposed as the live Atlas')
    else:
        require(phase is not None and phase['paused'] is True and len(phase['bodies']) == recipe['bodies'], 'Paused population differs')
        if recipe['bodies'] == 16:
            metadata = phase['dynamics16']
            require(metadata is not None and metadata['electromagnetic_coupling'] is False and metadata['nuclear_coupling'] is False, 'Sixteen-body scientific domain differs')
        else:
            require(phase['dynamics16'] is None, 'Four-center phase mislabeled as sixteen')
    if recipe['instrument'] in ['layers', 'spatial']:
        require(value['modules'][recipe['instrument']]['artifact']['source']['reference_id' if recipe['instrument'] == 'spatial' else 'body_reference_id'] == 'sol:naif:' + recipe['body'], 'Frozen layer source differs')
    elif recipe['instrument'] == 'particles':
        particle = value['modules']['particles']
        require(particle['paused'] is True and particle['experiment']['step_index'] == 256, 'Particle microphase differs')
        require(particle['experiment']['phase'] == particle['view']['confirmed_phase'], 'Particle native phase is not current')
        body = next(body for body in phase['bodies'] if body['reference_id'] == 'sol:naif:' + recipe['body'])
        require(particle['experiment']['source_body_id'] == body['id'], 'Particle archived body differs')
    elif recipe['instrument'] == 'solar-zone':
        solar = value['modules']['solar-zone']
        require(not solar['playing'] and solar['worker']['view']['selected_index'] == 120, 'Nuclear playback/sample differs')
        require(solar['worker']['configuration']['acting'] == dict(strong=True, weak=True, electromagnetic=True), 'Nuclear force configuration differs')
        require(len(solar['worker']['configuration']['channel_switches']) == 18, 'Nuclear channel population differs')
    if expected is not None:
        require(value == expected, 'Stable scientific scenario changed')
    return digest(value)


def identities(rows, roots, known=None):
    known = known or {}
    by_pid = {row['pid']: row for row in rows}
    require(len(rows) == len(by_pid) and set(roots) <= set(by_pid), 'Duplicate/missing owned roots')
    for pid, row in by_pid.items():
        raw_gpu.integer(pid, minimum=1)
        raw_gpu.integer(row['created_filetime'], minimum=116444736000000001)
        require(row['scope_root'] is (pid in roots), 'Ownership root marker differs')
        require(abs((row['created_filetime'] - 116444736000000000) / 1e7 - row['started_unix']) <= 5e-6, 'Native process clocks differ')
        if pid not in roots:
            parent = by_pid.get(row['parent'])
            require(parent is not None and row['parent_created_filetime'] == parent['created_filetime'] <= row['created_filetime'], 'Child belongs to another temporal parent')
        if pid in known:
            require(known[pid]['identity'] == row, 'Retained process identity changed')
        visited, cursor = set(), pid
        while cursor in by_pid:
            require(cursor not in visited, 'Cycle in owned tree')
            visited.add(cursor)
            cursor = by_pid[cursor]['parent']
    return by_pid


def gpu_row(row, session):
    roots = {session['app'], session['server']}
    before = identities(row['inventory_before']['owned'], roots)
    after = identities(row['inventory_after']['owned'], roots)
    known = history_audit.row(row, session)
    configured = row['configured_counter_paths']
    require(type(configured) is list and len(set(configured)) == len(configured), 'Duplicate PDH paths')
    require(configured == row['counter_paths_after'], 'GPU paths changed within a sample')
    require(set(row['counter_metadata']) == set(configured), 'PDH metadata path set differs')
    for path, metadata in row['counter_metadata'].items():
        identity = raw_gpu.parse_path(path)
        require(metadata['kind'] == 0x10100 and type(metadata['kind']) is int, 'GPU counter type differs')
        require(metadata['pid'] == identity['pid'] and metadata['instance'] == identity['instance'] and metadata['counter'] == identity['counter'], 'GPU metadata identity differs')
        require(metadata['object'] == ('GPU Process Memory' if identity['kind'] == 'product' else 'GPU Adapter Memory'), 'GPU metadata object differs')
    totals = raw_gpu.sample(row, configured, set(known))
    require(any(raw_gpu.parse_path(path)['pid'] == session['app'] and raw_gpu.parse_path(path)['counter'] == 'dedicated usage' for path in configured), 'Engine dedicated GPU counter absent')
    exposed = {raw_gpu.parse_path(path)['pid'] for path in configured} - {None}
    require(set(row['owned_without_exposed_gpu_counter']) == set(known) - exposed, 'Unexposed process was silently assigned GPU zero')
    ram = row['ram']
    combined = ram['processes'] + ram['completed_before_read']
    require({entry['pid'] for entry in combined} == set(before) and len(combined) == len(before), 'RAM ownership differs')
    for entry in ram['processes']:
        require(entry['created_filetime'] == before[entry['pid']]['created_filetime'], 'RAM identity differs')
        raw_gpu.integer(entry['working_set_bytes'])
        raw_gpu.integer(entry['private_bytes'])
    require(ram['sum_working_set_bytes'] == sum(entry['working_set_bytes'] for entry in ram['processes']), 'RAM sum differs')
    require(all(row[key] == value for key, value in totals.items()), 'GPU raw projections differ')
    return dict(GPU_bytes=totals['product_dedicated_plus_shared_sum_bytes'], RAM_bytes=ram['sum_working_set_bytes'])


def ledger(records, observations, session):
    require(type(records) is list and records, 'Native lifecycle records required')
    by_pid = {record['identity']['pid']: record for record in records}
    require(len(by_pid) == len(records), 'Reused PID in retained lifecycle records')
    roots = {session['app'], session['server']}
    for index, observation in enumerate(observations):
        rows = observation['inventory_after']['owned']
        identities(rows, roots, by_pid)
        for row in rows:
            record = by_pid[row['pid']]
            require(record['first_sample'] <= index <= record['last_sample'], 'Process outside its observed lifetime')
    for pid, record in by_pid.items():
        first, last = record['first_sample'], record['last_sample']
        require(type(first) is int and type(last) is int and 0 <= first <= last < len(observations), 'Invalid process sample interval')
        actual = [index for index, observation in enumerate(observations) if pid in {entry['pid'] for entry in observation['inventory_after']['owned']}]
        require(actual == list(range(first, last + 1)), 'Process vanished and reappeared in lifecycle')
        if record['exit'] is not None:
            require(record['exit']['code'] == 0 and type(record['exit']['code']) is int, 'Owned worker exited abnormally')
            raw_gpu.integer(record['exit']['exited_filetime'], minimum=116444736000000001)
            require(record['identity']['created_filetime'] <= record['exit']['exited_filetime'], 'Worker exit predates creation')
            require(record['exit']['observed_sample'] == last + 1, 'Exit witness is not the first absent process observation')
            require(last < len(observations) - 1, 'Final live process falsely marked exited')
        else:
            require(last == len(observations) - 1, 'Previously owned process disappeared without native exit proof')
    return dict(processes=len(records), observed_births=sum(record['first_sample'] > 0 for record in records),
                observed_exits=sum(record['exit'] is not None for record in records))


def frames(capture, wall_s, *, steady):
    require(capture['width'] == 1920 and capture['height'] == 1080, 'Framebuffer dimensions differ')
    require(capture['invalid_samples'] == 0 and capture['capacity_reached'] is False, 'Native frame data invalid or truncated')
    raw = capture['samples_s']
    if isinstance(raw, dict):
        require(set(raw) == {str(index) for index in range(1, len(raw) + 1)}, 'Native frame indices differ')
        raw = [raw[str(index)] for index in range(1, len(raw) + 1)]
    require(isinstance(raw, list) and all(type(value) in (int, float) and math.isfinite(value) and value > 0 for value in raw), 'Invalid native frame duration')
    values = raw[1:] if steady else raw
    require(values, 'Empty native frame interval')
    ordered = sorted(values)
    def percentile(q):
        position = (len(ordered) - 1) * q
        a, b = math.floor(position), math.ceil(position)
        return ordered[a] + (ordered[b] - ordered[a]) * (position - a)
    result = dict(frames=len(values), excluded_initial_intervals=1 if steady else 0,
                  interval_s=math.fsum(values), median_ms=percentile(.5) * 1000,
                  p95_ms=percentile(.95) * 1000, p99_ms=percentile(.99) * 1000,
                  maximum_ms=max(values) * 1000, over_100ms=sum(value > .1 for value in values))
    if steady:
        require(len(values) > 1000 and abs(result['interval_s'] - 60) < .5 and abs(wall_s - 60) < .5, 'Frame interval does not cover the60second stable window')
        require(all(result[key] <= LIMITS[key] for key in ['median_ms', 'p95_ms', 'p99_ms', 'over_100ms']), 'Stable frame limits exceeded')
    return result
