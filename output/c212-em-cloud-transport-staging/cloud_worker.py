"""Bounded line-JSON process for the SI prescribed-field EM cloud.

Only metadata crosses stdout. Scientific buffers remain in the child; explicit
sealed checkpoints and selected-particle queries expose confirmed SI phases.
A single scientific step and output back pressure cannot be preempted.
"""
from dataclasses import asdict
from pathlib import Path
import argparse
import hashlib
import json
import math
import queue
import re
import sys
import threading
import time
import uuid
import numpy as np
from cloud_checkpoint import canonical, controls, generation, load, save, timestep, unique
from cloud_presets import NAMES, create
from cloud_core import System
from cloud_fields import evaluate
from em_fields import Model, Source, scalar
import cloud_transport as wire

FRAME = 'synthetic_EM_inertial_cartesian_SI'
MAX_LINE = 65536
QUANTUM_STEPS = 16
QUANTUM_SECONDS = .008
ROOT = Path(__file__).resolve().parent


def model_from_record(value):
    if not isinstance(value, dict) or set(value) != {'sources', 'uniform_E_V_m', 'uniform_B_T'}:
        raise ValueError('Explicit prescribed EM source model required')
    if not isinstance(value['sources'], list) or len(value['sources']) > 128:
        raise ValueError('At most128 prescribed EM sources allowed')
    return Model(tuple(Source(**s) for s in value['sources']), value['uniform_E_V_m'], value['uniform_B_T'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--storage', required=True, type=Path)
    args = parser.parse_args()
    storage = args.storage.resolve()
    base = (ROOT.parent / 'c212-em-cloud-worker').resolve()
    if storage == base or not storage.is_relative_to(base):
        raise ValueError('Use an isolated child of output/c212-em-cloud-worker')
    storage.mkdir(parents=True, exist_ok=True)
    commands = queue.Queue(maxsize=32)

    def reader():
        while True:
            line = sys.stdin.readline(MAX_LINE+1)
            if not line:
                commands.put({'command': 'quit'})
                return
            if len(line) > MAX_LINE:
                while line and not line.endswith('\n'):
                    line = sys.stdin.readline(MAX_LINE+1)
                commands.put({'command': 'invalid'})
                continue
            try:
                value = json.loads(line, object_pairs_hook=unique,
                                   parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
                if isinstance(value, dict) and 'id' in value:
                    identifier = value['id']
                    if not (type(identifier) is int and 0 <= identifier <= 2**53 or
                            type(identifier) is str and 1 <= len(identifier) <= 100):
                        raise ValueError('Bounded command identifier required')
                commands.put(value if isinstance(value, dict) else {'command': 'invalid'})
            except (ValueError, RecursionError):
                commands.put({'command': 'invalid'})

    threading.Thread(target=reader, daemon=True).start()
    system, phase, dt, acting = create('helix', 1)
    paused = True
    sequence = revision = 0
    system_id, token = uuid.uuid4().hex, uuid.uuid4().hex
    selected = 0
    cloud_id = uuid.uuid4().hex
    source_id = wire.source_id(system, dt, acting)
    publication_sequence = 0
    published_key = None
    transport = None
    rate, effective = 1., 0.
    notice = None
    rate_wall = next_publish = time.perf_counter()
    rate_time = phase.time_s
    scientific_generation = generation()
    runtime_generation = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
                          for p in ('cloud_worker.py', 'cloud_presets.py', 'cloud_transport.py')}
    last_compute_ms = 0.
    last_work = None

    def emit(value):
        print(json.dumps(value, separators=(',', ':'), allow_nan=False), flush=True)

    def point(index):
        return {**phase.point(index), 'charge_C': float(system.charges()[index]),
                'mass_kg': float(system.masses()[index]), 'frame': FRAME}

    def snapshot():
        nonlocal transport, publication_sequence, published_key
        key = (system_id, token, cloud_id, source_id, sequence)
        if key != published_key:
            try:
                packet, metadata = wire.encode(phase, system_id, token, cloud_id, source_id,
                                               publication_sequence+1)
                wire.publish(storage/'positions.bin', packet)
                publication_sequence += 1
                transport = {'status': 'published', 'metadata': metadata,
                             'packet_path': str(storage/'positions.bin')}
                published_key = key
            except (ValueError, OSError, ArithmeticError) as error:
                transport = {'status': 'unavailable', 'error': str(error),
                             'scientific_phase_preserved': True}
        try:
            diagnostics = system.diagnostics(phase)
        except (ValueError, ArithmeticError) as error:
            diagnostics = {'count': phase.count, 'time_s': phase.time_s,
                           'unavailable': str(error), 'backreaction': False,
                           'test_test_interaction': False}
        if last_work is not None:
            def total(value):
                try:
                    return math.fsum(value.tolist())
                except OverflowError:
                    return None
            diagnostics['last_step'] = {
                'electric_work_J': total(last_work['electric_work_J']),
                'kinetic_change_J': total(last_work['kinetic_change_J']),
                'sha256': hashlib.sha256(last_work['electric_work_J'].tobytes()+
                                         last_work['kinetic_change_J'].tobytes()).hexdigest(),
                'sample_time_s': last_work['sample_time_s']}
        emit({'type': 'snapshot', 'sequence': sequence, 'system_id': system_id,
              'edit_token': token, 'revision': revision, 'frame': FRAME,
              'paused': paused, 'time_s': phase.time_s, 'count': phase.count,
              'dt_s': dt, 'controls': acting, 'model': asdict(system.model),
              'requested_model_s_per_wall_s': rate, 'effective_model_s_per_wall_s': effective,
              'rate_persistence': 'runtime_only', 'compute_ms': last_compute_ms,
              'integration_quantum_steps': QUANTUM_STEPS,
              'integration_budget_ms': QUANTUM_SECONDS*1000,
              'notice': notice, 'scientific_generation': scientific_generation,
              'runtime_generation': runtime_generation, 'diagnostics': diagnostics,
              'phase_sha256': hashlib.sha256(phase._x+phase._v).hexdigest(),
              'selected_particle': point(selected), 'cloud_id': cloud_id,
              'source_id': source_id, 'cloud_transport': transport})

    def expect(command, live=False):
        if not paused and not live:
            raise ValueError('Pause the EM cloud first')
        t = command.get('expected_time_s')
        valid_time = (type(t) in (int, float) and math.isfinite(t) and
                      (t == phase.time_s if paused else 0 <= t <= phase.time_s))
        if (command.get('system_id') != system_id or command.get('edit_token') != token or
                type(command.get('revision')) is not int or command['revision'] != revision or
                command.get('frame') != FRAME or not valid_time):
            raise ValueError('Stale EM cloud command; obtain the confirmed state')

    def checkpoint_path(command):
        name = command.get('file')
        if not isinstance(name, str) or not re.fullmatch('[a-zA-Z0-9_-]{1,40}', name):
            raise ValueError('Bounded local checkpoint name required')
        path = storage / (name+'.json')
        if path.is_symlink() or path.resolve().parent != storage:
            raise ValueError('Checkpoint must remain inside worker storage')
        return path

    def advance_one():
        nonlocal phase, last_work, sequence, last_compute_ms
        began = time.perf_counter()
        trial, work = system.step(phase, dt, **acting)
        phase, last_work = trial, work
        sequence += 1
        last_compute_ms = (time.perf_counter()-began)*1000

    emit({'type': 'ready', 'protocol': 1, 'kind': 'cosmos2_prescribed_EM_cloud_SI',
          'paused': True, 'presets': NAMES, 'storage': str(storage)})
    snapshot()
    guard_fields = {'system_id', 'edit_token', 'revision', 'frame', 'expected_time_s'}
    arguments = {
        'quit': set(), 'pause': set(), 'snapshot': set(), 'resume': guard_fields,
        'load_preset': guard_fields | {'preset', 'count'},
        'set_controls': guard_fields | {'controls'}, 'set_model': guard_fields | {'model'},
        'set_timestep': guard_fields | {'dt_s'}, 'set_rate': guard_fields | {'value'},
        'advance': guard_fields | {'steps'}, 'save': guard_fields | {'file'},
        'load': guard_fields | {'file'}, 'select': guard_fields | {'index'},
        'probe': guard_fields | {'position_m'}, 'field_map': guard_fields | {'points_m'}}
    while True:
        now = time.perf_counter()
        try:
            command = commands.get(timeout=max(0, next_publish-now) if paused else 0)
        except queue.Empty:
            command = None
            if not paused:
                began = time.perf_counter()
                target = min(phase.time_s+.25*rate, rate_time+(began-rate_wall)*rate)
                try:
                    for _ in range(QUANTUM_STEPS):
                        if (not commands.empty() or time.perf_counter()-began >= QUANTUM_SECONDS or
                                phase.time_s+dt > target):
                            break
                        advance_one()
                except (ValueError, ArithmeticError) as error:
                    paused, effective = True, 0.
                    notice = 'Paused at last valid EM cloud phase: '+str(error)
                elapsed = time.perf_counter()-rate_wall
                if not paused:
                    effective = (phase.time_s-rate_time)/elapsed if elapsed else 0.
                    if phase.time_s+dt > target:
                        try:
                            command = commands.get(timeout=min(.01, dt/rate))
                        except queue.Empty:
                            pass
            if time.perf_counter() >= next_publish:
                snapshot()
                next_publish = time.perf_counter()+.1
            if command is None:
                continue
        name, began, result = command.get('command'), time.perf_counter(), None
        try:
            if not isinstance(name, str) or name not in arguments:
                raise ValueError('Unknown EM cloud command')
            if set(command)-({'id', 'command'} | arguments[name]):
                raise ValueError('Unknown EM cloud command fields')
            if name == 'quit':
                emit({'type': 'ack', 'id': command.get('id'), 'command': name})
                return
            if name == 'pause':
                paused, effective = True, 0.
            elif name == 'snapshot':
                pass
            else:
                expect(command, live=name in ('select', 'set_rate'))
                if name == 'resume':
                    paused, notice, effective = False, None, 0.
                    rate_wall, rate_time = time.perf_counter(), phase.time_s
                elif name == 'load_preset':
                    trial = create(command.get('preset'), command.get('count'))
                    system, phase, dt, acting = trial
                    revision = sequence = selected = 0
                    system_id, token = uuid.uuid4().hex, uuid.uuid4().hex
                    cloud_id = uuid.uuid4().hex
                    source_id = wire.source_id(system, dt, acting)
                    notice, last_work = None, None
                elif name == 'set_controls':
                    acting = controls(command.get('controls'))
                    source_id = wire.source_id(system, dt, acting)
                    revision += 1
                    notice, last_work = None, None
                elif name == 'set_model':
                    model = model_from_record(command.get('model'))
                    trial = System(model, system.charges(), system.masses())
                    evaluate(trial.model, phase.positions(), potential=False)
                    system = trial
                    source_id = wire.source_id(system, dt, acting)
                    revision += 1
                    notice, last_work = None, None
                elif name == 'set_timestep':
                    dt = timestep(command.get('dt_s'))
                    source_id = wire.source_id(system, dt, acting)
                    revision += 1
                    notice, last_work = None, None
                elif name == 'set_rate':
                    trial = scalar(command.get('value'))
                    if not .001 <= trial <= 100:
                        raise ValueError('Requested model seconds per wall second must be in.001..100')
                    rate, effective = trial, 0.
                    rate_wall, rate_time = time.perf_counter(), phase.time_s
                elif name == 'advance':
                    steps = command.get('steps')
                    if type(steps) is not int or not 1 <= steps <= 32:
                        raise ValueError('Manual cloud advance must be1..32 steps')
                    for _ in range(steps):
                        advance_one()
                elif name in ('save', 'load'):
                    path = checkpoint_path(command)
                    if name == 'save':
                        save(path, system, phase, dt, acting)
                        result = {'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                    else:
                        trial = load(path)
                        system, phase, dt, acting = trial
                        sequence = selected = revision = 0
                        system_id, token = uuid.uuid4().hex, uuid.uuid4().hex
                        cloud_id = uuid.uuid4().hex
                        source_id = wire.source_id(system, dt, acting)
                        notice, last_work = None, None
                elif name == 'select':
                    trial = command.get('index')
                    result = point(trial)
                    selected = trial
                elif name == 'probe':
                    result = {**system.model.evaluate(command.get('position_m')),
                              'time_s': phase.time_s, 'frame': FRAME, 'system_id': system_id,
                              'edit_token': token, 'revision': revision, 'source_id': source_id}
                elif name == 'field_map':
                    points = command.get('points_m')
                    if not isinstance(points, list) or not 1 <= len(points) <= 128:
                        raise ValueError('Field map requires1..128 SI sample positions')
                    result = {'time_s': phase.time_s, 'frame': FRAME, 'system_id': system_id,
                              'edit_token': token, 'revision': revision, 'source_id': source_id,
                              'samples': [system.model.evaluate(p) for p in points]}
            snapshot()
            emit({'type': 'ack', 'id': command.get('id'), 'command': name,
                  'time_s': phase.time_s, 'paused': paused,
                  'elapsed_ms': (time.perf_counter()-began)*1000,
                  **({'result': result} if result is not None else {})})
            next_publish = time.perf_counter()+.1
        except (ValueError, TypeError, KeyError, OSError, ArithmeticError) as error:
            snapshot()
            emit({'type': 'error', 'id': command.get('id'), 'command': name,
                  'message': str(error), 'time_s': phase.time_s, 'sequence': sequence})


if __name__ == '__main__':
    main()
