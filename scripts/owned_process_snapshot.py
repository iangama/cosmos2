"""One Windows Toolhelp snapshot and creation-time checked ownership."""
from pathlib import Path
import ctypes as c
import hashlib
import os

ROOT = Path(__file__).resolve().parents[1]
FILES = [Path(__file__),ROOT/'IS-6-GPU-IDENTIDADE-PROCESSOS.md']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
IMPORTED = {p.relative_to(ROOT).as_posix():sha(p) for p in FILES}


class FileTime(c.Structure):
    _fields_=[('low',c.c_uint32),('high',c.c_uint32)]


class Entry(c.Structure):
    _fields_=[('size',c.c_uint32),('usage',c.c_uint32),('pid',c.c_uint32),
        ('heap',c.c_size_t),('module',c.c_uint32),('threads',c.c_uint32),
        ('parent',c.c_uint32),('priority',c.c_int32),('flags',c.c_uint32),('name',c.c_wchar*260)]


def generation():
    if any(sha(ROOT/name)!=seal for name,seal in IMPORTED.items()):
        raise ValueError('Restart after owned process reader source changes')
    return dict(id='cosmos2:toolhelp-creation-time-ownership',version='0.1.0',source_sha256=dict(IMPORTED))


def classify(entries,roots,read):
    """Pure ownership rule. read(pid) must return fresh native identity data."""
    identities={}
    rejected=[]
    for root in roots:
        if root not in entries:
            raise ValueError('Owned scope root missing from Windows snapshot')
        identities[root]={**read(root),'scope_root':True}
        if identities[root]['parent']!=entries[root]['parent']:
            raise ValueError('Owned root parent changed after Windows snapshot')
    pending=list(roots)
    visited=set()
    while pending:
        parent=pending.pop()
        if parent in visited:
            raise ValueError('Cycle in owned Windows process snapshot')
        visited.add(parent)
        for pid,row in entries.items():
            if row['parent']!=parent or pid in roots:
                continue
            try:
                identity=read(pid)
            except (OSError,ValueError) as error:
                raise ValueError('Unresolved candidate in owned snapshot: pid='+str(pid)+' parent='+str(parent)) from error
            if identity['parent']!=parent:
                raise ValueError('Candidate parent changed after Windows snapshot')
            if identity['created_filetime']<identities[parent]['created_filetime']:
                rejected.append(dict(pid=pid,parent=parent,created_filetime=identity['created_filetime'],
                                     parent_created_filetime=identities[parent]['created_filetime'],
                                     reason='Candidate predates current PPID owner; not its descendant'))
                continue
            if pid in identities:
                raise ValueError('Cycle or duplicate owned Windows identity')
            identities[pid]={**identity,'scope_root':False,'parent_created_filetime':identities[parent]['created_filetime']}
            pending.append(pid)
    for pid in identities:
        chain=set()
        cursor=pid
        while cursor in identities:
            if cursor in chain:
                raise ValueError('Cycle in confirmed owned parent identities')
            chain.add(cursor)
            cursor=identities[cursor]['parent']
    return dict(owned=[identities[pid] for pid in sorted(identities)],excluded_old_parent_links=rejected)


def snapshot(session):
    if os.name!='nt':
        raise ValueError('Native Windows process snapshot required')
    kernel=c.WinDLL('kernel32',use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes=[c.c_uint32,c.c_uint32]
    kernel.CreateToolhelp32Snapshot.restype=c.c_void_p
    kernel.Process32FirstW.argtypes=[c.c_void_p,c.POINTER(Entry)]
    kernel.Process32NextW.argtypes=[c.c_void_p,c.POINTER(Entry)]
    kernel.OpenProcess.argtypes=[c.c_uint32,c.c_int32,c.c_uint32]
    kernel.OpenProcess.restype=c.c_void_p
    kernel.CloseHandle.argtypes=[c.c_void_p]
    kernel.GetProcessTimes.argtypes=[c.c_void_p,*[c.POINTER(FileTime)]*4]
    kernel.GetExitCodeProcess.argtypes=[c.c_void_p,c.POINTER(c.c_uint32)]
    handle=kernel.CreateToolhelp32Snapshot(2,0)
    if handle==c.c_void_p(-1).value:
        raise c.WinError(c.get_last_error())
    entries={}
    try:
        entry=Entry();entry.size=c.sizeof(Entry)
        present=kernel.Process32FirstW(handle,c.byref(entry))
        while present:
            entries[entry.pid]=dict(pid=entry.pid,parent=entry.parent,name=entry.name)
            present=kernel.Process32NextW(handle,c.byref(entry))
        if c.get_last_error() not in {0,18}:
            raise c.WinError(c.get_last_error())
    finally:
        kernel.CloseHandle(handle)
    def read(pid):
        process=kernel.OpenProcess(0x101000,False,pid)
        if not process:
            raise c.WinError(c.get_last_error())
        try:
            created,exited,system,user=FileTime(),FileTime(),FileTime(),FileTime()
            if not kernel.GetProcessTimes(process,c.byref(created),c.byref(exited),c.byref(system),c.byref(user)):
                raise c.WinError(c.get_last_error())
            status=c.c_uint32()
            if not kernel.GetExitCodeProcess(process,c.byref(status)) or status.value!=259:
                raise ValueError('Process exited during owned Windows inventory: '+str(pid))
            value=(created.high<<32)|created.low
            # Full path comes from the already validated live process only.
            import psutil
            try:
                fresh=psutil.Process(pid)
                if fresh.ppid()!=entries[pid]['parent']:
                    raise ValueError('Process parent changed while reading identity')
                return dict(pid=pid,parent=entries[pid]['parent'],name=entries[pid]['name'],created_filetime=value,
                    started_unix=(value-116444736000000000)/10000000,executable=fresh.exe())
            except psutil.Error as error:
                raise OSError('Owned snapshot identity no longer available: '+str(pid)) from error
        finally:
            kernel.CloseHandle(process)
    result=classify(entries,{session['app'],session['server']},read)
    result['generation']=generation()
    return result
