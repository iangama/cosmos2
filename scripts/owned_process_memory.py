"""Read a retained process object's RAM once, bracketed by native termination evidence."""
import ctypes as ct


class Counters(ct.Structure):
    _fields_ = [('cb', ct.c_uint32), ('PageFaultCount', ct.c_uint32),
                *[(name, ct.c_size_t) for name in ['PeakWorkingSetSize', 'WorkingSetSize',
                  'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                  'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage', 'PrivateUsage']]]


class Reader:
    def __init__(self, tracker):
        assert ct.sizeof(ct.c_void_p) == 8 and ct.sizeof(Counters) == 80
        self.tracker = tracker
        self.api = tracker.kernel.K32GetProcessMemoryInfo
        self.api.argtypes = [ct.c_void_p, ct.POINTER(Counters), ct.c_uint32]
        self.api.restype = ct.c_int32

    def read(self, identity, value=None):
        tracker = self.tracker
        with tracker.lock:
            assert tracker.failure is None, tracker.failure
            pid = identity['pid']
            assert tracker.records[pid]['identity'] == identity, 'RAM retained identity differs'
            value = {} if value is None else value
            value.update(pid=pid, created_filetime=identity['created_filetime'],
                         observation_started_filetime=tracker.clock(), api_called=False)
            before = tracker.refresh(pid)
            value['native_before'] = before
            if before['wait'] == 0:
                value.update(status='completed_before_read', native_after=before,
                             observation_finished_filetime=tracker.clock())
                return value
            value['api_called'] = True
            raw = Counters(); raw.cb = ct.sizeof(raw)
            value['read_started_filetime'] = tracker.clock()
            ct.set_last_error(0)
            ok = self.api(tracker.handles[pid], ct.byref(raw), ct.sizeof(raw))
            error = ct.get_last_error()
            value.update(read_finished_filetime=tracker.clock(), api_return=int(ok), api_error=error if not ok else 0,
                         raw={name: getattr(raw, name) for name, _ in Counters._fields_})
            value['native_after'] = tracker.refresh(pid)
            value['observation_finished_filetime'] = tracker.clock()
            if not ok:
                value['status'] = 'read_failed'
            else:
                value.update(status='measured', working_set_bytes=raw.WorkingSetSize, private_bytes=raw.PrivateUsage)
            return value


def collect(reader, identities, result):
    values, ended = [], []
    result.update(model='retained-native-process-memory/1', processes=values, completed_before_read=ended,
                  sum_working_set_bytes=None)
    for identity in identities:
        value = {}
        values.append(value)
        reader.read(identity, value)
        if value['status'] == 'completed_before_read':
            values.pop()
            ended.append(value)
    if all(value['status'] == 'measured' for value in values):
        result['sum_working_set_bytes'] = sum(value['working_set_bytes'] for value in values)
    return result
