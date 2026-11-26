"""Direct Python PID and Windows kill-on-close ownership of calculation processes."""
from pathlib import Path
import ctypes
import sys


def python_argv(script,arguments):
    if sys.platform!='win32':raise RuntimeError('This native worker requires Windows')
    root=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
    executable=Path(getattr(sys,'_base_executable',sys.executable))
    packages=root/'.tooling/python/Lib/site-packages'
    script=Path(script).resolve()
    if not executable.is_file() or not packages.is_dir():raise ValueError('Scientific Python runtime unavailable')
    bootstrap=(f'import runpy,site,sys;site.addsitedir({str(packages)!r});'
               f'sys.path.insert(0,{str(script.parent)!r});sys.argv=[{str(script)!r}]+sys.argv[1:];'
               'runpy.run_path(sys.argv[0],run_name="__main__")')
    return [str(executable),'-S','-Xutf8','-u','-c',bootstrap,*arguments]


class BasicLimits(ctypes.Structure):
    _fields_=[('PerProcessUserTimeLimit',ctypes.c_longlong),('PerJobUserTimeLimit',ctypes.c_longlong),
              ('LimitFlags',ctypes.c_uint32),('MinimumWorkingSetSize',ctypes.c_size_t),
              ('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',ctypes.c_uint32),
              ('Affinity',ctypes.c_size_t),('PriorityClass',ctypes.c_uint32),('SchedulingClass',ctypes.c_uint32)]


class IoCounters(ctypes.Structure):
    _fields_=[(name,ctypes.c_ulonglong) for name in ['ReadOperationCount','WriteOperationCount','OtherOperationCount',
                                                  'ReadTransferCount','WriteTransferCount','OtherTransferCount']]


class ExtendedLimits(ctypes.Structure):
    _fields_=[('BasicLimitInformation',BasicLimits),('IoInfo',IoCounters),
              ('ProcessMemoryLimit',ctypes.c_size_t),('JobMemoryLimit',ctypes.c_size_t),
              ('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]


class CalculationJob:
    def __init__(self):
        if sys.platform!='win32':raise RuntimeError('Windows calculation ownership required')
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p]
        self.kernel.CreateJobObjectW.restype=ctypes.c_void_p
        self.kernel.SetInformationJobObject.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_uint32]
        self.kernel.AssignProcessToJobObject.argtypes=[ctypes.c_void_p,ctypes.c_void_p]
        self.kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        self.handle=self.kernel.CreateJobObjectW(None,None)
        if not self.handle:raise ctypes.WinError(ctypes.get_last_error())
        info=ExtendedLimits();info.BasicLimitInformation.LimitFlags=0x00002000
        if not self.kernel.SetInformationJobObject(self.handle,9,ctypes.byref(info),ctypes.sizeof(info)):
            error=ctypes.get_last_error();self.close();raise ctypes.WinError(error)

    def assign(self,process):
        if not self.kernel.AssignProcessToJobObject(self.handle,ctypes.c_void_p(int(process._handle))):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle);self.handle=None
