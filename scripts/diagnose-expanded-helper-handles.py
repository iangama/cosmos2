"""Fast helper discovery with retained Windows handles; diagnostic only, not a performance profile."""
import argparse
import ctypes as ct
import datetime as dt
import hashlib
import json
from pathlib import Path
import time
import traceback
import zipfile

import psutil
from owned_process_snapshot import Entry, FileTime

ROOT = Path(__file__).resolve().parents[1]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and len(args.label) <= 24 and all(ch in 'abcdefghijklmnopqrstuvwxyz0123456789-' for ch in args.label)
    out = ROOT / f'evidence/is6-expanded-helper-handles-{args.label}.json'
    folder = ROOT / f'output/is6-expanded-helper-handles-{args.label}'
    assert not out.exists() and not folder.exists()
    session_path = ROOT / 'output/session.json'
    session = json.loads(session_path.read_text(encoding='utf-8-sig'))
    engine = psutil.Process(session['app'])
    assert engine.name().lower() == 'openspace.exe' and Path(engine.exe()).resolve() == Path(session['runtime']) / 'bin/OpenSpace.exe'
    assert Path(session['serverScript']).resolve() == ROOT / 'output/is6-expanded-journey-product0.27.0/app/server.py'
    folder.mkdir()
    sources = {path.relative_to(ROOT).as_posix(): sha(path) for path in [Path(__file__), ROOT / 'scripts/owned_process_snapshot.py']}
    with zipfile.ZipFile(folder / 'executed-sources.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for name in sources:
            archive.write(ROOT / name, name)
    kernel = ct.WinDLL('kernel32', use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [ct.c_uint32, ct.c_uint32]
    kernel.CreateToolhelp32Snapshot.restype = ct.c_void_p
    kernel.Process32FirstW.argtypes = [ct.c_void_p, ct.POINTER(Entry)]
    kernel.Process32NextW.argtypes = [ct.c_void_p, ct.POINTER(Entry)]
    kernel.CloseHandle.argtypes = [ct.c_void_p]
    kernel.OpenProcess.argtypes = [ct.c_uint32, ct.c_int32, ct.c_uint32]
    kernel.OpenProcess.restype = ct.c_void_p
    kernel.GetProcessTimes.argtypes = [ct.c_void_p, *[ct.POINTER(FileTime)] * 4]
    kernel.GetExitCodeProcess.argtypes = [ct.c_void_p, ct.POINTER(ct.c_uint32)]
    handles = {}
    report = dict(completed=False, diagnostic_only=True, profile_accepted=False, session=session, source_sha256=sources,
                  samples=0, helpers=[], unresolved=[], started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                  scope='120second high-frequency Toolhelp discovery of direct native-engine helpers, with exact creation/exit times and exit codes from retained handles; command lines when readable. All failed opens retained; no scientific/profile acceptance.')
    began = time.perf_counter()

    def times(handle):
        values = [FileTime() for _ in range(4)]
        if not kernel.GetProcessTimes(handle, *[ct.byref(value) for value in values]):
            raise ct.WinError(ct.get_last_error())
        status = ct.c_uint32()
        if not kernel.GetExitCodeProcess(handle, ct.byref(status)):
            raise ct.WinError(ct.get_last_error())
        return [(value.high << 32) | value.low for value in values], status.value

    def persist():
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')

    try:
        previous_save = began
        while time.perf_counter() - began < 120:
            tick = time.perf_counter()
            snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
            if snapshot == ct.c_void_p(-1).value:
                raise ct.WinError(ct.get_last_error())
            try:
                row = Entry(); row.size = ct.sizeof(Entry)
                present = kernel.Process32FirstW(snapshot, ct.byref(row))
                while present:
                    if row.parent == session['app'] and row.name.lower() == 'openspace_helper.exe':
                        pid = row.pid
                        if pid not in handles:
                            handle = kernel.OpenProcess(0x101000, False, pid)
                            if not handle:
                                report['unresolved'].append(dict(pid=pid, parent=row.parent, name=row.name, error=ct.get_last_error(), offset_s=time.perf_counter()-began))
                            else:
                                native, code = times(handle)
                                record = dict(pid=pid, parent=row.parent, name=row.name, created_filetime=native[0],
                                              first_observed_s=time.perf_counter()-began, initial_code=code, command_line=None, exit=None)
                                handles[pid] = handle, record
                                report['helpers'].append(record)
                                try:
                                    process = psutil.Process(pid)
                                    assert abs(process.create_time() - (native[0]-116444736000000000)/1e7) <= 5e-6
                                    record['command_line'] = process.cmdline()
                                    record['executable'] = process.exe()
                                except Exception:
                                    record['command_line_failure'] = traceback.format_exc()
                    present = kernel.Process32NextW(snapshot, ct.byref(row))
            finally:
                kernel.CloseHandle(snapshot)
            for handle, record in handles.values():
                if record['exit'] is None:
                    native, code = times(handle)
                    assert native[0] == record['created_filetime']
                    if code != 259:
                        record['exit'] = dict(code=code, exited_filetime=native[1], duration_s=(native[1]-native[0])/1e7,
                                              observed_offset_s=time.perf_counter()-began)
            report['samples'] += 1
            if time.perf_counter() - previous_save >= 10:
                persist(); previous_save = time.perf_counter()
            remaining = .01 - (time.perf_counter()-tick)
            if remaining > 0:
                time.sleep(remaining)
        assert json.loads(session_path.read_text(encoding='utf-8-sig')) == session
        assert all(sha(ROOT / name) == seal for name, seal in sources.items())
        report.update(completed=True, wall_s=time.perf_counter()-began)
    except Exception:
        report['failure'] = traceback.format_exc()
    finally:
        for handle, _ in handles.values():
            kernel.CloseHandle(handle)
        persist()
    print(json.dumps(dict(completed=report['completed'], samples=report['samples'], helpers=len(report['helpers']), unresolved=len(report['unresolved']), failure=report.get('failure'))), flush=True)
    return 0 if report['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
