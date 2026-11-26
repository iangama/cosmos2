"""Time three untouched candidate observations by stage; diagnosis, no GPU/FPS acceptance."""
import argparse
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import time
import traceback

import psutil
import collect_expanded_residency_v5 as original
from owned_process_history import History

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: dt.datetime.now(dt.timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and len(args.label) <= 20 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
    folder = ROOT / f'output/is6-expanded-pdh-startup-{args.label}'
    out = ROOT / f'evidence/is6-expanded-pdh-startup-{args.label}.json'
    assert not folder.exists() and not out.exists()
    session_path = ROOT / 'output/session.json'
    session = json.loads(session_path.read_text(encoding='utf-8-sig'))
    engine = psutil.Process(session['app'])
    assert engine.name().lower() == 'openspace.exe' and Path(engine.exe()).resolve().is_relative_to(ROOT)
    assert Path(session['serverScript']).resolve() == ROOT / 'output/is6-expanded-journey-product0.27.0/app/server.py'
    folder.mkdir()
    result = dict(diagnostic_completed=False, accepted=False, session=session, observations=[],
                  source_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in [Path(__file__), Path(original.__file__),
                                  Path(original.pdh.__file__), ROOT / 'scripts/owned_process_history.py']},
                  scope='Three diagnostic observations in a fresh Windows Python process. No scenario change and no admission of original D or sustained performance.')
    tracker = History(session, folder / 'process-history.jsonl')
    tracker.start()
    try:
        with (folder / 'observations.jsonl').open('x', encoding='utf8') as stream:
            for index in range(3):
                row = dict(index=index, started_utc=now(), stages={})

                def timed(name, function):
                    began = time.perf_counter()
                    try:
                        return function()
                    finally:
                        row['stages'][name] = time.perf_counter() - began

                began = time.perf_counter()
                tree = timed('inventory_before', tracker.snapshot)
                row['inventory_before'] = tree
                inputs = timed('scenario', lambda: dict(state=original.get('/api/state'), modules={name: original.get('/api/' + name + '/state') for name in ['spatial', 'layers', 'particles', 'solar-zone']}))
                inputs['navigation'] = timed('navigation', lambda: original.get('/api/navigation/state')) if inputs['state']['mode'] == 'atlas' else None
                row['scenario_inputs'] = inputs
                row.update(timed('projection', lambda: original.project(inputs, 'prepare')))

                def ram():
                    values = []
                    for identity in tree['owned']:
                        process = psutil.Process(identity['pid'])
                        assert abs(process.create_time()-identity['started_unix']) <= 5e-6
                        start = tracker.clock()
                        memory = process.memory_info()
                        values.append(dict(pid=identity['pid'], created_filetime=identity['created_filetime'], working_set_bytes=memory.rss, private_bytes=memory.private, read_started_filetime=start, read_finished_filetime=tracker.clock()))
                    return dict(processes=values, sum_working_set_bytes=sum(v['working_set_bytes'] for v in values))

                row['ram'] = timed('ram', ram)
                query = timed('query_construct', original.pdh.Query)
                with query:
                    known = {record['identity']['pid'] for record in tracker.export()['records']}
                    paths = timed('discover_before', lambda: query.discover(known))
                    timed('select', lambda: query.select(paths))
                    row.update(timed('sample', query.sample), configured_counter_paths=sorted(paths), counter_metadata=copy.deepcopy(query.metadata))
                    row['inventory_after'] = timed('inventory_after', tracker.snapshot)
                    row['native_history'] = tracker.export()
                    known = {record['identity']['pid'] for record in row['native_history']['records']}
                    row['counter_paths_after'] = sorted(timed('discover_after', lambda: query.discover(known)))
                row.update(original.raw_gpu.sample(row, row['configured_counter_paths'], known))
                row['owned_without_exposed_gpu_counter'] = sorted(known - {entry['pid'] for entry in paths.values() if entry['pid'] is not None})
                timed('validate', lambda: original.contract.gpu_row(row, session))
                row.update(finished_utc=now(), duration_s=time.perf_counter()-began)
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
                stream.flush()
                summary = {k: row[k] for k in ['index', 'started_utc', 'finished_utc', 'duration_s', 'stages']}
                result['observations'].append(summary)
                print(json.dumps(summary), flush=True)
                if index < 2:
                    time.sleep(max(0, 1-(time.perf_counter()-began)))
        assert json.loads(session_path.read_text(encoding='utf-8-sig')) == session
        assert all(sha(ROOT / name) == seal for name, seal in result['source_sha256'].items())
        result['diagnostic_completed'] = True
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        tracker.close()
        result['data_sha256'] = sha(folder / 'observations.jsonl')
        result['process_history_sha256'] = sha(folder / 'process-history.jsonl')
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    return 0 if result['diagnostic_completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
