"""Close only the identified Atlas test host and retain real Windows exit codes."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import argparse
import ctypes
import hashlib
import json
import time
import psutil

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument('--host-label',required=True)
parser.add_argument('--gpu-report',required=True)
args = parser.parse_args()
if not args.host_label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.host_label):
    parser.error('Invalid label')
report_path = (ROOT / args.gpu_report).resolve()
assert report_path.is_relative_to(ROOT / 'evidence')
gpu = json.loads(report_path.read_text())
assert gpu['valid'] is True
session = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
assert session == gpu['session']
driver = json.loads((ROOT / ('output/is6-spatial-import-host-'+args.host_label+'.json')).read_text())
assert Path(session['serverScript']).resolve() == ROOT / 'output/is6-spatial-import-product0.22.1/app/server.py'
engine = psutil.Process(session['app'])
assert engine.name().lower() == 'openspace.exe' and Path(engine.exe()).resolve().is_relative_to(ROOT)
assert engine.create_time() == gpu['engine_started_unix'] and sha(Path(engine.exe())) == gpu['engine_sha256']
launcher = psutil.Process(session['launcher'])
wrapper = launcher.parent()
assert wrapper.pid == driver['pid'] and any('launch-is6-spatial-import-candidate-v2.py' in arg for arg in launcher.cmdline())
out = ROOT / ('evidence/is6-gpu-pdh-host-closed-'+args.host_label+'.json')
assert not out.exists()
kernel = ctypes.WinDLL('kernel32',use_last_error=True)
kernel.OpenProcess.argtypes = [ctypes.c_ulong,ctypes.c_bool,ctypes.c_ulong]
kernel.OpenProcess.restype = ctypes.c_void_p
kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
kernel.GetExitCodeProcess.restype = ctypes.c_bool
kernel.CloseHandle.argtypes = [ctypes.c_void_p]
roles = dict(engine=session['app'],server=session['server'],launcher=session['launcher'],launcher_wrapper=wrapper.pid)
handles = {name:kernel.OpenProcess(0x101000,False,pid) for name,pid in roles.items()}
assert all(handles.values())
owner = sha(ROOT / 'user/sessions/latest.json')
result = dict(accepted=False,completed=False,session=session,pids=roles,source_sha256={
    Path(__file__).relative_to(ROOT).as_posix():sha(Path(__file__)),report_path.relative_to(ROOT).as_posix():sha(report_path)},
    owner_sha256=owner,scope='Only identified owned Atlas GPU-probe host cleanup; no launcher activation or performance acceptance.')
try:
    h = SourceFileLoader('gpu_probe_close_helpers',str(ROOT / 'scripts/benchmark-body-points-native.py')).load_module()
    assert h.get('/api/state')['mode'] == 'atlas'
    h.native('openspace.toggleShutdown();return {closing=true}')
    h._socket.close()
    deadline = time.monotonic()+55
    while True:
        codes = {}
        for role,handle in handles.items():
            value = ctypes.c_ulong()
            assert kernel.GetExitCodeProcess(handle,ctypes.byref(value))
            codes[role] = value.value
        if all(code != 259 for code in codes.values()):
            break
        if time.monotonic() > deadline:
            raise TimeoutError('Owned host shutdown not confirmed')
        time.sleep(.1)
    result['process_exit_codes'] = codes
    assert all(code == 0 for code in codes.values()) and sha(ROOT / 'user/sessions/latest.json') == owner
    result.update(accepted=True,completed=True)
finally:
    for handle in handles.values():
        kernel.CloseHandle(handle)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(accepted=result['accepted'],process_exit_codes=result.get('process_exit_codes'))))
