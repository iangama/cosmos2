"""Isolated static-body particle actor; bounded input and integration quanta."""
from pathlib import Path
from dataclasses import asdict
import argparse
import copy
import hashlib
import json
import math
import queue
import sys
import threading
import time
import uuid

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
sys.path.insert(0,str(ROOT/'output/is3-body-points-product/app'))
from is4_experiment import Experiment,generation
from is4_values import scalar

FRAME='is4_frozen_body_snapshot_axes_m'
GUARD={'worker_id','experiment_id','edit_token','revision','expected_time_s','frame'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--storage',type=Path,required=True);args=parser.parse_args()
    storage=args.storage.resolve()
    if not storage.is_relative_to((ROOT/'output').resolve()):raise ValueError('IS4 worker storage must remain under output')
    commands=queue.Queue(maxsize=32)
    def reader():
        while True:
            line=sys.stdin.readline(4*1024*1024+1)
            if not line:commands.put({'_eof':True});return
            if len(line)>4*1024*1024:
                while line and not line.endswith('\n'):line=sys.stdin.readline(4*1024*1024+1)
                commands.put({'command':'invalid'});continue
            try:
                value=json.loads(line);commands.put(value if isinstance(value,dict) else {'command':'invalid'})
            except ValueError:commands.put({'command':'invalid'})
    threading.Thread(target=reader,daemon=True).start()
    experiment=None;paused=True;worker_id=uuid.uuid4().hex;sequence=0;notice=None;rate=1.;effective=0.
    anchor_wall=time.perf_counter();anchor_time=0.;next_publish=anchor_wall
    quantum_max_ms=0.;quantum_count=0
    def emit(value):print(json.dumps(value,separators=(',',':'),allow_nan=False),flush=True)
    def state():
        nonlocal sequence
        sequence+=1
        value={'worker_id':worker_id,'sequence':sequence,'frame':FRAME,'paused':paused,'notice':notice,
            'requested_particle_s_per_wall_s':rate,'effective_particle_s_per_wall_s':effective,
            'execution':{'quantum_step_cap':16,'between_steps_budget_ms':20,'observed_max_quantum_ms':quantum_max_ms,'quanta':quantum_count},
            'experiment':None}
        if experiment is not None:
            reading=experiment.source_reading;trail=experiment.trail;stride=max(1,math.ceil((len(trail)-1)/128))
            recent=trail[::stride]
            if recent[-1]!=trail[-1]:recent=[*recent,trail[-1]]
            earth=reading['kind']=='scene_Earth_IGRF14_passive_point'
            value['experiment']={'id':experiment.id,'edit_token':experiment.edit_token,'revision':experiment.revision,
                'step_index':experiment.step_index,'phase':asdict(experiment.phase),
                'parameters':copy.deepcopy(experiment.parameters),'controls':dict(experiment.controls),'termination':copy.deepcopy(experiment.termination),
                'snapshot_configuration_sha256':experiment.model.configuration_sha256,'scientific_generation':copy.deepcopy(experiment.scientific_generation),
                'snapshot_epoch':copy.deepcopy(reading['epoch']),'scene_time':reading['time'],'source_body_id':reading['body_id'],
                'model':reading['provenance']['model'],'degree':13 if earth else reading['degree'],
                'model_to_J2000':copy.deepcopy(reading['ITRF93_to_J2000' if earth else 'SystemIII_to_J2000']),
                'J2000_to_render':copy.deepcopy(reading['J2000_to_render']),
                'body_center_inertial_m':list(reading['earth_center_inertial_m' if earth else 'jupiter_center_inertial_m']),
                'recent_trajectory':copy.deepcopy(recent),'trajectory_policy':'At most129 actual samples from the most recent513 states; not a full history.',
                'clock':'independent_particle_seconds; source epoch/orientation/centers frozen','parameter_origin':'explicit_SI_test_parameters',
                'native_confirmation':None}
        return value
    def expect(request,pausing=False):
        guard=request.get('guard')
        if not isinstance(guard,dict) or set(guard)!=GUARD or guard['worker_id']!=worker_id or guard['frame']!=FRAME:raise ValueError('Worker/frame guard differs')
        if not paused and not pausing:raise ValueError('Pause the particle experiment first')
        if experiment is None:
            if any(guard[k] is not None for k in ['experiment_id','edit_token','revision','expected_time_s']):raise ValueError('No active particle experiment')
        else:
            if guard['experiment_id']!=experiment.id or guard['edit_token']!=experiment.edit_token or type(guard['revision']) is not int or guard['revision']!=experiment.revision:raise ValueError('Particle identity/revision differs')
            confirmed=scalar(guard['expected_time_s'])
            if not (0<=confirmed<=experiment.phase.time_s if pausing else confirmed==experiment.phase.time_s):raise ValueError('Particle time guard differs')
    emit({'type':'ready','protocol':1,'worker_id':worker_id,'frame':FRAME,'storage':str(storage),'paused':True,
        'scientific_generation':generation(),'worker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    emit({'type':'snapshot','state':state()})
    while True:
        now=time.perf_counter()
        timeout=max(0.,next_publish-now) if paused else 0.
        try:request=commands.get(timeout=timeout)
        except queue.Empty:
            request=None
            if not paused and experiment is not None:
                began=time.perf_counter();target=anchor_time+(began-anchor_wall)*rate;advanced=0
                try:
                    for _ in range(16):
                        if not commands.empty() or time.perf_counter()-began>=.02 or experiment.phase.time_s+experiment.parameters['dt_s']>target:break
                        result=experiment.advance_steps(1);advanced+=result['accepted_steps']
                        if result['termination']:
                            paused=True;notice=result['termination'];break
                except (ValueError,ArithmeticError,OSError) as error:
                    paused=True;notice={'kind':'integration_error','message':str(error),'time_s':experiment.phase.time_s}
                if advanced:quantum_count+=1;quantum_max_ms=max(quantum_max_ms,(time.perf_counter()-began)*1000)
                elapsed=time.perf_counter()-anchor_wall;effective=0. if paused else (experiment.phase.time_s-anchor_time)/elapsed if elapsed else 0.
                if not advanced and not paused:
                    try:request=commands.get(timeout=min(.01,max(.0005,experiment.parameters['dt_s']/rate)))
                    except queue.Empty:pass
            if time.perf_counter()>=next_publish:
                emit({'type':'snapshot','state':state()});next_publish=time.perf_counter()+.05
            if request is None:continue
        if request.get('_eof'):return
        began=time.perf_counter();name=request.get('command');identifier=request.get('id');result=None
        try:
            if type(identifier) is not int or not 1<=identifier<=2**31-1:raise ValueError('Positive integer request id required')
            extras={'create':{'source_phase','source_reading','parameters','controls'},'advance':{'steps'},'set_controls':{'controls'},'set_rate':{'value'}}
            guarded={'create','pause','resume','advance','set_controls','set_rate','save','load','sample','export_payload'}
            allowed={'id','command'}|extras.get(name,set())|({'guard'} if name in guarded else set())
            if set(request)!=allowed:raise ValueError('Exact command fields required')
            if name=='quit':emit({'type':'ack','id':identifier,'command':name});return
            if name=='state':pass
            elif name in guarded:
                expect(request,pausing=name=='pause')
                if name=='create':
                    candidate=Experiment(storage,request['source_phase'],request['source_reading'],request['parameters'],request['controls'])
                    experiment=candidate;paused=True;notice=None;effective=0.;rate=candidate.execution_preferences['particle_s_per_wall_s']
                elif name=='load':
                    candidate=Experiment.load(storage);experiment=candidate;paused=True;notice=None;effective=0.;rate=candidate.execution_preferences['particle_s_per_wall_s']
                elif name=='pause':paused=True;effective=0.
                elif name=='resume':
                    if experiment is None or experiment.termination is not None:raise ValueError('Create a valid resumable particle experiment')
                    paused=False;notice=None;effective=0.;anchor_wall=time.perf_counter();anchor_time=experiment.phase.time_s
                elif name=='set_rate':
                    if experiment is None:raise ValueError('Create a particle experiment first')
                    value=scalar(request['value'])
                    if not 1e-15<=value<=1e6:raise ValueError('Particle playback rate outside declared SI range')
                    rate=value;experiment.execution_preferences={'particle_s_per_wall_s':value};effective=0.;anchor_wall=time.perf_counter();anchor_time=experiment.phase.time_s
                else:
                    if experiment is None:raise ValueError('Create a particle experiment first')
                    if name=='advance':result=experiment.advance_steps(request['steps'])
                    elif name=='set_controls':experiment.set_controls(request['controls']);notice=None
                    elif name=='save':result=experiment.save()
                    elif name=='sample':result=experiment.sample()
                    elif name=='export_payload':result=experiment.payload()
            else:raise ValueError('Unknown IS4 command')
            emit({'type':'ack','id':identifier,'command':name,'state':state(),'elapsed_ms':(time.perf_counter()-began)*1000,**({'result':result} if result is not None else {})})
            next_publish=time.perf_counter()+.05
        except (ValueError,TypeError,KeyError,OSError,ArithmeticError) as error:
            emit({'type':'error','id':identifier,'command':name,'message':str(error),'state':state(),'elapsed_ms':(time.perf_counter()-began)*1000})


if __name__=='__main__':main()
