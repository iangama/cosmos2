"""Read an atomically replaced control/status file with Windows delete sharing.

This is IPC handling only. It never retries raw process/PDH/RAM observations.
https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew
"""
import ctypes as c
import json
import time


def read_json(path, timeout_s=1.):
    k = c.WinDLL('kernel32', use_last_error=True)
    k.CreateFileW.argtypes = [c.c_wchar_p,c.c_uint32,c.c_uint32,c.c_void_p,c.c_uint32,c.c_uint32,c.c_void_p]
    k.CreateFileW.restype = c.c_void_p
    k.GetFileSizeEx.argtypes = [c.c_void_p,c.POINTER(c.c_int64)]
    k.ReadFile.argtypes = [c.c_void_p,c.c_void_p,c.c_uint32,c.POINTER(c.c_uint32),c.c_void_p]
    k.CloseHandle.argtypes = [c.c_void_p]
    deadline = time.monotonic()+timeout_s
    while True:
        handle = k.CreateFileW(str(path),0x80000000,7,None,3,0x80,None)  # READ|WRITE|DELETE sharing
        if handle != c.c_void_p(-1).value:
            break
        error = c.get_last_error()
        if error not in [2,3,5,32] or time.monotonic() >= deadline:
            raise c.WinError(error)
        time.sleep(.005)
    try:
        size = c.c_int64()
        if not k.GetFileSizeEx(handle,c.byref(size)):
            raise c.WinError(c.get_last_error())
        if not 0 < size.value <= 65536:
            raise ValueError('Control/status JSON size differs')
        data = c.create_string_buffer(size.value)
        count = c.c_uint32()
        if not k.ReadFile(handle,data,size.value,c.byref(count),None):
            raise c.WinError(c.get_last_error())
        if count.value != size.value:
            raise ValueError('Control/status file ended early')
        return json.loads(data.raw.decode('utf-8-sig'))
    finally:
        k.CloseHandle(handle)
