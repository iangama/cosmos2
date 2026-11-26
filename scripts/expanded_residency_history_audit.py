"""Pure temporal membership checks for retained ordinary process handles."""
from pathlib import PureWindowsPath

import expanded_residency_contract_v2 as base
import gpu_pdh_audit_dynamics16_base as raw


def records(history, session):
    values = history['records']
    base.require(type(values) is list and values, 'Retained native history absent')
    by_pid = {record['identity']['pid']: record for record in values}
    base.require(len(by_pid) == len(values), 'Duplicate/reused retained PID')
    identities = base.identities([record['identity'] for record in values], {session['app'],session['server']})
    for pid, record in by_pid.items():
        identity = identities[pid]
        base.require(PureWindowsPath(identity['executable']).name.lower() == identity['name'].lower(), 'Native executable/name differs')
        raw.integer(record['first_observed_filetime'], minimum=identity['created_filetime'])
        native = record['last_native']
        base.require(native['created_filetime'] == identity['created_filetime'] and type(native['wait']) is int and native['wait'] in [0,258], 'Retained handle creation/wait differs')
        raw.integer(native['code'])
        raw.integer(native['observed_filetime'], minimum=record['first_observed_filetime'])
        if record['exit'] is not None:
            end = record['exit']
            base.require(type(end['code']) is int and end['code'] == 0 and native['wait'] == 0 and native['code'] == 0,
                         'Nonzero or unsignaled retained process exit')
            raw.integer(end['exited_filetime'], minimum=identity['created_filetime'])
            base.require(end['exited_filetime'] == native['exited_filetime'] <= native['observed_filetime'], 'Retained process exit clocks differ')
        else:
            base.require(native['wait'] == 258, 'Signaled native exit lacks proof')
    return by_pid


def row(value, session):
    history = records(value['native_history'], session)
    roots = {session['app'],session['server']}
    before = base.identities(value['inventory_before']['owned'], roots)
    after = base.identities(value['inventory_after']['owned'], roots)
    a, b = value['inventory_before']['started_filetime'], value['inventory_after']['finished_filetime']
    base.require(a <= value['inventory_before']['finished_filetime'] <= b and a <= value['inventory_after']['started_filetime'] <= b,
                 'Native inventory intervals overlap backwards')
    for pid, identity in (before | after).items():
        base.require(pid in history and history[pid]['identity'] == identity, 'Sampled identity differs from retained handle')
    for pid in set(before)-set(after):
        end = history[pid]['exit']
        base.require(end is not None and a <= end['exited_filetime'] <= b, 'Process disappeared without an interval exit proof')
    for pid in set(after)-set(before):
        base.require(a <= after[pid]['created_filetime'] <= b, 'Process appeared outside the observed creation interval')
    for tree in [value['inventory_before'], value['inventory_after']]:
        for excluded in tree['excluded_completed']:
            pid = excluded['identity']['pid']
            base.require(pid in history and excluded['identity'] == history[pid]['identity'] and excluded['exit'] == history[pid]['exit'],
                         'Completed Toolhelp candidate lacks original native proof')
            base.require(excluded['entry'] == {key: excluded['identity'][key] for key in ['pid','parent','name']}, 'Completed Toolhelp entry changed')
            base.require(excluded['exit']['exited_filetime'] <= tree['finished_filetime'], 'Excluded candidate had not exited')
        for excluded in tree['excluded_old_parent_links']:
            base.require(excluded['identity']['created_filetime'] < excluded['parent_created_filetime'], 'Old parent-link exclusion lacks temporal proof')
    for memory in value['ram']['processes']:
        pid = memory['pid']; end = history[pid]['exit']
        base.require(a <= memory['read_started_filetime'] <= memory['read_finished_filetime'] <= b, 'RAM read clocks differ')
        if end is not None:
            base.require(memory['read_started_filetime'] <= end['exited_filetime'], 'RAM was read after the process ended')
    return history


def sampled_ledger(rows, history):
    by_pid = {record['identity']['pid']: record for record in history['records']}
    seen = {}
    for index, value in enumerate(rows):
        for identity in value['inventory_after']['owned']:
            pid = identity['pid']
            if pid not in seen:
                seen[pid] = dict(identity=identity, first_sample=index, last_sample=index, exit=None)
            seen[pid]['last_sample'] = index
    for pid, record in seen.items():
        if record['last_sample'] < len(rows)-1:
            end = by_pid[pid]['exit']
            base.require(end is not None, 'Previously sampled process lacks final retained exit')
            record['exit'] = {key:end[key] for key in ['code','exited_filetime']} | dict(observed_sample=record['last_sample']+1)
    return [seen[pid] for pid in sorted(seen)]
