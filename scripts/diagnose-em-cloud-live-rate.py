"""Read live worker timing and host pressure; this is not a formal benchmark."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import time
import urllib.request
import psutil

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--label',required=True)
parser.add_argument('--seconds',type=int,default=45)
parser.add_argument('--profile',help='Completed profile whose fixed fixture and second layer combination are reproduced.')
args=parser.parse_args()
assert args.label.isalnum() and len(args.label)<=24 and 5<=args.seconds<=120
destination=ROOT/f'evidence/em-cloud-live-rate-{args.label}.json'
assert not destination.exists()
session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
owner=(ROOT/'user/sessions/latest.json').read_bytes()

def state():
    return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/em-cloud/state',timeout=10))

def command(name,**parameters):
    s=state()['state']
    guard={} if name in ('pause','snapshot') else {k:s[k] for k in ('system_id','edit_token','revision','frame')}|{'expected_time_s':s['time_s']}
    request=urllib.request.Request('http://127.0.0.1:4700/api/em-cloud/command',
        data=json.dumps({'command':name,**guard,**parameters}).encode(),headers={'Content-Type':'application/json'})
    result=json.load(urllib.request.urlopen(request,timeout=15))
    assert not result.get('display'),result

entered=False
if args.profile:
    assert args.profile.isalnum() and len(args.profile)<=18
    raw=json.loads((ROOT/f'evidence/native-emcloud-{args.profile}.json').read_bytes())
    assert raw['completed'] and len(raw['runs'])==3
    request=urllib.request.Request('http://127.0.0.1:4700/api/em-cloud/enter',data=b'{}',headers={'Content-Type':'application/json'})
    json.load(urllib.request.urlopen(request,timeout=15));entered=True
    command('pause');command('load',file=Path(raw['fixture_checkpoint']).stem)
    command('set_rate',value=1.)
    command('set_visual',changes={'cloud_visible':False,'electric_visible':True,'magnetic_visible':True})
    command('field_map',points_m=[s['position_m'] for s in raw['runs'][1]['frozen_field_map']['measurement']['samples']])
initial=state();assert initial['state']['paused'] and initial['native']['active']
worker=psutil.Process(initial['worker_pid']);engine=psutil.Process(session['app'])
# Windows venv python.exe can be a launcher shim; count its real child too.
workers=[worker,*worker.children(recursive=True)]
product={p.pid:p for p in [psutil.Process(session['server']),engine]}
product.update({p.pid:p for p in psutil.Process(session['server']).children(recursive=True)})
for process in product.values():process.cpu_percent()
psutil.cpu_percent(percpu=True)
battery=psutil.sensors_battery()
report={'scope':'Diagnostic only; no frame/resource-window or throughput acceptance. Samples include the live compute duration reported by the worker, not every step.',
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'session':session,'initial':initial,'battery':None if battery is None else dict(battery._asdict()),
        'samples':[],'completed':False}
def persist():
    temporary=destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    temporary.replace(destination)

try:
    command('resume');began=time.perf_counter()
    for i in range(args.seconds):
        delay=began+i+1-time.perf_counter()
        if delay>0:time.sleep(delay)
        value=state();s=value['state'];memory=psutil.virtual_memory()
        row={'utc':datetime.now(timezone.utc).isoformat(),'wall_elapsed_s':time.perf_counter()-began,
             'model_time_s':s['time_s'],'effective_model_s_per_wall_s':s['effective_model_s_per_wall_s'],
             'compute_ms':s['compute_ms'],'sequence':s['sequence'],'paused':s['paused'],'notice':s['notice'],
             'native_time_s':value['native']['confirmation']['metadata']['time_s'],
             'native_error':value['native']['error'],'total_CPU_percent_per_logical_processor':psutil.cpu_percent(percpu=True),
             'available_RAM_bytes':memory.available,'RAM_used_percent':memory.percent,
             'product_processes':[{'pid':p.pid,'CPU_percent_of_one_processor':p.cpu_percent(),
                                   'RSS_bytes':p.memory_info().rss,'threads':p.num_threads(),
                                   'worker_descendant':p.pid in {w.pid for w in workers}} for p in product.values() if p.is_running()]}
        report['samples'].append(row)
        assert not s['paused'] and s['notice'] is None,row
        if (i+1)%5==0:
            persist();print(json.dumps(row),flush=True)
    report.update(final=state(),wall_interval_s=time.perf_counter()-began,completed=True)
finally:
    command('pause')
    if entered:
        request=urllib.request.Request('http://127.0.0.1:4700/api/em-cloud/leave',data=b'{}',headers={'Content-Type':'application/json'})
        json.load(urllib.request.urlopen(request,timeout=15))
    report['owner_pointer_preserved']=(ROOT/'user/sessions/latest.json').read_bytes()==owner
    persist()
print(json.dumps({'report':str(destination),'completed':report['completed']}),flush=True)
