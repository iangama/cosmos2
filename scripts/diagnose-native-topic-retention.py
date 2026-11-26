"""Controlled completed-Lua-topic load; diagnostic only, never acceptance."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import statistics
import sys
import time
import urllib.request
import uuid
from websockets.sync.client import connect
from cef_page import Page

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT/'output/c212-em-cloud-native-product'
sys.path.insert(0, str(CANDIDATE/'em'))
from em_experiment import Experiment

parser = argparse.ArgumentParser()
parser.add_argument('--label', required=True)
args = parser.parse_args()
assert args.label.isalnum() and len(args.label) <= 20
destination = ROOT/f'evidence/native-topic-retention-{args.label}.json'
assert not destination.exists()
session = json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert Path(session['serverScript']).resolve() == (CANDIDATE/'app/server.py').resolve()
owner = (ROOT/'user/sessions/latest.json').read_bytes()
profile = json.loads((ROOT/'evidence/native-em128-c212mutnewa.json').read_bytes())
seed = 'topic-diagnostic-'+uuid.uuid4().hex[:12]
Experiment.from_payload(profile['fixture']).save(CANDIDATE/'c212-em-worker/product'/(seed+'.json'))
report = {'scope': 'Diagnostic: same 128 mutual bodies, camera, 97 map samples and checkpoint; '
          'completed asynchronous Lua topics on one extra live connection. Close that connection for recovery. '
          'No production bytes changed; not a performance acceptance.',
          'session': session, 'fixture': profile['fixture'], 'runs': [], 'completed': False,
          'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [
              ROOT/'.upstream/openspace/src/topic/connection.cpp',
              ROOT/'.upstream/openspace/src/topic/topics/luascripttopic.cpp',
              ROOT/'.upstream/openspace/src/topic/server.cpp',
              ROOT/'.upstream/openspace/src/properties/property.cpp']}}

def persist():
    temporary = destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    temporary.replace(destination)

def state():
    return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/em/state', timeout=15))

def command(name, **values):
    s = state()['state']
    guard = {} if name == 'pause' else {k: s[k] for k in ('system_id', 'edit_token', 'revision', 'frame')} | {'expected_time_s': s['time_s']}
    request = urllib.request.Request('http://127.0.0.1:4700/api/em/command', data=json.dumps({'command': name, **guard, **values}).encode(), headers={'Content-Type': 'application/json'})
    value = json.load(urllib.request.urlopen(request, timeout=20))
    assert not value.get('display'), value
    return value

def connection():
    ws = connect('ws://127.0.0.1:4682', open_timeout=5, close_timeout=.2, ping_interval=None, max_size=4*1024*1024)
    ws.send(json.dumps({'type': 'apiHandshake', 'apiVersion': {'major': 1, 'minor': 0, 'patch': 0}}))
    return ws

control = connection()
def native(code):
    # One in flight, fixed topic: this diagnostic control must not accumulate topics.
    control.send(json.dumps({'topic': 1, 'type': 'luascript', 'payload': {'script': code, 'return': True}}))
    value = json.loads(control.recv(timeout=20))
    assert value['topic'] == 1, value
    def normalize(x):
        if isinstance(x, dict):
            if x and set(x) == {str(k) for k in range(1, len(x)+1)}: return [normalize(x[str(k)]) for k in range(1,len(x)+1)]
            return {k:normalize(v) for k,v in x.items()}
        return x
    return normalize(value['payload']['1'])

def percentile(values, q):
    ordered = sorted(values); x = (len(values)-1)*q
    return ordered[math.floor(x)]+(ordered[math.ceil(x)]-ordered[math.floor(x)])*(x-math.floor(x))

extra = None
completed = 0
def add_topics(count):
    global extra, completed
    if extra is None: extra = connection()
    began = time.perf_counter()
    while completed < count:
        batch = set(range(completed+1, min(count, completed+100)+1))
        for topic in batch:
            extra.send(json.dumps({'topic': topic, 'type': 'luascript', 'payload': {'script': 'return {probe='+str(topic)+'}', 'return': True}}))
        seen = set()
        for _ in batch:
            value = json.loads(extra.recv(timeout=20))
            assert value['topic'] in batch and value['topic'] not in seen, value
            assert value['payload']['1']['probe'] == value['topic'], value
            seen.add(value['topic'])
        assert seen == batch
        completed += len(batch)
    report.setdefault('seeding', []).append({'completed_topics': completed, 'wall_s': time.perf_counter()-began})
    persist()

persist()
try:
    with Page() as page:
        page.goto('http://127.0.0.1:4700/')
        page.wait_for_function('typeof appState!=="undefined"&&appState!==null')
        page.locator('#em-lab').click()
        page.wait_for_function('location.pathname==="/em.html"&&nativeState?.confirmation?.state==="accepted"&&!pending', timeout=30000)
        for label, count in [('baseline', 0), ('completed1000', 1000), ('completed5000', 5000), ('closed_connection', -1)]:
            command('pause'); command('load', file=seed)
            command('set_visual', changes={'electric_visible': True, 'magnetic_visible': True})
            command('field_map', points_m=[s['position_m'] for s in profile['frozen_field_map']['samples']])
            native('openspace.navigation.setNavigationState({Anchor="C2EMCamera",ReferenceFrame="C2EMRoot",Position={0,-24000000000,16000000000},Up={0,0,1}});return {queued=true}')
            if count > 0: add_topics(count)
            if count < 0:
                extra.close(); extra = None
            command('resume')
            print(json.dumps({'phase': 'warmup', 'condition': label, 'seconds': 30}), flush=True)
            time.sleep(30)
            initial = state()
            native('openspace.cosmos2BeginFrameCapture(5000);return {started=true}')
            began = time.perf_counter()
            time.sleep(15)
            captured = native('return openspace.cosmos2EndFrameCapture()')
            elapsed = time.perf_counter()-began
            final = state()
            values = captured['samples_s'][1:]
            assert captured['width'] == 1920 and captured['height'] == 1080 and captured['invalid_samples'] == 0
            summary = {'median_ms': statistics.median(values)*1000, 'p95_ms': percentile(values,.95)*1000,
                       'p99_ms': percentile(values,.99)*1000, 'over100ms': sum(x>.1 for x in values)}
            report['runs'].append({'condition': label, 'extra_completed_topics': max(0,count), 'initial': initial, 'final': final,
                                   'capture': captured, 'wall_s': elapsed, 'frame_statistics': summary,
                                   'observed_model_s_per_wall_s': (final['state']['time_s']-initial['state']['time_s'])/elapsed})
            persist(); print(json.dumps({'condition': label, **summary}), flush=True)
        command('pause')
        assert (ROOT/'user/sessions/latest.json').read_bytes() == owner
        report.update(completed=True, owner_pointer_preserved=True)
        persist()
finally:
    try:
        command('pause')
        with Page() as page: page.goto('http://127.0.0.1:4700/')
    finally:
        if extra is not None: extra.close()
        control.close()
