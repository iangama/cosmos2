"""Responsive protocol owner; heavy recomputation is a cancellable child process."""
from pathlib import Path
from collections import deque
import argparse
import copy
import json
import math
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from is5_compression_artifact import Run,Store,DEFAULT_VIEW,MAX_BYTES,generation,view,index
from is5_solar_source import digest
from is5_compression_process import python_argv,CalculationJob

CALCULATION_BUDGET_S=600.


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--storage',type=Path,required=True);args=parser.parse_args()
    store=Store(args.storage);work=store.folder/'_work';work.mkdir(exist_ok=True)
    commands=queue.Queue(maxsize=16)
    def reader():
        while True:
            line=sys.stdin.readline(MAX_BYTES+1)
            if not line:commands.put({'_eof':True});return
            if len(line.encode('utf-8'))>MAX_BYTES:
                while line and not line.endswith('\n'):line=sys.stdin.readline(MAX_BYTES+1)
                commands.put({'id':None,'command':'invalid'});continue
            try:commands.put(json.loads(line,object_pairs_hook=Store.unique))
            except ValueError:commands.put({'id':None,'command':'invalid'})
    threading.Thread(target=reader,daemon=True).start()
    worker_id=uuid.uuid4().hex;token=uuid.uuid4().hex;revision=sequence=0
    run=None;preferences=copy.deepcopy(DEFAULT_VIEW);run_sha=None;parent=None;pending=None
    branches=store.catalog()
    def state():
        nonlocal sequence
        sequence+=1
        compute=None if pending is None else dict(request_id=pending['request']['id'],
            process_id=pending['process'].pid,elapsed_wall_s=time.monotonic()-pending['started'],budget_s=pending['budget'])
        return dict(worker_id=worker_id,sequence=sequence,artifact_id=None if run is None else run.id,
            edit_token=token,revision=revision,artifact_sha256=run_sha,
            source=None if run is None else copy.deepcopy(run._payload['source']),
            configuration=None if run is None else copy.deepcopy(run._payload['configuration']),
            sample=None if run is None else run.sample(preferences['selected_index']),view=copy.deepcopy(preferences),
            checkpoint_available=store.path.exists(),branches=copy.deepcopy(branches),branch_parent=parent,
            busy=pending is not None,calculation=compute,
            execution='241 calculated knots; sample selection/playback is not realtime nuclear integration.')
    def emit(value):
        text=json.dumps(value,separators=(',',':'),allow_nan=False)
        if len(text.encode('utf-8'))>MAX_BYTES:raise ValueError('Coulomb publication exceeds16MiB')
        print(text,flush=True)
    def expect(request):
        wanted=dict(worker_id=worker_id,artifact_id=None if run is None else run.id,edit_token=token,revision=revision)
        guard=request.get('guard')
        if not isinstance(guard,dict) or set(guard)!=set(wanted) or type(guard.get('revision')) is not int or guard!=wanted:
            raise ValueError('Coulomb worker/artifact/token/revision changed')
    def cleanup(task,terminate=False):
        process=task['process']
        if terminate and process.poll() is None:
            process.terminate()
            try:process.wait(3)
            except subprocess.TimeoutExpired:process.kill();process.wait(3)
        if process.poll() is None:raise RuntimeError('Calculation still running during cleanup')
        task['job'].close()
        task['error_thread'].join(1)
        process.stderr.close()
        paths=[task['input'],task['output'],*work.glob(task['output'].name+'.*.tmp')]
        for path in paths:
            until=time.monotonic()+2
            while True:
                try:path.unlink(missing_ok=True);break
                except PermissionError:
                    if time.monotonic()>=until:raise
                    time.sleep(.02)
    def start(request,payload,restored_view=None,branch=None):
        nonlocal pending
        budget=request.get('budget_s',CALCULATION_BUDGET_S)
        if type(budget) not in (int,float) or not math.isfinite(budget) or not .01<=budget<=CALCULATION_BUDGET_S:
            raise ValueError('Calculation budget must be0.01..600s')
        expected_generation=generation()
        path=work/(uuid.uuid4().hex+'.json')
        Store.atomic(path,payload)
        job=CalculationJob();process=None
        try:
            process=subprocess.Popen(python_argv(Path(__file__).with_name('is5_compression_calculate.py'),
                ['--request',str(path),'--parent-pid',str(os.getpid())]),stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,encoding='utf-8')
            job.assign(process)
        except Exception:
            job.close()
            if process is not None:
                if process.poll() is None:process.terminate();process.wait(5)
                process.stderr.close()
            path.unlink(missing_ok=True)
            raise
        errors=deque(maxlen=20)
        def drain():
            for line in process.stderr:errors.append(line.rstrip()[:1000])
        error_thread=threading.Thread(target=drain,daemon=True);error_thread.start()
        pending=dict(request=copy.deepcopy(request),process=process,job=job,input=path,output=path.with_suffix('.result.json'),
            started=time.monotonic(),budget=budget,errors=errors,error_thread=error_thread,
            restored_view=restored_view,branch=branch,expected_generation=expected_generation,
            expected_restore=payload.get('payload'))
    emit(dict(type='ready',protocol=2,kind='is5_compression_calculated_solar_zone',scientific_generation=generation(),state=state()))
    try:
        while True:
            if pending is not None:
                task=pending
                expired=time.monotonic()-task['started']>task['budget']
                if expired or task['process'].poll() is not None:
                    request=task['request'];error=None;candidate=None
                    try:
                        if expired:
                            cleanup(task,terminate=True)
                            raise TimeoutError('Calculation budget exceeded; previous artifact preserved')
                        if task['process'].returncode!=0:
                            raise RuntimeError('Calculation process failed: '+' '.join(task['errors']))
                        if task['output'].stat().st_size>MAX_BYTES:raise ValueError('Calculation result exceeds16MiB')
                        answer=json.loads(task['output'].read_text(encoding='utf-8'),object_pairs_hook=Store.unique)
                        if not isinstance(answer,dict) or answer.get('ok') is not True:
                            raise ValueError(answer.get('error','Invalid calculation result') if isinstance(answer,dict) else 'Invalid calculation result')
                        if set(answer)!={'ok','run','process_id'} or answer['process_id']!=task['process'].pid or answer['run']['scientific_generation']!=task['expected_generation'] or generation()!=task['expected_generation']:
                            raise ValueError('Calculation scientific generation differs')
                        if task['expected_restore'] is not None and digest(answer['run'])!=digest(task['expected_restore']):
                            raise ValueError('Recomputed restore differs')
                        candidate=Run();candidate._payload=answer['run']
                    except Exception as ex:error=str(ex)
                    finally:
                        try:cleanup(task,terminate=True)
                        except Exception as ex:error='Calculation cleanup failed: '+str(ex)
                        pending=None
                    if error is None:
                        run=candidate;token=uuid.uuid4().hex;revision+=1;run_sha=digest(run._payload)
                        if request['command'] in ['load','branch_load']:
                            preferences=task['restored_view'];parent=request.get('branch_id')
                        else:
                            preferences={**preferences,'selected_index':0}
                            if request['command']=='create':parent=None
                        emit(dict(type='ack',id=request['id'],command=request['command'],result=None,state=state()))
                    else:emit(dict(type='error',id=request['id'],command=request['command'],message=error,state=state()))
            try:request=commands.get(timeout=.025)
            except queue.Empty:continue
            if isinstance(request,dict) and request.get('_eof'):return
            request_id=request.get('id') if isinstance(request,dict) else None
            command=request.get('command') if isinstance(request,dict) else None
            try:
                if type(request_id) is not int or not 1<=request_id<=2**31-1:raise ValueError('Positive request id required')
                calculations={'create','configure','restart','load','branch_load'}
                extras={'create':{'source_phase','configuration'},'configure':{'configuration'},'sample':{'index'},
                        'set_view':{'view'},'branch_create':{'name','parent'},'branch_load':{'branch_id'}}
                names={'state','quit','create','configure','sample','set_view','save','load','branch_create','branch_load','get_result','export','restart'}
                expected={'id','command'}|extras.get(command,set())|({'guard'} if command not in ['state','quit'] else set())
                actual_fields=set(request)-({'budget_s'} if command in calculations else set())
                if command not in names or actual_fields!=expected:raise ValueError('Exact Coulomb command schema required')
                if command=='quit':
                    if pending is not None:
                        task=pending;cleanup(task,terminate=True);pending=None
                        emit(dict(type='error',id=task['request']['id'],command=task['request']['command'],message='Calculation cancelled by graceful shutdown',state=state()))
                    emit(dict(type='ack',id=request_id,command='quit',result=None,state=state()));return
                if command!='state':expect(request)
                if pending is not None and command!='state':raise ValueError('Calculation in progress; previous artifact preserved')
                result=None
                if command in ['create','configure','restart']:
                    if command!='create' and run is None:raise ValueError('Create or restore a Coulomb zone first')
                    phase=request['source_phase'] if command=='create' else run._payload['source_phase']
                    config=run._payload['configuration'] if command=='restart' else request['configuration']
                    start(request,dict(action='create',source_phase=phase,configuration=config));continue
                elif command in ['load','branch_load']:
                    record=store._read(request.get('branch_id'))
                    start(request,dict(action='restore',payload=record['run']),view(record['view']),record['branch']);continue
                elif command not in ['state','quit']:
                    if run is None:raise ValueError('Create or restore a Coulomb zone first')
                    if command=='sample':preferences['selected_index']=index(request['index'])
                    elif command=='set_view':preferences=view(request['view'])
                    elif command=='save':result=store.save(run,preferences)
                    elif command=='branch_create':
                        result=store.save(run,preferences,name=request['name'],parent=request['parent']);parent=result['branch']['id'];branches=store.catalog()
                    elif command=='get_result':result=run.payload
                    elif command=='export':
                        folder=store.folder/'exports';folder.mkdir(exist_ok=True);path=folder/(uuid.uuid4().hex+'.json')
                        payload=dict(kind='is5_compression_solar_export',run=run.payload,view=copy.deepcopy(preferences),sample=run.sample(preferences['selected_index']))
                        record={**payload,'record_sha256':digest(payload)};Store.atomic(path,record)
                        result=dict(path=str(path),record_sha256=record['record_sha256'])
                emit(dict(type='ack',id=request_id,command=command,result=result,state=state()))
            except Exception as error:emit(dict(type='error',id=request_id,command=command,message=str(error),state=state()))
    finally:
        if pending is not None:cleanup(pending,terminate=True)


if __name__=='__main__':main()
