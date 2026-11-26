"""Raw GPU admission with narrowly witnessed post-gauge child birth/zero exit."""
import datetime as dt
import time

import expanded_residency_contract_v4 as base
import expanded_residency_history_audit_v2 as history_audit
import gpu_pdh_audit_dynamics16_base as raw_gpu

require = base.require
identities = base.identities


def filetime(value):
    stamp = dt.datetime.fromisoformat(value.replace('Z','+00:00'))
    require(stamp.tzinfo is not None and stamp.utcoffset() == dt.timedelta(0), 'UTC call boundary required')
    delta = stamp-dt.datetime(1601,1,1,tzinfo=dt.timezone.utc)
    return (delta.days*86400+delta.seconds)*10_000_000+delta.microseconds*10


def changes(value):
    configured, after = value['configured_counter_paths'], value['counter_paths_after']
    require(len(configured) == len(set(configured)) and len(after) == len(set(after)), 'Duplicate paths in discovery')
    removed, added = sorted(set(configured)-set(after)), sorted(set(after)-set(configured))
    return removed, added


def resolve(value, tracker):
    """No PDH operation here: retain original witnesses and wait only for handles."""
    removed, added = changes(value)
    if not removed and not added:
        value['counter_transition'] = None
        return
    pids = {raw_gpu.parse_path(path)['pid'] for path in removed}
    require(None not in pids and not pids.intersection(tracker.roots), 'Adapter/root counter changed')
    began = time.perf_counter()
    witness = dict(kind='native-counter-lifetime/1', started_filetime=tracker.clock(),
                   initial_inventory=value['inventory_after'], initial_history=value['native_history'],
                   removed_paths=removed, added_paths=added, budget_s=.25)
    value['counter_transition'] = witness
    try:
        while True:
            value['inventory_after'] = tracker.snapshot()
            value['native_history'] = tracker.export()
            records = {row['identity']['pid']:row for row in value['native_history']['records']}
            if all(pid in records and records[pid]['exit'] is not None and records[pid]['last_native']['wait'] == 0 for pid in pids):
                break
            require(time.perf_counter()-began < .25, 'Counter exit witness deadline exceeded')
            time.sleep(.005)
    finally:
        witness.update(finished_filetime=tracker.clock(), duration_s=time.perf_counter()-began)


def transition(value, session):
    removed, added = changes(value)
    witness = value.get('counter_transition')
    if not removed and not added:
        require(witness is None, 'Unneeded counter exception witness')
        return dict(removed_pids=[], added_after_query_pids=[])
    require(witness and witness['kind'] == 'native-counter-lifetime/1' and witness['budget_s'] == .25 and
            0 <= witness['duration_s'] <= .25 and witness['removed_paths'] == removed and witness['added_paths'] == added,
            'Counter change lacks its bounded original witness')
    roots = {session['app'],session['server']}
    records = history_audit.records(value['native_history'],session)
    before = identities(value['inventory_before']['owned'],roots)
    final = identities(value['inventory_after']['owned'],roots)
    initial = identities(witness['initial_inventory']['owned'],roots)
    initial_records = history_audit.records(witness['initial_history'],session)
    a,b = witness['started_filetime'],witness['finished_filetime']
    require(witness['initial_inventory']['finished_filetime'] <= a <= value['inventory_after']['started_filetime'] <=
            value['inventory_after']['finished_filetime'] <= b and abs((b-a)/1e7-witness['duration_s']) < .02,
            'Counter witness clocks differ')
    require(all(pid in records and record['identity'] == records[pid]['identity'] for pid,record in initial_records.items()),
            'Counter original handle identity changed')
    for identity in initial.values():
        require(identity['pid'] in initial_records and initial_records[identity['pid']]['identity'] == identity,
                'Counter original inventory differs from its native history')
    raw = {row['path']:row for row in value['raw_counter_samples']}
    offset = value['query_utc_filetime']-value['query_filetime']
    started,finished = filetime(value['call_started_utc']),filetime(value['call_finished_utc'])

    def pairs(paths):
        by_pid = {}
        for path in paths:
            parsed = raw_gpu.parse_path(path)
            require(parsed['kind'] == 'product' and parsed['pid'] not in roots, 'Adapter/root counter changed')
            by_pid.setdefault(parsed['pid'],{}).setdefault(parsed['instance'],set()).add(parsed['counter'])
        require(all(counters == {'dedicated usage','shared usage'} for instances in by_pid.values() for counters in instances.values()),
                'Counter lifetime exception has only half a pair')
        return by_pid

    lost, born = pairs(removed), pairs(added)
    require(not set(lost).intersection(born), 'Existing PID changed GPU contexts')
    for pid in lost:
        require(pid in before and pid in records and pid not in final, 'Removed counter lacks original/final process membership')
        record = records[pid];native = record['last_native'];end = record['exit']
        require(end is not None and native['wait'] == 0 and native['code'] == end['code'] == 0 and
                native['created_filetime'] == before[pid]['created_filetime'] and
                end['exited_filetime'] == native['exited_filetime'] <= native['observed_filetime'] <= b,
                'Removed GPU process lacks its exact signaled zero exit')
        require(not any(raw_gpu.parse_path(path)['pid'] == pid for path in value['counter_paths_after']),
                'Removed process still exposes other GPU paths')
        for path in removed:
            if raw_gpu.parse_path(path)['pid'] != pid:
                continue
            entry = raw[path]
            stamp = entry['raw_timestamp_filetime']+offset
            require(started-10 <= stamp <= finished+10 and before[pid]['created_filetime'] <= stamp < end['exited_filetime'],
                    'GPU raw value was not collected before the proven exit')
    for pid in born:
        require(pid not in before and pid in final and pid in records and records[pid]['identity'] == final[pid] and
                final[pid]['created_filetime'] > finished+9, 'New GPU context was not born after the full PDH call')
    return dict(removed_pids=sorted(lost), added_after_query_pids=sorted(born))


def gpu_row(row, session):
    roots = {session['app'], session['server']}
    before = identities(row['inventory_before']['owned'], roots)
    after = identities(row['inventory_after']['owned'], roots)
    known = history_audit.row(row, session)
    configured = row['configured_counter_paths']
    require(type(configured) is list and len(set(configured)) == len(configured), 'Duplicate PDH paths')
    transition(row, session)
    require(set(row['counter_metadata']) == set(configured), 'PDH metadata path set differs')
    for path, metadata in row['counter_metadata'].items():
        identity = raw_gpu.parse_path(path)
        require(metadata['kind'] == 0x10100 and type(metadata['kind']) is int, 'GPU counter type differs')
        require(metadata['pid'] == identity['pid'] and metadata['instance'] == identity['instance'] and metadata['counter'] == identity['counter'], 'GPU metadata identity differs')
        require(metadata['object'] == ('GPU Process Memory' if identity['kind'] == 'product' else 'GPU Adapter Memory'), 'GPU metadata object differs')
    totals = raw_gpu.sample(row, configured, set(known))
    require(any(raw_gpu.parse_path(path)['pid'] == session['app'] and raw_gpu.parse_path(path)['counter'] == 'dedicated usage' for path in configured), 'Engine dedicated GPU counter absent')
    exposed = {raw_gpu.parse_path(path)['pid'] for path in configured} - {None}
    require(set(row['owned_without_exposed_gpu_counter']) == set(known) - exposed, 'Unexposed process was silently assigned GPU zero')
    ram = row['ram']
    combined = ram['processes'] + ram['completed_before_read']
    require({entry['pid'] for entry in combined} == set(before) and len(combined) == len(before), 'RAM ownership differs')
    for entry in ram['processes']:
        require(entry['created_filetime'] == before[entry['pid']]['created_filetime'], 'RAM identity differs')
        raw_gpu.integer(entry['working_set_bytes'])
        raw_gpu.integer(entry['private_bytes'])
    require(ram['sum_working_set_bytes'] == sum(entry['working_set_bytes'] for entry in ram['processes']), 'RAM sum differs')
    require(all(row[key] == value for key, value in totals.items()), 'GPU raw projections differ')
    return dict(GPU_bytes=totals['product_dedicated_plus_shared_sum_bytes'], RAM_bytes=ram['sum_working_set_bytes'])

