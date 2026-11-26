"""Retain current native handles, verify archived instruments, close four exits and reopen detached."""
import argparse
import ctypes
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

import psutil
from cef_page_v2 import Page

ROOT = Path(__file__).resolve().parents[1]
h = SourceFileLoader('expanded_reopen_host_helpers', str(ROOT / 'scripts/benchmark-body-points-native.py')).load_module()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--seed-label', required=True)
    args = parser.parse_args()
    for label in [args.label, args.seed_label]:
        assert label and len(label) <= 24 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label)
    folder = ROOT / f'output/is6-expanded-journey-reopen-host-{args.label}'
    out = ROOT / f'evidence/is6-expanded-journey-reopen-host-{args.label}.json'
    assert not folder.exists() and not out.exists()
    lifecycle = json.loads((ROOT / f'evidence/is6-expanded-journey-native-host-recovery-{args.seed_label}.json').read_text())
    assert lifecycle['accepted'] and lifecycle['completed'] and set(lifecycle['processes'].values()) == {0}
    session = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
    assert Path(session['serverScript']).resolve() == ROOT / 'output/is6-expanded-journey-product0.27.0/app/server.py'
    wrapper = psutil.Process(session['launcher']).parent()
    assert any('launch-is6-expanded-journey-candidate.py' in a for a in wrapper.cmdline())
    folder.mkdir()
    result = dict(accepted=False, completed=False, state='retaining_handles', pid=__import__('os').getpid(), session=session,
                  script_sha256=h.sha(Path(__file__)), verifier_sha256=h.sha(ROOT / 'scripts/verify-native-is6-expanded-reopen.py'))
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    roles = dict(engine=session['app'], server=session['server'], launcher=session['launcher'], launcher_wrapper=wrapper.pid)
    handles, original_id = {}, None
    def persist():
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    def close_current():
        if h.get('/api/state')['mode'] == 'experiment':
            h.post('/api/command', dict(command='atlas'))
        h.native('openspace.toggleShutdown();return {closing=true}')
        result['processes'] = {}
        for role, handle in handles.items():
            deadline = time.monotonic() + 90
            while kernel.WaitForSingleObject(handle, 0) != 0:
                if time.monotonic() > deadline:
                    raise TimeoutError('Native process did not exit: ' + role)
                time.sleep(.1)
            value = ctypes.c_ulong()
            assert kernel.GetExitCodeProcess(handle, ctypes.byref(value))
            result['processes'][role] = value.value
        h._socket = None
        assert len(result['processes']) == 4 and set(result['processes'].values()) == {0}
    persist()
    try:
        for role, pid in roles.items():
            handle = kernel.OpenProcess(0x101000, False, pid)
            if not handle:
                raise ctypes.WinError(ctypes.get_last_error())
            handles[role] = handle
        result['original_navigation'] = h.get('/api/navigation/state')
        result['original_favorites'] = h.get('/api/navigation/favorites')['views']
        views = h.post('/api/navigation/save', dict(name='Retorno do host de reabertura ampliada'))['navigation']['views']
        original_id = next(v['id'] for v in views if v['id'] not in {a['id'] for a in result['original_favorites']})
        result.update(temporary_favorite=original_id, state='verifying_same_archives')
        persist()
        with (folder / 'journey.log').open('xb') as stream:
            child = subprocess.run([sys.executable, '-u', '-Xutf8', str(ROOT / 'scripts/verify-native-is6-expanded-reopen.py'),
                                    '--label', args.label, '--seed-label', args.seed_label], cwd=ROOT,
                                   stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT)
        path = ROOT / f'evidence/is6-expanded-journey-reopen-{args.label}.json'
        proof = json.loads(path.read_text()) if path.exists() else {}
        result.update(verification_exit=child.returncode, verification_accepted=proof.get('accepted') is True,
                      verification_receipt_sha256=h.sha(path) if path.exists() else None, state='closing')
        persist()
        close_current()
        assert child.returncode == 0 and proof.get('accepted') is True, proof.get('failure')
        result.update(accepted=True, completed=True)
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        try:
            if handles and 'processes' not in result:
                close_current()
            result['state'] = 'reopening'
            persist()
            with (folder / 'reopen.log').open('xb') as stream:
                opened = subprocess.run([sys.executable, '-Xutf8', str(ROOT / 'scripts/open-expanded-journey-app.py')], cwd=ROOT,
                                        stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, timeout=360)
            assert opened.returncode == 0
            if original_id:
                restored = h.post('/api/navigation/restore', dict(id=original_id))['navigation']
                h.post('/api/navigation/delete', dict(id=original_id))
                assert restored['et'] == result['original_navigation']['et']
                assert h.get('/api/navigation/favorites')['views'] == result['original_favorites']
                with Page() as page:
                    page.wait_for_function('appState?.mode==="atlas"&&navigationState&&!pending')
                    page.locator('#ui-scale').select_option('1')
                    page.evaluate('selectTarget(' + json.dumps(restored['target']) + ',true)')
            result['owner_app_kept_open'] = True
            result['final_session'] = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
        except Exception:
            result['cleanup_failure'] = traceback.format_exc()
            result['accepted'] = False
        for handle in handles.values():
            kernel.CloseHandle(handle)
        result['state'] = 'complete' if result['accepted'] else 'failed'
        persist()
    print(json.dumps(dict(accepted=result['accepted'], state=result['state'], processes=result.get('processes'), failure=result.get('failure'), cleanup_failure=result.get('cleanup_failure'))), flush=True)
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
