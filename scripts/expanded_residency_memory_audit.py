"""Pure admission of native-bracketed RAM, including explicit proven completed objects."""
import expanded_residency_contract_v2 as base
import gpu_pdh_audit_dynamics16_base as raw

FIELDS = {'cb', 'PageFaultCount', 'PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage',
          'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage', 'QuotaNonPagedPoolUsage',
          'PagefileUsage', 'PeakPagefileUsage', 'PrivateUsage'}


def admit(value, before, history, a, b):
    base.require(value['model'] == 'retained-native-process-memory/1', 'Unknown RAM accounting model')
    measured, ended = value['processes'], value['completed_before_read']
    all_rows = measured + ended
    pids = [entry['pid'] for entry in all_rows]
    base.require(len(pids) == len(set(pids)) and set(pids) == set(before), 'RAM ownership missing/duplicated')
    for entry in all_rows:
        pid = entry['pid']; identity = before[pid]
        base.require(entry['created_filetime'] == identity['created_filetime'], 'RAM identity changed')
        start, finish = entry['observation_started_filetime'], entry['observation_finished_filetime']
        first, last = entry['native_before'], entry['native_after']
        for number in [start, finish, first['observed_filetime'], last['observed_filetime']]:
            raw.integer(number, minimum=identity['created_filetime'])
        base.require(a <= start <= first['observed_filetime'] <= last['observed_filetime'] <= finish <= b, 'RAM native bracket outside inventory')
        for native in [first, last]:
            base.require(native['created_filetime'] == identity['created_filetime'] and type(native['wait']) is int and native['wait'] in [0, 258], 'RAM native identity/wait differs')
            raw.integer(native['code'])
            if native['wait'] == 0:
                end = history[pid]['exit']
                base.require(end is not None and type(native['code']) is int and native['code'] == 0 and
                             native['exited_filetime'] == end['exited_filetime'] and
                             identity['created_filetime'] <= native['exited_filetime'] <= native['observed_filetime'], 'RAM completed object lacks exact zero exit')
        if entry['status'] == 'completed_before_read':
            base.require(entry in ended and first['wait'] == last['wait'] == 0 and entry['api_called'] is False, 'RAM exclusion lacks pre-read completion')
            base.require(not any(k in entry for k in ['working_set_bytes', 'private_bytes', 'raw', 'read_started_filetime', 'read_finished_filetime', 'api_return']), 'Completed RAM was assigned synthetic bytes')
        else:
            base.require(entry in measured and entry['status'] == 'measured' and first['wait'] == 258 and entry['api_called'] is True,
                         'Unmeasured/failed RAM query')
            base.require(type(entry['api_return']) is int and entry['api_return'] != 0 and entry['api_error'] == 0, 'RAM native API failed')
            raw.integer(entry['read_started_filetime'], minimum=start)
            raw.integer(entry['read_finished_filetime'], minimum=start)
            base.require(first['observed_filetime'] <= entry['read_started_filetime'] <= entry['read_finished_filetime'] <= last['observed_filetime'], 'RAM call outside native bracket')
            counters = entry['raw']
            base.require(set(counters) == FIELDS and counters['cb'] == 80, 'RAM raw struct differs')
            for number in counters.values():
                raw.integer(number)
            base.require(entry['working_set_bytes'] == counters['WorkingSetSize'] and entry['private_bytes'] == counters['PrivateUsage'], 'RAM raw/projection differs')
    raw.integer(value['sum_working_set_bytes'])
    base.require(value['sum_working_set_bytes'] == sum(entry['working_set_bytes'] for entry in measured), 'RAM measured sum differs')
    return dict(measured=len(measured), completed_before_read=len(ended), exits_during_read=sum(entry['native_after']['wait'] == 0 for entry in measured))
