"""Retain identities from ordinary Toolhelp discovery; exact native exit proof, no debugger."""
import copy
import ctypes as c
import datetime as dt
import hashlib
import json
from pathlib import Path
import threading
import time
import traceback

import psutil
from owned_process_snapshot import Entry, FileTime

ROOT = Path(__file__).resolve().parents[1]
FILES = [Path(__file__), ROOT / 'scripts/owned_process_snapshot.py', ROOT / 'IS-6-PERCURSO-AMPLIADO16-RESIDENCIA-REVISAO-D.md']
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


class History:
    def __init__(self, session, path):
        self.session, self.roots = copy.deepcopy(session), {session['app'], session['server']}
        self.records, self.handles, self.failure = {}, {}, None
        self.old_parent_links = {}
        self.polls, self.maximum_poll_gap_s = 0, 0.
        self.sources = {p.relative_to(ROOT).as_posix(): sha(p) for p in FILES}
        self.stream = Path(path).open('x', encoding='utf8')
        self.lock, self.stop, self.thread = threading.RLock(), threading.Event(), None
        self.kernel = k = c.WinDLL('kernel32', use_last_error=True)
        k.CreateToolhelp32Snapshot.argtypes = [c.c_uint32, c.c_uint32]
        k.CreateToolhelp32Snapshot.restype = c.c_void_p
        k.Process32FirstW.argtypes = [c.c_void_p, c.POINTER(Entry)]
        k.Process32NextW.argtypes = [c.c_void_p, c.POINTER(Entry)]
        k.OpenProcess.argtypes = [c.c_uint32, c.c_int32, c.c_uint32]
        k.OpenProcess.restype = c.c_void_p
        k.CloseHandle.argtypes = [c.c_void_p]
        k.GetProcessTimes.argtypes = [c.c_void_p, *[c.POINTER(FileTime)] * 4]
        k.GetExitCodeProcess.argtypes = [c.c_void_p, c.POINTER(c.c_uint32)]
        k.WaitForSingleObject.argtypes = [c.c_void_p, c.c_uint32]
        k.QueryFullProcessImageNameW.argtypes = [c.c_void_p, c.c_uint32, c.c_wchar_p, c.POINTER(c.c_uint32)]
        k.GetSystemTimePreciseAsFileTime.argtypes = [c.POINTER(FileTime)]
        self.previous_poll = None

    def clock(self):
        value = FileTime()
        self.kernel.GetSystemTimePreciseAsFileTime(c.byref(value))
        return (value.high << 32) | value.low

    def emit(self, kind, **fields):
        self.stream.write(json.dumps(dict(kind=kind, utc=dt.datetime.now(dt.timezone.utc).isoformat(), **fields), ensure_ascii=False) + '\n')
        self.stream.flush()

    def native(self, pid):
        handle = self.handles[pid]
        values = [FileTime() for _ in range(4)]
        if not self.kernel.GetProcessTimes(handle, *[c.byref(value) for value in values]):
            raise c.WinError(c.get_last_error())
        status = c.c_uint32()
        if not self.kernel.GetExitCodeProcess(handle, c.byref(status)):
            raise c.WinError(c.get_last_error())
        wait = self.kernel.WaitForSingleObject(handle, 0)
        assert wait in [0, 258], 'Invalid retained-handle wait result'
        return dict(created_filetime=(values[0].high << 32) | values[0].low,
                    exited_filetime=(values[1].high << 32) | values[1].low,
                    code=status.value, wait=wait, observed_filetime=self.clock())

    def refresh(self, pid):
        value = self.native(pid)
        record = self.records[pid]
        assert value['created_filetime'] == record['identity']['created_filetime'], 'Retained process creation identity changed'
        record['last_native'] = value
        if value['wait'] == 0:
            assert value['exited_filetime'] >= value['created_filetime'] > 116444736000000000, 'Signaled process lacks valid native exit time'
            if record['exit'] is None:
                record['exit'] = dict(code=value['code'], exited_filetime=value['exited_filetime'], observed_filetime=value['observed_filetime'])
                self.emit('exit', pid=pid, created_filetime=value['created_filetime'], exit=record['exit'])
            else:
                assert record['exit']['code'] == value['code'] and record['exit']['exited_filetime'] == value['exited_filetime'], 'Retained native exit changed'
            assert value['code'] == 0, 'Owned process exited nonzero: ' + str(pid) + '/' + str(value['code'])
        else:
            assert record['exit'] is None, 'Exited retained PID reappeared'
            if value['code'] != 259 and 'first_terminating_native' not in record:
                record['first_terminating_native'] = value
                self.emit('terminating', pid=pid, native=value)
        return value

    def entries(self):
        handle = self.kernel.CreateToolhelp32Snapshot(2, 0)
        if handle == c.c_void_p(-1).value:
            raise c.WinError(c.get_last_error())
        result = {}
        try:
            entry = Entry(); entry.size = c.sizeof(Entry)
            present = self.kernel.Process32FirstW(handle, c.byref(entry))
            while present:
                result[entry.pid] = dict(pid=entry.pid, parent=entry.parent, name=entry.name)
                present = self.kernel.Process32NextW(handle, c.byref(entry))
            assert c.get_last_error() in [0, 18], 'Toolhelp enumeration failed'
        finally:
            self.kernel.CloseHandle(handle)
        return result

    def discover(self, entry, parent=None):
        pid = entry['pid']
        if pid in self.records:
            value = self.records[pid]['identity']
            assert value['parent'] == entry['parent'] and value['name'] == entry['name'], 'Retained PID/name/parent changed'
            self.refresh(pid)
            return value
        assert len(self.records) < 512, 'Process history budget exhausted'
        handle = self.kernel.OpenProcess(0x101000, False, pid)
        if not handle:
            raise c.WinError(c.get_last_error())
        self.handles[pid] = handle
        value = self.native(pid)
        size = c.c_uint32(32768); path = c.create_unicode_buffer(size.value)
        if not self.kernel.QueryFullProcessImageNameW(handle, 0, path, c.byref(size)):
            self.kernel.CloseHandle(self.handles.pop(pid))
            raise c.WinError(c.get_last_error())
        identity = dict(**entry, created_filetime=value['created_filetime'],
                        started_unix=(value['created_filetime']-116444736000000000)/1e7,
                        executable=path.value, scope_root=pid in self.roots)
        assert Path(identity['executable']).name.lower() == entry['name'].lower(), 'Native image differs from Toolhelp entry'
        if parent is not None:
            if identity['created_filetime'] < parent['created_filetime']:
                self.old_parent_links[pid] = dict(identity=identity, parent_created_filetime=parent['created_filetime'])
                self.kernel.CloseHandle(self.handles.pop(pid))
                return None
            identity['parent_created_filetime'] = parent['created_filetime']
        record = dict(identity=identity, first_observed_filetime=value['observed_filetime'], exit=None, last_native=value, command_line=None)
        self.records[pid] = record
        try:
            process = psutil.Process(pid)
            assert abs(process.create_time()-identity['started_unix']) <= 5e-6 and process.ppid() == identity['parent']
            record['command_line'] = process.cmdline()
        except psutil.Error as error:
            record['command_line_unavailable'] = str(error)
        self.emit('birth', record=copy.deepcopy(record))
        self.refresh(pid)
        return identity

    def step(self):
        began = time.perf_counter()
        if self.previous_poll is not None:
            self.maximum_poll_gap_s = max(self.maximum_poll_gap_s, began-self.previous_poll)
        self.previous_poll = began
        entries = self.entries()
        try:
            for root in self.roots:
                assert root in entries, 'Native ownership root missing'
                self.discover(entries[root])
                assert self.records[root]['exit'] is None, 'Native ownership root exited'
            pending, visited, excluded_old = list(self.records), set(), []
            while pending:
                parent = pending.pop()
                if parent in visited:
                    continue
                visited.add(parent)
                parent_identity = self.records[parent]['identity']
                for pid, entry in entries.items():
                    if entry['parent'] != parent or pid in self.roots:
                        continue
                    identity = self.discover(entry, parent_identity)
                    if identity is None:
                        excluded_old.append(copy.deepcopy(self.old_parent_links[pid]))
                    else:
                        pending.append(pid)
            for pid in self.records:
                self.refresh(pid)
            live = {pid: record['identity'] for pid, record in self.records.items() if record['exit'] is None}
            for pid, identity in live.items():
                if pid not in self.roots:
                    assert identity['parent'] in live and identity['parent_created_filetime'] == live[identity['parent']]['created_filetime'], 'Live owned orphan'
                visited_chain, cursor = set(), pid
                while cursor in live:
                    assert cursor not in visited_chain, 'Cycle in owned identity chain'
                    visited_chain.add(cursor)
                    cursor = live[cursor]['parent']
            self.polls += 1
            return entries, excluded_old
        except Exception:
            self.emit('failure', failure=traceback.format_exc(), toolhelp_entries=entries)
            raise

    def start(self):
        with self.lock:
            self.step()
        def loop():
            try:
                while not self.stop.wait(.01):
                    with self.lock:
                        self.step()
            except Exception:
                with self.lock:
                    self.failure = traceback.format_exc()
                self.stop.set()
        self.thread = threading.Thread(target=loop, name='owned-native-history', daemon=True)
        self.thread.start()

    def snapshot(self):
        with self.lock:
            assert self.failure is None, self.failure
            began = self.clock()
            entries, excluded_old = self.step()
            live = [copy.deepcopy(record['identity']) for record in self.records.values() if record['exit'] is None]
            completed = [dict(entry=entries[pid], identity=copy.deepcopy(record['identity']), exit=copy.deepcopy(record['exit']))
                         for pid, record in self.records.items() if record['exit'] is not None and pid in entries]
            return dict(owned=sorted(live, key=lambda entry:entry['pid']), excluded_completed=completed,
                        excluded_old_parent_links=excluded_old, started_filetime=began, finished_filetime=self.clock(),
                        generation=dict(id='cosmos2:retained-native-history', version='0.1.0', source_sha256=self.sources))

    def export(self):
        with self.lock:
            assert self.failure is None, self.failure
            return dict(records=copy.deepcopy([self.records[pid] for pid in sorted(self.records)]), polls=self.polls,
                        maximum_poll_gap_s=self.maximum_poll_gap_s, source_sha256=self.sources)

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=5)
            assert not self.thread.is_alive()
        for handle in self.handles.values():
            self.kernel.CloseHandle(handle)
        self.handles = {}
        self.stream.close()
