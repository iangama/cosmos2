"""Offline native-RAM lifecycle, no-zero/no-retry and raw-projection refusals."""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import traceback
import zipfile

import expanded_residency_memory_audit as audit
import owned_process_memory as reader

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and len(args.label) <= 20 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
    folder = ROOT / f'output/is6-expanded-memory-offline-{args.label}'
    out = ROOT / f'evidence/is6-expanded-memory-offline-{args.label}.json'
    assert not folder.exists() and not out.exists()
    predecessor = ROOT / 'evidence/is6-expanded-timing-offline-20261114b.json'
    previous = json.loads(predecessor.read_text())
    assert previous['accepted'] and previous['completed']
    fixture_path = ROOT / 'evidence/is6-owned-memory-fixture-20261114c.json'
    fixture = json.loads(fixture_path.read_text())
    assert fixture['accepted'] and fixture['completed'] and all(p['code'] == 0 for p in fixture['child_exits'])
    names = ['scripts/verify-expanded-residency-memory.py', 'scripts/owned_process_memory.py',
             'scripts/expanded_residency_memory_audit.py', 'scripts/expanded_residency_history_audit_v2.py',
             'scripts/expanded_residency_contract_v4.py', 'scripts/collect_expanded_residency_v7.py',
             'scripts/expanded_residency_audit_v5.py', 'scripts/audit-expanded-residency-v5.py',
             'scripts/profile-expanded-residency-v6.py', 'scripts/run-expanded-residency-v6.py',
             'scripts/verify-expanded-residency-preflight-v8.py', 'scripts/prepare-expanded-residency-v7.py',
             'IS-6-PERCURSO-AMPLIADO16-RESIDENCIA-REVISAO-G.md',
             fixture_path.relative_to(ROOT).as_posix(), predecessor.relative_to(ROOT).as_posix()]
    sources = previous['source_sha256'] | fixture['source_sha256'] | {name: sha(ROOT / name) for name in names}
    assert all(sha(ROOT / name) == seal for name, seal in sources.items())
    for name in names:
        if name.endswith('.py'):
            ast.parse((ROOT / name).read_text())
    folder.mkdir()
    with zipfile.ZipFile(folder / 'executed-sources.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for name in sources:
            archive.write(ROOT / name, name)
    result = dict(accepted=False, completed=False, source_sha256=sources, checks=[], refusals=[],
                  scope='Offline RAM admission fixtures only. E and all previous original profiles remain refused.')

    def admit(value, witness):
        known = {r['identity']['pid']: r for r in witness['native_history']['records']}
        return audit.admit(value, {witness['identity']['pid']: witness['identity']}, known, *witness['interval'])

    def refuse(name, value, witness):
        try:
            admit(value, witness)
        except (ValueError, KeyError, TypeError, AssertionError) as error:
            result['refusals'].append(dict(name=name, error=str(error)))
        else:
            raise AssertionError('Invalid RAM accepted: ' + name)

    try:
        live, dead = fixture['witnesses']
        admit(live['ram'], live)
        admit(dead['ram'], dead)
        result['checks'].append('Real successful native RAM and explicit completed-before-read fixture admitted')
        closing = copy.deepcopy(live['ram'])
        entry = closing['processes'][0]
        entry['native_before'].update(code=0, exited_filetime=entry['read_started_filetime']-1000)
        entry['native_after'].update(code=0, exited_filetime=entry['read_started_filetime']-1000)
        admit(closing, live)
        result['checks'].append('Unsignaled native object does not use undefined exitTime as a completed-process proof')
        during, witness = copy.deepcopy(live['ram']), copy.deepcopy(live)
        entry = during['processes'][0]
        when = entry['read_finished_filetime']
        entry['native_after'].update(wait=0, code=0, exited_filetime=when)
        native = next(r for r in witness['native_history']['records'] if r['identity']['pid'] == entry['pid'])
        native['exit'] = dict(code=0, exited_filetime=when, observed_filetime=entry['native_after']['observed_filetime'])
        native['last_native'] = copy.deepcopy(entry['native_after'])
        assert admit(during, witness)['exits_during_read'] == 1
        assert during['sum_working_set_bytes'] == live['ram']['sum_working_set_bytes']
        result['checks'].append('Synthetic exit during successful read retains every measured byte in the conservative sum')
        c = copy.deepcopy(live['ram']); c['processes'][0]['status'] = 'read_failed'; c['processes'][0]['api_return'] = 0; refuse('API-failed-without-zero-substitution', c, live)
        c = copy.deepcopy(live['ram']); c['processes'][0]['api_called'] = False; refuse('RAM-API-not-called', c, live)
        c = copy.deepcopy(live['ram']); c['processes'][0]['created_filetime'] += 1; refuse('RAM-PID-reuse', c, live)
        c = copy.deepcopy(live['ram']); c['processes'][0]['native_before']['created_filetime'] += 1; refuse('RAM-native-identity-changed', c, live)
        c = copy.deepcopy(live['ram']); c['sum_working_set_bytes'] += 1; refuse('RAM-sum-mismatch', c, live)
        c = copy.deepcopy(live['ram']); c['processes'][0]['working_set_bytes'] += 1; refuse('RAM-working-set-projection', c, live)
        c = copy.deepcopy(live['ram']); c['processes'][0]['private_bytes'] += 1; refuse('RAM-private-projection', c, live)
        c = copy.deepcopy(live['ram']); c['processes'][0]['raw']['WorkingSetSize'] = -1; refuse('negative-native-RAM', c, live)
        c = copy.deepcopy(live['ram']); c['processes'][0]['raw']['cb'] = 72; refuse('wrong-native-struct-size', c, live)
        c = copy.deepcopy(live['ram']); c['processes'][0]['read_started_filetime'] = live['interval'][0]-1; refuse('RAM-outside-native-bracket', c, live)
        c = copy.deepcopy(live['ram']); c['processes'][0]['observation_finished_filetime'] = live['interval'][1]+1; refuse('RAM-outside-inventory', c, live)
        c = copy.deepcopy(live['ram']); c['processes'].append(copy.deepcopy(c['processes'][0])); refuse('duplicate-RAM-process', c, live)
        c = copy.deepcopy(live['ram']); c['processes'] = []; c['sum_working_set_bytes'] = 0; refuse('silently-missing-RAM-process', c, live)
        c = copy.deepcopy(live['ram']); c['processes'][0]['native_before']['wait'] = 0; refuse('measured-after-pre-read-completion', c, live)
        c = copy.deepcopy(dead['ram']); c['completed_before_read'][0]['working_set_bytes'] = 0; refuse('invented-zero-for-completed-object', c, dead)
        c = copy.deepcopy(dead['ram']); c['completed_before_read'][0]['native_before']['wait'] = 258; refuse('unsignaled-exclusion', c, dead)
        c = copy.deepcopy(dead['ram']); c['completed_before_read'][0]['native_before']['code'] = 7; refuse('nonzero-exit-exclusion', c, dead)
        c = copy.deepcopy(dead['ram']); c['completed_before_read'][0]['native_before']['exited_filetime'] = 0; refuse('missing-exit-FILETIME', c, dead)
        c = copy.deepcopy(dead['ram']); c['completed_before_read'][0]['native_after']['exited_filetime'] += 1; refuse('changed-final-exit-FILETIME', c, dead)
        c = copy.deepcopy(dead['ram']); c['completed_before_read'][0]['api_called'] = True; refuse('hidden-call-on-completed-object', c, dead)
        c = copy.deepcopy(live['ram']); c['model'] = 'unknown'; refuse('unknown-RAM-model', c, live)
        calls = []

        class FailedReader:
            def read(self, identity, value):
                calls.append(identity['pid'])
                value.update(copy.deepcopy(live['ram']['processes'][0]))
                value.pop('working_set_bytes'); value.pop('private_bytes')
                value.update(status='read_failed', api_return=0, api_error=87)
                return value

        failure = reader.collect(FailedReader(), [live['identity']], {})
        assert calls == [live['identity']['pid']] and failure['sum_working_set_bytes'] is None
        refuse('single-API-failure-kept-without-retry-or-sum', failure, live)
        result['checks'].append('Failed API called once and retained with null aggregate; no fabricated zero or retry')
        assert len(result['refusals']) >= 20
        assert all(sha(ROOT / name) == seal for name, seal in sources.items())
        result.update(accepted=True, completed=True)
    except Exception:
        result['failure'] = traceback.format_exc()
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}, ensure_ascii=False), flush=True)
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
