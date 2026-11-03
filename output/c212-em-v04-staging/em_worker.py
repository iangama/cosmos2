"""Isolated prototype worker, bounded commands and short fixed-step integration quanta.

Local line JSON protocol1. Parent must continuously drain stdout; output back
pressure stalls the worker rather than accumulating an unbounded output queue.
No native/UI or real-time population throughput approval follows from this file.
"""
from pathlib import Path
import argparse
import json
import queue
import re
import sys
import threading
import time
import uuid
from em_experiment import Experiment,generation
from em_presets import create,NAMES
from em_editor import FRAME,apply_intervention,apply_visual,diagnostics
from em_fields import lorentz

ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--storage',type=Path,required=True);args=parser.parse_args()
    storage=args.storage.resolve();base=(ROOT.parent/'c212-em-worker').resolve()
    if not storage.is_relative_to(base):raise ValueError('Prototype storage must remain under output/c212-em-worker')
    storage.mkdir(parents=True,exist_ok=True)
    commands=queue.Queue(maxsize=32)
    def reader():
        while True:
            line=sys.stdin.readline(8193)
            if not line:commands.put({'command':'quit'});return
            if len(line)>8192:
                while line and not line.endswith('\n'):line=sys.stdin.readline(8193)
                commands.put({'command':'invalid'});continue
            try:
                value=json.loads(line)
                commands.put(value if isinstance(value,dict) else {'command':'invalid'})
            except ValueError:commands.put({'command':'invalid'})
    threading.Thread(target=reader,daemon=True).start()
    experiment=create('helix');paused=True;revision=sequence=0;notice=None
    system_id=uuid.uuid4().hex;token=uuid.uuid4().hex;rate=1.;effective=0.
    rate_wall=time.perf_counter();rate_time=0.;next_publish=rate_wall
    scientific_generation=generation()
    def emit(value):print(json.dumps(value,separators=(',',':'),allow_nan=False),flush=True)
    def snapshot():
        emit({'type':'snapshot','sequence':sequence,'system_id':system_id,'edit_token':token,'revision':revision,'frame':FRAME,
            'paused':paused,'time_s':experiment.phase.time_s,'requested_model_s_per_wall_s':rate,
            'effective_model_s_per_wall_s':effective,'integration_quantum_steps':32,'integration_budget_ms':20,
            'notice':notice,'scientific_generation':scientific_generation,'experiment':experiment.payload(),
            'editor':experiment.editor,'diagnostics':diagnostics(experiment)})
    def expect(command,visual=False):
        if not paused and not visual:raise ValueError('Pause the EM experiment first')
        confirmed=command.get('expected_time_s')
        valid_time=type(confirmed) in (int,float) and (confirmed==experiment.phase.time_s if paused or not visual else 0<=confirmed<=experiment.phase.time_s)
        if command.get('system_id')!=system_id or command.get('edit_token')!=token or type(command.get('revision')) is not int or command['revision']!=revision or not valid_time or command.get('frame')!=FRAME:
            raise ValueError('Stale EM command; obtain the current confirmed state')
    emit({'type':'ready','protocol':1,'paused':True,'presets':NAMES,'storage':str(storage)});snapshot()
    while True:
        now=time.perf_counter()
        try:command=commands.get(timeout=max(0,next_publish-now) if paused else 0)
        except queue.Empty:
            if not paused:
                began=time.perf_counter();target=min(experiment.phase.time_s+.25*rate,rate_time+(began-rate_wall)*rate)
                try:
                    for _ in range(32):
                        if not commands.empty() or time.perf_counter()-began>=.02 or experiment.phase.time_s+experiment.dt_s>target:break
                        experiment.advance();sequence+=1
                except (ValueError,ArithmeticError) as error:paused=True;notice='Paused at last valid EM phase: '+str(error)
                elapsed=time.perf_counter()-rate_wall;effective=(experiment.phase.time_s-rate_time)/elapsed if elapsed else 0.
                if paused:effective=0.
                if experiment.phase.time_s+experiment.dt_s>target:
                    # The next full step is not due; the queue wait remains
                    # interruptible by pause and avoids busy spinning.
                    try:command=commands.get(timeout=min(.01,experiment.dt_s/rate))
                    except queue.Empty:command=None
                else:command=None
            else:command=None
            if time.perf_counter()>=next_publish:
                snapshot();next_publish=time.perf_counter()+.1
            if command is None:continue
        name=command.get('command');began=time.perf_counter();result=None
        try:
            if name=='quit':emit({'type':'ack','id':command.get('id'),'command':name});return
            if name=='pause':paused=True;effective=0.
            elif name=='resume':
                paused=False;notice=None;rate_wall=time.perf_counter();rate_time=experiment.phase.time_s
            elif name=='snapshot':pass
            elif name=='load_preset':
                expect(command);trial=create(command.get('preset'))
                experiment=trial;revision=sequence=0;system_id=uuid.uuid4().hex;token=uuid.uuid4().hex;notice=None
            elif name=='set_controls':
                expect(command)
                trial=apply_intervention(experiment,{'operation':'set_controls','controls':command.get('controls')})
                experiment=trial;revision=trial.editor['physics_revision'];notice=None
            elif name=='edit':
                expect(command);trial=apply_intervention(experiment,command.get('edit'))
                experiment=trial;revision=trial.editor['physics_revision'];notice=None
            elif name=='set_visual':
                expect(command,visual=True);apply_visual(experiment,command.get('changes'))
            elif name=='advance':
                expect(command);steps=command.get('steps')
                if type(steps) is not int or not 1<=steps<=32:raise ValueError('Manual quantum is1..32 steps')
                for _ in range(steps):experiment.advance();sequence+=1
            elif name in ('save','load'):
                expect(command)
                file=command.get('file')
                if not isinstance(file,str) or not re.fullmatch('[a-zA-Z0-9_-]{1,40}',file):raise ValueError('Bounded local checkpoint name required')
                path=storage/(file+'.json')
                if name=='save':experiment.save(path)
                else:
                    trial=Experiment.load(path);experiment=trial;revision=trial.editor['physics_revision'];sequence=0;token=uuid.uuid4().hex;system_id=uuid.uuid4().hex;notice=None
            elif name in ('probe','field_map','export_sample'):
                expect(command)
                model=experiment.model if experiment.mode=='test_particle' else experiment.model.field_snapshot(experiment.phase,command.get('exclude_id'))
                if name=='probe':result=model.evaluate(command.get('position_m'))
                elif name=='export_sample':
                    sample=model.evaluate(command.get('position_m'))
                    result={'schema':1,'kind':'cosmos2_em_SI_measurement','scientific_generation':scientific_generation,
                        'time_s':experiment.phase.time_s,'frame':FRAME,'system_id':system_id,'revision':revision,
                        'experiment':experiment.payload(),'editor':experiment.editor,'diagnostics':diagnostics(experiment),
                        'sample':sample,'sample_units':{'position_m':'m','electric_field_V_m':'V/m','magnetic_field_T':'T','electric_potential_V':'V'}}
                    if experiment.mode=='test_particle':result['particle_force']=lorentz(experiment.model,experiment.phase.position_m,
                        experiment.phase.velocity_m_s,experiment.charge_C,experiment.mass_kg,**experiment.controls)
                else:
                    points=command.get('points_m')
                    if not isinstance(points,list) or not 1<=len(points)<=128:raise ValueError('Field map needs1..128 explicit SI sample positions')
                    result={'time_s':experiment.phase.time_s,'frame':FRAME,'system_id':system_id,'edit_token':token,
                        'revision':revision,'samples':[model.evaluate(p) for p in points]}
            else:raise ValueError('Unknown EM worker command')
            snapshot()
            emit({'type':'ack','id':command.get('id'),'command':name,'time_s':experiment.phase.time_s,
                'paused':paused,'elapsed_ms':(time.perf_counter()-began)*1000,**({'result':result} if result is not None else {})})
            next_publish=time.perf_counter()+.1
        except (ValueError,TypeError,KeyError,OSError,ArithmeticError) as error:
            snapshot();emit({'type':'error','id':command.get('id'),'command':name,'message':str(error)})

if __name__=='__main__':main()
