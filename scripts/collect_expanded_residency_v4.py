"""Continuous1Hz owned raw-PDH/RAM evidence with acknowledged phase boundaries, schema5."""
import argparse
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback
import urllib.request
import uuid

import psutil
from expanded_residency_projection import project
import windows_gpu_pdh_v2 as pdh
import owned_process_snapshot as ownership
from owned_process_history import History
import expanded_residency_history_audit as history_audit
import expanded_residency_contract_v3 as contract
import gpu_pdh_audit_dynamics16_base as raw_gpu

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get(path):
    with OPENER.open('http://127.0.0.1:4700' + path, timeout=4) as response:
        return json.load(response)


def scenario():
    state = get('/api/state')
    modules = {name: get('/api/' + name + '/state') for name in ['spatial', 'layers', 'particles', 'solar-zone']}
    navigation = get('/api/navigation/state') if state['mode'] == 'atlas' else None
    return contract.scenario(state, modules, navigation)


def atomic(path, value):
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
        deadline = time.monotonic() + 2
        while True:
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(.01)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--folder', required=True, type=Path)
    parser.add_argument('--max-samples', type=int, default=3600)
    args = parser.parse_args()
    contract.require(args.label and len(args.label) <= 32 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label), 'Invalid collector label')
    contract.require(1 <= args.max_samples <= 7200, 'Collector sample budget differs')
    folder = args.folder.resolve()
    contract.require(folder.is_relative_to((ROOT / 'output').resolve()) and folder.is_dir(), 'Own collection folder required')
    out = ROOT / f'evidence/is6-expanded-residency-collector-{args.label}.json'
    data, control, status, stop = [folder / name for name in ['memory.jsonl', 'control.json', 'collector-status.json', 'stop.json']]
    contract.require(not out.exists() and not data.exists() and not status.exists() and not stop.exists(), 'Preserve continuous residency evidence')
    session_path = ROOT / 'output/session.json'
    session = json.loads(session_path.read_text(encoding='utf-8-sig'))
    engine = psutil.Process(session['app'])
    executable = Path(engine.exe()).resolve()
    contract.require(executable.is_relative_to(ROOT) and executable.name.lower() == 'openspace.exe', 'Owned native engine required')
    sources = {p.relative_to(ROOT).as_posix(): sha(p) for p in [Path(__file__), Path(pdh.__file__), Path(ownership.__file__),
               ROOT / 'scripts/expanded_residency_processes.py', Path(contract.__file__), Path(raw_gpu.__file__),
               *ownership.FILES[1:], pdh.CONTRACT, pdh.TIME_CONTRACT, ROOT / 'IS-6-PERCURSO-AMPLIADO16-RESIDENCIA-IDENTIDADE.md', ROOT / 'scripts/expanded_residency_projection.py', ROOT / 'IS-6-PERCURSO-AMPLIADO16-RESIDENCIA-REVISAO-C.md', ROOT / 'scripts/owned_process_history.py', ROOT / 'scripts/expanded_residency_history_audit.py', ROOT / 'IS-6-PERCURSO-AMPLIADO16-RESIDENCIA-REVISAO-D.md']}
    report = dict(schema=6, valid=False, completed=False, failure=None, label=args.label, session=session,
                  source_sha256=sources, engine_sha256=sha(executable), engine_started_unix=engine.create_time(),
                  pdh_generation=pdh.generation(), ownership_generation=ownership.generation(),
                  max_samples=args.max_samples, samples=0, data_file=data.relative_to(ROOT).as_posix(),
                  scope='Continuous1Hz own raw WDDM gauges and temporally proven RAM/lifetimes; unknown identities or invalid selected values refuse the whole collection. Unexposed processes are never assigned GPU zero.')
    tracker = History(session, folder / 'process-history.jsonl')
    phase_count, previous_id = 0, None
    began = time.monotonic()
    try:
        tracker.start()
        with data.open('x', encoding='utf8', newline='\n') as stream:
            for index in range(args.max_samples):
                if stop.exists():
                    report['stop_request'] = json.loads(stop.read_text())
                    break
                remaining = began + index - time.monotonic()
                if remaining > 0:
                    time.sleep(remaining)
                row = dict(index=index, started_utc=dt.datetime.now(dt.timezone.utc).isoformat(), monotonic_offset_s=time.monotonic() - began)
                try:
                    phase_before = json.loads(control.read_text())
                    contract.require(set(phase_before) == {'schema', 'id', 'kind', 'window', 'recipe', 'expected_scenario'}, 'Exact collector phase control required')
                    contract.require(type(phase_before['schema']) is int and phase_before['schema'] == 1 and phase_before['kind'] in ['prepare', 'transition', 'warmup', 'stable', 'cleanup'], 'Unknown residency phase')
                    tree = tracker.snapshot()
                    owned = {entry['pid'] for entry in tree['owned']}
                    row.update(phase_before=phase_before, inventory_before=tree, scenario_inputs={})
                    inputs = row['scenario_inputs']
                    inputs['state'] = get('/api/state')
                    inputs['modules'] = {}
                    for name in ['spatial', 'layers', 'particles', 'solar-zone']:
                        inputs['modules'][name] = get('/api/' + name + '/state')
                    inputs['navigation'] = get('/api/navigation/state') if inputs['state']['mode'] == 'atlas' else None
                    row.update(project(inputs, phase_before['kind']))
                    ram_rows = []
                    for identity in tree['owned']:
                        process = psutil.Process(identity['pid'])
                        contract.require(abs(process.create_time() - identity['started_unix']) <= 5e-6, 'RAM process was reused')
                        read_started = tracker.clock()
                        memory = process.memory_info()
                        ram_rows.append(dict(pid=identity['pid'], created_filetime=identity['created_filetime'], working_set_bytes=memory.rss, private_bytes=memory.private, read_started_filetime=read_started, read_finished_filetime=tracker.clock()))
                    row['ram'] = dict(processes=ram_rows, sum_working_set_bytes=sum(entry['working_set_bytes'] for entry in ram_rows))
                    with pdh.Query() as query:
                        known = {entry['identity']['pid'] for entry in tracker.export()['records']}
                        paths = query.discover(known)
                        query.select(paths)
                        row.update(query.sample(), configured_counter_paths=sorted(paths), counter_metadata=copy.deepcopy(query.metadata))
                        row['inventory_after'] = tracker.snapshot()
                        row['native_history'] = tracker.export()
                        known = {entry['identity']['pid'] for entry in row['native_history']['records']}
                        row['counter_paths_after'] = sorted(query.discover(known))
                    row.update(raw_gpu.sample(row, row['configured_counter_paths'], known))
                    row['owned_without_exposed_gpu_counter'] = sorted(known - {entry['pid'] for entry in paths.values() if entry['pid'] is not None})
                    contract.gpu_row(row, session)
                    phase_after = json.loads(control.read_text())
                    row.update(phase_after=phase_after, boundary=phase_before != phase_after,
                               finished_utc=dt.datetime.now(dt.timezone.utc).isoformat())
                    if phase_before == phase_after and phase_before['kind'] == 'stable':
                        contract.admit_scenario(row['scenario'], phase_before['recipe'], phase_before['expected_scenario'])
                    stream.write(json.dumps(row, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')
                    stream.flush()
                    report['samples'] = index + 1
                    if not row['boundary']:
                        phase_count = phase_count + 1 if phase_before['id'] == previous_id else 1
                        previous_id = phase_before['id']
                    atomic(status, dict(schema=6, collector_pid=os.getpid(), session_engine_pid=session['app'], samples=index + 1,
                           acknowledged_id=previous_id, phase_samples=phase_count, last_sample_utc=row['utc'], valid=True))
                except Exception:
                    row['failure'] = traceback.format_exc()
                    stream.write(json.dumps(row, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')
                    stream.flush()
                    raise
        contract.require(report['samples'] > 0, 'No continuous GPU samples')
        contract.require(json.loads(session_path.read_text(encoding='utf-8-sig')) == session, 'Native session changed')
        contract.require(engine.create_time() == report['engine_started_unix'] and sha(executable) == report['engine_sha256'], 'Engine identity/executable changed')
        contract.require(all(sha(ROOT / name) == seal for name, seal in sources.items()), 'Collector source changed')
        report.update(valid=True, completed=True)
    except Exception:
        report['failure'] = traceback.format_exc()
        atomic(status, dict(schema=6, collector_pid=os.getpid(), samples=report['samples'], valid=False, failure=report['failure']))
    finally:
        tracker.close()
        try:
            report['native_history'] = tracker.export()
            if data.exists():
                rows = [json.loads(line) for line in data.read_text(encoding='utf8').splitlines()]
                complete = [row for row in rows if not row.get('failure')]
                report['process_records'] = history_audit.sampled_ledger(complete, report['native_history']) if complete else []
        except Exception:
            report['history_failure'] = traceback.format_exc()
            report['valid'] = False
        tracker.close()
        report['data_sha256'] = sha(data) if data.exists() else None
        report['process_history_sha256'] = sha(folder / 'process-history.jsonl')
        atomic(out, report)
    print(json.dumps(dict(valid=report['valid'], samples=report['samples'], failure=report['failure'])), flush=True)
    return 0 if report['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
