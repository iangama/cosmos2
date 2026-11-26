"""Detached controller: retain four native handles, profile, audit, close and restore owner view."""
import argparse
import ctypes as ct
import datetime as dt
import hashlib
from importlib.machinery import SourceFileLoader
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

import psutil
from cef_page_v2 import Page
import owned_process_snapshot as ownership
from expanded_residency_processes import RetainedProcesses

ROOT = Path(__file__).resolve().parents[1]
h = SourceFileLoader('expanded_residency_host_helpers', str(ROOT / 'scripts/benchmark-body-points-native.py')).load_module()
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--plan-label', required=True)
    args = parser.parse_args()
    for label in [args.label, args.plan_label]:
        assert label and len(label) <= 20 and all(ch in 'abcdefghijklmnopqrstuvwxyz0123456789-' for ch in label)
    folder = ROOT / f'output/is6-expanded-residency-host-{args.label}'
    out = ROOT / f'evidence/is6-expanded-residency-host-{args.label}.json'
    assert not folder.exists() and not out.exists()
    plan_path = ROOT / f'evidence/is6-expanded-residency-plan-{args.plan_label}.json'
    plan = json.loads(plan_path.read_text())
    assert plan['accepted'] and all(sha(ROOT / name) == seal for name, seal in (plan['source_sha256'] | plan['protected_sha256']).items())
    session = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
    app = ROOT / 'output/is6-expanded-journey-product0.27.0/app/server.py'
    assert Path(session['serverScript']).resolve() == app
    engine, server, launcher = [psutil.Process(session[key]) for key in ['app', 'server', 'launcher']]
    wrapper = launcher.parent()
    assert engine.name().lower() == 'openspace.exe' and Path(engine.exe()).resolve() == Path(session['runtime']) / 'bin/OpenSpace.exe'
    assert any(Path(arg).resolve() == app for arg in server.cmdline() if 'server.py' in arg.lower())
    assert all(any('launch-is6-expanded-journey-candidate.py' in arg for arg in proc.cmdline()) for proc in [launcher, wrapper])
    assert wrapper.create_time() <= launcher.create_time() <= server.create_time() <= engine.create_time()
    folder.mkdir()
    result = dict(accepted=False, completed=False, state='retaining_handles', pid=os.getpid(), session=session,
                  plan_sha256=sha(plan_path), processes={}, handle_identities={}, started_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    tracker = RetainedProcesses(session)
    kernel, handles = tracker.kernel, {}
    kernel.WaitForSingleObject.argtypes = [ct.c_void_p, ct.c_uint32]
    kernel.WaitForSingleObject.restype = ct.c_uint32
    original_id = None

    def persist():
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')

    def close_current():
        for name in ['spatial', 'layers', 'particles', 'solar-zone']:
            value = h.get('/api/' + name + '/state')
            if value['active'] or value.get('recovery_required'):
                request = dict(command='leave')
                if name in ['spatial', 'layers']:
                    request['guard'] = value['guard']
                elif name == 'solar-zone':
                    request['guard'] = {key: value['worker'][key] for key in ['worker_id', 'artifact_id', 'edit_token', 'revision']}
                h.post('/api/' + name + '/command', request)
        with Page() as page:
            page.evaluate('document.body.inert=false')
        if h.get('/api/state')['mode'] == 'experiment':
            h.post('/api/command', dict(command='atlas'))
        h.native('openspace.toggleShutdown();return {closing=true}')
        for role, handle in handles.items():
            deadline = time.monotonic() + 90
            while kernel.WaitForSingleObject(handle, 0) != 0:
                if time.monotonic() > deadline:
                    raise TimeoutError('Native handle did not exit: ' + role)
                time.sleep(.1)
            times, code = tracker.native_times(handle)
            assert code == 0 and times[0] == result['handle_identities'][role]['created_filetime'] and times[1] >= times[0]
            result['processes'][role] = dict(code=code, created_filetime=times[0], exited_filetime=times[1])
        h._socket = None
        assert len(result['processes']) == 4

    persist()
    try:
        for role, process in dict(engine=engine, server=server, launcher=launcher, launcher_wrapper=wrapper).items():
            handle = kernel.OpenProcess(0x101000, False, process.pid)
            if not handle:
                raise ct.WinError(ct.get_last_error())
            handles[role] = handle
            times, code = tracker.native_times(handle)
            assert code == 259 and abs((times[0] - 116444736000000000) / 1e7 - process.create_time()) <= 5e-6
            result['handle_identities'][role] = dict(pid=process.pid, created_filetime=times[0], exe=process.exe(), cmdline=process.cmdline())
        assert h.get('/api/state')['mode'] == 'atlas'
        result['original_navigation'] = h.get('/api/navigation/state')
        result['original_favorites'] = h.get('/api/navigation/favorites')['views']
        views = h.post('/api/navigation/save', dict(name='Retorno após residência ampliada'))['navigation']['views']
        original_id = next(value['id'] for value in views if value['id'] not in {item['id'] for item in result['original_favorites']})
        result.update(temporary_favorite=original_id, state='profiling')
        persist()
        with (folder / 'profile.log').open('xb') as stream:
            child = subprocess.run([sys.executable, '-u', '-Xutf8', str(ROOT / 'scripts/profile-expanded-residency.py'),
                                    '--label', args.label, '--plan-label', args.plan_label], cwd=ROOT,
                                   stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT)
        result.update(profile_exit=child.returncode, state='auditing')
        persist()
        with (folder / 'audit.log').open('xb') as stream:
            checked = subprocess.run([sys.executable, '-Xutf8', str(ROOT / 'scripts/audit-expanded-residency.py'), '--label', args.label],
                                     cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, timeout=180)
        audit_path = ROOT / f'evidence/is6-expanded-residency-audit-{args.label}.json'
        proof = json.loads(audit_path.read_text())
        result.update(audit_exit=checked.returncode, audit_sha256=sha(audit_path), state='closing')
        persist()
        close_current()
        assert child.returncode == 0 and checked.returncode == 0 and proof['accepted'], proof.get('failure')
        result.update(accepted=True, completed=True)
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        try:
            if handles and len(result['processes']) != 4:
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
                before = result['original_navigation']
                assert restored['et'] == before['et'] and restored['target'] == before['target']
                assert restored['navigation'] == before['navigation']
                assert h.get('/api/navigation/favorites')['views'] == result['original_favorites']
                with Page() as page:
                    page.wait_for_function('appState?.mode==="atlas"&&navigationState&&!pending')
                    page.locator('#ui-scale').select_option('1')
                    page.evaluate('selectTarget(' + json.dumps(restored['target']) + ',true)')
            assert all(sha(ROOT / name) == seal for name, seal in (plan['source_sha256'] | plan['protected_sha256']).items())
            result.update(owner_app_kept_open=True, final_session=json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig')))
        except Exception:
            result['cleanup_failure'] = traceback.format_exc()
            result['accepted'] = False
        for handle in handles.values():
            kernel.CloseHandle(handle)
        result['state'] = 'complete' if result['accepted'] else 'failed'
        persist()
    print(json.dumps(dict(accepted=result['accepted'], state=result['state'], failure=result.get('failure'), cleanup_failure=result.get('cleanup_failure'))), flush=True)
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
