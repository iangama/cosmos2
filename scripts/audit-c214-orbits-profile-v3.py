"""Recompute C2-14 admission from raw frames, HTTP objects, CEF and native RAM/PDH."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import traceback

import c214_profile_contract as c
import c214_profile_history_v3 as native_polls
import c214_profile_gpu_v2 as gpu_lifetime
import expanded_residency_history_audit_v2 as history
import expanded_residency_timing as timing
from expanded_residency_audit_v5 import trace

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
stamp = timing.stamp


def audit(report, collected, rows):
    c.require(report['completed'] is True and report['collector_exit'] == 0 and not report.get('failure') and
              not report.get('cleanup_failure') and not report['page_errors'], 'Profile executor did not complete')
    c.require(collected['schema'] == 9 and collected['valid'] and collected['completed'] and collected['failure'] is None and not collected['javascript_errors'] and
              collected.get('stop_request') == dict(reason='c214_windows_complete'), 'Collector did not complete by the sealed stop marker')
    c.require(collected['session'] == report['session'] and len(rows) == collected['samples'] and len(rows) >= 384,
              'Raw collector/session/sample count differs')
    initialization = timing.admit_bootstrap(collected['initialization'], report['session'], rows[0])
    objects = {}
    metrics, durations, gaps = [], [], []
    previous = None
    counter_transitions = []
    for index, row in enumerate(rows):
        duration, gap = c.admit_row(row, previous, index)
        durations.append(duration)
        if gap is not None:
            gaps.append(gap)
        previous = row
        c.require(row['phase_before']['kind'] in ['prepare','transition','warmup','stable','cleanup'], 'Unknown raw phase')
        reference = row['http_reference']
        path = (ROOT/reference['path']).resolve()
        folder = ROOT/Path(collected['data_file']).parent/'http-objects'
        c.require(path.is_relative_to(folder.resolve()) and path.name == reference['sha256']+'.json', 'Foreign HTTP object')
        if reference['sha256'] not in objects:
            c.require(sha(path) == reference['sha256'] and path.stat().st_size == reference['bytes'], 'Raw HTTP bytes differ')
            objects[reference['sha256']] = json.loads(path.read_bytes())
        value = objects[reference['sha256']]
        projection = c.service(value, reference['sha256']) if value['phase'] == 'complete' and not value['busy'] else None
        c.require(projection == row['worker_projection'], 'Worker projection differs from raw HTTP')
        if not row['boundary'] and row['phase_before']['kind'] == 'stable':
            c.admit_service(projection, row['phase_before']['recipe'], row['phase_before']['expected_scenario'])
            c.admit_ui(row['ui'], projection, row['phase_before']['recipe'], value['result']['result'])
            c.require(row['backend']['mode'] == 'atlas' and row['backend']['renderer_confirmed'], 'Backend/native state differs')
        native = gpu_lifetime.gpu_row(row, report['session'])
        if row.get('counter_transition'):
            counter_transitions.append(dict(sample=index, **gpu_lifetime.transition(row, report['session'])))
        metrics.append(dict(GPU_bytes=row['product_dedicated_sum_bytes'], RAM_bytes=native['RAM_bytes'],
                            GPU_dedicated_plus_shared_bytes=row['product_dedicated_plus_shared_sum_bytes']))
    history.records(collected['native_history'], report['session'])
    c.require(collected['native_history']['polls'] > len(rows) and collected['native_history']['maximum_poll_gap_s'] <= .25,
              'Native process history cadence insufficient')
    lifecycle = c.native.ledger(collected['process_records'], rows, report['session'])
    peaks = {key:max(value[key] for value in metrics) for key in metrics[0]}
    c.require(peaks['RAM_bytes'] <= c.LIMITS['RAM_bytes'] and peaks['GPU_bytes'] <= c.LIMITS['GPU_bytes'], 'Native memory limit exceeded')
    c.require([run['recipe'] for run in report['runs']] == c.WINDOWS, 'Four-window recipe/order differs')
    results = []
    for run in report['runs']:
        recipe, control = run['recipe'], run['stable_control']
        selected = [row for row in rows if not row['boundary'] and row['phase_before'] == control]
        c.require(len(selected) >= 66, 'Stable phase has fewer than 66 complete samples')
        selected = selected[:66]
        start, finish = stamp(run['capture_start_utc']), stamp(run['capture_end_utc'])
        c.require(abs((finish-start)-run['wall_interval_s']) < .1 and finish > start, 'Native capture clocks disagree')
        c.require(stamp(selected[2]['finished_utc']) <= start and stamp(selected[3]['started_utc']) >= start-.15 and
                  stamp(selected[-1]['started_utc']) >= finish, 'First 66 observations do not bracket the full native capture')
        frame = c.native.frames(run['capture'], run['wall_interval_s'], steady=True)
        trace(run['trace'])
        warm = run['warmup']
        c.require(30 <= warm['wall_interval_s'] < 31, 'Warmup duration differs')
        warm_frame = c.native.frames(warm['capture'], warm['wall_interval_s'], steady=False)
        trace(warm['trace'])
        c.require(abs(warm_frame['interval_s']-warm['wall_interval_s']) < .5, 'Warmup frame interval differs')
        warm_rows = [row for row in rows if not row['boundary'] and row['phase_before'] == warm['control']]
        c.require(warm_rows and stamp(warm_rows[0]['finished_utc']) <= stamp(warm['capture_start_utc']) and
                  stamp(warm_rows[-1]['finished_utc'])+1.15 >= stamp(warm['capture_end_utc']), 'Warmup raw coverage absent')
        c.require(len(run['samples']) == 4, 'Four native/CEF witnesses required')
        body = objects[control['expected_scenario']['body_sha256']]['result']['result']
        for part, witness in enumerate(run['samples']):
            c.require(abs(witness['offset_s']-20*part) < .5, 'Native witness offset differs')
            c.admit_ui(witness['ui'], control['expected_scenario'], recipe, body)
            c.require(witness['native']['camera']['Anchor'] == selected[0]['backend']['anchor'], 'Native camera anchor differs')
        playback = c.animation(run['samples'][0]['ui'], run['samples'][-1]['ui'], run['samples'][-1]['offset_s']-run['samples'][0]['offset_s'])
        results.append(dict(name=recipe['name'], first_sample=selected[0]['index'], last_sample=selected[-1]['index'], frames=frame, playback=playback))
    return dict(accepted=True, windows=results, samples=len(rows), http_objects=len(objects), peaks=peaks,
                initialization=initialization, lifecycle=lifecycle, counter_transitions=counter_transitions,
                timing=dict(maximum_raw_duration_s=max(durations), minimum_cadence_s=min(gaps), maximum_cadence_s=max(gaps)),
                native_poll_gap_s=collected['native_history']['maximum_poll_gap_s'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    c.require(args.label and len(args.label) <= 20 and all(ch in 'abcdefghijklmnopqrstuvwxyz0123456789-' for ch in args.label), 'Invalid audit label')
    out = ROOT/f'evidence/c214-orbits-profile-audit-{args.label}.json'
    c.require(not out.exists(), 'Preserve original audit')
    answer = dict(accepted=False, completed=False, label=args.label)
    try:
        report_path = ROOT/f'evidence/c214-orbits-profile-{args.label}.json'
        collector_path = ROOT/f'evidence/c214-orbits-profile-collector-{args.label}.json'
        report, collected = [json.loads(p.read_text()) for p in [report_path, collector_path]]
        c.require(all(sha(ROOT/name) == seal for name, seal in report['source_sha256'].items()), 'Executor sources changed')
        c.require(all(sha(ROOT/name) == seal for name, seal in collected['source_sha256'].items()), 'Collector sources changed')
        folder = ROOT/f'output/c214-orbits-profile-{args.label}'
        c.require(sha(folder/'executed-sources.zip') == report['source_archive_sha256'], 'Executed source archive differs')
        data = ROOT/collected['data_file']
        c.require(sha(data) == collected['data_sha256'] and sha(folder/'process-history.jsonl') == collected['process_history_sha256'], 'Raw native files differ')
        c.require(sha(folder/'pdh-bootstrap.json') == collected['initialization_sha256'] and
                  json.loads((folder/'pdh-bootstrap.json').read_text()) == collected['initialization'], 'Raw initialization differs')
        rows = [json.loads(line) for line in data.read_text(encoding='utf8').splitlines()]
        poll_path=folder/'process-polls.jsonl'
        c.require(sha(poll_path)==collected['native_poll_history_sha256'],'Raw native poll file differs')
        polls=[json.loads(line) for line in poll_path.read_text().splitlines()]
        answer['raw_poll_admission']=native_polls.admit(polls,collected['native_history'],collected['initialization'],rows)
        answer.update(audit(report, collected, rows), completed=True,
                      executor_sha256=sha(report_path), collector_sha256=sha(collector_path))
    except Exception:
        answer['failure'] = traceback.format_exc()
    out.write_text(json.dumps(answer, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
    print(json.dumps(answer, ensure_ascii=False), flush=True)
    return 0 if answer['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
