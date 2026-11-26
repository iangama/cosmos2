"""Retain both native sessions, run the C2-14 profile/audit, close and restore the owner."""
import argparse
import ctypes as ct
import datetime as dt
import hashlib
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
import zipfile

import psutil
import shutil
from ordinary_native_input_v9 import NativeInput
from cef_page_v2 import Page
from expanded_residency_processes import RetainedProcesses

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / 'output/c214-orbits-product0.28.2'
OWNER=ROOT/'output/original-flow-hotfix-product0.27.7'

def material(p):return {k:p.get(k) for k in ['system_id','revision','time','paused','bodies','atlas_initial','interventions']}
h = SourceFileLoader('c214_native_helpers', str(ROOT / 'scripts/benchmark-body-points-native.py')).load_module()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--plan-label', required=True)
    args = parser.parse_args()
    assert args.plan_label and len(args.plan_label) <= 20 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.plan_label)
    assert args.label and len(args.label) <= 20 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
    folder = ROOT / f'output/c214-orbits-profile-host-{args.label}'
    out = ROOT / f'evidence/c214-orbits-profile-host-{args.label}.json'
    assert not folder.exists() and not out.exists()
    plan_path = ROOT / f'evidence/c214-orbits-profile-plan-{args.plan_label}.json'
    plan = json.loads(plan_path.read_text())
    assert plan['accepted']
    sources = plan['source_sha256'] | {plan_path.relative_to(ROOT).as_posix(): sha(plan_path)}
    assert all(sha(ROOT / name) == seal for name, seal in sources.items())
    folder.mkdir()
    result = dict(accepted=False, completed=False, visual_accepted=False, performance_accepted=False,
                  pid=__import__('os').getpid(), state='preparing', source_sha256=sources,
                  groups=[], captures=[], closures=[], javascript_errors=[], started_utc=dt.datetime.now(dt.timezone.utc).isoformat())

    def persist():
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')

    (folder / 'recipe-before-execution.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    with zipfile.ZipFile(folder / 'executed-sources.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in sources:
            if name.startswith((CANDIDATE.relative_to(ROOT).as_posix() + '/', 'scripts/')) or name.startswith('C2-14-ORBITAS-PERFIL') or name == plan_path.relative_to(ROOT).as_posix():
                archive.write(ROOT / name, name)
    result['source_archive_sha256'] = sha(folder / 'executed-sources.zip')
    retained = []
    owner_closed = False
    candidate_started = False
    candidate_closed = False
    favorite = None

    def retain(session):
        tracker = RetainedProcesses(session)
        kernel = tracker.kernel
        kernel.WaitForSingleObject.argtypes = [ct.c_void_p, ct.c_uint32]
        kernel.WaitForSingleObject.restype = ct.c_uint32
        processes = {key: psutil.Process(session[field]) for key, field in [('engine', 'app'), ('server', 'server'), ('launcher', 'launcher')]}
        processes['launcher_wrapper'] = processes['launcher'].parent()
        assert processes['engine'].name().lower() == 'openspace.exe'
        assert Path(processes['engine'].exe()).resolve() == Path(session['runtime']) / 'bin/OpenSpace.exe'
        assert any(Path(arg).resolve() == Path(session['serverScript']).resolve() for arg in processes['server'].cmdline() if 'server.py' in arg)
        for role in ['launcher', 'launcher_wrapper']:
            assert any(Path(session['launcher_script']).name in arg for arg in processes[role].cmdline())
        rows = {}
        for role, process in processes.items():
            handle = kernel.OpenProcess(0x101000, False, process.pid)
            assert handle
            times, code = tracker.native_times(handle)
            assert code == 259 and abs((times[0] - 116444736000000000) / 1e7 - process.create_time()) <= 5e-6
            rows[role] = dict(handle=handle, pid=process.pid, created_filetime=times[0], exe=process.exe(), cmdline=process.cmdline())
        item = (tracker, rows, session)
        retained.append(item)
        return item

    def close(item):
        tracker, rows, session = item
        with Page() as page:
            window=NativeInput(session['app'],page)
            window.key(115,alt=True)
            result.setdefault('normal_close_actions',[]).append(window.actions)
        exits = {}
        for role, row in rows.items():
            deadline = time.monotonic() + 90
            while tracker.kernel.WaitForSingleObject(row['handle'], 0) != 0:
                assert time.monotonic() < deadline, role
                time.sleep(.1)
            times, code = tracker.native_times(row['handle'])
            assert code == 0 and times[0] == row['created_filetime'] and times[1] >= times[0]
            exits[role] = dict(pid=row['pid'], code=code, created_filetime=times[0], exited_filetime=times[1])
        result['closures'].append(dict(server_script=session['serverScript'], exits=exits))
        h._socket = None
        persist()

    try:
        session = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
        assert Path(session['serverScript']).resolve() == OWNER/'app/server.py'
        original = retain(session)
        assert h.get('/api/state')['mode'] == 'atlas'
        result['original_navigation'] = h.get('/api/navigation/state')
        result['original_favorites'] = h.get('/api/navigation/favorites')['views']
        current=h.get('/api/state')
        assert current['physics'] and current['physics']['paused']
        result['original_phase']=material(current['physics'])
        for kind in ['spatial','layers','particles','solar-zone']:
            state=h.get('/api/'+kind+'/state')
            assert not state.get('active') and not state.get('busy') and not state.get('recovery_required')
        previous=folder/'saved-before';previous.mkdir()
        for name in ['latest.json',json.loads((OWNER/'gravity-sessions/latest.json').read_text())['binary']]:
            shutil.copy2(OWNER/'gravity-sessions'/name,previous/name)
        favorites_path=OWNER/'navigation/favorites.json'
        shutil.copy2(favorites_path,previous/'favorites.json')
        result['favorites_before_sha256']=sha(favorites_path)
        views = h.post('/api/navigation/save', dict(name='Retorno após perfil C2-14'))['navigation']['views']
        favorite = next(row['id'] for row in views if row['id'] not in {v['id'] for v in result['original_favorites']})
        with Page() as page:
            window=NativeInput(session['app'],page)
            if page.evaluate('appState.mode==="atlas"'):
                window.click('#experiment');page.wait_for_function('!pending&&appState.mode==="experiment"')
            assert material(h.get('/api/state')['physics'])==result['original_phase']
            window.click('#save');page.wait_for_function('!pending&&document.getElementById("notice").textContent!=="Aplicando comando…"')
            assert json.loads((OWNER/'gravity-sessions/latest.json').read_text())['system_id']==result['original_phase']['system_id']
            window.click('#atlas');page.wait_for_function('!pending&&appState.mode==="atlas"')
            result['save_actions']=window.actions
        result['preserved_files']={}
        for directory in OWNER.iterdir():
            if not directory.is_dir() or directory.name in {'app','data','execution-logs','__pycache__'}:continue
            for source in directory.rglob('*'):
                if not source.is_file() or '__pycache__' in source.parts:continue
                relative=source.relative_to(OWNER);target=folder/'preserved-owner'/relative
                if relative.as_posix()=='navigation/favorites.json':continue
                target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
                assert sha(source)==sha(target);result['preserved_files'][relative.as_posix()]=sha(source)
        result.update(temporary_favorite=favorite, state='closing_owner')
        persist()
        owner_closed = True
        close(original)
        with (folder / 'candidate.log').open('xb') as stream:
            wrapper = subprocess.Popen([sys.executable, '-u', '-Xutf8', str(ROOT / 'scripts/launch-c214-orbits-candidate-v4.py'),'--plan-label',args.plan_label], cwd=ROOT,
                                       stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
                                       creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        candidate_started = True
        result.update(state='starting_candidate', candidate_wrapper=wrapper.pid)
        persist()
        deadline = time.monotonic() + 300
        while True:
            assert wrapper.poll() is None, 'Candidate launcher exited; inspect candidate.log'
            try:
                current = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
                if Path(current['serverScript']).resolve() == CANDIDATE / 'app/server.py' and (ROOT / 'output/bootstrap-ui.json').stat().st_mtime >= psutil.Process(current['app']).create_time():
                    break
            except (OSError, ValueError, KeyError, psutil.NoSuchProcess):
                pass
            assert time.monotonic() < deadline
            time.sleep(.1)
        active = retain(current)
        result.update(session=current, state='testing_cef')
        persist()
        result['state'] = 'profiling'
        persist()
        with (folder / 'profile.log').open('xb') as stream:
            child = subprocess.run([sys.executable, '-u', '-Xutf8', str(ROOT / 'scripts/profile-c214-orbits-v3.py'), '--label', args.label, '--plan-label', args.plan_label], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, timeout=1200)
        result.update(profile_exit=child.returncode, state='auditing')
        persist()
        with (folder / 'audit.log').open('xb') as stream:
            checked = subprocess.run([sys.executable, '-Xutf8', str(ROOT / 'scripts/audit-c214-orbits-profile-v3.py'), '--label', args.label], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, timeout=180)
        audit_path = ROOT / f'evidence/c214-orbits-profile-audit-{args.label}.json'
        admission = json.loads(audit_path.read_text())
        result.update(audit_exit=checked.returncode, audit_sha256=sha(audit_path), state='closing_candidate')
        persist()
        close(active)
        candidate_closed = True
        assert child.returncode == 0 and checked.returncode == 0 and admission['accepted'], admission.get('failure')
        result.update(accepted=True, completed=True, performance_accepted=True)
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        try:
            if candidate_started and not candidate_closed:
                current = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
                if Path(current['serverScript']).resolve() == CANDIDATE / 'app/server.py' and psutil.pid_exists(current['app']):
                    close(retained[-1] if len(retained) > 1 else retain(current))
            if owner_closed:
                result['state'] = 'restoring_owner'
                persist()
                with (folder / 'reopen.log').open('xb') as stream:
                    opened = subprocess.run(['cmd.exe','/d','/c',str(ROOT/'Iniciar-Cosmos2.cmd')], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, timeout=360)
                assert opened.returncode == 0
                with Page() as page:
                    page.wait_for_function('location.pathname==="/"&&!pending&&appState.mode==="atlas"',timeout=60000)
                    current_session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
                    assert Path(current_session['serverScript']).resolve()==OWNER/'app/server.py'
                    window=NativeInput(current_session['app'],page)
                    window.click('#experiment');page.wait_for_function('!pending&&appState.mode==="experiment"')
                    window.click('#load');page.wait_for_function('!pending&&appState.physics?.paused')
                    assert material(h.get('/api/state')['physics'])==result['original_phase']
                    window.click('#atlas');page.wait_for_function('!pending&&appState.mode==="atlas"')
                    result['restore_actions']=window.actions
                    result['restored_session']=current_session
                restored = h.post('/api/navigation/restore', dict(id=favorite))['navigation']
                h.post('/api/navigation/delete', dict(id=favorite))
                before = result['original_navigation']
                assert restored['et'] == before['et'] and restored['target'] == before['target']
                for key, value in before['navigation'].items():
                    assert all(abs(x-y) <= 1e-12 for x,y in zip(value,restored['navigation'][key],strict=True)) if key == 'Up' else value == restored['navigation'][key]
                assert h.get('/api/navigation/favorites')['views'] == result['original_favorites']
                assert sha(favorites_path)==result['favorites_before_sha256']
                assert all(sha(OWNER/name)==digest for name,digest in result['preserved_files'].items())
                result['owner_restored'] = True
            assert all(sha(ROOT / name) == seal for name, seal in sources.items())
        except Exception:
            result['cleanup_failure'] = traceback.format_exc()
            result['accepted'] = False
        for tracker, rows, _ in retained:
            for row in rows.values():
                tracker.kernel.CloseHandle(row['handle'])
        result['performance_accepted'] = bool(result['accepted'])
        result['state'] = 'complete' if result['accepted'] else 'failed'
        persist()
    print(json.dumps({key: result.get(key) for key in ['accepted', 'state', 'failure', 'cleanup_failure']}), flush=True)
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
