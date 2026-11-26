"""Independent admission of the ten-window experiment; no native or PDH calls."""
import copy
import datetime as dt
import math

import expanded_residency_contract_v2 as c
from expanded_residency_projection import project


def timestamp(value):
    result = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    c.require(result.tzinfo is not None and result.utcoffset().total_seconds() == 0, 'UTC witness required')
    return result.timestamp()


def trace(value):
    c.require(value['truncated'] is False and value['stats'], 'Native CPU trace absent/truncated')
    for entry in value['stats'].values():
        number = entry['count']
        c.require(type(number) in (int, float) and math.isfinite(number) and number > 0 and number == int(number), 'Invalid native stage count')
        c.require(all(math.isfinite(entry[key]) for key in ['maximum_s', 'total_s']) and
                  0 <= entry['maximum_s'] <= entry['total_s'], 'Invalid native stage durations')


def phase_equal(actual, archived):
    actual, archived = copy.deepcopy(actual), c.physical(archived)
    # Loading an archived checkpoint must issue a fresh editing identity.
    c.require(actual.pop('edit_token') != archived.pop('edit_token'), 'Archived edit token was reused')
    c.require(actual == archived, 'Archived orbital physics changed')


def coverage(rows, run):
    phase = run['stable_control']
    selected = [row for row in rows if not row['boundary'] and row['phase_before'] == phase]
    c.require(len(selected) >= 66, 'Stable phase has fewer than66 complete samples')
    selected = selected[:66]
    a, b = timestamp(run['capture_start_utc']), timestamp(run['capture_end_utc'])
    c.require(b > a and abs((b - a) - run['wall_interval_s']) < .1, 'Capture clocks disagree')
    c.require(timestamp(selected[2]['finished_utc']) <= a and timestamp(selected[3]['started_utc']) >= a - .15,
              'First66 samples do not retain the three-sample pre-roll')
    c.require(timestamp(selected[-1]['started_utc']) >= b and timestamp(selected[0]['started_utc']) < a,
              'First66 samples do not cover the full native capture')
    identity = selected[0]['inventory_before']['owned']
    paths = selected[0]['configured_counter_paths']
    for row in selected:
        c.require(row['inventory_before']['owned'] == identity and row['configured_counter_paths'] == paths,
                  'Population/counter paths changed during stable66')
        c.admit_scenario(row['scenario'], run['recipe'], phase['expected_scenario'])
    return selected


def expected_anchor(value, recipe, seed):
    name = recipe['instrument']
    if recipe['mode'] == 'atlas':
        return 'Earth'
    if name == 'spatial':
        return value['modules'][name]['scene']['focus']
    if name == 'layers':
        return value['modules'][name]['scene']['spatial_frame'].replace('SpatialFrame_', 'SpatialFocus_')
    if name == 'particles':
        return value['modules'][name]['view']['native_nodes']['focus']
    if name == 'solar-zone':
        return value['modules'][name]['scene']['node']
    return 'LabFrame' if not recipe.get('body') else next(body['scene_node'] for body in seed['checkpoint16']['bodies']
                                                        if body['reference_id'] == 'sol:naif:' + recipe['body'])


def phase_capture(rows, stage):
    control = stage['control']
    selected = [row for row in rows if not row['boundary'] and row['phase_before'] == control]
    c.require(selected and timestamp(selected[0]['finished_utc']) <= timestamp(stage['capture_start_utc']) and
              timestamp(selected[-1]['finished_utc']) + 1.5 >= timestamp(stage['capture_end_utc']),
              'Native interval lacks its acknowledged continuous phase coverage')


def provenance(value, recipe, seed, common4, service):
    c.admit_scenario(value, recipe)
    if recipe['mode'] == 'atlas':
        c.require(value['atlas_anchor'] == 'Earth' and value['atlas_epoch_et_tdb_s'] ==
                  seed['checkpoint16']['atlas_initial']['source']['epoch']['et_tdb_s'], 'Atlas Earth/epoch differs')
        return
    if recipe['bodies'] == 16:
        phase_equal(value['physics'], seed['checkpoint16'])
    else:
        c.require(value['physics'] == common4, 'The shared live four-body phase changed')
        phase_equal(common4, seed['common_source_phase4'])
    name = recipe['instrument']
    if name == 'spatial':
        c.require(value['modules'][name]['artifact']['configuration'] == service['recipe_before_execution']['spatial_configuration'], 'Simple mesh configuration differs')
    if name == 'layers':
        artifact = value['modules'][name]['artifact']
        c.require(artifact['live_source_guard'] == {key: common4[key] for key in ['system_id', 'edit_token', 'revision', 'time']} |
                  dict(frame=common4['contract']['frame']), 'Live layer source guard differs')
        if name == 'layers':
            c.require(artifact['archived'] is True and artifact['sha256'] == seed['instrument_checkpoints'][recipe['body']]['layer_sha256'] and
                      artifact['visible'] == dict(spatial=True, magnetic=True), 'Archived coordinated layers differ')
    elif name == 'particles':
        experiment = value['modules'][name]['experiment']
        c.require(experiment['phase'] == seed['instrument_checkpoints'][recipe['body']]['particle_phase'], 'Archived particle phase changed')
    elif name == 'solar-zone':
        worker = value['modules'][name]['worker']
        c.require(all(worker[key] == seed['solar_checkpoint'][key] for key in ['artifact_id', 'artifact_sha256', 'sample', 'source']),
                  'Archived nuclear artifact/sample/source changed')
        c.require(worker['configuration'] == service['recipe_before_execution']['solar_configuration'], 'Nuclear recipe differs')


def audit(report, collector, rows, seed, service):
    c.require(report['completed'] is True and not report.get('failure') and not report.get('cleanup_failure') and
              not report['page_errors'], 'Executor did not complete cleanly')
    c.require(collector['schema'] == 5 and collector['valid'] is True and collector['completed'] is True and
              collector['failure'] is None and collector.get('stop_request') == dict(reason='ten_windows_complete'),
              'Continuous collector did not stop by the declared completion marker')
    c.require(collector['session'] == report['session'] and len(rows) == collector['samples'] and len(rows) > 660,
              'Collector/session/row coverage differs')
    previous = None
    metrics = []
    for index, row in enumerate(rows):
        c.require(row['index'] == index and not row.get('failure'), 'Missing/failed/reordered raw sample')
        a, b, gauge = map(timestamp, [row['started_utc'], row['finished_utc'], row['utc']])
        c.require(a <= gauge <= b and b - a < 1, 'Raw sample timing exceeds1Hz budget')
        c.require(row['boundary'] is (row['phase_before'] != row['phase_after']), 'Boundary marker differs')
        if previous:
            delta = row['monotonic_offset_s'] - previous['monotonic_offset_s']
            c.require(.5 <= delta <= 1.5 and abs((a - timestamp(previous['started_utc'])) - delta) < .1,
                      'Continuous sample cadence/UTC changed')
        projection = project(row['scenario_inputs'], row['phase_before']['kind'])
        c.require(all(row[key] == value for key, value in projection.items()), 'Raw scenario projection differs')
        metrics.append(c.gpu_row(row, report['session']))
        previous = row
    lifecycle = c.ledger(collector['process_records'], rows, report['session'])
    peaks = {key: max(row[key] for row in metrics) for key in ['GPU_bytes', 'RAM_bytes']}
    c.require(all(value <= c.LIMITS[key] for key, value in peaks.items()), 'Journey memory limit exceeded')
    c.require([run['recipe'] for run in report['runs']] == c.WINDOWS, 'Ten-window recipe/order differs')
    results = []
    for run in report['runs']:
        value = run['stable_control']['expected_scenario']
        provenance(value, run['recipe'], seed, report.get('common4'), service)
        selected = coverage(rows, run)
        frame = c.frames(run['capture'], run['wall_interval_s'], steady=True)
        trace(run['trace'])
        warmup = run['warmup']
        phase_capture(rows, warmup)
        c.require(30 <= warmup['wall_interval_s'] < 31, 'Warmup duration differs')
        warm_metrics = c.frames(warmup['capture'], warmup['wall_interval_s'], steady=False)
        c.require(abs(warm_metrics['interval_s'] - warmup['wall_interval_s']) < .5, 'Warmup frame coverage differs')
        trace(warmup['trace'])
        c.require(len(run['samples']) == 4, 'Four native scene witnesses required')
        c.require(run['expected_anchor'] == expected_anchor(value, run['recipe'], seed), 'Native anchor differs from the declared scene')
        for part, sample in enumerate(run['samples']):
            c.require(abs(sample['offset_s'] - 20 * part) < .5, 'Native witness clock differs')
            c.require(sample['native']['camera']['Anchor'] == run['expected_anchor'] and sample['ui']['scale'] == '1' and
                      sample['ui']['mode'] == run['recipe']['mode'] and sample['ui']['width'] == 1920 and sample['ui']['height'] == 1080,
                      'Native anchor/CEF presentation differs')
            c.admit_scenario(sample['scenario'], run['recipe'], value)
        results.append(dict(name=run['recipe']['name'], first_sample=selected[0]['index'], last_sample=selected[-1]['index'], frames=frame))
    transitions = []
    c.require(len(report['transitions']) == 11, 'Ten entries plus final cleanup transition required')
    for transition in report['transitions']:
        phase_capture(rows, transition)
        c.require(0 < transition['wall_interval_s'] <= transition['budget_s'] and transition['budget_s'] in [70, 750],
                  'Transition conclusion budget exceeded')
        frame = c.frames(transition['capture'], transition['wall_interval_s'], steady=False)
        c.require(abs(frame['interval_s'] - transition['wall_interval_s']) < .5, 'Transition frame coverage differs')
        trace(transition['trace'])
        transitions.append(dict(name=transition['name'], seconds=transition['wall_interval_s'], frames=frame))
    c.require(len(report['cleanups']) == 7 and all(item['nodes'] and not any(item['nodes'].values()) for item in report['cleanups']),
              'Native instrument cleanup witnesses absent')
    # Exact camera/visibility return is checked again from the recorded contexts.
    for item in report['cleanups']:
        a, b = item['before'], item['after']
        c.require(a['flags'] == b['flags'] and set(a['camera']) == set(b['camera']), 'Instrument visibility/camera shape changed')
        for key, value in a['camera'].items():
            c.require(all(abs(x-y) <= 1e-12 for x,y in zip(value,b['camera'][key],strict=True)) if key == 'Up' else value == b['camera'][key],
                      'Instrument did not restore its camera')
    return dict(accepted=True, completed=True, windows=results, transitions=transitions, peaks_bytes=peaks, lifecycle=lifecycle,
                scope='Paused residence and stable native frames only; all transition stalls are reported. Does not close IS6, K5A or V1.')
