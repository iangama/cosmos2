"""Bounded isolated calculated-zone worker; newest summary, full curves on request."""
from pathlib import Path
import argparse
import copy
import json
import queue
import sys
import threading
import uuid

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
sys.path.append(str(ROOT/'output/is4-solar-wind-product0.9.1/app'))
from is5_artifact import Run,Store,DEFAULT_VIEW,MAX_BYTES,generation,view,index,identity
from is5_solar_source import digest

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--storage',type=Path,required=True);args=parser.parse_args()
    store=Store(args.storage);commands=queue.Queue(maxsize=16)
    def reader():
        while True:
            line=sys.stdin.readline(MAX_BYTES+1)
            if not line:commands.put({'_eof':True});return
            if len(line)>MAX_BYTES:
                while line and not line.endswith('\n'):line=sys.stdin.readline(MAX_BYTES+1)
                commands.put({'id':None,'command':'invalid'});continue
            try:commands.put(json.loads(line,object_pairs_hook=Store.unique))
            except ValueError:commands.put({'id':None,'command':'invalid'})
    threading.Thread(target=reader,daemon=True).start()
    worker_id=uuid.uuid4().hex;token=uuid.uuid4().hex;revision=0;sequence=0;run=None;preferences=copy.deepcopy(DEFAULT_VIEW);run_sha=None;parent=None;branches=store.catalog()
    def state():
        nonlocal sequence
        sequence+=1
        return dict(worker_id=worker_id,sequence=sequence,artifact_id=None if run is None else run.id,edit_token=token,revision=revision,artifact_sha256=run_sha,
            source=None if run is None else copy.deepcopy(run._payload['source']),configuration=None if run is None else copy.deepcopy(run._payload['configuration']),
            sample=None if run is None else run.sample(preferences['selected_index']),view=copy.deepcopy(preferences),checkpoint_available=store.path.exists(),branches=copy.deepcopy(branches),branch_parent=parent,
            execution='Calculated241knots; changing selected index is reading/playback only, not realtime nuclear integration.')
    def expect(request):
        expected=dict(worker_id=worker_id,artifact_id=None if run is None else run.id,edit_token=token,revision=revision)
        guard=request.get('guard')
        if not isinstance(guard,dict) or set(guard)!=set(expected) or type(guard.get('revision')) is not int or guard!=expected:raise ValueError('Nuclear worker/artifact/token/revision changed')
    def emit(value):print(json.dumps(value,separators=(',',':'),allow_nan=False),flush=True)
    emit(dict(type='ready',protocol=1,kind='is5_calculated_solar_zone',scientific_generation=generation(),state=state()))
    while True:
        request=commands.get()
        if isinstance(request,dict) and request.get('_eof'):return
        request_id=request.get('id') if isinstance(request,dict) else None
        command=request.get('command') if isinstance(request,dict) else None
        try:
            if type(request_id) is not int or not 1<=request_id<=2**31-1:raise ValueError('Positive request id required')
            extras={'create':{'source_phase','configuration'},'configure':{'configuration'},'sample':{'index'},'set_view':{'view'},'branch_create':{'name','parent'},'branch_load':{'branch_id'}}
            names={'state','quit','create','configure','sample','set_view','save','load','branch_create','branch_load','get_result','export','restart'}
            if command not in names or set(request)!={'id','command'}|extras.get(command,set())|({'guard'} if command not in ['state','quit'] else set()):raise ValueError('Exact nuclear command schema required')
            if command=='quit':emit(dict(type='ack',id=request_id,command=command));return
            result=None
            if command!='state':expect(request)
            if command in ['create','configure','restart']:
                if command!='create' and run is None:raise ValueError('Create or restore a solar zone first')
                phase=request['source_phase'] if command=='create' else run._payload['source_phase']
                config=run._payload['configuration'] if command=='restart' else request['configuration']
                candidate=Run.create(phase,config)
                run=candidate;token=uuid.uuid4().hex;revision+=1;run_sha=digest(run._payload);preferences={**preferences,'selected_index':0}
                if command=='create':parent=None
            elif command in ['load','branch_load']:
                branch_id=request.get('branch_id');candidate,restored,branch=store.load(branch_id)
                run=candidate;preferences=restored;token=uuid.uuid4().hex;revision+=1;run_sha=digest(run._payload);parent=branch_id
            elif command not in ['state','quit']:
                if run is None:raise ValueError('Create or restore a solar zone first')
                if command=='sample':preferences['selected_index']=index(request['index'])
                elif command=='set_view':preferences=view(request['view'])
                elif command=='save':result=store.save(run,preferences)
                elif command=='branch_create':
                    result=store.save(run,preferences,name=request['name'],parent=request['parent']);parent=result['branch']['id'];branches=store.catalog()
                elif command=='get_result':result=run.payload
                elif command=='export':
                    folder=store.folder/'exports';folder.mkdir(exist_ok=True);path=folder/(uuid.uuid4().hex+'.json');payload=dict(kind='is5_solar_export',run=run.payload,view=copy.deepcopy(preferences),sample=run.sample(preferences['selected_index']))
                    record={**payload,'record_sha256':digest(payload)};Store.atomic(path,record);result=dict(path=str(path),record_sha256=record['record_sha256'])
            emit(dict(type='ack',id=request_id,command=command,result=result,state=state()))
        except Exception as error:emit(dict(type='error',id=request_id,command=command,message=str(error),state=state()))

if __name__=='__main__':main()
