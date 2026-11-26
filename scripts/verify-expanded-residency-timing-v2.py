"""Offline startup/no-discard and temporal refusals before a new native experiment."""
import argparse
import ast
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import traceback
import zipfile

import expanded_residency_timing as timing

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and len(args.label) <= 20 and all(ch in 'abcdefghijklmnopqrstuvwxyz0123456789-' for ch in args.label)
    out = ROOT / f'evidence/is6-expanded-timing-offline-{args.label}.json'
    folder = ROOT / f'output/is6-expanded-timing-offline-{args.label}'
    assert not out.exists() and not folder.exists()
    names = ['scripts/verify-expanded-residency-timing-v2.py', 'scripts/expanded_residency_timing.py',
             'scripts/collect_expanded_residency_v6.py', 'scripts/expanded_residency_audit_v4.py',
             'scripts/profile-expanded-residency-v5.py', 'scripts/audit-expanded-residency-v4.py',
             'scripts/run-expanded-residency-v5.py', 'IS-6-PERCURSO-AMPLIADO16-RESIDENCIA-REVISAO-F.md',
             'scripts/verify-expanded-residency-preflight-v7.py', 'scripts/prepare-expanded-residency-v6.py',
             'evidence/is6-expanded-residency-diagnosis-20261114d.json',
             'evidence/is6-expanded-pdh-startup-20261114a.json',
             'output/is6-expanded-pdh-startup-20261114a/observations.jsonl']
    predecessor = ROOT / 'evidence/is6-expanded-residency-ipc-preparation-20261113a.json'
    prior = json.loads(predecessor.read_text())
    assert prior['accepted'] and prior['completed']
    sources = dict(prior['source_sha256'])
    sources.update({p: sha(ROOT / p) for p in names})
    sources[predecessor.relative_to(ROOT).as_posix()] = sha(predecessor)
    assert all(sha(ROOT / name) == seal for name, seal in sources.items())
    folder.mkdir()
    for name in names:
        if name.endswith('.py'):
            ast.parse((ROOT / name).read_text())
    with zipfile.ZipFile(folder / 'executed-sources.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for name in sources:
            archive.write(ROOT / name, name)
    result = dict(accepted=False, completed=False, source_sha256=sources, checks=[], refusals=[],
                  scope='Offline startup and strict timing fixtures only; no native performance acceptance and D remains refused.')

    def refuse(name, call):
        try:
            call()
        except (ValueError, KeyError, TypeError, AssertionError, OSError) as error:
            result['refusals'].append(dict(name=name, error=str(error)))
        else:
            raise AssertionError('Invalid fixture accepted: ' + name)

    try:
        diagnostic = json.loads((ROOT / names[-2]).read_text())
        assert diagnostic['diagnostic_completed'] and diagnostic['accepted'] is False
        row = json.loads((ROOT / names[-1]).read_text().splitlines()[0])
        session = diagnostic['session']
        paths = {path: {k: value[k] for k in ['localized_path', 'instance', 'pid', 'object', 'counter']}
                 for path, value in row['counter_metadata'].items()}
        phase = dict(schema=1, id='fixture-prepare', kind='prepare', window=None, recipe=None, expected_scenario=None)
        calls = []

        class Query:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                calls.append('close')

            def discover(self, known):
                calls.append('discover')
                assert known == {r['identity']['pid'] for r in row['native_history']['records']}
                return copy.deepcopy(paths)

            def sample(self):
                raise AssertionError('Initialization must never collect/discard a gauge')

        class Tracker:
            def snapshot(self):
                tree = copy.deepcopy(row['inventory_before'])
                filetime = 116444736000000000 + int(dt.datetime.now(dt.timezone.utc).timestamp()*1e7)
                tree.update(started_filetime=filetime, finished_filetime=filetime)
                return tree

            def export(self):
                witness = copy.deepcopy(row['native_history'])
                # This is a synthetic bounded-cadence fixture, not a claim about diagnostic timing.
                witness['maximum_poll_gap_s'] = .01
                return witness

        good = {}
        timing.initialize(good, lambda: copy.deepcopy(phase), lambda: copy.deepcopy(row['scenario']), Tracker(), Query)
        timing.admit_bootstrap(good, session)
        assert calls == ['discover', 'close'] and good['gauge_samples'] == 0
        result['checks'].append('One discovery in prepare with retained native evidence; no value collection or retry')
        calls.clear()

        class BrokenQuery(Query):
            def discover(self, known):
                calls.append('discover')
                raise OSError('Provider refusal fixture')

        failed = {}
        refuse('provider-error-without-retry', lambda: timing.initialize(failed, lambda: phase, lambda: row['scenario'], Tracker(), BrokenQuery))
        assert calls == ['discover', 'close'] and failed['attempts'] == 1 and 'finished_utc' in failed
        c = copy.deepcopy(good); c['attempts'] = 2; refuse('initialization-retry', lambda: timing.admit_bootstrap(c, session))
        c = copy.deepcopy(good); c['gauge_samples'] = 1; refuse('discarded-bootstrap-gauge', lambda: timing.admit_bootstrap(c, session))
        c = copy.deepcopy(good); c['duration_s'] = 11; refuse('initialization-over-budget', lambda: timing.admit_bootstrap(c, session))
        c = copy.deepcopy(good); c['phase_after']['id'] = 'changed'; refuse('phase-change-during-initialization', lambda: timing.admit_bootstrap(c, session))
        c = copy.deepcopy(good); c['scenario_after']['atlas_anchor'] = 'Moon'; refuse('scientific-change-during-initialization', lambda: timing.admit_bootstrap(c, session))
        c = copy.deepcopy(good); c['discovered_paths'] = {}; refuse('empty-provider-discovery', lambda: timing.admit_bootstrap(c, session))
        c = copy.deepcopy(good); c['native_history']['maximum_poll_gap_s'] = 1; refuse('initializer-observer-gap', lambda: timing.admit_bootstrap(c, session))
        c = copy.deepcopy(good); c['known_processes'].append(999999); refuse('unknown-initialization-process', lambda: timing.admit_bootstrap(c, session))
        c = copy.deepcopy(good); next(iter(c['discovered_paths'].values()))['pid'] = 999999; refuse('foreign-path-metadata', lambda: timing.admit_bootstrap(c, session))
        c = copy.deepcopy(good); c['finished_utc'] = good['started_utc']; refuse('initializer-clock-mismatch', lambda: timing.admit_bootstrap(c | dict(duration_s=2), session))
        start = dt.datetime.fromisoformat(good['finished_utc']) + dt.timedelta(seconds=.01)
        stamp = lambda seconds: (start + dt.timedelta(seconds=seconds)).isoformat()
        rows = [dict(index=i, started_utc=stamp(i), utc=stamp(i+.02), finished_utc=stamp(i+.05),
                     monotonic_offset_s=i+.001, phase_before=copy.deepcopy(phase), phase_after=copy.deepcopy(phase), boundary=False)
                for i in range(30)]
        timing.admit_bootstrap(good, session, rows[0])
        assert timing.admit_rows(rows)['samples'] == 30
        result['checks'].append('All30fixture rows, including index0, satisfy the unchanged duration/cadence bounds')
        c = copy.deepcopy(rows); c[0]['finished_utc'] = stamp(1.336167); refuse('original-D-cold-duration', lambda: timing.admit_rows(c))
        c = copy.deepcopy(rows); c[1]['utc'] = stamp(2); refuse('gauge-outside-observation', lambda: timing.admit_rows(c))
        c = copy.deepcopy(rows); c.pop(4); refuse('dropped-observation', lambda: timing.admit_rows(c))
        c = copy.deepcopy(rows); c[1]['monotonic_offset_s'] = 2; refuse('cadence-gap', lambda: timing.admit_rows(c))
        c = copy.deepcopy(rows); c[1]['monotonic_offset_s'] = 1.2; refuse('UTC-monotonic-drift', lambda: timing.admit_rows(c))
        c = copy.deepcopy(rows); c[1]['boundary'] = True; refuse('boundary-mismatch', lambda: timing.admit_rows(c))
        c = copy.deepcopy(rows); c[1]['failure'] = 'fixture'; refuse('failed-observation-retained', lambda: timing.admit_rows(c))
        c = copy.deepcopy(rows); c[0]['monotonic_offset_s'] = .5; refuse('delayed-monotonic-origin', lambda: timing.admit_rows(c))
        c = copy.deepcopy(rows[0]); c['index'] = 1; refuse('missing-first-row', lambda: timing.admit_bootstrap(good, session, c))
        c = copy.deepcopy(rows[0]); c['started_utc'] = stamp(2); refuse('gap-after-initialization', lambda: timing.admit_bootstrap(good, session, c))
        c = copy.deepcopy(rows[0]); c['phase_before']['id'] = 'changed'; refuse('transition-before-prepare-samples', lambda: timing.admit_bootstrap(good, session, c))
        assert all(sha(ROOT / name) == seal for name, seal in sources.items())
        result.update(accepted=True, completed=True)
    except Exception:
        result['failure'] = traceback.format_exc()
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}, ensure_ascii=False), flush=True)
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
