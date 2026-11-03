"""Process-isolated physics worker. Line-delimited JSON stdin/stdout protocol v1.

The owning thread integrates and serializes all state. Reader thread queues
commands. A 30 Hz target is the snapshot cadence, never the integrator timestep.
"""
import json
import queue
import sys
import threading
import time
from pathlib import Path
import argparse
import faulthandler
import rebound
from session import Session

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--storage', type=Path, default=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())/'user'/'sessions')
    parser.add_argument('--cloud-output', type=Path)
    args = parser.parse_args()
    commands = queue.Queue()
    def reader():
        for line in sys.stdin:
            try:
                value = json.loads(line)
                commands.put(value if isinstance(value, dict) else {'command': 'invalid'})
            except json.JSONDecodeError:
                commands.put({"command": "invalid"})
        commands.put({"command": "quit"})
    threading.Thread(target=reader, daemon=True).start()
    session = Session(args.storage)
    paused = True
    sequence = 0
    cloud_sequence = 0
    rate = 1.0
    rate_started = time.perf_counter()
    rate_time = 0.0
    effective_rate = 0.0
    integration_yielded=False
    integration_notice=None
    horizon_pending=False
    experiment_horizon_reached=False
    def emit(message):
        print(json.dumps(message, separators=(",", ":"), allow_nan=False), flush=True)
    def publish(compute_ms=0):
        nonlocal cloud_sequence
        state=session.state()
        if args.cloud_output is not None and session._cloud is not None:
            import cloud_transport
            try:
                cloud_sequence+=1
                packet,metadata=cloud_transport.encode(session._cloud,session.system_id,session.edit_token,
                    cloud_sequence,session.contract()['frame'])
                cloud_transport.publish(args.cloud_output,packet)
                state['cloud_transport']={'status':'published','packet_path':str(args.cloud_output),'metadata':metadata}
            except (ValueError,OSError) as error:
                state['cloud_transport']={'status':'unavailable','error':str(error),
                    'requested_sequence':cloud_sequence,'policy':'No new native phase is confirmed by this failed publication.'}
        history_began=time.perf_counter()
        if not paused and session.collect_history(state,history_began):
            import instrument_history
            state['instrument_history']=instrument_history.public(session.instrument_history)
        if not paused and session.collect_orbital_history(state,history_began):
            import orbital_instruments
            state['orbital_instruments']=orbital_instruments.public(session.orbital_instruments)
        state['history_evaluation_ms']=(time.perf_counter()-history_began)*1000
        emit({'type': 'snapshot', 'sequence': sequence, 'paused': paused,
              'requested_rate': rate, 'effective_rate': effective_rate,
              'integration_yielded':integration_yielded,'integration_budget_ms':40,
              'integration_notice':integration_notice,
              'experiment_horizon_reached':experiment_horizon_reached,
              'compute_ms': compute_ms, **state})
    emit({"type": "ready", "protocol": 1, "count": session.sim.N, "paused": paused})
    publish()
    deadline = time.perf_counter()
    while True:
        try:
            command = commands.get(timeout=max(0, deadline-time.perf_counter()))
            name = command.get("command")
            result=None
            command_started = time.perf_counter()
            if name == "quit":
                emit({"type": "ack", "id": command.get("id"), "command": name})
                return
            if name == "pause":
                paused = True
                effective_rate = 0.0
            elif name == "resume":
                paused = False
                integration_notice=None
                experiment_horizon_reached=False
                rate_started, rate_time = time.perf_counter(), session.sim.t
                deadline = time.perf_counter() + 1/30
            elif name == "reset":
                try:
                    session.reset(command.get("count", 32))
                except (ValueError, TypeError) as error:
                    emit({"type": "error", "id": command.get("id"), "message": str(error)})
                    continue
                paused, effective_rate = True, 0.0
            elif name in ('cloud_point','set_cloud','load_cloud_experiment','configure_orbital_instruments','sample_orbital_instruments','orbital_curves','orbital_export','orbital_point','load_resonant_experiment','load_tidal_experiment','set_tides','set_j2','create_branch','load_branch','compare_branches','configure_history','clear_history','history_curves','history_point','history_export','configure_fields','sample_fields','configure_instruments','sample_instruments','probe','load_experiment','orbit','set_mass', 'set_body','set_attributes', 'create_body','remove_body','new_system','restart_seed', 'save', 'load', 'import_atlas', 'restart_atlas'):
                try:
                    if name in ('cloud_point','configure_orbital_instruments','sample_orbital_instruments','orbital_curves','orbital_export','orbital_point','configure_history','clear_history','history_curves','history_point','history_export','configure_fields','sample_fields','configure_instruments','sample_instruments','probe','orbit'):result=getattr(session,name)(command)
                    elif name in ('import_atlas', 'restart_atlas'):
                        initial = command.get('initial_state') if name == 'import_atlas' else session.atlas_initial
                        session.import_atlas(initial)
                        paused, effective_rate = True, 0.0
                    elif name in ('create_branch','load_branch','compare_branches'):
                        if not paused:raise ValueError('Pause a evolução antes de consultar ou trocar ramos.')
                        result=getattr(session,name)(command)
                    elif name == 'set_body':
                        session.set_body(command)
                        paused,effective_rate=True,0.0
                    elif name in ('set_cloud','load_cloud_experiment','load_resonant_experiment','load_tidal_experiment','set_tides','set_j2','load_experiment','set_attributes','create_body','remove_body','new_system','restart_seed'):
                        method=getattr(session,name)
                        method() if name=='restart_seed' else method(command)
                        paused,effective_rate=True,0.0
                    elif name == 'set_mass':
                        faulthandler.dump_traceback_later(2,repeat=False)
                        try:
                            session.set_mass(command.get('body'), command.get('mass'))
                        finally:
                            faulthandler.cancel_dump_traceback_later()
                        paused, effective_rate = True, 0.0
                    elif name == 'save':
                        session.save()
                    else:
                        session.load()
                        paused, effective_rate = True, 0.0
                except (ValueError, TypeError, OSError, KeyError, RuntimeError) as error:
                    emit({'type':'error', 'id':command.get('id'), 'message':str(error)})
                    continue
            elif name == 'rate':
                candidate = command.get('value')
                if type(candidate) not in (int,float) or candidate not in (0.1,1,10):
                    emit({'type':'error', 'id':command.get('id'), 'message':'Supported rates: 0.1, 1, 10'})
                    continue
                rate = candidate
                rate_started, rate_time = time.perf_counter(), session.sim.t
            elif name == 'snapshot':
                pass
            else:
                emit({"type": "error", "id": command.get("id"), "message": "Unknown command"})
                continue
            if name in ('set_cloud','load_cloud_experiment','load_resonant_experiment','load_tidal_experiment','set_tides','set_j2','load_branch','load_experiment','reset','set_mass','set_body','set_attributes','create_body','remove_body','new_system','restart_seed','load','import_atlas','restart_atlas'):
                integration_notice=None;integration_yielded=False
                scenario=session.seed.get('scenario');horizon_pending=bool(scenario and session.sim.t<scenario['horizon_model_time']);experiment_horizon_reached=False
            publish()
            emit({"type": "ack", "id": command.get("id"), "command": name, "paused": paused, "time": session.sim.t,
                  'revision':session.revision,'elapsed_ms':(time.perf_counter()-command_started)*1000,
                  **({'result':result} if result is not None else {})})
        except queue.Empty:
            if not paused:
                started = time.perf_counter()
                integration_yielded=False
                def heartbeat(pointer):
                    nonlocal integration_yielded
                    if not commands.empty() or time.perf_counter()-started>.04:
                        integration_yielded=True
                        pointer.contents.stop()
                # Integrate to the next presentation time with adaptive internal steps.
                try:
                    target=session.sim.t+rate/30
                    if session._cloud:
                        # The30Hz publication target is not a numerical timestep.
                        # A10k adaptive step can outlast a presentation slot. Track
                        # the requested wall clock, with bounded catch-up and the
                        # same40ms heartbeat, instead of slowing physical time.
                        target=max(session.sim.t,min(session.sim.t+rate*.25,
                            rate_time+rate*(time.perf_counter()-rate_started)+rate/30))
                    if horizon_pending:target=min(target,session.seed['scenario']['horizon_model_time'])
                    session.integrate(target,heartbeat=heartbeat)
                    if horizon_pending and session.sim.t>=session.seed['scenario']['horizon_model_time']:
                        paused,effective_rate=True,0.;horizon_pending=False;experiment_horizon_reached=True
                except (ValueError,RuntimeError,rebound.GenericError,rebound.Encounter,rebound.Collision,rebound.Escape,rebound.NoParticles) as error:
                    paused,effective_rate=True,0.0
                    integration_notice='Integração pausada no limite do modelo gravitacional: '+str(error)
                finally:
                    # Runtime callbacks must never leak into a checkpoint or a clone.
                    session.sim.heartbeat=0
                sequence += 1
                if not paused:effective_rate = (session.sim.t-rate_time)/max(1e-6,time.perf_counter()-rate_started)
                publish((time.perf_counter()-started)*1000)
            # Absolute deadlines avoid adding Windows timer overshoot and work time
            # to every interval. Bound catch-up after a long stall.
            deadline += 1/30
            if deadline < time.perf_counter() - 0.5:
                deadline = time.perf_counter()

if __name__ == "__main__":
    main()
