"""Diagnostic controls for CEF, marker drawing and live updates; never acceptance."""
from pathlib import Path
import argparse
import ctypes
from ctypes import wintypes as wt
import hashlib
import json
import math
import os
import statistics
import sys
import time
import urllib.request
import uuid
from websockets.sync.client import connect
from cef_page import Page
import native_product_memory as ram

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT/'output/c212-em-cloud-native-product'
sys.path.insert(0, str(CANDIDATE/'em'))
from em_experiment import Experiment

parser = argparse.ArgumentParser()
parser.add_argument('--label', required=True)
parser.add_argument('--prime-cloud-worker', action='store_true')
args = parser.parse_args()
assert 1 <= len(args.label) <= 18 and all(c.isalnum() or c in '_-' for c in args.label)
destination = ROOT/f'evidence/em128-cost-diagnostic-{args.label}.json'
assert not destination.exists()
session = json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert Path(session['serverScript']).resolve() == (CANDIDATE/'app/server.py').resolve()
ram.session = session
original = (ROOT/'user/sessions/latest.json').read_bytes()
profile = json.loads((ROOT/'evidence/native-em128-c212mutnewa.json').read_bytes())
experiment = Experiment.from_payload(profile['fixture'])
seed_name = 'diagnostic-'+uuid.uuid4().hex[:15]
experiment.save(CANDIDATE/'c212-em-worker/product'/(seed_name+'.json'))
report = {'scope': 'Diagnostic, not acceptance:15s windows after30s warmup, fixed camera and same checkpoint per condition. '
                   'Runtime/physics bytes unchanged. Markers can be hidden while native updates continue; CEF refresh can be temporarily suspended.',
          'session': session, 'fixture': profile['fixture'], 'runs': [], 'completed': False,
          'warmup_s': 30, 'window_s': 15, 'logical_processors': os.cpu_count(),
          'prime_cloud_worker': args.prime_cloud_worker,
          'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}

def persist():
    temporary = destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    temporary.replace(destination)

def state():
    return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/em/state', timeout=10))

def command(name, **values):
    s = state()['state']
    guard = {} if name in ('pause', 'snapshot') else {k: s[k] for k in ('system_id', 'edit_token', 'revision', 'frame')} | {'expected_time_s': s['time_s']}
    request = urllib.request.Request('http://127.0.0.1:4700/api/em/command', data=json.dumps({'command': name, **guard, **values}).encode(), headers={'Content-Type': 'application/json'})
    result = json.load(urllib.request.urlopen(request, timeout=20))
    assert not result.get('display'), result
    return result

socket = connect('ws://127.0.0.1:4682', open_timeout=5, close_timeout=.2, ping_interval=None, max_size=4*1024*1024)
socket.send(json.dumps({'type': 'apiHandshake', 'apiVersion': {'major': 1, 'minor': 0, 'patch': 0}}))
topic = 0
def native(code):
    global topic
    topic += 1
    socket.send(json.dumps({'topic': topic, 'type': 'luascript', 'payload': {'script': code, 'return': True}}))
    value = json.loads(socket.recv(timeout=15))
    assert value.get('topic') == topic
    def normalized(x):
        if isinstance(x, dict):
            if x and set(x) == {str(k) for k in range(1, len(x)+1)}: return [normalized(x[str(k)]) for k in range(1, len(x)+1)]
            return {k: normalized(v) for k, v in x.items()}
        return x
    return normalized(value['payload']['1'])

ram.kernel.GetProcessTimes.argtypes = [wt.HANDLE, *([ctypes.POINTER(wt.FILETIME)]*4)]
ram.kernel.GetProcessTimes.restype = wt.BOOL
def cpu():
    result = {}
    for p in ram.product_memory()['processes']:
        handle = ram.kernel.OpenProcess(0x1000, False, p['pid'])
        if not handle: continue
        try:
            times = [wt.FILETIME() for _ in range(4)]
            assert ram.kernel.GetProcessTimes(handle, *[ctypes.byref(t) for t in times])
            def seconds(t): return ((t.dwHighDateTime << 32) | t.dwLowDateTime)*1e-7
            result[str(p['pid'])] = {'name': p['name'], 'CPU_s': seconds(times[2])+seconds(times[3])}
        finally:
            ram.kernel.CloseHandle(handle)
    return result

def markers(visible):
    s = state()['state']
    nodes = ['C2EMBody_'+hashlib.sha256(('body:'+identity).encode()).hexdigest()[:24] for identity in s['experiment']['system']['ids']]
    code = 'local n=0;'
    for node in nodes:
        prop = json.dumps('Scene.'+node+'.Renderable.Enabled')
        code += 'openspace.setPropertyValueSingle('+prop+','+str(visible).lower()+');if openspace.propertyValue('+prop+') then n=n+1 end;'
    assert native(code+'return {enabled=n}')['enabled'] == (128 if visible else 0)

def percentile(values, q):
    a = sorted(values); x = (len(a)-1)*q; lo = math.floor(x); hi = math.ceil(x)
    return a[lo]+(a[hi]-a[lo])*(x-lo)

persist()
try:
    with Page() as page:
        if args.prime_cloud_worker:
            page.goto('http://127.0.0.1:4700/em-cloud.html')
            page.wait_for_function('state&&native?.active&&!pending&&state.paused',timeout=30000)
            cloud_profile=json.loads((ROOT/'evidence/native-emcloud-c212src128a.json').read_bytes())
            seed_file=Path(cloud_profile['fixture_checkpoint']).stem
            page.evaluate("command('load',{file:"+json.dumps(seed_file)+"})")
            page.evaluate("command('advance',{steps:1})")
            page.wait_for_function('!pending&&native?.confirmation?.metadata.time_s===state.time_s',timeout=30000)
            page.locator('#return').click()
            page.wait_for_function('location.pathname==="/"',timeout=30000)
        report['cloud_worker_before']=json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/em-cloud/state',timeout=10))
        page.goto('http://127.0.0.1:4700/')
        page.wait_for_function('typeof appState!=="undefined"&&appState!==null')
        page.locator('#em-lab').click()
        page.wait_for_function('location.pathname==="/em.html"&&nativeState?.confirmation?.state==="accepted"&&!pending', timeout=30000)
        hook = '''(() => {
          window.__emCost=[];window.__emCostOriginals={};
          for(const name of ['render','renderEditor','renderNativeEM','renderPotentialEM']){
            const fn=window[name];if(typeof fn!=='function')continue;window.__emCostOriginals[name]=fn;
            window[name]=function(...args){const began=performance.now();try{return fn.apply(this,args);}finally{window.__emCost.push({name,t:began,ms:performance.now()-began});}};
          }
          window.__emOriginalRefresh=refresh;
          return true;
        })()'''
        assert page.evaluate(hook)
        points = [s['position_m'] for s in profile['frozen_field_map']['samples']]
        conditions = [('live', True, True, True), ('hidden_markers', True, False, True),
                      ('paused', False, True, True), ('no_CEF_refresh', True, True, False),
                      ('live_repeat', True, True, True)]
        for label, running, visible, refresh in conditions:
            page.evaluate('refresh=window.__emOriginalRefresh;true')
            command('pause'); command('load', file=seed_name)
            command('set_visual', changes={'electric_visible': True, 'magnetic_visible': True})
            command('field_map', points_m=points)
            markers(True)
            native('openspace.navigation.setNavigationState({Anchor="C2EMCamera",ReferenceFrame="C2EMRoot",Position={0,-24000000000,16000000000},Up={0,0,1}});return {queued=true}')
            command('resume')
            print(json.dumps({'phase': 'warmup', 'condition': label, 'seconds': 30}), flush=True)
            time.sleep(30)
            if not running: command('pause')
            markers(visible)
            if not refresh: page.evaluate('refresh=async()=>{};true')
            page.evaluate('window.__emCost=[];true')
            initial = state()
            before = cpu()
            native('openspace.cosmos2BeginFrameCapture(5000);return {started=true}')
            began = time.perf_counter()
            echoes = []
            for part in range(5):
                time.sleep(max(0, began+(part+1)*3-time.perf_counter()))
                start = time.perf_counter()
                actual = native('return {stamp=__c2EMNativeStamp}')
                echoes.append({'wall_ms': (time.perf_counter()-start)*1000, 'stamp': actual.get('stamp')})
            captured = native('return openspace.cosmos2EndFrameCapture()')
            elapsed = time.perf_counter()-began
            after = cpu()
            final = state()
            hooks = page.evaluate('window.__emCost')
            values = captured['samples_s'][1:]
            assert captured['width'] == 1920 and captured['height'] == 1080 and captured['invalid_samples'] == 0
            cpu_cost = {pid: {'name': value['name'], 'CPU_s': value['CPU_s']-before[pid]['CPU_s']}
                        for pid, value in after.items() if pid in before}
            summary = {'median_ms': statistics.median(values)*1000, 'p95_ms': percentile(values, .95)*1000,
                       'p99_ms': percentile(values, .99)*1000, 'over100ms': sum(x>.1 for x in values)}
            component = {}
            for name in {x['name'] for x in hooks}:
                costs = [x['ms'] for x in hooks if x['name'] == name]
                component[name] = {'calls': len(costs), 'median_ms': statistics.median(costs), 'p95_ms': percentile(costs, .95), 'max_ms': max(costs)}
            record = {'condition': label, 'physics_running': running, 'markers_visible': visible, 'CEF_refresh_enabled': refresh,
                      'initial': initial, 'final': final, 'wall_s': elapsed, 'capture': captured, 'frame_statistics': summary,
                      'process_CPU_cost': cpu_cost, 'CEF_hooks_raw': hooks, 'CEF_component_costs': component,
                      'native_echoes': echoes, 'observed_model_s_per_wall_s': (final['state']['time_s']-initial['state']['time_s'])/elapsed}
            report['runs'].append(record); persist()
            print(json.dumps({'condition': label, **summary, 'CEF_costs': component, 'CPU': cpu_cost}), flush=True)
        page.evaluate('refresh=window.__emOriginalRefresh;true')
        markers(True);command('pause')
        assert (ROOT/'user/sessions/latest.json').read_bytes() == original
        report.update(completed=True, owner_pointer_preserved=True)
        persist()
finally:
    try:
        command('pause')
        with Page() as page:
            page.evaluate('if(window.__emOriginalRefresh)refresh=window.__emOriginalRefresh;true')
            page.goto('http://127.0.0.1:4700/')
    finally:
        socket.close()
