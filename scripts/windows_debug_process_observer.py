"""Unprivileged debugger for a newly launched diagnostic tree; never attach to unrelated processes.

Windows supplies process handles before the first user instruction and an exact exit code.
https://learn.microsoft.com/en-us/windows/win32/api/debugapi/nf-debugapi-waitfordebugevent
https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags
This instrument changes scheduling and is a diagnostic, not an ordinary FPS measurement.
"""
import ctypes as c
import datetime as dt
import subprocess
import time

import psutil


class FileTime(c.Structure):
    _fields_ = [('low', c.c_uint32), ('high', c.c_uint32)]


class ExceptionRecord(c.Structure):
    _fields_ = [('code', c.c_uint32), ('flags', c.c_uint32), ('record', c.c_void_p), ('address', c.c_void_p),
                ('parameters', c.c_uint32), ('information', c.c_size_t * 15)]


class ExceptionInfo(c.Structure):
    _fields_ = [('record', ExceptionRecord), ('first_chance', c.c_uint32)]


class CreateProcess(c.Structure):
    _fields_ = [('file', c.c_void_p), ('process', c.c_void_p), ('thread', c.c_void_p), ('base', c.c_void_p),
                ('debug_offset', c.c_uint32), ('debug_size', c.c_uint32), ('thread_local', c.c_void_p),
                ('start', c.c_void_p), ('image_name', c.c_void_p), ('unicode', c.c_uint16)]


class LoadDll(c.Structure):
    _fields_ = [('file', c.c_void_p), ('base', c.c_void_p), ('debug_offset', c.c_uint32),
                ('debug_size', c.c_uint32), ('image_name', c.c_void_p), ('unicode', c.c_uint16)]


class EventData(c.Union):
    _fields_ = [('exception', ExceptionInfo), ('create', CreateProcess), ('load', LoadDll), ('exit_code', c.c_uint32)]


class DebugEvent(c.Structure):
    _fields_ = [('code', c.c_uint32), ('pid', c.c_uint32), ('tid', c.c_uint32), ('data', EventData)]


class Observer:
    def __init__(self, record):
        assert c.sizeof(c.c_void_p) == 8 and c.sizeof(DebugEvent) == 176
        self.record = record
        self.records, self.handles, self.initial_breakpoints = {}, {}, set()
        self.events, self.started = 0, time.perf_counter()
        self.kernel = k = c.WinDLL('kernel32', use_last_error=True)
        k.WaitForDebugEventEx.argtypes = [c.POINTER(DebugEvent), c.c_uint32]
        k.ContinueDebugEvent.argtypes = [c.c_uint32, c.c_uint32, c.c_uint32]
        k.DebugSetProcessKillOnExit.argtypes = [c.c_int32]
        k.CloseHandle.argtypes = [c.c_void_p]
        k.GetCurrentProcess.restype = c.c_void_p
        k.DuplicateHandle.argtypes = [c.c_void_p, c.c_void_p, c.c_void_p, c.POINTER(c.c_void_p), c.c_uint32, c.c_int32, c.c_uint32]
        k.GetProcessTimes.argtypes = [c.c_void_p, *[c.POINTER(FileTime)] * 4]
        k.GetExitCodeProcess.argtypes = [c.c_void_p, c.POINTER(c.c_uint32)]
        k.DebugActiveProcessStop.argtypes = [c.c_uint32]
        self.child = None

    def times(self, handle):
        values = [FileTime() for _ in range(4)]
        if not self.kernel.GetProcessTimes(handle, *[c.byref(value) for value in values]):
            raise c.WinError(c.get_last_error())
        status = c.c_uint32()
        if not self.kernel.GetExitCodeProcess(handle, c.byref(status)):
            raise c.WinError(c.get_last_error())
        return [(value.high << 32) | value.low for value in values], status.value

    def start(self, argv, cwd, stream):
        assert self.child is None
        self.child = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
                                      creationflags=0x1)  # DEBUG_PROCESS, descendants included
        if not self.kernel.DebugSetProcessKillOnExit(False):
            raise c.WinError(c.get_last_error())
        return self.child.pid

    def pump(self, timeout_ms=50):
        event = DebugEvent()
        if not self.kernel.WaitForDebugEventEx(c.byref(event), timeout_ms):
            error = c.get_last_error()
            if error == 121:
                return False
            raise c.WinError(error)
        self.events += 1
        row = dict(sequence=self.events, code=event.code, pid=event.pid, tid=event.tid,
                   utc=dt.datetime.now(dt.timezone.utc).isoformat(), offset_s=time.perf_counter()-self.started)
        continue_status = 0x10002  # DBG_CONTINUE for lifecycle/dll/thread/output events
        try:
            if event.code == 3:  # CREATE_PROCESS_DEBUG_EVENT
                assert event.pid not in self.records, 'PID reuse in this diagnostic tree'
                handle = c.c_void_p()
                current = self.kernel.GetCurrentProcess()
                if not self.kernel.DuplicateHandle(current, event.data.create.process, current, c.byref(handle), 0, False, 2):
                    raise c.WinError(c.get_last_error())
                self.handles[event.pid] = handle
                native, status = self.times(handle)
                assert native[0] > 116444736000000000 and status == 259
                process = psutil.Process(event.pid)
                identity = dict(pid=event.pid, parent=process.ppid(), name=process.name(), executable=process.exe(),
                                command_line=process.cmdline(), created_filetime=native[0], exit=None)
                assert abs(process.create_time()-(native[0]-116444736000000000)/1e7) <= 5e-6
                self.records[event.pid] = identity
                row['identity'] = identity.copy()
                if event.data.create.file:
                    self.kernel.CloseHandle(event.data.create.file)
            elif event.code == 5:  # EXIT_PROCESS_DEBUG_EVENT
                row['exit_code'] = event.data.exit_code
                assert event.pid in self.records and self.records[event.pid]['exit'] is None
                self.records[event.pid]['exit'] = dict(code=event.data.exit_code, event_utc=row['utc'], event_sequence=self.events)
            elif event.code == 6 and event.data.load.file:
                self.kernel.CloseHandle(event.data.load.file)
            elif event.code == 1:  # EXCEPTION_DEBUG_EVENT
                code = event.data.exception.record.code
                first = event.data.exception.first_chance
                row.update(exception_code=code, first_chance=first)
                # Consume only the Windows initial debugger breakpoint, once per process.
                # All other exceptions retain the target's own exception handling.
                if code == 0x80000003 and first and event.pid not in self.initial_breakpoints:
                    self.initial_breakpoints.add(event.pid)
                else:
                    continue_status = 0x80010001  # DBG_EXCEPTION_NOT_HANDLED
            self.record(row)
        finally:
            if not self.kernel.ContinueDebugEvent(event.pid, event.tid, continue_status):
                raise c.WinError(c.get_last_error())
        if event.code == 5:
            native, status = self.times(self.handles[event.pid])
            assert native[0] == self.records[event.pid]['created_filetime']
            assert status == event.data.exit_code and native[1] >= native[0]
            self.records[event.pid]['exit'].update(exited_filetime=native[1], duration_s=(native[1]-native[0])/1e7)
        return True

    def finished(self):
        return bool(self.records) and all(record['exit'] is not None for record in self.records.values())

    def close(self):
        for pid, record in self.records.items():
            if record['exit'] is None:
                self.kernel.DebugActiveProcessStop(pid)
        for handle in self.handles.values():
            self.kernel.CloseHandle(handle)
        self.handles = {}
