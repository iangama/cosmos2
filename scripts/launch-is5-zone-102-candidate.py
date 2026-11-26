"""Windows native diagnostic launcher; IS5 solar zone candidate with separate storage; accepted bases unchanged."""
from pathlib import Path
import ctypes
import json
import os
import shutil
import subprocess
import time
import urllib.request
import psutil

ROOT=Path(__file__).resolve().parents[1]


def main():
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_bool,ctypes.c_wchar_p]
    kernel.CreateMutexW.restype=ctypes.c_void_p
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    handle=kernel.CreateMutexW(None,True,'Local\\Cosmos2Launcher')
    if not handle:raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error()==183:raise RuntimeError('Cosmos2 launcher already active.')
    session=ROOT/'output/session.json'
    if session.exists():
        old=json.loads(session.read_text(encoding='utf-8-sig'))
        if psutil.pid_exists(old['app']):
            p=psutil.Process(old['app'])
            if p.name()=='OpenSpace.exe' and Path(p.exe()).is_relative_to(ROOT):raise RuntimeError('Cosmos2 already running.')
    runtime=ROOT/'.runtime-is4-stream';candidate=ROOT/'output/is5-solar-zone-product0.10.2'
    env=os.environ.copy();env.update(COSMOS2_ROOT=ROOT.as_posix(),OPENSPACE_USER=(ROOT/'user').as_posix(),
        COSMOS2_STORAGE=str(ROOT/'output/is5-solar-zone-product0.10.2/gravity-sessions'),COSMOS2_INSPECT_CEF='1',
        COSMOS2_WINDOW_CONFIG=(ROOT/'config/window-1080.json').as_posix())
    for name in ['COSMOS2_OFFLINE','COSMOS2_CACHE']:env.pop(name,None)
    shutil.copy2(ROOT/'config/cosmos2.cfg',runtime/'cosmos2.cfg')
    outputs=[];server=app=None
    def spawn(argv,cwd,log,error):
        stdout=(ROOT/'output'/log).open('wb');stderr=(ROOT/'output'/error).open('wb');outputs.extend([stdout,stderr])
        return subprocess.Popen(argv,cwd=cwd,env=env,stdout=stdout,stderr=stderr)
    python=ROOT/'.tooling/python/Scripts/python.exe'
    try:
        server=spawn([str(python),'-u',str(candidate/'app/server.py')],ROOT,'server.log','server-errors.log')
        app=spawn([str(runtime/'bin/OpenSpace.exe'),'--file','cosmos2.cfg','--bypassLauncher'],runtime,'engine.log','engine-errors.log')
        fields=['solarIntegration','solarTides','earthField','jupiterField','bodyVector','bodyLines','bodyView','bodyViewTopology','bodyMaps','nodeLifecycle','nodeLifecycleV2','bodyPoints','is4ParticleProduct','is4WindProduct','is5SolarZone']
        launch={key+'Candidate':True for key in fields}
        launch.update(app=app.pid,server=server.pid,launcher=os.getpid(),runtime=str(runtime),runtimeVariant='is4-stream',
            storage=env['COSMOS2_STORAGE'],serverScript=str(candidate/'app/server.py'),cloudCandidate=False,
            runtimeSelectionReason='IS5-solar-zone-0.10.2-unpromoted',
            solarInitialFormat='solar_four_physical_centers/1.0.0',started=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
            offline=False,coldCache=False,cache=None,launcher_script=str(Path(__file__)))
        session.write_text(json.dumps(launch,indent=2)+'\n',encoding='utf-8')
        bootstrap=spawn([str(python),'-Xutf8',str(ROOT/'scripts/bootstrap-native-ui.py')],ROOT,'bootstrap-ui.log','bootstrap-ui-errors.log')
        result=bootstrap.wait(timeout=120)
        print(json.dumps({'app':app.pid,'server':server.pid,'bootstrap_exit':result}),flush=True)
        code=app.wait()
        print(json.dumps({'engine_exit':code}),flush=True)
        if code:raise RuntimeError(f'Engine exited with {code}.')
    finally:
        if server is not None and server.poll() is None:
            try:
                req=urllib.request.Request('http://127.0.0.1:4700/api/shutdown',data=b'{}',headers={'Content-Type':'application/json'},method='POST')
                urllib.request.urlopen(req,timeout=3).close();server.wait(timeout=8)
            except Exception:
                if server.poll() is None:server.terminate();server.wait(timeout=8)
        for out in outputs:out.close()
        kernel.CloseHandle(handle)


if __name__=='__main__':main()
