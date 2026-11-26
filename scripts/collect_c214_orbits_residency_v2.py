"""C2-14 1Hz native RAM/PDH plus losslessly deduplicated HTTP and actual CEF witnesses."""
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
import owned_process_memory as memory
import expanded_residency_timing as timing
from windows_shared_json_v2 import read_json
from cef_page_v2 import Page
import c214_profile_contract as c214
import c214_profile_gpu_v2 as gpu_lifetime
import windows_gpu_pdh_v2 as pdh
import owned_process_snapshot as ownership
from owned_process_history import History
import expanded_residency_history_audit_v2 as history_audit
import expanded_residency_contract_v4 as contract
import gpu_pdh_audit_dynamics16_base as raw_gpu

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get(path):
    with OPENER.open('http://127.0.0.1:4700' + path, timeout=4) as response:
        return json.load(response)


def scenario():
    state = get('/api/state')
    navigation = get('/api/navigation/state')
    return dict(mode=state['mode'], renderer_confirmed=bool(navigation['navigation']['Anchor']),
                anchor=navigation['navigation']['Anchor'], et=navigation['et'])


def http_object(folder):
    with OPENER.open('http://127.0.0.1:4700/api/timelike/state', timeout=4) as response:
        raw = response.read()
    seal = hashlib.sha256(raw).hexdigest()
    path = folder / 'http-objects' / (seal + '.json')
    if not path.exists():
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(raw)
    else:
        assert path.stat().st_size == len(raw)
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=seal, bytes=len(raw)), json.loads(raw)


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
    out = ROOT / f'evidence/c214-orbits-profile-collector-{args.label}.json'
    data, control, status, stop = [folder / name for name in ['memory.jsonl', 'control.json', 'collector-status.json', 'stop.json']]
    contract.require(not out.exists() and not data.exists() and not status.exists() and not stop.exists(), 'Preserve continuous residency evidence')
    session_path = ROOT / 'output/session.json'
    session = json.loads(session_path.read_text(encoding='utf-8-sig'))
    engine = psutil.Process(session['app'])
    executable = Path(engine.exe()).resolve()
    contract.require(executable.is_relative_to(ROOT) and executable.name.lower() == 'openspace.exe', 'Owned native engine required')
    sources = {p.relative_to(ROOT).as_posix(): sha(p) for p in [Path(__file__), Path(pdh.__file__), Path(ownership.__file__),
               ROOT / 'scripts/expanded_residency_processes.py', Path(contract.__file__), Path(raw_gpu.__file__), Path(gpu_lifetime.__file__), ROOT/'C2-14-ORBITAS-PERFIL-REVISAO-B-20261114.md',
               *ownership.FILES[1:], pdh.CONTRACT, pdh.TIME_CONTRACT, ROOT / 'IS-6-PERCURSO-AMPLIADO16-RESIDENCIA-IDENTIDADE.md', ROOT / 'scripts/c214_profile_contract.py', ROOT / 'scripts/cef_page_v2.py', ROOT / 'C2-14-ORBITAS-PERFIL-CONTRATO-20261114.md', ROOT / 'C2-14-ORBITAS-PERFIL-RECEITA-TECNICA-20261114.md', ROOT / 'IS-6-PERCURSO-AMPLIADO16-RESIDENCIA-REVISAO-C.md', ROOT / 'scripts/owned_process_history.py', ROOT / 'scripts/expanded_residency_history_audit.py', ROOT / 'IS-6-PERCURSO-AMPLIADO16-RESIDENCIA-REVISAO-D.md', ROOT / 'scripts/windows_shared_json_v2.py', ROOT / 'IS-6-PERCURSO-AMPLIADO16-RESIDENCIA-REVISAO-E.md', ROOT / 'scripts/expanded_residency_timing.py', ROOT / 'IS-6-PERCURSO-AMPLIADO16-RESIDENCIA-REVISAO-F.md', ROOT / 'scripts/owned_process_memory.py', ROOT / 'scripts/expanded_residency_memory_audit.py', ROOT / 'scripts/expanded_residency_history_audit_v2.py', ROOT / 'IS-6-PERCURSO-AMPLIADO16-RESIDENCIA-REVISAO-G.md']}
    report = dict(schema=8, valid=False, completed=False, failure=None, label=args.label, session=session,
                  source_sha256=sources, engine_sha256=sha(executable), engine_started_unix=engine.create_time(),
                  pdh_generation=pdh.generation(), ownership_generation=ownership.generation(),
                  max_samples=args.max_samples, samples=0, data_file=data.relative_to(ROOT).as_posix(),
                  scope='Continuous1Hz own raw WDDM gauges and temporally proven RAM/lifetimes; unknown identities or invalid selected values refuse the whole collection. Unexposed processes are never assigned GPU zero.')
    tracker = History(session, folder / 'process-history.jsonl')
    phase_count, previous_id = 0, None
    page = Page()
    report['javascript_errors'] = []
    page.on('pageerror', lambda error: report['javascript_errors'].append(error))
    try:
        tracker.start()
        bootstrap = {}
        report['initialization'] = bootstrap
        try:
            timing.initialize(bootstrap, lambda: read_json(control), scenario, tracker, pdh.Query)
            timing.admit_bootstrap(bootstrap, session)
        except Exception:
            bootstrap['failure'] = traceback.format_exc()
            raise
        finally:
            atomic(folder / 'pdh-bootstrap.json', bootstrap)
            report['initialization_sha256'] = sha(folder / 'pdh-bootstrap.json')
        memory_reader = memory.Reader(tracker)
        began = time.monotonic()
        previous_timed = None
        with data.open('x', encoding='utf8', newline='\n') as stream:
            for index in range(args.max_samples):
                if stop.exists():
                    report['stop_request'] = read_json(stop)
                    break
                remaining = began + index - time.monotonic()
                if remaining > 0:
                    time.sleep(remaining)
                row = dict(index=index, started_utc=dt.datetime.now(dt.timezone.utc).isoformat(), monotonic_offset_s=time.monotonic() - began)
                try:
                    phase_before = read_json(control)
                    contract.require(set(phase_before) == {'schema', 'id', 'kind', 'window', 'recipe', 'expected_scenario'}, 'Exact collector phase control required')
                    contract.require(type(phase_before['schema']) is int and phase_before['schema'] == 1 and phase_before['kind'] in ['prepare', 'transition', 'warmup', 'stable', 'cleanup'], 'Unknown residency phase')
                    tree = tracker.snapshot()
                    owned = {entry['pid'] for entry in tree['owned']}
                    row.update(phase_before=phase_before, inventory_before=tree)
                    reference, state = http_object(folder)
                    row['http_reference'] = reference
                    row['worker_projection'] = c214.service(state, reference['sha256']) if state['phase'] == 'complete' and not state['busy'] else None
                    row['backend'] = scenario()
                    row['ui'] = page.evaluate(c214.UI_EXPRESSION)
                    c214.require(not report['javascript_errors'], 'CEF JavaScript exception during raw collection')
                    row['ram'] = {}
                    memory.collect(memory_reader, tree['owned'], row['ram'])
                    with pdh.Query() as query:
                        known = {entry['identity']['pid'] for entry in tracker.export()['records']}
                        paths = query.discover(known)
                        query.select(paths)
                        row.update(query.sample(), configured_counter_paths=sorted(paths), counter_metadata=copy.deepcopy(query.metadata))
                        row['inventory_after'] = tracker.snapshot()
                        row['native_history'] = tracker.export()
                        known = {entry['identity']['pid'] for entry in row['native_history']['records']}
                        row['counter_paths_after'] = sorted(query.discover(known))
                    gpu_lifetime.resolve(row, tracker)
                    known = {entry['identity']['pid'] for entry in row['native_history']['records']}
                    row.update(raw_gpu.sample(row, row['configured_counter_paths'], known))
                    row['owned_without_exposed_gpu_counter'] = sorted(known - {entry['pid'] for entry in paths.values() if entry['pid'] is not None})
                    gpu_lifetime.gpu_row(row, session)
                    phase_after = read_json(control)
                    row.update(phase_after=phase_after, boundary=phase_before != phase_after,
                               finished_utc=dt.datetime.now(dt.timezone.utc).isoformat())
                    c214.admit_row(row, previous_timed, index)
                    previous_timed = row
                    if phase_before == phase_after and phase_before['kind'] == 'stable':
                        c214.admit_service(row['worker_projection'], phase_before['recipe'], phase_before['expected_scenario'])
                        c214.admit_ui(row['ui'], row['worker_projection'], phase_before['recipe'], state['result']['result'])
                        c214.require(row['backend']['mode'] == 'atlas' and row['backend']['renderer_confirmed'], 'Backend/native connection changed')
                    stream.write(json.dumps(row, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')
                    stream.flush()
                    report['samples'] = index + 1
                    if not row['boundary']:
                        phase_count = phase_count + 1 if phase_before['id'] == previous_id else 1
                        previous_id = phase_before['id']
                    atomic(status, dict(schema=8, collector_pid=os.getpid(), session_engine_pid=session['app'], samples=index + 1,
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
        atomic(status, dict(schema=8, collector_pid=os.getpid(), samples=report['samples'], valid=False, failure=report['failure']))
    finally:
        page.__exit__(None, None, None)
        tracker.close()
        try:
            report['native_history'] = tracker.export()
            if data.exists():
                rows = [json.loads(line) for line in data.read_text(encoding='utf8').splitlines()]
                if report['valid']:
                    report['timing'] = timing.admit_rows(rows)
                    timing.admit_bootstrap(report['initialization'], session, rows[0])
                complete = [row for row in rows if not row.get('failure')]
                report['process_records'] = history_audit.sampled_ledger(complete, report['native_history']) if complete else []
        except Exception:
            report['history_failure'] = traceback.format_exc()
            report['valid'] = False
            report['completed'] = False
        tracker.close()
        report['data_sha256'] = sha(data) if data.exists() else None
        report['process_history_sha256'] = sha(folder / 'process-history.jsonl')
        atomic(out, report)
    print(json.dumps(dict(valid=report['valid'], samples=report['samples'], failure=report['failure'])), flush=True)
    return 0 if report['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
