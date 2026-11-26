"""Open the isolated sixteen-body app independently of a Codex test session."""
import ctypes
from ctypes import wintypes as w
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

import psutil

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / 'scripts/launch-is6-expanded-journey-candidate.py'
CANDIDATE = ROOT / 'output/is6-expanded-journey-product0.27.0/app/server.py'


def focus(pid):
    user = ctypes.WinDLL('user32',use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
    user.EnumWindows.argtypes = [callback_type,w.LPARAM]
    user.EnumWindows.restype = w.BOOL
    user.GetWindowThreadProcessId.argtypes = [w.HWND,ctypes.POINTER(w.DWORD)]
    user.GetWindowThreadProcessId.restype = w.DWORD
    user.IsWindowVisible.argtypes = [w.HWND]
    user.IsWindowVisible.restype = w.BOOL
    user.ShowWindow.argtypes = [w.HWND,ctypes.c_int]
    user.SetForegroundWindow.argtypes = [w.HWND]
    user.SetForegroundWindow.restype = w.BOOL
    matches = []
    @callback_type
    def each(hwnd, _):
        actual = w.DWORD()
        user.GetWindowThreadProcessId(hwnd,ctypes.byref(actual))
        if actual.value == pid and user.IsWindowVisible(hwnd): matches.append(hwnd)
        return True
    if not user.EnumWindows(each,0): raise ctypes.WinError(ctypes.get_last_error())
    if not matches: return dict(visible=False,foreground=False)
    user.ShowWindow(matches[0],9)
    return dict(visible=True,foreground=bool(user.SetForegroundWindow(matches[0])))


def own_engines():
    result = []
    for process in psutil.process_iter(['name','exe']):
        try:
            if (process.info['name'] or '').lower() == 'openspace.exe' and Path(process.info['exe']).is_relative_to(ROOT):
                result.append(process)
        except (psutil.NoSuchProcess,psutil.AccessDenied,TypeError): pass
    return result


def main():
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + str(time.time_ns())
    record = ROOT / 'output' / ('is6-expanded-journey-open-' + stamp + '.json')
    result = dict(started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),completed=False,
                  requested_candidate='0.27.0',detached=True)
    try:
        engines = own_engines()
        if engines:
            assert len(engines) == 1,'Mais de uma janela do Cosmos2 encontrada.'
            result.update(reused=True,app_pid=engines[0].pid,window=focus(engines[0].pid))
            session = json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
            result['requested_candidate_active'] = Path(session['serverScript']).resolve() == CANDIDATE
            print('A janela dos planetas já estava aberta.' if result['requested_candidate_active'] else
                  'Cosmos2 já está aberto em outra versão. A janela atual foi ativada.',flush=True)
        else:
            with record.with_suffix('.log').open('xb') as out, record.with_suffix('.errors.log').open('xb') as err:
                process = subprocess.Popen([sys.executable,'-u','-Xutf8',str(LAUNCHER)],cwd=ROOT,
                    stdin=subprocess.DEVNULL,stdout=out,stderr=err,
                    creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP)
            result.update(reused=False,launcher_wrapper_pid=process.pid,launcher_wrapper_started_unix=time.time())
            record.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
            deadline = time.monotonic()+300
            while True:
                if process.poll() is not None: raise RuntimeError('Falha ao iniciar a janela. Veja o registro: '+str(record.with_suffix('.errors.log')))
                try:
                    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
                    app=psutil.Process(session['app'])
                    if (Path(session['serverScript']).resolve() == CANDIDATE and
                        app.create_time() >= result['launcher_wrapper_started_unix']-.5 and
                        (ROOT/'output/bootstrap-ui.json').stat().st_mtime >= app.create_time()):
                        result.update(app_pid=app.pid,session=session,requested_candidate_active=True,window=focus(app.pid))
                        break
                except (OSError,ValueError,KeyError,psutil.NoSuchProcess): pass
                if time.monotonic() >= deadline: raise TimeoutError('A interface não confirmou a inicialização no prazo. Registro: '+str(record))
                time.sleep(.1)
            print('Cosmos2 aberto: oito planetas e sete luas. A janela continua disponível após fechar este terminal.',flush=True)
        assert result['window']['visible'],'O processo existe, mas sua janela ainda não foi encontrada.'
        result['completed']=True
    except Exception:
        result['failure']=traceback.format_exc()
        print(result['failure'],file=sys.stderr,flush=True)
    finally:
        record.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return 0 if result['completed'] else 1


if __name__=='__main__': raise SystemExit(main())
