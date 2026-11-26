"""Own the local corrected backend/renderer lifecycle; preserve all sealed generations."""
from importlib.machinery import SourceFileLoader
from pathlib import Path
import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
import urllib.request

from native_ui_readiness import wait_for_ui

ROOT = Path(__file__).resolve().parents[1]
entry = SourceFileLoader('cosmos2_working_entry', str(ROOT / 'scripts/open-working-cosmos2.py')).load_module()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--record', required=True)
    args = parser.parse_args()
    folder = Path(args.record).resolve()
    assert folder.is_relative_to(ROOT / 'output/local-product-launches') and folder.is_dir()
    choice, product, runtime = entry.selection()
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    kernel.CreateMutexW.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    mutex = kernel.CreateMutexW(None, True, 'Local\\Cosmos2Launcher')
    assert mutex and ctypes.get_last_error() != 183, 'Cosmos2 já está iniciando.'
    assert not entry.running(), 'Preserve a janela atual antes de abrir outra.'
    previous = folder / 'preserved-previous-launch'
    previous.mkdir()
    names = ['session.json', 'engine.log', 'engine-errors.log', 'server.log', 'server-errors.log',
             'bootstrap-ui.log', 'bootstrap-ui-errors.log', 'bootstrap-ui.json', 'local-ui-readiness.json']
    for name in names:
        if (ROOT / 'output' / name).is_file():
            shutil.copy2(ROOT / 'output' / name, previous / name)
    env = os.environ.copy()
    env.update(COSMOS2_ROOT=ROOT.as_posix(), OPENSPACE_USER=(ROOT / 'user').as_posix(),
               COSMOS2_STORAGE=str(product / 'gravity-sessions'), COSMOS2_INSPECT_CEF='1',
               COSMOS2_WINDOW_CONFIG=(ROOT / 'config/window.json').as_posix())
    for name in ['COSMOS2_OFFLINE', 'COSMOS2_CACHE']:
        env.pop(name, None)
    shutil.copy2(ROOT / 'output/is6-principal-moons-navigation-staging-v2/cosmos2.cfg', runtime / 'cosmos2.cfg')
    streams = []
    def spawn(argv, cwd, stem):
        stdout = (ROOT / 'output' / (stem + '.log')).open('wb')
        stderr = (ROOT / 'output' / (stem + '-errors.log')).open('wb')
        streams.extend([stdout, stderr])
        return subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
    server = app = None
    exits = dict(completed=False)
    try:
        server = spawn([sys.executable, '-u', '-Xutf8', str(product / 'app/server.py')], ROOT, 'server')
        ready = wait_for_ui(timeout_s=240, child_alive=lambda:server.poll() is None)
        (ROOT / 'output/local-ui-readiness.json').write_text(json.dumps(ready, indent=2)+'\n', encoding='utf8')
        app = spawn([str(runtime / 'bin/OpenSpace.exe'), '--file', 'cosmos2.cfg', '--bypassLauncher'], runtime, 'engine')
        session = dict(app=app.pid, server=server.pid, launcher=os.getpid(), runtime=str(runtime),
                       runtimeVariant='is4-stream', runtimeSelectionReason='Local-working-product-0.27.1-functional-review',
                       serverScript=str(product / 'app/server.py'), storage=env['COSMOS2_STORAGE'],
                       started=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), launcher_script=str(Path(__file__)),
                       localWorkingProduct=True, localProductVersion=choice['candidate'],
                       is6ExpandedJourneyCandidate=True, is6LayersCandidate=True, is6SpatialImportCandidate=True,
                       is6LayerImportCandidate=True, is6PlanetNavigationCandidate=True, is6PrincipalMoonsCandidate=True,
                       is6Dynamics16Candidate=True, promoted=False, offline=False, coldCache=False, cache=None)
        temporary = ROOT / 'output/session-working.tmp'
        temporary.write_text(json.dumps(session, indent=2)+'\n', encoding='utf8')
        temporary.replace(ROOT / 'output/session.json')
        bootstrap = spawn([sys.executable, '-Xutf8', str(ROOT / 'scripts/bootstrap-native-ui-v2.py')], ROOT, 'bootstrap-ui')
        assert bootstrap.wait(timeout=150) == 0, 'A interface não confirmou a abertura. Consulte os registros da sessão.'
        print(json.dumps(dict(app=app.pid, server=server.pid, bootstrap_exit=0)), flush=True)
        exits['app_exit'] = app.wait()
        assert exits['app_exit'] == 0
        exits['completed'] = True
    except Exception:
        exits['failure'] = traceback.format_exc()
        if app and app.poll() is None:
            app.terminate()
            app.wait(timeout=15)
            exits['app_exit'] = app.returncode
        raise
    finally:
        if server and server.poll() is None:
            try:
                req = urllib.request.Request('http://127.0.0.1:4700/api/shutdown', data=b'{}', headers={'Content-Type':'application/json'})
                urllib.request.urlopen(req, timeout=3).close()
                server.wait(timeout=15)
            except Exception:
                if server.poll() is None:
                    server.terminate()
                    server.wait(timeout=15)
        exits['server_exit'] = None if server is None else server.poll()
        for stream in streams:
            stream.close()
        for name in names:
            if (ROOT / 'output' / name).is_file():
                shutil.copy2(ROOT / 'output' / name, folder / name)
        (folder / 'process-result.json').write_text(json.dumps(exits, indent=2)+'\n', encoding='utf8')
        kernel.CloseHandle(mutex)


if __name__ == '__main__':
    main()
