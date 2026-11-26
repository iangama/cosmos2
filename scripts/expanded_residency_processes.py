"""Retain native process identities across scientific worker births and normal exits."""
import ctypes as c

import owned_process_snapshot as ownership
from expanded_residency_contract import identities, require


class RetainedProcesses:
    def __init__(self, session):
        self.session, self.records, self.handles = session, {}, {}
        self.kernel = c.WinDLL('kernel32', use_last_error=True)
        self.kernel.OpenProcess.argtypes = [c.c_uint32, c.c_int32, c.c_uint32]
        self.kernel.OpenProcess.restype = c.c_void_p
        self.kernel.CloseHandle.argtypes = [c.c_void_p]
        self.kernel.GetProcessTimes.argtypes = [c.c_void_p, *[c.POINTER(ownership.FileTime)] * 4]
        self.kernel.GetExitCodeProcess.argtypes = [c.c_void_p, c.POINTER(c.c_uint32)]
        self.root_identities = None

    def native_times(self, handle):
        values = [ownership.FileTime() for _ in range(4)]
        if not self.kernel.GetProcessTimes(handle, *[c.byref(value) for value in values]):
            raise c.WinError(c.get_last_error())
        status = c.c_uint32()
        if not self.kernel.GetExitCodeProcess(handle, c.byref(status)):
            raise c.WinError(c.get_last_error())
        return [(value.high << 32) | value.low for value in values], status.value

    def observe(self, tree, sample_index):
        roots = {self.session['app'], self.session['server']}
        by_pid = identities(tree['owned'], roots, self.records)
        current_roots = {pid: by_pid[pid] for pid in roots}
        if self.root_identities is None:
            self.root_identities = current_roots
        require(current_roots == self.root_identities, 'Residency engine/server identity changed')
        require(len(self.records) + len(set(by_pid) - set(self.records)) <= 256, 'Native process lifecycle budget exceeded')
        for pid, identity in by_pid.items():
            if pid not in self.records:
                handle = self.kernel.OpenProcess(0x101000, False, pid)
                if not handle:
                    raise c.WinError(c.get_last_error())
                self.handles[pid] = handle
                times, code = self.native_times(handle)
                require(times[0] == identity['created_filetime'] and code == 259, 'Native process changed before its handle was retained')
                self.records[pid] = dict(identity=identity, first_sample=sample_index, last_sample=sample_index, exit=None)
            record = self.records[pid]
            require(record['exit'] is None, 'Retained exited PID reappeared')
            record['last_sample'] = sample_index
        for pid, record in self.records.items():
            if pid in by_pid or record['exit'] is not None:
                continue
            times, code = self.native_times(self.handles[pid])
            require(times[0] == record['identity']['created_filetime'], 'Retained process creation identity differs')
            require(code != 259 and times[1] > 0, 'Previously owned live process fell outside its original tree')
            record['exit'] = dict(code=code, exited_filetime=times[1], observed_sample=sample_index)
            require(code == 0, 'Scientific/native child exited abnormally')

    def rows(self):
        return [self.records[pid] for pid in sorted(self.records)]

    def close(self):
        for handle in self.handles.values():
            self.kernel.CloseHandle(handle)
        self.handles = {}
