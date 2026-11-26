"""Read selected Windows GPU byte gauges through documented PDH APIs."""
from pathlib import Path
import ctypes as c
import datetime as dt
import hashlib
import os
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(__file__)
CONTRACT = ROOT / 'IS-6-GPU-PDH-PYTHON-CONTRATO.md'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
TIME_CONTRACT = ROOT / 'IS-6-GPU-PDH-PYTHON-TEMPO.md'
IMPORTED = {p.relative_to(ROOT).as_posix():sha(p) for p in [SOURCE,CONTRACT,TIME_CONTRACT]}
DWORD, LONG, I64, HANDLE = c.c_uint32, c.c_int32, c.c_int64, c.c_void_p
MORE_DATA = 0x800007D2
REFRESH_COUNTERS = 4
FMT_LARGE_NOSCALE = 0x400 | 0x1000
LARGE_RAW_COUNT = 0x10100
GOOD_STATUS = {0,1}
PATH = re.compile('(?:\\\\\\\\[^\\\\]+)?\\\\([^\\\\(]+)\\(([^)]+)\\)\\\\([^\\\\]+)')
PROCESS_INSTANCE = re.compile(r'pid_(\d+)_[^)]+',re.I)
SPECS = [('GPU Process Memory','Dedicated Usage'),('GPU Process Memory','Shared Usage'),
         ('GPU Adapter Memory','Dedicated Usage')]


class FileTime(c.Structure):
    _fields_ = [('low',DWORD),('high',DWORD)]


class Raw(c.Structure):
    _fields_ = [('status',DWORD),('stamp',FileTime),('first',I64),('second',I64),('multiple',DWORD)]


class ValueUnion(c.Union):
    _fields_ = [('large',I64),('real',c.c_double),('small',LONG),('text',c.c_void_p)]


class Formatted(c.Structure):
    _fields_ = [('status',DWORD),('value',ValueUnion)]


class InfoPrefix(c.Structure):
    _fields_ = [('length',DWORD),('kind',DWORD),('version',DWORD),('status',DWORD),
                ('scale',LONG),('default_scale',LONG),('user',c.c_size_t),
                ('query_user',c.c_size_t),('full_path',c.c_wchar_p)]


def generation():
    if any(sha(ROOT / name) != seal for name,seal in IMPORTED.items()):
        raise ValueError('Restart after PDH reader source changes')
    return dict(schema=1,id='cosmos2:windows-pdh-owned-gpu-bytes',version='0.2.0',source_sha256=dict(IMPORTED))


def check(status, operation):
    if status != 0:
        raise OSError('PDH '+operation+' failed: 0x'+format(status,'08x'))


def filetime_utc(value):
    if type(value) is not int or value <= 116444736000000000:
        raise ValueError('PDH FILETIME outside adopted UTC range')
    return (dt.datetime(1601,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(microseconds=value//10)).isoformat()


class Query:
    def __init__(self):
        if os.name != 'nt' or c.sizeof(HANDLE) != 8:
            raise ValueError('Native Windows64 PDH required')
        assert c.sizeof(Raw) == 40 and Raw.first.offset == 16
        assert c.sizeof(Formatted) == 16 and Formatted.value.offset == 8
        self.generation = generation()
        self.kernel = c.WinDLL('kernel32',use_last_error=True)
        self.kernel.LocalFileTimeToFileTime.argtypes = [c.POINTER(FileTime),c.POINTER(FileTime)]
        self.kernel.LocalFileTimeToFileTime.restype = c.c_int32
        self.api = c.WinDLL('pdh.dll')
        signatures = {
            'PdhOpenQueryW':([c.c_wchar_p,c.c_size_t,c.POINTER(HANDLE)],DWORD),
            'PdhCloseQuery':([HANDLE],DWORD),
            'PdhAddEnglishCounterW':([HANDLE,c.c_wchar_p,c.c_size_t,c.POINTER(HANDLE)],DWORD),
            'PdhAddCounterW':([HANDLE,c.c_wchar_p,c.c_size_t,c.POINTER(HANDLE)],DWORD),
            'PdhRemoveCounter':([HANDLE],DWORD),
            'PdhGetCounterInfoW':([HANDLE,c.c_int32,c.POINTER(DWORD),c.c_void_p],DWORD),
            'PdhExpandWildCardPathW':([c.c_wchar_p,c.c_wchar_p,c.c_void_p,c.POINTER(DWORD),DWORD],DWORD),
            'PdhCollectQueryDataWithTime':([HANDLE,c.POINTER(I64)],DWORD),
            'PdhGetRawCounterValue':([HANDLE,c.POINTER(DWORD),c.POINTER(Raw)],DWORD),
            'PdhGetFormattedCounterValue':([HANDLE,DWORD,c.POINTER(DWORD),c.POINTER(Formatted)],DWORD),
        }
        for name,(args,result) in signatures.items():
            function = getattr(self.api,name)
            function.argtypes,function.restype = args,result
        self.query = HANDLE()
        check(self.api.PdhOpenQueryW(None,0,c.byref(self.query)),'OpenQuery')
        self.handles,self.metadata = {},{}

    def __enter__(self):
        return self

    def __exit__(self,*_):
        self.close()

    def close(self):
        if self.query:
            check(self.api.PdhCloseQuery(self.query),'CloseQuery')
            self.query = HANDLE()

    def info(self, handle):
        size = DWORD()
        status = self.api.PdhGetCounterInfoW(handle,False,c.byref(size),None)
        if status != MORE_DATA or not c.sizeof(InfoPrefix) <= size.value <= 1024*1024:
            raise ValueError('PDH counter metadata size/status differs: '+hex(status))
        buffer = c.create_string_buffer(size.value)
        check(self.api.PdhGetCounterInfoW(handle,False,c.byref(size),buffer),'GetCounterInfo')
        info = InfoPrefix.from_buffer(buffer)
        return dict(path=info.full_path,kind=info.kind,scale=info.scale,default_scale=info.default_scale)

    def expanded(self, path):
        size = DWORD()
        status = self.api.PdhExpandWildCardPathW(None,path,None,c.byref(size),REFRESH_COUNTERS)
        if status != MORE_DATA or not 1 < size.value <= 1024*1024:
            raise ValueError('PDH expansion size/status differs: '+hex(status))
        buffer = c.create_unicode_buffer(size.value)
        check(self.api.PdhExpandWildCardPathW(None,path,buffer,c.byref(size),REFRESH_COUNTERS),'ExpandWildCardPath')
        return [s for s in buffer[:size.value].split('\0') if s]

    def discover(self, owned):
        result = {}
        for object_name,counter_name in SPECS:
            wildcard = '\\'+object_name+'(*)\\'+counter_name
            handle = HANDLE()
            check(self.api.PdhAddEnglishCounterW(self.query,wildcard,0,c.byref(handle)),'AddEnglishCounter')
            try:
                localized = self.info(handle)['path']
                match = PATH.fullmatch(localized)
                if match is None or match[2] != '*':
                    raise ValueError('Unexpected localized PDH wildcard')
                for path in self.expanded(localized):
                    actual = PATH.fullmatch(path)
                    if actual is None or actual[1].lower() != match[1].lower() or actual[3].lower() != match[3].lower():
                        raise ValueError('PDH expansion changed its object/counter')
                    instance = actual[2].lower()
                    pid = None
                    if object_name == 'GPU Process Memory':
                        identity = PROCESS_INSTANCE.fullmatch(instance)
                        if identity is None:
                            raise ValueError('Unknown GPU process counter identity')
                        pid = int(identity[1])
                        if pid not in owned:
                            continue
                    canonical = '\\'+object_name.lower()+'('+instance+')\\'+counter_name.lower()
                    if canonical in result:
                        raise ValueError('Duplicate canonical PDH counter')
                    result[canonical] = dict(localized_path=path,instance=instance,pid=pid,
                                             object=object_name,counter=counter_name.lower())
            finally:
                check(self.api.PdhRemoveCounter(handle),'RemoveWildcardCounter')
        if not result or not any(row['pid'] is not None for row in result.values()):
            raise ValueError('No owned GPU process counters exposed')
        for row in list(result.values()):
            if row['pid'] is not None:
                prefix='\\gpu process memory('+row['instance']+')\\'
                if any(prefix+counter not in result for counter in ['dedicated usage','shared usage']):
                    raise ValueError('Incomplete dedicated/shared GPU pair')
        return result

    def select(self, paths):
        if self.handles:
            raise ValueError('PDH query path set is already frozen')
        for canonical,row in sorted(paths.items()):
            handle = HANDLE()
            check(self.api.PdhAddCounterW(self.query,row['localized_path'],0,c.byref(handle)),'AddSelectedCounter')
            info = self.info(handle)
            if info['kind'] != LARGE_RAW_COUNT:
                raise ValueError('GPU bytes require PERF_COUNTER_LARGE_RAWCOUNT')
            self.handles[canonical] = handle
            self.metadata[canonical] = {**row,**info}

    def sample(self):
        before = dt.datetime.now(dt.timezone.utc)
        stamp = I64()
        check(self.api.PdhCollectQueryDataWithTime(self.query,c.byref(stamp)),'CollectQueryDataWithTime')
        local_stamp = FileTime(stamp.value & 0xffffffff,stamp.value >> 32)
        utc_stamp = FileTime()
        if not self.kernel.LocalFileTimeToFileTime(c.byref(local_stamp),c.byref(utc_stamp)):
            raise c.WinError(c.get_last_error())
        utc_filetime = (utc_stamp.high << 32) | utc_stamp.low
        query_time = filetime_utc(utc_filetime)
        rows = []
        for path,handle in self.handles.items():
            raw,formatted,raw_type,fmt_type = Raw(),Formatted(),DWORD(),DWORD()
            raw_api = self.api.PdhGetRawCounterValue(handle,c.byref(raw_type),c.byref(raw))
            fmt_api = self.api.PdhGetFormattedCounterValue(handle,FMT_LARGE_NOSCALE,c.byref(fmt_type),c.byref(formatted))
            row = dict(path=path,raw_api_status=raw_api,formatted_api_status=fmt_api,
                raw_status=raw.status,formatted_status=formatted.status,raw_type=raw_type.value,
                formatted_type=fmt_type.value,raw_first_value=raw.first,raw_second_value=raw.second,
                raw_multi_count=raw.multiple,raw_timestamp_filetime=(raw.stamp.high<<32)|raw.stamp.low,
                formatted_bytes=formatted.value.large,format=FMT_LARGE_NOSCALE)
            rows.append(row)
        after = dt.datetime.now(dt.timezone.utc)
        return dict(utc=query_time,query_filetime=stamp.value,query_utc_filetime=utc_filetime,
                    time_basis='PDH local FILETIME converted by LocalFileTimeToFileTime',
                    local_to_utc_seconds=(utc_filetime-stamp.value)/10000000,call_started_utc=before.isoformat(),
                    call_finished_utc=after.isoformat(),raw_counter_samples=rows)
