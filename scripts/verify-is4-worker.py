"""Real IS4 subprocess, guarded commands, pacing, exact reload/new process and domain stop."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import os
import queue
import struct
import subprocess
import sys
import threading
import time
import traceback
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/is4-body-particle-staging';APP=ROOT/'output/is3-body-points-product/app'
sys.path[:0]=[str(STAGE),str(APP)]
from is4_experiment import Experiment
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def comparable(payload):
    result=copy.deepcopy(payload);result.pop('edit_token');return json.loads(json.dumps(result))


class Client:
    def __init__(self,storage,folder,name):
        self.serial=0;self.last=None;self.queue=queue.Queue(maxsize=256);self.latencies=[]
        self.log=(folder/(name+'-protocol.jsonl')).open('w',encoding='utf-8')
        self.stderr=(folder/(name+'-stderr.log')).open('w',encoding='utf-8')
        self.process=subprocess.Popen([sys.executable,'-Xutf8','-u',str(STAGE/'is4_worker.py'),'--storage',str(storage)],
            cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.stderr,text=True,encoding='utf-8',bufsize=1)
        def reader():
            try:
                for line in self.process.stdout:
                    self.log.write(line);self.log.flush();self.queue.put(json.loads(line))
            finally:self.queue.put({'type':'eof'})
        self.thread=threading.Thread(target=reader,daemon=True);self.thread.start()
        self.ready=self.receive(lambda value:value.get('type')=='ready',15.)
        assert self.ready['protocol']==1 and self.ready['worker_sha256']==sha(STAGE/'is4_worker.py')
        self.receive(lambda value:value.get('type')=='snapshot',5.)
    def receive(self,predicate,timeout):
        deadline=time.monotonic()+timeout
        while True:
            value=self.queue.get(timeout=max(.001,deadline-time.monotonic()))
            if value.get('type')=='eof':raise RuntimeError('Worker exited before expected message')
            if value.get('state') is not None:self.last=value['state']
            if predicate(value):return value
            if time.monotonic()>deadline:raise TimeoutError('Worker response deadline')
    def guard(self):
        value=self.last;experiment=value['experiment']
        return {'worker_id':value['worker_id'],'experiment_id':None if experiment is None else experiment['id'],
            'edit_token':None if experiment is None else experiment['edit_token'],'revision':None if experiment is None else experiment['revision'],
            'expected_time_s':None if experiment is None else experiment['phase']['time_s'],'frame':value['frame']}
    def call(self,name,extra=None,guard=None,error=False):
        self.serial+=1;request={'id':self.serial,'command':name,**(extra or {})}
        if name not in ['state','quit']:request['guard']=self.guard() if guard is None else guard
        began=time.perf_counter();self.process.stdin.write(json.dumps(request)+'\n');self.process.stdin.flush()
        response=self.receive(lambda v:v.get('id')==self.serial and v.get('type') in ['ack','error'],15.)
        self.latencies.append({'command':name,'wall_ms':(time.perf_counter()-began)*1000,'worker_ms':response.get('elapsed_ms')})
        assert response['type']==('error' if error else 'ack'),response
        return response
    def payload(self):return self.call('export_payload')['result']
    def advance(self,count):
        while count:
            n=min(256,count);response=self.call('advance',{'steps':n});assert response['result']['accepted_steps']==n;count-=n
    def close(self):
        if self.process.poll() is None:
            self.call('quit');self.process.stdin.close();assert self.process.wait(timeout=8)==0
        self.thread.join(timeout=2);self.stderr.close();self.log.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    folder=ROOT/('output/is4-worker-'+args.label);receipt=ROOT/('evidence/is4-worker-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve worker evidence.')
    folder.mkdir();fixture=ROOT/'output/is4-body-snapshot-20261025b/JRM33-13.json'
    data=json.loads(fixture.read_text(encoding='utf-8'));constants=json.loads((STAGE/'constants.json').read_text(encoding='utf-8'))
    p,r=data['phase'],data['reading'];b=np.array(r['field_SystemIII_T']);axis=np.eye(3)[int(np.argmin(abs(b)))];v=np.cross(b,axis);v=v/np.linalg.norm(v)*1e6
    params={'charge_C':-constants['elementary_charge_C']['value'],'mass_kg':constants['electron_mass_kg']['value'],
        'dt_s':float(2*math.pi/(constants['elementary_charge_C']['value']/constants['electron_mass_kg']['value']*np.linalg.norm(b))/800),
        'initial_position_m':r['point_SystemIII_m'],'initial_velocity_m_s':v.tolist()};flags={'electric':True,'magnetic':True,'gravity':True}
    files=[*STAGE.glob('*.py'),STAGE/'constants.json',Path(__file__),fixture,ROOT/'IS-4-WORKER-CONTRATO.md']
    hashes={path.relative_to(ROOT).as_posix():sha(path) for path in files};owner=sha(ROOT/'user/sessions/latest.json')
    with zipfile.ZipFile(folder/'executed-sources-and-fixtures.zip','w',zipfile.ZIP_DEFLATED) as z:
        for path in files:z.write(path,path.relative_to(ROOT).as_posix())
    report={'schema':1,'accepted':False,'completed':False,'source_sha256':hashes,'checks':[]};clients=[]
    try:
        storage=folder/'storage';client=Client(storage,folder,'first');clients.append(client)
        assert client.last['paused'] and client.last['experiment'] is None
        client.call('create',{'source_phase':p,'source_reading':r,'parameters':params,'controls':flags})
        client.call('set_rate',{'value':params['dt_s']*200})
        client.call('resume');time.sleep(.12)
        client.call('set_controls',{'controls':{**flags,'gravity':False}},error=True)
        response=client.call('pause');pause_ms=client.latencies[-1]['wall_ms'];assert pause_ms<=250.,pause_ms
        assert client.last['paused'] and client.last['experiment']['step_index']>0 and client.last['experiment']['scene_time']==p['time']
        assert client.last['execution']['observed_max_quantum_ms']<=50.
        assert len(client.last['experiment']['recent_trajectory'])<=129 and client.last['experiment']['native_confirmation'] is None
        report['checks'].append({'running_pause':True,'pause_wall_ms':pause_ms,'execution':client.last['execution'],'independent_orbital_clock':True})
        before=client.payload();refusals=0
        for changes in [{'edit_token':'stale'},{'frame':'other'},{'revision':True},{'expected_time_s':True}]:
            client.call('advance',{'steps':1},guard={**client.guard(),**changes},error=True);refusals+=1
            assert comparable(client.payload())==comparable(before)
        for value in [True,0,257]:
            client.call('advance',{'steps':value},error=True);refusals+=1;assert comparable(client.payload())==comparable(before)
        for value in [True,0.,float('nan')]:
            client.call('set_rate',{'value':value},error=True);refusals+=1;assert comparable(client.payload())==comparable(before)
        bad_phase=copy.deepcopy(p);bad_phase['paused']=False
        client.call('create',{'source_phase':bad_phase,'source_reading':r,'parameters':params,'controls':flags},error=True);refusals+=1
        assert comparable(client.payload())==comparable(before)
        client.advance(123);client.call('save');saved=client.payload();old_token=client.last['experiment']['edit_token']
        requested=client.last['requested_particle_s_per_wall_s'];old_guard=client.guard()
        direct=Experiment.load(storage);advance_left=777
        while advance_left:
            n=min(256,advance_left);direct.advance_steps(n);advance_left-=n
        client.advance(777);future=client.payload();assert comparable(future)==comparable(direct.payload())
        client.call('load');assert client.last['experiment']['edit_token']!=old_token
        assert client.last['requested_particle_s_per_wall_s']==requested and client.last['paused']
        assert comparable(client.payload())==comparable(saved)
        client.call('advance',{'steps':1},guard=old_guard,error=True);refusals+=1
        client.advance(777);assert comparable(client.payload())==comparable(future)
        first_pid=client.process.pid;client.close();clients.remove(client)
        reopened=Client(storage,folder,'reopened');clients.append(reopened);assert reopened.process.pid!=first_pid
        reopened.call('load');assert reopened.last['paused'] and reopened.last['requested_particle_s_per_wall_s']==requested
        reopened.advance(777);assert comparable(reopened.payload())==comparable(future)
        report['checks'].append({'checkpoint_reload_and_new_worker_future_exact':True,'first_pid':first_pid,'reopened_pid':reopened.process.pid,'nondefault_rate_preserved':requested})
        stable=reopened.payload();manifest=storage/'latest.json';bytes_before=manifest.read_bytes();manifest.write_text('{}\n',encoding='utf-8')
        reopened.call('load',error=True);refusals+=1;assert comparable(reopened.payload())==comparable(stable);manifest.write_bytes(bytes_before)
        sample_before=reopened.call('sample')['result'];phase_before=copy.deepcopy(reopened.last['experiment']['phase'])
        reopened.call('set_controls',{'controls':{**flags,'gravity':False}})
        sample_after=reopened.call('sample')['result']
        assert phase_before==reopened.last['experiment']['phase'] and sample_before['field']==sample_after['field']
        assert sample_after['reference_time_s']==sample_after['phase']['time_s'] and sample_after['gravity_work_J']==0.
        report['checks'].append({'physical_control_and_frozen_field_separate':True,'control_reference_reset':True,'transactional_refusals':refusals})
        edge=copy.deepcopy(params);edge.update(charge_C=0.,dt_s=1.,initial_position_m=[19.999*71492000.,0.,0.],initial_velocity_m_s=[1e6,0.,0.])
        reopened.call('create',{'source_phase':p,'source_reading':r,'parameters':edge,'controls':flags});initial_edge=copy.deepcopy(reopened.last['experiment']['phase'])
        reopened.call('resume');reopened.receive(lambda value:value.get('state',{}).get('experiment',{}).get('termination') is not None,3.)
        assert reopened.last['paused'] and reopened.last['experiment']['phase']==initial_edge and reopened.last['experiment']['step_index']==0
        report['checks'].append({'domain_auto_pause_at_last_valid_phase':True})
        reopened.close();clients.remove(reopened)
        assert all(sha(ROOT/name)==value for name,value in hashes.items()) and sha(ROOT/'user/sessions/latest.json')==owner
        report.update(accepted=True,completed=True,refusals=refusals,latencies=client.latencies+reopened.latencies,owner_pointer_unchanged=True,
            scope='Real isolated worker, guarded mutation/pacing/pause, physical controls, sealed phase+rate save/load/new-process future exact, last-valid domain pause and clean quit. Native upload/render/UI/performance remain separate.')
    except Exception:report['failure']=traceback.format_exc()
    finally:
        for client in clients:
            try:client.close()
            except Exception:
                if client.process.poll() is None:client.process.terminate();client.process.wait(timeout=5)
        receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'accepted':report['accepted'],'checks':len(report['checks']),'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
