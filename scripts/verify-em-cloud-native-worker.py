"""Operational child processes: exact futures, SI selection, time controls and faults."""
from pathlib import Path
import hashlib
import json
import queue
import subprocess
import sys
import threading
import time
import uuid
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT/'output/c212-em-cloud-native-staging'
sys.path.insert(0, str(STAGE))
from cloud_checkpoint import canonical, generation, save
from cloud_core import System, Phase
from cloud_presets import create
from em_fields import Model, Source

BASE = ROOT/'output/c212-em-cloud-worker'/('verification-'+uuid.uuid4().hex)
BASE.mkdir(parents=True)
OWNER = ROOT/'user/sessions/latest.json'
owner_bytes = OWNER.read_bytes()
app_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (ROOT/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}


class Worker:
    def __init__(self, storage):
        self.storage, self.serial, self.state, self.lines = storage, 0, None, []
        storage.mkdir(parents=True, exist_ok=True)
        self.process = subprocess.Popen([sys.executable, '-X', 'utf8', '-u', str(STAGE/'cloud_worker.py'),
                                         '--storage', str(storage)], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        self.messages = queue.Queue()

        def reader():
            for line in self.process.stdout:
                self.lines.append(len(line))
                try:
                    self.messages.put(json.loads(line))
                except ValueError:
                    self.messages.put({'type': 'invalid_output', 'line': line})
            self.messages.put({'type': 'closed'})
        threading.Thread(target=reader, daemon=True).start()
        ready = self.read()
        assert ready['type'] == 'ready' and ready['kind'] == 'cosmos2_prescribed_EM_cloud_SI', ready
        while self.state is None:
            self.read()

    def read(self):
        value = self.messages.get(timeout=30)
        assert value['type'] not in ('invalid_output', 'closed'), value
        if value['type'] == 'snapshot':
            self.state = value
        return value

    def guard(self):
        return {k: self.state[k] for k in ('system_id', 'edit_token', 'revision', 'frame')} | {
            'expected_time_s': self.state['time_s']}

    def call(self, name, error=False, guarded=True, **args):
        self.serial += 1
        command = {'id': self.serial, 'command': name,
                   **(self.guard() if guarded and name not in ('pause', 'snapshot', 'quit') else {}), **args}
        began = time.perf_counter()
        self.process.stdin.write(json.dumps(command, allow_nan=False)+'\n')
        self.process.stdin.flush()
        while True:
            value = self.read()
            if value.get('id') == self.serial:
                assert value['type'] == ('error' if error else 'ack'), value
                return value, (time.perf_counter()-began)*1000

    def stable(self):
        return {k: self.state[k] for k in ('system_id', 'edit_token', 'revision', 'time_s', 'sequence',
                                          'phase_sha256', 'controls', 'dt_s', 'model', 'selected_particle')}

    def close(self, eof=False):
        if self.process.poll() is None:
            if eof:
                self.process.stdin.close()
            else:
                self.call('quit')
            self.process.wait(timeout=10)
        errors = self.process.stderr.read()
        assert self.process.returncode == 0 and not errors, (self.process.returncode, errors)


workers, futures, presets, refusals, pauses, rates = [], [], [], [], [], []
try:
    # Each future is compared with an independently running parent, every step,
    # then checkpointed and resumed in a second clean operational process.
    for count, steps in ((1, 777), (128, 777), (10000, 64)):
        folder = BASE/str(count)
        worker = Worker(folder)
        workers.append(worker)
        i = np.arange(count)
        x = np.column_stack((np.sin(i), np.cos(i), np.full(count, 5.)))
        model = (Model((Source('charge-and-dipole', (0, 0, 0), .1, 1e-9, (1e4, 0, 2e4)),),
                       (.1, 0, 0), (0, 0, .5)) if count < 10000 else
                 Model(tuple(Source(str(k), (8*__import__('math').cos(k), 8*__import__('math').sin(k), 4*(-1)**k), .02, (-1)**k*1e-10, (1e4, -2e4, 3e4)) for k in range(128)), uniform_B_T=(0, 0, .5)))
        s = System(model, np.where(i % 2, 1., -1.), 1+i/(count+1))
        p, dt = Phase(x, x*.01), .002
        acting = {'electric_acting': True, 'magnetic_acting': True}
        for _ in range(17):
            p, _ = s.step(p, dt, **acting)
        save(folder/'seed.json', s, p, dt, acting)
        seed = (folder/'seed.json').read_bytes()
        worker.call('load', file='seed')
        digest = hashlib.sha256()
        for _ in range(steps):
            p, work = s.step(p, dt, **acting)
            worker.call('advance', steps=1)
            phase_hash = hashlib.sha256(p._x+p._v).hexdigest()
            work_hash = hashlib.sha256(work['electric_work_J'].tobytes()+work['kinetic_change_J'].tobytes()).hexdigest()
            assert worker.state['phase_sha256'] == phase_hash and worker.state['time_s'] == p.time_s
            assert worker.state['diagnostics']['last_step']['sha256'] == work_hash
            digest.update(bytes.fromhex(phase_hash+work_hash))
        ack, _ = worker.call('select', index=count-1)
        assert ack['result'] == {**p.point(count-1), 'charge_C': float(s.charges()[-1]),
                                 'mass_kg': float(s.masses()[-1]), 'frame': worker.state['frame']}
        worker.call('save', file='future')
        save(folder/'oracle.json', s, p, dt, acting)
        assert (folder/'future.json').read_bytes() == (folder/'oracle.json').read_bytes()
        stale = worker.guard()
        worker.call('load', file='future')
        baseline = worker.stable()
        worker.call('advance', error=True, steps=1, **stale)
        assert worker.stable() == baseline
        worker.close()
        restarted = Worker(folder)
        workers.append(restarted)
        restarted.call('load', file='future')
        for _ in range(33):
            p, work = s.step(p, dt, **acting)
            restarted.call('advance', steps=1)
            assert restarted.state['phase_sha256'] == hashlib.sha256(p._x+p._v).hexdigest()
            assert restarted.state['time_s'] == p.time_s
        restarted.close(eof=True)
        assert (folder/'seed.json').read_bytes() == seed
        futures.append({'count': count, 'every_step_phase_work_time_exact': steps,
                        'second_process_exact_future_steps': 33, 'all_steps_sha256': digest.hexdigest(),
                        'checkpoint_bytes_equal_to_independent_oracle': True, 'source_checkpoint_preserved': True})
        print(f'cloud worker exact future {count}/{steps} passed', flush=True)

    worker = Worker(BASE/'controls')
    workers.append(worker)
    for name in ('electric', 'helix', 'crossed', 'dipole', 'coulomb'):
        worker.call('load_preset', preset=name, count=128)
        s, initial, dt, _ = create(name, 128)
        worker.call('probe', position_m=[10, 1, -2])
        for e, b in ((False, False), (False, True), (True, False), (True, True)):
            worker.call('load_preset', preset=name, count=128)
            acting = {'electric_acting': e, 'magnetic_acting': b}
            before = worker.state['phase_sha256']
            worker.call('set_controls', controls=acting)
            assert worker.state['phase_sha256'] == before
            p = initial
            for _ in range(32):
                p, _ = s.step(p, dt, **acting)
            worker.call('advance', steps=32)
            assert worker.state['phase_sha256'] == hashlib.sha256(p._x+p._v).hexdigest()
        presets.append({'preset': name, 'four_acting_combinations_exact': True})

    worker.call('load_preset', preset='helix', count=10000)
    # Rate is a scheduler request. Actual throughput is recorded separately;
    # these measurements are not native performance acceptance.
    for requested in (.1, .5, 1.):
        worker.call('set_rate', value=requested)
        start = worker.state['time_s']
        began = time.perf_counter()
        worker.call('resume')
        time.sleep(1.)
        _, wall = worker.call('pause')
        pauses.append(wall)
        actual = (worker.state['time_s']-start)/(time.perf_counter()-began)
        assert 0 < actual <= requested*1.05
        rates.append({'requested': requested, 'observed': actual, 'count': 10000})
    for _ in range(20):
        worker.call('resume')
        time.sleep(.04)
        worker.call('select', index=9999)
        _, wall = worker.call('pause')
        pauses.append(wall)
    assert max(pauses) < 250, pauses
    before = worker.stable()
    time.sleep(.12)
    worker.call('snapshot')
    assert worker.stable() == before

    for field, value in (('system_id', 'stale'), ('edit_token', 'stale'), ('revision', -1),
                         ('frame', 'gravity'), ('expected_time_s', -1)):
        worker.call('advance', error=True, steps=1, **{field: value})
        assert worker.stable() == before
        refusals.append('stale '+field)
    for name, args in (
            ('advance', {'steps': True}), ('advance', {'steps': 33}),
            ('select', {'index': True}), ('select', {'index': 10000}),
            ('set_rate', {'value': 0}), ('set_rate', {'value': True}),
            ('set_timestep', {'dt_s': False}), ('set_controls', {'controls': {'electric_acting': 1}}),
            ('save', {'file': '../outside'}), ('load', {'file': 'missing'}),
            ('load_preset', {'preset': 'helix', 'count': True}),
            ('load_preset', {'preset': 'unknown', 'count': 1}),
            ('snapshot', {'gravity': True}), ('field_map', {'points_m': [[0, 0, 0]]*129}),
            ('set_model', {'model': {'sources': [{'id': 'invalid'}], 'uniform_E_V_m': [0, 0, 0],
                                     'uniform_B_T': [0, 0, 0]}})):
        worker.call(name, error=True, **args)
        assert worker.stable() == before, name
        refusals.append(name+' '+str(args)[:80])
    worker.call('save', file='valid')
    original = json.loads((worker.storage/'valid.json').read_bytes())
    for fault in ('seal', 'generation', 'nan', 'exclusion'):
        r = json.loads(json.dumps(original))
        if fault == 'seal':
            r['phase']['time_s'] += 1
        elif fault == 'generation':
            r['generation']['model'] = 'IAS15'
        elif fault == 'nan':
            r['phase']['position_f64le_hex'] = np.array([float('nan')], dtype='<f8').tobytes().hex()+r['phase']['position_f64le_hex'][16:]
        elif fault == 'exclusion':
            r['model']['sources'] = [{'id': 'excluded', 'position_m': worker.state['selected_particle']['position_m'],
                                     'charge_C': 0, 'magnetic_moment_A_m2': [0, 0, 0], 'exclusion_radius_m': 1}]
        if fault != 'seal':
            r.pop('sha256')
            r['sha256'] = hashlib.sha256(canonical(r)).hexdigest()
        (worker.storage/'corrupt.json').write_bytes(canonical(r))
        worker.call('load', error=True, file='corrupt')
        assert worker.stable() == before
        refusals.append('corrupt checkpoint '+fault)
    old_profile = json.loads((ROOT/'evidence/native-emcloud-c212em10kc.json').read_bytes())
    old_path = ROOT/old_profile['fixture_checkpoint'].replace('\\', '/')
    old_bytes = old_path.read_bytes()
    (worker.storage/'old-v2.json').write_bytes(old_bytes)
    worker.call('load', error=True, file='old-v2')
    assert worker.stable() == before and (worker.storage/'old-v2.json').read_bytes() == old_bytes
    refusals.append('real frozen NumPyv2 checkpoint requires explicit migration')
    worker.call('resume')
    for name, args in (('save', {'file': 'running'}), ('advance', {'steps': 1}),
                       ('set_controls', {'controls': {'electric_acting': False, 'magnetic_acting': False}})):
        worker.call(name, error=True, **args)
        refusals.append(name+' while running')
    worker.call('pause')
    assert not (worker.storage/'running.json').exists()

    # Refuse an unsafe drift at the last completed phase, including in live mode.
    s = System.uniform(Model((Source('excluded', (0, 0, 0), 1),)), 1, 1, 1)
    p = Phase([[-2, 0, 0]], [[2, 0, 0]])
    save(worker.storage/'collision.json', s, p, 1., {'electric_acting': True, 'magnetic_acting': True})
    worker.call('load', file='collision')
    before = worker.stable()
    worker.call('advance', error=True, steps=1)
    assert worker.stable() == before
    worker.call('set_rate', value=100)
    worker.call('resume')
    deadline = time.perf_counter()+5
    while not worker.state['paused']:
        assert time.perf_counter() < deadline
        worker.read()
    assert worker.state['phase_sha256'] == before['phase_sha256'] and worker.state['time_s'] == 0
    assert 'last valid' in worker.state['notice']
    worker.call('load_preset', preset='helix', count=1)
    worker.call('advance', steps=1)

    # Invalid raw packets cannot stop the reader or poison its response JSON.
    for packet in ('{"command":"snapshot","command":"pause"}\n',
                   '{"command":"snapshot","id":1e999}\n', '['*2000+'0'+']'*2000+'\n',
                   'x'*70000+'\n'):
        worker.process.stdin.write(packet)
        worker.process.stdin.flush()
        while worker.read()['type'] != 'error':
            pass
        worker.call('snapshot')
        refusals.append('malformed raw packet')
    worker.close()
    assert OWNER.read_bytes() == owner_bytes
    assert app_hashes == {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in (ROOT/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    report = {
        'status': 'operational_isolated_EM_cloud_worker_verified', 'futures': futures, 'presets': presets,
        'pause_samples': len(pauses), 'pause_API_wall_max_ms': max(pauses), 'observed_worker_rates': rates,
        'refusals': refusals, 'clean_child_processes': len(workers),
        'maximum_snapshot_or_ack_line_bytes': max(n for w in workers for n in w.lines),
        'bounded_command_queue': 32, 'input_max_characters': 65536,
        'quantum_max_steps': 16, 'quantum_budget_ms': 8, 'one_scientific_step_not_preemptible': True,
        'last_valid_phase_on_domain_exit_and_recovery': True, 'EOF_clean_exit': True,
        'installed_app_files_preserved': len(app_hashes), 'owner_pointer_preserved': True,
        'scientific_generation': generation(), 'storage': str(BASE),
        'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in (*[p for p in STAGE.iterdir() if p.is_file()], Path(__file__))},
        'scope': 'Operational isolated SI prescribed-field worker. Exact scientific checkpoints; rate remains runtime-only. '
                 'No native GPU transport, native10k profile,128-source throughput or UI acceptance.'}
    (ROOT/'evidence/em-cloud-native-worker-check.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ('status', 'pause_API_wall_max_ms', 'observed_worker_rates',
                                           'clean_child_processes', 'maximum_snapshot_or_ack_line_bytes')}, indent=2))
finally:
    for w in workers:
        if w.process.poll() is None:
            w.process.terminate()
            w.process.wait(timeout=5)
    assert OWNER.read_bytes() == owner_bytes
