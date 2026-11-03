"""Real native websocket callback and subscription lifecycle regression checks."""
from pathlib import Path
import hashlib
import json
import time
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
destination = ROOT/'evidence/topic-cleanup-native-lifecycle-check.json'
assert not destination.exists()
session = json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
receipt = json.loads((ROOT/'evidence/built-runtime-topic-cleanup.json').read_bytes())
assert Path(session['runtime']).resolve() == (ROOT/'.runtime-topic-cleanup').resolve()
assert hashlib.sha256((ROOT/'.runtime-topic-cleanup/bin/OpenSpace.exe').read_bytes()).hexdigest() == receipt['engine_sha256']
owner = (ROOT/'user/sessions/latest.json').read_bytes()
report = {'scope': 'Actual Windows native API. Completed, pending, reused and interleaved Lua topics; '
          'active propertyTree subscription, stop and recreation; disconnect before callback delivery. '
          'No physics or performance acceptance.', 'session': session, 'engine_sha256': receipt['engine_sha256'],
          'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'completed': False}
PROP = 'Scene.CatalogStars.Renderable.Enabled'
SUB = 9000000
events = []

def connection():
    ws = connect('ws://127.0.0.1:4682', open_timeout=5, close_timeout=.2, ping_interval=None, max_size=4*1024*1024)
    ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
    return ws

ws = connection()
def send(topic, code, sync=True):
    ws.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True,'shouldBeSynchronized':sync}}))

def receive(count):
    replies = []
    while len(replies) < count:
        value = json.loads(ws.recv(timeout=20))
        if value['topic'] == SUB:
            if value['payload'].get('uri') == PROP: events.append(value['payload'])
        else: replies.append(value)
    return replies

def call(topic, code):
    send(topic, code)
    value = receive(1)[0]
    assert value['topic'] == topic, value
    return value['payload']['1']

original = call(1, 'return {value=openspace.propertyValue('+json.dumps(PROP)+')}')['value']
assert isinstance(original, bool)
try:
    # Multiple asynchronous results coexist; every ID/value must arrive exactly once.
    for start in range(0,4096,128):
        for i in range(start,start+128): send(i+100, 'return {probe='+str(i)+'}', i%2 == 0)
        replies = receive(128)
        assert {r['topic'] for r in replies} == set(range(start+100,start+228))
        assert {r['payload']['1']['probe'] for r in replies} == set(range(start,start+128))
        assert all(r['payload']['1']['probe'] == r['topic']-100 for r in replies)
    report['distinct_completed_callbacks'] = 4096
    time.sleep(.15)  # Cross several preSync passes after all callbacks return.
    for i in range(128): assert call(77, 'return {probe='+str(i)+'}') == {'probe':i}
    report['reused_ID_sequential_callbacks'] = 128
    for i in range(128): send(78, 'return {probe='+str(i)+'}', i%2 == 0)
    replies = receive(128)
    assert all(r['topic'] == 78 for r in replies)
    assert {r['payload']['1']['probe'] for r in replies} == set(range(128))
    report['same_ID_inflight_callbacks'] = 128
    # A live subscription must survive the per-frame completed-topic sweep.
    ws.send(json.dumps({'topic':SUB,'type':'propertyTree','payload':{'event':'start_subscription'}}))
    for i in range(128): send(i+10000, 'return {probe='+str(i)+'}')
    assert {r['payload']['1']['probe'] for r in receive(128)} == set(range(128))
    time.sleep(.15)
    for value in (not original, original):
        before = len(events)
        actual = call(79, 'openspace.setPropertyValueSingle('+json.dumps(PROP)+','+str(value).lower()+');return {value=openspace.propertyValue('+json.dumps(PROP)+')}')
        assert actual['value'] == value
        assert any(e['value'] == value for e in events[before:]), events
    report['live_subscription_events'] = list(events)
    ws.send(json.dumps({'topic':SUB,'type':'propertyTree','payload':{'event':'stop_subscription'}}))
    before = len(events)
    for value in (not original,original):
        call(79,'openspace.setPropertyValueSingle('+json.dumps(PROP)+','+str(value).lower()+');return {ok=true}')
    assert len(events) == before
    report['unsubscribe_stopped_events'] = True
    ws.send(json.dumps({'topic':SUB,'type':'propertyTree','payload':{'event':'start_subscription'}}))
    for value in (not original,original):
        call(79,'openspace.setPropertyValueSingle('+json.dumps(PROP)+','+str(value).lower()+');return {ok=true}')
    assert len(events) == before+2
    ws.send(json.dumps({'topic':SUB,'type':'propertyTree','payload':{'event':'stop_subscription'}}))
    report['same_subscription_ID_recreated'] = True
    # Destroy transport before scripts necessarily finish; callbacks may not use freed topics.
    for batch in range(12):
        drop = connection()
        for i in range(64):
            drop.send(json.dumps({'topic':i+1,'type':'luascript','payload':{'script':'return {probe='+str(i)+'}','return':True}}))
        drop.close()
        assert call(80,'return {alive=true}') == {'alive':True}
    report['disconnects_with_pending_scripts'] = 12
    assert call(81,'return {alive=true,value=openspace.propertyValue('+json.dumps(PROP)+')}') == {'alive':True,'value':original}
    assert (ROOT/'user/sessions/latest.json').read_bytes() == owner
    report.update(completed=True, owner_pointer_preserved=True)
    destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('session','live_subscription_events')}),flush=True)
finally:
    try: call(82,'openspace.setPropertyValueSingle('+json.dumps(PROP)+','+str(original).lower()+');return {restored=true}')
    finally: ws.close()
