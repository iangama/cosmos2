"""Candidate HTTP/child/GPU integration and independent SI buffer confirmation."""
from pathlib import Path
import hashlib
import json
import math
import sys
import time
import urllib.error
import urllib.request
import uuid
import zlib
import numpy as np
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT/'output/c212-em-cloud-product'
sys.path.insert(0, str(CANDIDATE/'em-cloud'))
import cloud_transport as wire
from cloud_core import Phase
from cloud_presets import create

pointer = ROOT/'user/sessions/latest.json'
original = pointer.read_bytes()
app_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (ROOT/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
session = json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
receipt = json.loads((ROOT/'evidence/built-runtime-em-cloud.json').read_text())
assert Path(session['runtime']).resolve() == (ROOT/'.runtime-em-cloud').resolve()
assert hashlib.sha256((ROOT/'.runtime-em-cloud/bin/OpenSpace.exe').read_bytes()).hexdigest() == receipt['engine_sha256']


def post(path, value):
    request = urllib.request.Request('http://127.0.0.1:4700/api/em-cloud/'+path,
                                     data=json.dumps(value, allow_nan=False).encode(),
                                     headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise AssertionError((error.code, error.read().decode()))


def status():
    return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/em-cloud/state', timeout=10))


def guard():
    s = status()['state']
    return {k: s[k] for k in ('system_id', 'edit_token', 'revision', 'frame')} | {'expected_time_s': s['time_s']}


def command(name, **args):
    response = post('command', {'command': name, **(guard() if name not in ('pause', 'snapshot') else {}), **args})
    assert not response.get('display'), response
    return response


native_connection = None
native_topic = 0


def native(code):
    global native_connection, native_topic
    if native_connection is None:
        native_connection = connect('ws://127.0.0.1:4682', open_timeout=3, close_timeout=.2, ping_interval=None)
        native_connection.send(json.dumps({'type': 'apiHandshake', 'apiVersion': {'major': 1, 'minor': 0, 'patch': 0}}))
    native_topic += 1
    native_connection.send(json.dumps({'topic': native_topic, 'type': 'luascript', 'payload': {'script': code, 'return': True}}))
    response = json.loads(native_connection.recv(timeout=5))
    assert response.get('topic') == native_topic, response
    result = response.get('payload', {}).get('1')
    assert isinstance(result, dict), result
    return result


def literal(value):
    if isinstance(value, str):
        return '"'+''.join(chr(b) if 32 <= b <= 126 and b not in (34, 92) else '\\'+format(b, '03d') for b in value.encode())+'"'
    if type(value) is bool:
        return str(value).lower()
    if type(value) in (int, float):
        return repr(value)
    if isinstance(value, (tuple, list)):
        return '{'+','.join(literal(v) for v in value)+'}'
    if isinstance(value, dict):
        return '{'+','.join('['+literal(k)+']='+literal(v) for k, v in value.items())+'}'
    raise TypeError(value)


def array(value):
    return [value[str(k)] for k in range(1, len(value)+1)] if isinstance(value, dict) else value


states, refused = [], []
proof_node = 'C2EMWireProof'
created = False
try:
    post('enter', {})
    assert status()['parent_sources_sha256'] == {name: hashlib.sha256((CANDIDATE/'app'/name).read_bytes()).hexdigest()
                                               for name in ('server.py', 'em_cloud_laboratory.py', 'em_cloud_native.py', 'em_cloud_wire.py')}
    for count in (1, 128, 10000):
        command('load_preset', preset='crossed', count=count)
        system, phase, dt, acting = create('crossed', count)
        for _ in range(3):
            command('advance', steps=16)
            for _ in range(16):
                phase, _ = system.step(phase, dt, **acting)
        command('select', index=count-1)
        s = status()
        assert s['state']['phase_sha256'] == hashlib.sha256(phase._x+phase._v).hexdigest()
        assert s['native']['error'] is None and s['native']['confirmation']['metadata']['time_s'] == phase.time_s
        metadata, xyz = wire.decode(wire.read_packet(CANDIDATE/'native-cloud/positions.bin'),
                                    *[s['state'][k] for k in ('system_id', 'edit_token', 'cloud_id', 'source_id')], count)
        assert xyz.tobytes() == phase._x and metadata == s['native']['confirmation']['metadata']
        assert s['state']['selected_particle']['position_m'] == phase.point(count-1)['position_m']
        selected = native('return {position=openspace.propertyValue("Scene.C2EMCloudSelection.Translation.Position"),count=openspace.propertyValue("Scene.C2EMCloudStream.Renderable.NumberOfDataPoints")}')
        assert selected['count'] == count
        assert array(selected['position']) == [v*1e9 for v in phase.point(count-1)['position_m']]
        post('frame', {'selected': True})
        command('save', file='native-proof')
        saved = status()['state']
        command('advance', steps=16)
        command('load', file='native-proof')
        restored = status()['state']
        assert restored['phase_sha256'] == saved['phase_sha256'] and restored['time_s'] == saved['time_s']
        assert restored['selected_particle'] == saved['selected_particle']
        states.append({'count': count, 'collective_steps_exact': 48, 'native_f64_positions_exact': True,
                       'native_selection_graphic_coordinates_exact': True, 'save_load_phase_and_selected_exact': True,
                       'maximum_gpu_quantization_m': s['native']['confirmation']['maximum_gpu_position_quantization_m']})
        print('native EM cloud count '+str(count)+' passed', flush=True)

    # Frozen field vectors use the same source model and full independent stamp.
    points = [[3, 2, 1], [-3, -2, -1], [0, 0, 0]]
    command('field_map', points_m=points)
    s = status()
    assert s['field_map']['render']['sample_count'] == 3
    for point, sample in zip(points, s['field_map']['measurement']['samples']):
        assert sample['position_m'] == point and sample['electric_field_V_m'] == [.2, 0., 0.]
        assert sample['magnetic_field_T'] == [0., 0., 1.]
    before = s['state']['phase_sha256']
    for hidden in (False, True):
        command('set_visual', changes={'cloud_visible': hidden, 'electric_visible': hidden, 'magnetic_visible': not hidden})
        assert status()['state']['phase_sha256'] == before
    command('export_positions')

    # A separate native node makes receiver fault injections independent of the
    # operational bridge's pending/confirmed state machine.
    s = status()['state']
    source = s['source_id']
    ids = ('a'*32, 'b'*32, 'c'*32)
    path = CANDIDATE/'native-cloud/proof.bin'
    phase = Phase(xyz, np.zeros_like(xyz), 2.)
    sequence = 1
    packet, metadata = wire.encode(phase, *ids, source, sequence)
    wire.publish(path, packet)
    node = {'Identifier': proof_node, 'Parent': 'C2EMRoot',
            'Renderable': {'Type': 'RenderablePointCloud', 'ConfirmedCloud': {
                'File': path.as_posix(), 'SystemId': ids[0], 'EditToken': ids[1], 'CloudId': ids[2],
                'SourceId': source, 'Frame': wire.FRAME, 'Model': wire.VERSION,
                'TimeUnitS': 1., 'LengthUnitM': 1., 'Count': 10000},
                'Unit': 'm', 'UseCaching': False, 'Texture': {'Enabled': False},
                'SizeSettings': {'ScaleExponent': 0.}, 'Coloring': {'FixedColor': [0., 0., 0.]}}}
    native('openspace.addSceneGraphNode('+literal(node)+');return {created=true}')
    created = True

    def native_status():
        value = native('return {status=openspace.propertyValue('+literal('Scene.'+proof_node+'.Renderable.ConfirmedCloudStatus')+'),count=openspace.propertyValue('+literal('Scene.'+proof_node+'.Renderable.NumberOfDataPoints')+')}')
        return json.loads(value['status']), value['count']

    def wait(kind):
        deadline = time.perf_counter()+5
        while time.perf_counter() < deadline:
            value, count = native_status()
            if value['state'] == kind:
                assert count == 10000
                return value
            time.sleep(.02)
        raise AssertionError(value)

    assert wait('accepted')['metadata'] == metadata
    _, size = wire.HEADER.unpack_from(packet)
    raw = packet[wire.HEADER.size+size:]
    for key, bad in (('model', 'massless_central_ias15_v1'), ('system_id', '0'*32),
                     ('edit_token', '0'*32), ('cloud_id', '0'*32), ('source_id', 'em-'+'0'*64),
                     ('frame', 'gravity'), ('count', True), ('count', 9999),
                     ('sequence', True), ('time_model', 1.), ('time_unit_s', 2.), ('length_unit_m', 1e9),
                     ('schema', True), ('positions', 'float32'), ('payload_crc32', 0),
                     ('payload-bitflip', None), ('resealed-NaN', None), ('duplicate', None)):
        # Confirm a fresh valid packet before every invalid packet, so an old
        # rejection cannot accidentally satisfy a later fault case.
        sequence += 1
        packet, metadata = wire.encode(phase, *ids, source, sequence)
        wire.publish(path, packet)
        assert wait('accepted')['metadata'] == metadata
        m, payload = {**metadata, 'sequence': sequence+1}, raw
        if key == 'payload-bitflip':
            payload = raw[:-1]+bytes([raw[-1]^1])
        elif key == 'resealed-NaN':
            changed = xyz.copy()
            changed[9999, 0] = float('nan')
            payload = changed.astype('<f8').tobytes()
            m.update(payload_crc32=zlib.crc32(payload), payload_sha256=hashlib.sha256(payload).hexdigest())
        elif key != 'duplicate':
            m[key] = bad
        header = json.dumps(m, separators=(',', ':')).encode('ascii')
        if key == 'duplicate':
            header = b'{"schema":2,'+header[1:]
        wire.publish(path, wire.HEADER.pack(wire.MAGIC, len(header))+header+payload)
        rejection = wait('rejected')
        assert rejection['previous_buffer_preserved'] and rejection['last_accepted_sequence'] == sequence
        refused.append({'fault': key, 'native_error': rejection['error']})
    sequence += 1
    packet, metadata = wire.encode(phase, *ids, source, sequence)
    wire.publish(path, packet)
    assert wait('accepted')['metadata'] == metadata
    native('openspace.removeSceneGraphNode('+literal(proof_node)+');return {removed=true}')
    created = False
    post('leave', {})
    assert native('return {clean=not openspace.hasSceneGraphNode("C2EMRoot"),earth=openspace.hasSceneGraphNode("Earth")}') == {'clean': True, 'earth': True}
    assert pointer.read_bytes() == original
    assert app_hashes == {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in (ROOT/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    report = {'status': 'candidate_EM_cloud_operational_worker_native_GPU_and_SI_selection_verified',
              'engine_sha256': receipt['engine_sha256'], 'cases': states,
              'native_invalid_packets_refused_with_previous_buffer_preserved': refused,
              'three_frozen_field_samples_and_visibility_independence': True,
              'installed_app_files_preserved': len(app_hashes), 'owner_pointer_preserved': True,
              'native_cleanup_and_Atlas_return_confirmed': True,
              'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (*CANDIDATE.glob('app/em_cloud*.py'), *[p for p in (CANDIDATE/'em-cloud').iterdir() if p.is_file()], Path(__file__))},
              'scope': 'Native functional and fault integration, no CEF journey or formal performance/128-source approval.'}
    (ROOT/'evidence/em-cloud-native-check.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'status': report['status'], 'cases': len(states), 'native_refusals': len(refused)}, indent=2))
except Exception as error:
    (ROOT/'evidence'/('em-cloud-native-failure-'+uuid.uuid4().hex+'.json')).write_text(json.dumps({
        'error': str(error), 'states_completed': states, 'refusals_completed': refused,
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, indent=2)+'\n')
    raise
finally:
    if created:
        native('if openspace.hasSceneGraphNode('+literal(proof_node)+') then openspace.removeSceneGraphNode('+literal(proof_node)+') end;return {clean=true}')
    post('leave', {})
    assert pointer.read_bytes() == original
    if native_connection is not None:
        native_connection.close()
