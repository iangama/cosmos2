"""Windows product process memory; extracted unchanged from benchmark-cloud-native.
Session is explicit; importing this module never starts a benchmark.
"""
import ctypes
from ctypes import wintypes as wt

class Entry(ctypes.Structure):
    _fields_ = [('dwSize',wt.DWORD),('cntUsage',wt.DWORD),('pid',wt.DWORD),
                ('heap',ctypes.c_size_t),('module',wt.DWORD),('threads',wt.DWORD),
                ('parent',wt.DWORD),('priority',wt.LONG),('flags',wt.DWORD),('exe',wt.WCHAR*260)]
class Memory(ctypes.Structure):
    _fields_ = [('cb',wt.DWORD),('faults',wt.DWORD)]+[(name,ctypes.c_size_t) for name in
                ('peak_working','working','peak_paged','paged','peak_nonpaged','nonpaged',
                 'pagefile','peak_pagefile','private')]
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
psapi = ctypes.WinDLL('psapi', use_last_error=True)
kernel.CreateToolhelp32Snapshot.restype = wt.HANDLE
kernel.CreateToolhelp32Snapshot.argtypes = [wt.DWORD,wt.DWORD]
kernel.Process32FirstW.argtypes = [wt.HANDLE,ctypes.POINTER(Entry)]
kernel.Process32NextW.argtypes = [wt.HANDLE,ctypes.POINTER(Entry)]
kernel.OpenProcess.restype = wt.HANDLE
kernel.OpenProcess.argtypes = [wt.DWORD,wt.BOOL,wt.DWORD]
kernel.CloseHandle.argtypes = [wt.HANDLE]
psapi.GetProcessMemoryInfo.argtypes = [wt.HANDLE,ctypes.POINTER(Memory),wt.DWORD]

def product_memory(session):
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    processes = {}
    try:
        entry = Entry(); entry.dwSize = ctypes.sizeof(Entry)
        available = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while available:
            processes[entry.pid] = (entry.parent, entry.exe)
            available = kernel.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    owned = {session['app'], session['server']}
    while True:
        children = {pid for pid,(parent,_) in processes.items() if parent in owned}
        if children <= owned: break
        owned |= children
    entries = []
    for pid in sorted(owned):
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle: continue
        try:
            memory = Memory(); memory.cb = ctypes.sizeof(Memory)
            if psapi.GetProcessMemoryInfo(handle, ctypes.byref(memory), memory.cb):
                entries.append({'pid':pid,'name':processes.get(pid,(0,'unknown'))[1],
                                'working_set_bytes':memory.working,'private_bytes':memory.private})
        finally:
            kernel.CloseHandle(handle)
    if not any(item['pid'] == session['app'] for item in entries):
        raise RuntimeError('Motor ausente na leitura de memória.')
    return {'processes':entries,'sum_working_set_bytes':sum(e['working_set_bytes'] for e in entries),
            'method':'GetProcessMemoryInfo; sum of working sets can double-count shared DLL pages'}
