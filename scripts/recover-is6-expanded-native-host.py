"""Adopt still-live native handles after the WSL driver ended143; never repeat the verifier."""
import argparse
import ctypes
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

ROOT = Path(__file__).resolve().parents[1]
h = SourceFileLoader('expanded_host_recovery_helpers', str(ROOT / 'scripts/benchmark-body-points-native.py')).load_module()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and len(args.label) <= 24 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
    old_path = ROOT / f'evidence/is6-expanded-journey-native-host-{args.label}.json'
    journey_path = ROOT / f'evidence/is6-expanded-journey-native-{args.label}.json'
    out = ROOT / f'evidence/is6-expanded-journey-native-host-recovery-{args.label}.json'
    folder = ROOT / f'output/is6-expanded-journey-native-host-recovery-{args.label}'
    assert not out.exists() and not folder.exists()
    previous = json.loads(old_path.read_text())
    session = previous['session']
    assert not previous['completed'] and not previous['accepted']
    assert Path(session['serverScript']).resolve() == ROOT / 'output/is6-expanded-journey-product0.27.0/app/server.py'
    launcher = psutil.Process(session['launcher'])
    wrapper = launcher.parent()
    assert any('launch-is6-expanded-journey-candidate.py' in a for a in wrapper.cmdline())
    original_driver_pid = wrapper.ppid()
    assert not psutil.pid_exists(original_driver_pid), 'Do not compete with a live original driver'
    verifiers = []
    for process in psutil.process_iter(['pid', 'cmdline', 'name']):
        try:
            arguments = process.info['cmdline'] or []
            if any(Path(a).name == 'verify-native-is6-expanded-journey.py' for a in arguments):
                assert args.label in arguments
                verifiers.append(process)
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            pass
    assert len(verifiers) == 2, 'Adopt the actual venv wrapper and actual verifier before they finish'
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    kernel.GetExitCodeProcess.restype = ctypes.c_bool
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    roles = dict(engine=session['app'], server=session['server'], launcher=session['launcher'], launcher_wrapper=wrapper.pid)
    roles.update({f'verifier_{i}': process.pid for i, process in enumerate(sorted(verifiers, key=lambda p: p.create_time()))})
    handles = {}
    folder.mkdir()
    result = dict(accepted=False, completed=False, state='retaining_handles', pid=__import__('os').getpid(),
                  original_driver_pid=original_driver_pid, original_driver_absent=True, original_transport_exit=143,
                  previous_receipt_sha256=sha(old_path), session=session, roles=roles,
                  source_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in [Path(__file__), ROOT / 'scripts/cef_page_v2.py', ROOT / 'scripts/benchmark-body-points-native.py']},
                  scope='Recover lifecycle ownership of the same in-progress journey, with six real retained process handles. No repeated scientific/native journey or product change.')
    def persist():
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    def wait(role, timeout):
        deadline = time.monotonic() + timeout
        while kernel.WaitForSingleObject(handles[role], 0) != 0:
            if time.monotonic() > deadline:
                raise TimeoutError('Retained process did not finish: ' + role)
            time.sleep(.1)
        value = ctypes.c_ulong()
        assert kernel.GetExitCodeProcess(handles[role], ctypes.byref(value))
        return value.value
    persist()
    try:
        for role, pid in roles.items():
            process = psutil.Process(pid)
            assert process.name().lower() in ['python.exe', 'openspace.exe']
            handle = kernel.OpenProcess(0x101000, False, pid)
            if not handle:
                raise ctypes.WinError(ctypes.get_last_error())
            handles[role] = handle
        result.update(state='waiting_for_same_verifier', all_six_handles_retained=True)
        persist()
        result['verifier_exits'] = {role: wait(role, 2400) for role in handles if role.startswith('verifier_')}
        result['journey_receipt_sha256'] = sha(journey_path)
        journey = json.loads(journey_path.read_text())
        result['journey_accepted'] = journey['accepted'] and journey['completed']
        result.update(state='closing_same_host')
        persist()
        for instrument in ['solar-zone', 'particles', 'layers', 'spatial']:
            state = h.get('/api/' + instrument + '/state')
            if state['active'] or state.get('recovery_required'):
                request = dict(command='leave')
                if instrument == 'solar-zone':
                    request['guard'] = {key: state['worker'][key] for key in ['worker_id', 'artifact_id', 'edit_token', 'revision']}
                elif instrument in ['layers', 'spatial']:
                    request['guard'] = state['guard']
                h.post('/api/' + instrument + '/command', request)
        if h.get('/api/state')['mode'] == 'experiment':
            h.post('/api/command', dict(command='atlas'))
        h.native('openspace.toggleShutdown();return {closing=true}')
        result['processes'] = {role: wait(role, 90) for role in ['engine', 'server', 'launcher', 'launcher_wrapper']}
        h._socket = None
        result['state'] = 'reopening'
        persist()
        with (folder / 'reopen.log').open('xb') as stream:
            reopened = subprocess.run([sys.executable, '-Xutf8', str(ROOT / 'scripts/open-expanded-journey-app.py')],
                                     cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, timeout=360)
        assert reopened.returncode == 0
        restored = h.post('/api/navigation/restore', dict(id=previous['temporary_favorite']))['navigation']
        h.post('/api/navigation/delete', dict(id=previous['temporary_favorite']))
        assert restored['et'] == previous['original_navigation']['et']
        assert h.get('/api/navigation/favorites')['views'] == previous['original_favorites']
        with Page() as page:
            page.wait_for_function('appState?.mode==="atlas"&&navigationState&&!pending')
            page.locator('#ui-scale').select_option('1')
            page.evaluate('selectTarget(' + json.dumps(restored['target']) + ',true)')
        result['final_session'] = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
        result['owner_app_kept_open'] = True
        assert set(result['processes'].values()) == {0} and set(result['verifier_exits'].values()) == {0}
        assert result['journey_accepted'], journey.get('failure')
        result.update(state='complete', accepted=True, completed=True)
    except Exception:
        result.update(state='failed', failure=traceback.format_exc())
    finally:
        for handle in handles.values():
            kernel.CloseHandle(handle)
        persist()
    print(json.dumps(dict(accepted=result['accepted'], state=result['state'], processes=result.get('processes'),
                         verifier_exits=result.get('verifier_exits'), failure=result.get('failure'))), flush=True)
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
