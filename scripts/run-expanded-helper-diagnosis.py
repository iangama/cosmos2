"""Close four original handles, diagnose a fresh native opening and restore the owner's view."""
import argparse
import ctypes as ct
import hashlib
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

import psutil
from cef_page_v2 import Page
from expanded_residency_processes import RetainedProcesses

ROOT = Path(__file__).resolve().parents[1]
h = SourceFileLoader('helper_diagnosis_host', str(ROOT / 'scripts/benchmark-body-points-native.py')).load_module()
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and len(args.label) <= 24 and all(ch in 'abcdefghijklmnopqrstuvwxyz0123456789-' for ch in args.label)
    folder = ROOT / f'output/is6-expanded-helper-host-{args.label}'
    out = ROOT / f'evidence/is6-expanded-helper-host-{args.label}.json'
    assert not folder.exists() and not out.exists()
    warm = json.loads((ROOT / 'evidence/is6-expanded-helper-handles-20261113a.json').read_text())
    assert warm['completed'] and not warm.get('failure')
    session = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
    assert session == warm['session'] and h.get('/api/state')['mode'] == 'atlas'
    assert Path(session['serverScript']).resolve() == ROOT / 'output/is6-expanded-journey-product0.27.0/app/server.py'
    engine, server, launcher = [psutil.Process(session[key]) for key in ['app', 'server', 'launcher']]
    wrapper = launcher.parent()
    assert engine.name().lower() == 'openspace.exe' and Path(engine.exe()).resolve() == Path(session['runtime']) / 'bin/OpenSpace.exe'
    assert any('launch-is6-expanded-journey-candidate.py' in arg for arg in wrapper.cmdline())
    folder.mkdir()
    plan = json.loads((ROOT / 'evidence/is6-expanded-residency-plan-20261113b.json').read_text())
    protected = plan['protected_sha256']
    assert all(sha(ROOT / name) == seal for name, seal in protected.items())
    result = dict(completed=False, state='retaining_handles', diagnostic_only=True, session=session, processes={},
                  source_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in [Path(__file__), ROOT / 'scripts/diagnose-expanded-helper-handles-v2.py']},
                  protected_sha256=protected)
    tracker = RetainedProcesses(session)
    kernel, handles = tracker.kernel, {}
    kernel.WaitForSingleObject.argtypes = [ct.c_void_p, ct.c_uint32]
    original_id = None

    def persist():
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')

    try:
        result['handle_identities'] = {}
        for role, process in dict(engine=engine, server=server, launcher=launcher, wrapper=wrapper).items():
            handle = kernel.OpenProcess(0x101000, False, process.pid)
            if not handle:
                raise ct.WinError(ct.get_last_error())
            handles[role] = handle
            native, code = tracker.native_times(handle)
            assert code == 259 and abs((native[0] - 116444736000000000)/1e7-process.create_time()) <= 5e-6
            result['handle_identities'][role] = dict(pid=process.pid, created_filetime=native[0])
        result['original_navigation'] = h.get('/api/navigation/state')
        result['original_favorites'] = h.get('/api/navigation/favorites')['views']
        views = h.post('/api/navigation/save', dict(name='Retorno do diagnóstico de auxiliares'))['navigation']['views']
        original_id = next(item['id'] for item in views if item['id'] not in {value['id'] for value in result['original_favorites']})
        result['temporary_favorite'] = original_id
        result['state'] = 'closing_original'
        persist()
        h.native('openspace.toggleShutdown();return {closing=true}')
        for role, handle in handles.items():
            deadline = time.monotonic()+90
            while kernel.WaitForSingleObject(handle, 0) != 0:
                if time.monotonic() > deadline:
                    raise TimeoutError(role)
                time.sleep(.1)
            native, code = tracker.native_times(handle)
            assert code == 0 and native[0] == result['handle_identities'][role]['created_filetime'] and native[1] >= native[0]
            result['processes'][role] = dict(code=code, created_filetime=native[0], exited_filetime=native[1])
        h._socket = None
        result['state'] = 'opening_fresh'
        persist()
        with (folder / 'open.log').open('xb') as stream:
            opened = subprocess.run([sys.executable, '-Xutf8', str(ROOT / 'scripts/open-expanded-journey-app.py')], cwd=ROOT,
                                    stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, timeout=360)
        assert opened.returncode == 0
        result['fresh_session'] = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
        assert result['fresh_session']['app'] != session['app']
        result['state'] = 'diagnosing_fresh'
        persist()
        with (folder / 'diagnosis.log').open('xb') as stream:
            child = subprocess.run([sys.executable, '-u', '-Xutf8', str(ROOT / 'scripts/diagnose-expanded-helper-handles-v2.py'),
                                    '--label', args.label], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, timeout=330)
        proof = json.loads((ROOT / f'evidence/is6-expanded-helper-handles-{args.label}.json').read_text())
        assert child.returncode == 0 and proof['completed'] and not proof.get('failure')
        result.update(completed=True, diagnosis_exit=child.returncode)
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        try:
            if original_id:
                restored = h.post('/api/navigation/restore', dict(id=original_id))['navigation']
                h.post('/api/navigation/delete', dict(id=original_id))
                before = result['original_navigation']
                assert restored['et'] == before['et'] and restored['target'] == before['target']
                for key, value in before['navigation'].items():
                    assert all(abs(x-y) <= 1e-12 for x,y in zip(value,restored['navigation'][key],strict=True)) if key == 'Up' else value == restored['navigation'][key]
                assert h.get('/api/navigation/favorites')['views'] == result['original_favorites']
                with Page() as page:
                    page.wait_for_function('appState?.mode==="atlas"&&navigationState&&!pending')
                    page.locator('#ui-scale').select_option('1')
                    page.evaluate('selectTarget(' + json.dumps(restored['target']) + ',true)')
                result['owner_navigation_restored'] = restored
            assert all(sha(ROOT / name) == seal for name, seal in (protected | result['source_sha256']).items())
            result['owner_app_kept_open'] = True
        except Exception:
            result['cleanup_failure'] = traceback.format_exc()
            result['completed'] = False
        for handle in handles.values():
            kernel.CloseHandle(handle)
        result['state'] = 'complete' if result['completed'] else 'failed'
        persist()
    print(json.dumps({key:result.get(key) for key in ['completed','state','failure','cleanup_failure']}), flush=True)
    return 0 if result['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
