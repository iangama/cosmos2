"""Explicit pre-series PDH discovery and strict, unfiltered sample timing admission."""
import datetime as dt
import math
import time

import expanded_residency_contract_v3 as c
import expanded_residency_history_audit as history
import gpu_pdh_audit_dynamics16_base as raw

BOOTSTRAP_MAX_S = 10
now = lambda: dt.datetime.now(dt.timezone.utc).isoformat()


def stamp(value):
    result = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    c.require(result.tzinfo is not None and result.utcoffset().total_seconds() == 0, 'UTC initialization/sample witness required')
    return result.timestamp()


def initialize(record, read_control, read_scenario, tracker, query_factory):
    """Exactly one discovery; the API collecting a gauge is never invoked here."""
    began = time.perf_counter()
    record.update(schema=1, kind='pdh_provider_initialization', started_utc=now(), attempts=1, gauge_samples=0)
    try:
        record['phase_before'] = read_control()
        c.require(record['phase_before']['kind'] == 'prepare', 'PDH initialization must precede phase transitions')
        record['scenario_before'] = read_scenario()
        record['inventory_before'] = tracker.snapshot()
        known = {r['identity']['pid'] for r in tracker.export()['records']}
        record['known_processes'] = sorted(known)
        record['discovery_started_utc'] = now()
        discovery_began = time.perf_counter()
        with query_factory() as query:
            record['discovered_paths'] = query.discover(known)
        record['discovery_duration_s'] = time.perf_counter() - discovery_began
        record['discovery_finished_utc'] = now()
        record['inventory_after'] = tracker.snapshot()
        record['phase_after'] = read_control()
        record['scenario_after'] = read_scenario()
        record['native_history'] = tracker.export()
    finally:
        record.update(finished_utc=now(), duration_s=time.perf_counter()-began)


def admit_bootstrap(value, session, first_row=None):
    c.require(type(value['schema']) is int and value['schema'] == 1 and value['kind'] == 'pdh_provider_initialization' and not value.get('failure'), 'Initialization absent/failed')
    c.require(type(value['attempts']) is int and value['attempts'] == 1 and type(value['gauge_samples']) is int and value['gauge_samples'] == 0,
              'Initialization retried or discarded a gauge')
    a, b, x, y = map(stamp, [value['started_utc'], value['finished_utc'], value['discovery_started_utc'], value['discovery_finished_utc']])
    duration, discovery = value['duration_s'], value['discovery_duration_s']
    c.require(type(duration) in (int, float) and math.isfinite(duration) and 0 < duration <= BOOTSTRAP_MAX_S and abs((b-a)-duration) < .1,
              'Initialization duration/clock exceeds its declared budget')
    c.require(type(discovery) in (int, float) and math.isfinite(discovery) and 0 <= discovery <= duration and a <= x <= y <= b and abs((y-x)-discovery) < .1,
              'Initialization discovery clocks differ')
    c.require(value['phase_before'] == value['phase_after'] and value['phase_before']['kind'] == 'prepare', 'Phase changed during initialization')
    c.require(value['scenario_before'] == value['scenario_after'] and value['scenario_before']['mode'] == 'atlas' and value['scenario_before']['renderer_confirmed'] is True,
              'Scientific/native scenario changed during initialization')
    known = history.records(value['native_history'], session)
    for tree in [value['inventory_before'], value['inventory_after']]:
        identities = c.identities(tree['owned'], {session['app'], session['server']})
        c.require(all(pid in known and known[pid]['identity'] == identity for pid, identity in identities.items()), 'Initialization inventory identity differs')
        c.require(tree['started_filetime'] <= tree['finished_filetime'], 'Initialization inventory clocks reversed')
        c.require(a-.1 <= (tree['started_filetime']-116444736000000000)/1e7 <=
                  (tree['finished_filetime']-116444736000000000)/1e7 <= b+.1, 'Initialization inventory outside its recorded interval')
    c.require(value['inventory_before']['finished_filetime'] <= value['inventory_after']['started_filetime'], 'Initialization inventories reversed')
    c.require(value['native_history']['maximum_poll_gap_s'] <= .25, 'Initialization native observer cadence insufficient')
    c.require(type(value['known_processes']) is list and len(set(value['known_processes'])) == len(value['known_processes']) and set(value['known_processes']) <= set(known), 'Initialization ownership set differs')
    paths = value['discovered_paths']
    c.require(type(paths) is dict and paths, 'Initialization discovery is empty')
    exposed = set()
    for path, metadata in paths.items():
        identity = raw.parse_path(path)
        c.require(metadata['pid'] == identity['pid'] and metadata['instance'] == identity['instance'] and metadata['counter'] == identity['counter'] and metadata['localized_path'], 'Initialization path metadata differs')
        if identity['pid'] is not None:
            c.require(identity['pid'] in value['known_processes'], 'Initialization exposed a foreign GPU process')
            exposed.add((identity['pid'], identity['counter']))
    c.require((session['app'], 'dedicated usage') in exposed and (session['app'], 'shared usage') in exposed, 'Initialization engine GPU pair absent')
    c.require(all((pid, 'dedicated usage') in exposed and (pid, 'shared usage') in exposed for pid, _ in exposed), 'Initialization GPU pair incomplete')
    if first_row is not None:
        c.require(first_row['index'] == 0 and first_row['phase_before'] == value['phase_after'] and 0 <= stamp(first_row['started_utc']) - b <= 1,
                  'First raw observation missing/delayed after initialization')
    return dict(duration_s=duration, discovery_s=discovery, gauge_samples=0, attempts=1)


def admit_row(row, previous, index):
    c.require(type(row['index']) is int and row['index'] == index and not row.get('failure'), 'Missing/failed/reordered raw sample')
    a, b, gauge = map(stamp, [row['started_utc'], row['finished_utc'], row['utc']])
    c.require(a <= gauge <= b and 0 <= b-a < 1, 'Raw sample timing exceeds1Hz budget')
    offset = row['monotonic_offset_s']
    c.require(type(offset) in (int, float) and math.isfinite(offset) and offset >= 0, 'Invalid monotonic sample offset')
    c.require(row['boundary'] is (row['phase_before'] != row['phase_after']), 'Boundary marker differs')
    gap = None
    if previous is not None:
        gap = offset - previous['monotonic_offset_s']
        c.require(.5 <= gap <= 1.5 and abs((a-stamp(previous['started_utc']))-gap) < .1, 'Continuous sample cadence/UTC changed')
    else:
        c.require(offset < .25, 'First sample monotonic origin delayed')
    return b-a, gap


def admit_rows(rows):
    c.require(rows, 'No timed observations')
    durations, gaps = [], []
    previous = None
    for index, row in enumerate(rows):
        duration, gap = admit_row(row, previous, index)
        durations.append(duration)
        if gap is not None:
            gaps.append(gap)
        previous = row
    return dict(samples=len(rows), maximum_duration_s=max(durations), minimum_cadence_s=min(gaps) if gaps else None,
                maximum_cadence_s=max(gaps) if gaps else None)
