"""Audit original schema7 data and native frames without re-running the experiment."""
import argparse
import hashlib
import json
from pathlib import Path
import traceback
import zipfile

import expanded_residency_audit_v4 as audit

ROOT = Path(__file__).resolve().parents[1]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and len(args.label) <= 20 and all(ch in 'abcdefghijklmnopqrstuvwxyz0123456789-' for ch in args.label)
    path = ROOT / f'evidence/is6-expanded-residency-{args.label}.json'
    out = ROOT / f'evidence/is6-expanded-residency-audit-{args.label}.json'
    assert not out.exists(), 'Preserve first audit'
    answer = dict(accepted=False, completed=False, input_sha256=sha(path))
    try:
        report = json.loads(path.read_text())
        plan = json.loads((ROOT / report['plan']).read_text())
        assert plan['accepted'] and report['engine_sha256'] == plan['engine_sha256']
        seals = report['source_sha256'] | report['protected_sha256']
        assert all(sha(ROOT / name) == seal for name, seal in seals.items())
        folder = ROOT / f'output/is6-expanded-residency-{args.label}'
        archive_path = folder / 'executed-sources.zip'
        assert sha(archive_path) == report['source_archive_sha256']
        with zipfile.ZipFile(archive_path) as archive:
            assert set(archive.namelist()) == set(report['source_sha256'])
            assert all(hashlib.sha256(archive.read(name)).hexdigest() == seal for name, seal in report['source_sha256'].items())
        collector_path = ROOT / report['collector_receipt']
        assert sha(collector_path) == report['collector_sha256']
        collector = json.loads(collector_path.read_text())
        assert collector['engine_sha256'] == plan['engine_sha256']
        assert all(sha(ROOT / name) == seal for name, seal in collector['source_sha256'].items())
        bootstrap = folder / 'pdh-bootstrap.json'
        assert sha(bootstrap) == collector['initialization_sha256']
        assert json.loads(bootstrap.read_text()) == collector['initialization']
        data = ROOT / collector['data_file']
        assert sha(data) == collector['data_sha256']
        journal = folder / 'process-history.jsonl'
        assert sha(journal) == collector['process_history_sha256']
        events = [json.loads(line) for line in journal.read_text().splitlines()]
        births = {event['record']['identity']['pid']:event['record'] for event in events if event['kind']=='birth'}
        exits = {event['pid']:event['exit'] for event in events if event['kind']=='exit'}
        assert len(births) == sum(event['kind']=='birth' for event in events)
        assert len(exits) == sum(event['kind']=='exit' for event in events)
        assert not any(event['kind']=='failure' for event in events)
        for record in collector['native_history']['records']:
            pid=record['identity']['pid']
            assert births[pid]['identity']==record['identity']
            assert exits.get(pid)==record['exit']
        rows = [json.loads(line) for line in data.read_text().splitlines()]
        seed, service = [json.loads((ROOT / plan[key]).read_text()) for key in ['seed', 'service']]
        answer.update(audit.audit(report, collector, rows, seed, service), data_sha256=sha(data),
                      collector_sha256=sha(collector_path), protected_files=len(report['protected_sha256']))
    except Exception:
        answer['failure'] = traceback.format_exc()
    out.write_text(json.dumps(answer, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    print(json.dumps(answer, ensure_ascii=False), flush=True)
    return 0 if answer['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
