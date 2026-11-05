"""Own one gated Python native host, including Windows venv redirects and exits."""
from pathlib import Path
import ctypes
import json
import subprocess
import sys
import time
import psutil

ROOT = Path(__file__).resolve().parents[1]


class Host:
    def __init__(self,folder,helpers,*,candidate='output/is6-spatial-import-product0.22.1',
                 launcher='scripts/launch-is6-spatial-import-candidate-v2.py'):
        self.folder = Path(folder)
        self.helpers = helpers
        self.candidate = ROOT / candidate
        self.launcher = ROOT / launcher
        self.process,self.session,self.readiness = None,None,None
        self.logs,self.handles = [],{}
        self.kernel = ctypes.WinDLL('kernel32',use_last_error=True)
        self.kernel.OpenProcess.argtypes = [ctypes.c_ulong,ctypes.c_bool,ctypes.c_ulong]
        self.kernel.OpenProcess.restype = ctypes.c_void_p
        self.kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
        self.kernel.GetExitCodeProcess.restype = ctypes.c_bool
        self.kernel.CloseHandle.argtypes = [ctypes.c_void_p]

    def start(self):
        for p in psutil.process_iter(['name','exe']):
            try:
                if p.info['name'].lower() == 'openspace.exe' and Path(p.info['exe']).is_relative_to(ROOT):
                    raise RuntimeError('An own native engine is already running')
            except (psutil.NoSuchProcess,psutil.AccessDenied,TypeError):
                continue
        self.logs = [(self.folder/name).open('wb') for name in ['host.log','host-errors.log']]
        self.process = subprocess.Popen([sys.executable,'-u','-Xutf8',str(self.launcher)],cwd=ROOT,
                                        stdout=self.logs[0],stderr=self.logs[1])
        deadline = time.monotonic()+300
        while True:
            if self.process.poll() is not None:
                raise RuntimeError('Profile host launcher exited: '+str(self.process.returncode))
            try:
                session = json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
                pids = {self.process.pid,*[p.pid for p in psutil.Process(self.process.pid).children(recursive=True)
                        if any(str(self.launcher).lower() == arg.lower() for arg in p.cmdline())]}
                if session.get('launcher') in pids and Path(session['serverScript']).resolve() == self.candidate/'app/server.py':
                    self.session = session
                    # Retain handles immediately, even if bootstrap later fails.
                    if not self.handles:
                        for role in ['app','server','launcher']:
                            handle = self.kernel.OpenProcess(0x101000,False,session[role])
                            if not handle:
                                raise ctypes.WinError(ctypes.get_last_error())
                            self.handles['engine' if role == 'app' else role] = handle
                    ready = json.loads((ROOT/'output/local-ui-readiness.json').read_text())
                    if ready['server_pid'] == session['server'] and (ROOT/'output/bootstrap-ui.json').stat().st_mtime >= psutil.Process(session['app']).create_time():
                        if not ready['ready'] or not ready['http_ready_before_engine_start']:
                            raise ValueError('Profile host HTTP gate unconfirmed')
                        self.readiness = ready
                        return session
            except (OSError,ValueError,KeyError,psutil.NoSuchProcess):
                pass
            if time.monotonic() >= deadline:
                raise TimeoutError('Own profile host did not finish gated bootstrap')
            time.sleep(.1)

    def close(self):
        result = {}
        try:
            if self.session:
                for instrument in ['spatial','layers']:
                    state = self.helpers.get('/api/'+instrument+'/state')
                    if state['active'] or state.get('recovery_required'):
                        self.helpers.post('/api/'+instrument+'/command',dict(command='leave',guard=state['guard']))
                state = self.helpers.get('/api/state')
                if state['mode'] == 'experiment':
                    self.helpers.post('/api/command',dict(command='atlas'))
                self.helpers.native('openspace.toggleShutdown();return {closing=true}')
                if self.helpers._socket:
                    self.helpers._socket.close()
                result['launcher_wrapper_exit'] = self.process.wait(timeout=60)
                for role,handle in self.handles.items():
                    code = ctypes.c_ulong()
                    if not self.kernel.GetExitCodeProcess(handle,ctypes.byref(code)):
                        raise ctypes.WinError(ctypes.get_last_error())
                    result[role+'_exit'] = code.value
                if any(code != 0 for code in result.values()):
                    raise RuntimeError('Profile host exits differ: '+str(result))
            elif self.process is not None and self.process.poll() is None:
                self.process.terminate()
                result['launcher_wrapper_exit'] = self.process.wait(timeout=10)
        finally:
            for handle in self.handles.values():
                self.kernel.CloseHandle(handle)
            self.handles = {}
            for log in self.logs:
                log.close()
        return result
