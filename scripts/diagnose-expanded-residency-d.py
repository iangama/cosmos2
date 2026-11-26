"""Read-only breakdown of refused D; never changes its admission or original data."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys

import expanded_residency_audit_v3 as audit
import expanded_residency_contract_v3 as c
import expanded_residency_history_audit as history

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
stamp = lambda s: dt.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


def main():
    out = ROOT / 'evidence/is6-expanded-residency-diagnosis-20261114d.json'
    assert not out.exists(), 'Preserve diagnostic'
    paths = [ROOT / ('evidence/is6-expanded-residency' + suffix + '-20261113d.json')
             for suffix in ['', '-collector', '-host', '-audit', '-plan']]
    report, collector, host, rejected, plan = [json.loads(p.read_text()) for p in paths]
    data = ROOT / collector['data_file']
    assert sha(data) == collector['data_sha256']
    assert not rejected['accepted'] and not host['accepted']
    seed, service = [json.loads((ROOT / plan[key]).read_text()) for key in ['seed', 'service']]
    result = dict(accepted=False, diagnostic_completed=False, original_admission='refused',
                  source_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in [Path(__file__), *paths, data]},
                  timing_failures=[], cadence_failures=[], other_failures=[], windows=[], transitions=[],
                  scope='Diagnostic only. Every original sample is retained; D remains refused regardless of subsidiary results.')

    def check(label, function):
        try:
            return function()
        except Exception as error:
            result['other_failures'].append(dict(check=label, error=str(error)))

    rows = [json.loads(line) for line in data.open(encoding='utf8')]
    metrics, durations = [], []
    for index, row in enumerate(rows):
        a, b, gauge = map(stamp, [row['started_utc'], row['finished_utc'], row['utc']])
        durations.append(b - a)
        if not (a <= gauge <= b and b - a < 1):
            result['timing_failures'].append(dict(index=index, phase=row['phase_before']['id'],
                                                duration_s=b-a, gauge_offset_s=gauge-a))
        if index:
            delta = row['monotonic_offset_s'] - rows[index-1]['monotonic_offset_s']
            if not (.5 <= delta <= 1.5 and abs((a-stamp(rows[index-1]['started_utc']))-delta) < .1):
                result['cadence_failures'].append(dict(index=index, delta_s=delta))
        metric = check('raw_' + str(index), lambda row=row: c.gpu_row(row, report['session']))
        if metric:
            metrics.append(metric)
    check('history', lambda: history.records(collector['native_history'], report['session']))
    result['lifecycle'] = check('ledger', lambda: c.ledger(collector['process_records'], rows, report['session']))
    for run in report['runs']:
        name = run['recipe']['name']
        frame = check(name + '_frames', lambda: c.frames(run['capture'], run['wall_interval_s'], steady=True))
        selected = check(name + '_coverage', lambda: audit.coverage(rows, run))
        check(name + '_provenance', lambda: audit.provenance(run['stable_control']['expected_scenario'], run['recipe'], seed, report.get('common4'), service))
        check(name + '_warmup', lambda: audit.phase_capture(rows, run['warmup']))
        result['windows'].append(dict(name=name, frames=frame, samples=None if selected is None else len(selected)))
    for transition in report['transitions']:
        check(transition['name'] + '_coverage', lambda: audit.phase_capture(rows, transition))
        result['transitions'].append(dict(name=transition['name'], seconds=transition['wall_interval_s'],
                                         frames=c.frames(transition['capture'], transition['wall_interval_s'], steady=False)))
    result.update(diagnostic_completed=True, samples=len(rows), duration_max_s=max(durations),
                  subsequent_sample_max_s=max(durations[1:]),
                  peaks_bytes={key: max(m[key] for m in metrics) for key in ['GPU_bytes', 'RAM_bytes']},
                  retained_native_processes=len(collector['native_history']['records']),
                  native_polls=collector['native_history']['polls'],
                  native_maximum_poll_gap_s=collector['native_history']['maximum_poll_gap_s'],
                  four_zero_exits=len(host['processes']) == 4 and all(v['code'] == 0 for v in host['processes'].values()),
                  restored_owner_view=host.get('owner_app_kept_open') is True and not host.get('cleanup_failure'))
    assert all(sha(ROOT / name) == seal for name, seal in result['source_sha256'].items())
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    print(json.dumps({k: v for k, v in result.items() if k not in ['source_sha256', 'windows', 'transitions']}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
