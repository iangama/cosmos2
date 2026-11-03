"""Fresh server restart, exact future, sealed preferences, and real lost-ACK cleanup."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import time
import urllib.error
import urllib.request
import uuid
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT/'output/c212-em-cloud-product'
STORAGE = CANDIDATE/'c212-em-cloud-worker/product'
sys.path.insert(0, str(CANDIDATE/'em-cloud'))
from cloud_checkpoint import load
from cef_page import Page

original = (ROOT/'user/sessions/latest.json').read_bytes()
saved_science = (STORAGE/'ui-phase.json').read_bytes()
saved_aux = (STORAGE/'ui-phase.view.json').read_bytes()
system, phase, dt, acting = load(STORAGE/'ui-phase.json')
aux = json.loads(saved_aux)['payload']


def status():
    return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/em-cloud/state', timeout=10))


def command(name, error=False, **parameters):
    state = status()['state']
    guard = {k: state[k] for k in ('system_id', 'edit_token', 'revision', 'frame')} | {'expected_time_s': state['time_s']}
    request = urllib.request.Request('http://127.0.0.1:4700/api/em-cloud/command',
                                     data=json.dumps({'command': name, **guard, **parameters}).encode(),
                                     headers={'Content-Type': 'application/json'})
    try:
        result = json.load(urllib.request.urlopen(request, timeout=20))
    except urllib.error.HTTPError as failed:
        assert error and failed.code == 400, failed.read()
        return json.loads(failed.read())
    assert not error and not result.get('display'), result
    return result


def stable():
    value = status()
    return {k: value['state'][k] for k in ('system_id', 'edit_token', 'revision', 'time_s', 'phase_sha256',
                                          'model', 'dt_s', 'controls', 'selected_particle')} | {'visual': value['visual']}


def array(value):
    return [value[str(i)] for i in range(1, len(value)+1)] if isinstance(value, dict) else value


refused = []
with Page() as page:
    page.goto('http://127.0.0.1:4700/em-cloud.html')
    page.wait_for_function('state && !pending && state.paused && native?.confirmation?.metadata.time_s===state.time_s', timeout=25000)
    value = status()
    assert value['parent_sources_sha256'] == {name: hashlib.sha256((CANDIDATE/'app'/name).read_bytes()).hexdigest()
                                             for name in ('server.py', 'em_cloud_laboratory.py', 'em_cloud_native.py', 'em_cloud_wire.py')}
    s = value['state']
    assert s['phase_sha256'] == hashlib.sha256(phase._x+phase._v).hexdigest() and s['time_s'] == phase.time_s
    assert s['dt_s'] == dt and s['controls'] == acting and s['count'] == phase.count
    assert value['visual'] == aux['visual'] and s['requested_model_s_per_wall_s'] == aux['rate']
    assert s['selected_particle']['index'] == aux['selected']
    with connect('ws://127.0.0.1:4682', open_timeout=3, close_timeout=.2, ping_interval=None) as ws:
        ws.send(json.dumps({'type': 'apiHandshake', 'apiVersion': {'major': 1, 'minor': 0, 'patch': 0}}))
        ws.send(json.dumps({'topic': 1, 'type': 'luascript', 'payload': {'return': True, 'script': 'return {navigation=openspace.navigation.getNavigationState("C2EMRoot"),focus=openspace.propertyValue("Scene.C2EMCamera.Translation.Position")}'}}))
        pose = json.loads(ws.recv(timeout=5))['payload']['1']
    assert array(pose['focus']) == [x*1e9 for x in aux['view']['focus_model_m']]
    for key in ('Position', 'Up'):
        expected = aux['view']['navigation'][key]
        actual = array(pose['navigation'][key])
        assert max(abs(a-b) for a, b in zip(actual, expected)) <= max(.001, max(abs(x) for x in expected)*1e-12)
    assert pose['navigation']['Anchor'] == aux['view']['navigation']['Anchor']
    for _ in range(2):
        command('advance', steps=32)
        for _ in range(32):
            phase, _ = system.step(phase, dt, **acting)
        assert status()['state']['phase_sha256'] == hashlib.sha256(phase._x+phase._v).hexdigest()
    command('load', file='ui-phase')
    command('save', file='aux-proof')
    valid = json.loads((STORAGE/'aux-proof.view.json').read_bytes())
    baseline = stable()
    for fault in ('schema', 'extra', 'checkpoint', 'frame', 'anchor', 'visibility', 'radius', 'rate', 'selected', 'selection_bound'):
        envelope = json.loads(json.dumps(valid))
        body = envelope['payload']
        if fault == 'schema':body['schema'] = True
        elif fault == 'extra':body['gravity'] = True
        elif fault == 'checkpoint':body['checkpoint_sha256'] = '0'*64
        elif fault == 'frame':body['view']['frame'] = 'gravity'
        elif fault == 'anchor':body['view']['navigation']['Anchor'] = 'Earth'
        elif fault == 'visibility':body['visual']['cloud_visible'] = 1
        elif fault == 'radius':body['visual']['map_radius_m'] = 0
        elif fault == 'rate':body['rate'] = True
        elif fault == 'selected':body['selected'] = True
        elif fault == 'selection_bound':body['selected'] = status()['state']['count']
        envelope['sha256'] = hashlib.sha256(json.dumps(body, sort_keys=True, allow_nan=False, separators=(',', ':')).encode()).hexdigest()
        (STORAGE/'aux-proof.view.json').write_text(json.dumps(envelope)+'\n')
        command('load', error=True, file='aux-proof')
        assert stable() == baseline, fault
        refused.append('resealed '+fault)
    duplicate = saved_aux.replace(b'"schema": 1', b'"schema": 1,"schema":1', 1)
    assert duplicate != saved_aux
    for name, raw in (('duplicate', duplicate), ('oversized', b' '*16385), ('nonfinite', saved_aux.replace(b'"rate": 0.5', b'"rate": NaN'))):
        (STORAGE/'aux-proof.view.json').write_bytes(raw)
        command('load', error=True, file='aux-proof')
        assert stable() == baseline
        refused.append(name)
    shutil.copy2(STORAGE/'ui-phase.json', STORAGE/'without-view.json')
    command('set_visual', changes={'cloud_visible': False})
    command('set_rate', value=.1)
    command('load', file='without-view')
    defaults = status()
    assert defaults['state']['requested_model_s_per_wall_s'] == 1.
    assert defaults['visual']['cloud_visible'] and defaults['native']['visible']
    assert defaults['state']['phase_sha256'] == baseline['phase_sha256']
    command('load', file='ui-phase')
    page.goto('http://127.0.0.1:4700/')

# Own native object, same final files, no test hook in the HTTP product.
# Execute real node creation, then simulate losing only its acknowledgement.
snapshot = status()
assert not snapshot['native']['active'] and snapshot['state']['paused']
before = snapshot['state']['phase_sha256']
sys.path.insert(0, str(CANDIDATE/'em'))
sys.path.insert(0, str(CANDIDATE/'app'))
from em_cloud_native import NativeEMCloud
native = NativeEMCloud()
original_call = native._call
lost = []
try:
    native.enter()

    def lost_ack(code):
        value = original_call(code)
        if not lost and 'openspace.addSceneGraphNode' in code and 'C2EMCloudStream' in code:
            lost.append(True)
            raise TimeoutError('Simulated lost ACK after real aggregate creation')
        return value
    native._call = lost_ack
    try:
        native.sync(snapshot['state'])
    except TimeoutError:
        pass
    else:
        raise AssertionError('Fault was not injected')
    assert native.cleanup_required
    assert original_call('return {exists=openspace.hasSceneGraphNode("C2EMCloudStream")}')['exists']
    try:
        native.sync(snapshot['state'])
    except RuntimeError:
        pass
    else:
        raise AssertionError('Uncertain publication was retried')
    native._call = original_call
    native.leave()
    assert original_call('return {clean=not openspace.hasSceneGraphNode("C2EMRoot") and not openspace.hasSceneGraphNode("C2EMCloudStream") and not openspace.hasSceneGraphNode("C2EMCloudSelection")}')['clean']
    assert status()['state']['phase_sha256'] == before
finally:
    native._call = original_call
    native.leave()
    native.close()
assert (STORAGE/'ui-phase.json').read_bytes() == saved_science
assert (STORAGE/'ui-phase.view.json').read_bytes() == saved_aux
assert (ROOT/'user/sessions/latest.json').read_bytes() == original
report = {'status': 'fresh_EM_cloud_restart_exact_future_sealed_auxiliary_and_real_lost_ACK_cleanup_verified',
          'count': snapshot['state']['count'], 'restart_science_controls_rate_selection_and_camera_exact': True,
          'future_collective_steps_exact_after_fresh_server': 64, 'auxiliary_refusals_without_any_state_mutation': refused,
          'scientific_checkpoint_without_aux_uses_explicit_visible_rate1_defaults': True,
          'real_node_created_before_simulated_ACK_loss': True, 'uncertain_retry_blocked': True,
          'cleanup_confirmed_no_orphan_nodes_and_scientific_state_preserved': True,
          'saved_science_and_view_preserved': True, 'owner_pointer_preserved': True,
          'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (*CANDIDATE.glob('app/em_cloud*.py'), Path(__file__))},
          'scope': 'Fresh candidate process restart and real native fault lifecycle. No performance or128-source approval.'}
(ROOT/'evidence/em-cloud-persistence-resilience-check.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({'status': report['status'], 'refusals': len(refused), 'exact_future_steps': 64}, indent=2))
