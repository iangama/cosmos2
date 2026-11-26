"""Actual isolated worker batches, source snapshots and injected stale replies."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import math
import queue
import subprocess
import sys
import threading
import uuid
ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/c212-em-potential-staging';EM=ROOT/'output/c212-em-v04-product/em'
sys.path.insert(0,str(STAGE));from em_slice import sample_slice
# Staged worker storage uses its own fixed base under its candidate parent.
storage=EM.parent/'c212-em-worker'/('potential-'+uuid.uuid4().hex)
worker=subprocess.Popen([sys.executable,'-u',str(EM/'em_worker.py'),'--storage',str(storage)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
messages=queue.Queue();latest=None;serial=0;lock=threading.RLock()
def reader():
    for line in worker.stdout:messages.put(json.loads(line))
    messages.put({'type':'closed'})
threading.Thread(target=reader,daemon=True).start()
def read():
    global latest
    v=messages.get(timeout=10);assert v['type']!='closed'
    if v['type']=='snapshot':latest=v
    return v
def call(value):
    global serial
    serial+=1;worker.stdin.write(json.dumps({**value,'id':serial},allow_nan=False)+'\n');worker.stdin.flush()
    while True:
        reply=read()
        if reply.get('id')==serial:
            if reply['type']!='ack':raise ValueError(reply)
            return reply
def guard():return {k:latest[k] for k in ('system_id','edit_token','revision','frame')}|{'expected_time_s':latest['time_s']}
owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes();cases=[];rejections=[]
try:
    assert read()['type']=='ready'
    while latest is None:read()
    axis=[-2+i/4 for i in range(17)];grid={'x_m':axis,'y_m':axis,'z_m':.35}
    for preset in ('electric','coulomb'):
        call({'command':'load_preset',**guard(),'preset':preset});before=deepcopy(latest)
        layer=sample_slice(lambda:latest,call,lock,grid,[-.5,0.,.5])
        assert latest['experiment']==before['experiment'] and latest['editor']==before['editor'] and latest['paused']
        assert len(layer['measurement']['samples'])==289 and [b['samples'] for b in layer['batch_protocol']['batches']]==[128,128,33]
        assert layer['source_snapshot']==before['experiment'] and layer['scientific_generation']==before['scientific_generation']
        # Query selected non-grid control points independently as a sanity check
        # that the merged arrays carry the actual worker readings, in order.
        for index in (0,127,128,255,288):
            sample=layer['measurement']['samples'][index]
            assert sample==call({'command':'probe',**guard(),'position_m':sample['position_m']})['result']
        cases.append({'preset':preset,'sample_count':289,'batches':[128,128,33],'wall_ms':layer['batch_protocol']['elapsed_wall_ms'],'science_editor_unchanged':True})
    before=deepcopy(latest)
    # Untrusted/broken batch callbacks must never yield an apparently complete layer.
    for key,value in [('time_s',latest['time_s']+1),('revision',latest['revision']+1),('frame','OTHER'),('system_id','other'),('edit_token','other')]:
        def stale(request,key=key,value=value):
            ack=call(request);ack['result'][key]=value;return ack
        try:sample_slice(lambda:latest,stale,lock,grid,[0.])
        except ValueError:rejections.append('reply '+key)
        else:raise AssertionError('Stale reply accepted')
        assert latest['experiment']==before['experiment'] and latest['editor']==before['editor']
    for kind in ('position','count','live_state','budget'):
        def corrupt(request):
            ack=call(request)
            if kind=='position':ack['result']['samples'].reverse()
            elif kind=='count':ack['result']['samples'].pop()
            return ack
        reads=0
        def state_reader():
            global reads
            reads+=1;s=deepcopy(latest)
            if kind=='live_state' and reads>2:s['paused']=False
            return s
        try:sample_slice(state_reader,corrupt,lock,grid,[0.],budget_s=1e-12 if kind=='budget' else 2.)
        except (ValueError,TimeoutError):rejections.append(kind)
        else:raise AssertionError('Corrupt/expired batch accepted')
    call({'command':'resume'})
    try:sample_slice(lambda:latest,call,lock,grid,[0.])
    except ValueError:rejections.append('running worker')
    else:raise AssertionError('Running slice accepted')
    call({'command':'pause'});call({'command':'quit'});worker.wait(timeout=5)
    assert worker.returncode==0 and not worker.stderr.read() and owner.read_bytes()==original
    report={'status':'isolated_equipotential_real_worker_bounded_same_snapshot_batches_verified',
            'cases':cases,'rejected_without_publishing_partial_layer':rejections,'clean_exit':True,'owner_pointer_preserved':True,'scientific_generation':latest['scientific_generation'],
            'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (STAGE/'em_slice.py',STAGE/'em_potential.py',EM/'em_worker.py',Path(__file__))},
            'scope':'Isolated worker reads and geometry. No native/CEF integration, persistence, full128-source65x65 cost or final potential experience acceptance.'}
    (ROOT/'evidence/em-potential-worker-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
finally:
    if worker.poll() is None:worker.terminate();worker.wait(timeout=5)
    assert owner.read_bytes()==original
