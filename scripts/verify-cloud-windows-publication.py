"""Exercise real Windows delete-sharing locks, rather than mocking replace()."""
from pathlib import Path
import ctypes
from ctypes import wintypes as wt
import json
import sys
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'output/c211-cloud-product/app'))
import cloud_transport as wire
assert sys.platform=='win32'
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.CreateFileW.argtypes=[wt.LPCWSTR,wt.DWORD,wt.DWORD,ctypes.c_void_p,wt.DWORD,wt.DWORD,wt.HANDLE]
kernel.CreateFileW.restype=wt.HANDLE
kernel.CloseHandle.argtypes=[wt.HANDLE]
def lock(path):
    handle=kernel.CreateFileW(str(path),0x80000000,3,None,3,0x80,None)
    if handle==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
    return handle
with tempfile.TemporaryDirectory(prefix='cosmos2-cloud-lock-') as folder:
    path=Path(folder)/'packet.bin'
    old=wire.HEADER.pack(wire.MAGIC,1)+b'a'
    new=wire.HEADER.pack(wire.MAGIC,1)+b'b'
    wire.publish(path,old)
    handle=lock(path)
    def release():
        time.sleep(.003)
        kernel.CloseHandle(handle)
    thread=threading.Thread(target=release);thread.start()
    began=time.perf_counter();wire.publish(path,new);elapsed=(time.perf_counter()-began)*1000
    thread.join();assert path.read_bytes()==new
    handle=lock(path)
    try:
        began=time.perf_counter()
        try:wire.publish(path,old)
        except PermissionError:pass
        else:raise AssertionError('A persistent lock was silently bypassed')
        permanent_elapsed=(time.perf_counter()-began)*1000
        assert permanent_elapsed<100 and path.read_bytes()==new
        assert not list(Path(folder).glob('*.tmp'))
    finally:kernel.CloseHandle(handle)
report={'status':'real_Windows_transient_and_persistent_publication_locks_verified',
    'transient_lock_recovered_ms':elapsed,'persistent_lock_refused_ms':permanent_elapsed,
    'previous_packet_preserved_on_failure':True,'temporary_files_cleaned':True,
    'scope':'Atomic packet publication under actual Windows delete-sharing locks; no formal frame-profile acceptance.'}
(ROOT/'evidence/cloud-windows-publication-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
