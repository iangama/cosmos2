"""Durable native check of the installed app with the gated PowerShell launcher."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
import traceback
import psutil
from PIL import Image
from cef_page_v2 import Page

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--launcher-kind', choices=['installed','candidate'], default='candidate')
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    base = ROOT / ('output/native-ui-startup-' + args.label + '-driver')
    driver = base.with_suffix('.json')
    python = ROOT / '.tooling/python/Scripts/python.exe'
    if not args.worker:
        if driver.exists() or base.with_suffix('.log').exists():
            raise FileExistsError('Preserve startup check')
        with base.with_suffix('.log').open('wb') as stdout, base.with_name(base.name + '-errors').with_suffix('.log').open('wb') as stderr:
            proc = subprocess.Popen([str(python), '-u', '-Xutf8', str(Path(__file__)), '--label', args.label, '--launcher-kind', args.launcher_kind, '--worker'], cwd=ROOT, stdout=stdout, stderr=stderr, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        driver.write_text(json.dumps(dict(pid=proc.pid, completed=False), indent=2) + '\n')
        print(json.dumps(dict(pid=proc.pid)))
        return
    out = ROOT / ('evidence/local-ui-native-startup-' + args.label + '.json')
    folder = ROOT / ('output/local-ui-native-startup-' + args.label)
    if out.exists() or folder.exists():
        raise FileExistsError('Preserve native evidence')
    unit = ROOT / 'evidence/local-ui-readiness-check-20261104.json'
    assert json.loads(unit.read_text(encoding='utf8'))['accepted']
    for proc in psutil.process_iter(['name', 'exe']):
        try:
            assert not (proc.info['name'].lower() == 'openspace.exe' and Path(proc.info['exe']).is_relative_to(ROOT)), 'An own engine is still running'
        except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError):
            continue
    folder.mkdir()
    entry = folder / 'original-entry.cmd'
    shutil.copy2(ROOT / 'Iniciar-Cosmos2.cmd', entry)
    sources = {p.relative_to(ROOT).as_posix(): sha(p) for p in [Path(__file__), entry, unit,
        ROOT / 'scripts/start-cosmos2-v2.ps1', ROOT / 'scripts/bootstrap-native-ui-v2.py',
        ROOT / 'scripts/native_ui_readiness.py', ROOT / 'scripts/wait-local-ui.py',
        ROOT / 'scripts/launch-is6-layers-import-candidate-v3.py']}
    app_root = ROOT / ('app' if args.launcher_kind == 'installed' else 'output/is6-layers-product0.21.1/app')
    installed = {p.relative_to(ROOT).as_posix(): sha(p) for p in app_root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    r = dict(accepted=False, completed=False, source_sha256=sources, installed_app_before=installed,
             owner_sha256=sha(ROOT / 'user/sessions/latest.json'), worker_pid=os.getpid(), launcher_kind=args.launcher_kind,
             scope='Startup readiness gate verification in the selected app only; no scientific model change, entry-point activation, candidate promotion or K5 performance acceptance.')
    persist = lambda: out.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    persist()
    launch = engine = server = helper = None
    log = (folder / 'launcher.log').open('wb')
    try:
        argv = (['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT / 'scripts/start-cosmos2-v2.ps1'), '-Built', '-Benchmark1080', '-InspectCEF'] if args.launcher_kind == 'installed' else [str(python), '-u', '-Xutf8', str(ROOT / 'scripts/launch-is6-layers-import-candidate-v3.py')])
        launch = subprocess.Popen(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        r['launcher_pid'] = launch.pid
        persist()
        deadline = time.monotonic() + 300
        while True:
            if launch.poll() is not None:
                raise RuntimeError('Launcher ended before the native UI check: ' + str(launch.returncode))
            try:
                session = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
                ready = json.loads((ROOT / 'output/local-ui-readiness.json').read_text(encoding='utf8'))
                bootstrap = json.loads((ROOT / 'output/bootstrap-ui.json').read_text(encoding='utf8'))
                if Path(session['serverScript']).resolve() == app_root / 'server.py' and (ready.get('accepted') or ready.get('ready')) and ready['server_pid'] == session['server'] and bootstrap.get('http_ready_before_gui_navigation'):
                    engine, server = psutil.Process(session['app']), psutil.Process(session['server'])
                    if 'server_created_unix' in ready:
                        assert ready['server_created_unix'] == server.create_time()
                    assert (ROOT / 'output/local-ui-readiness.json').stat().st_mtime <= engine.create_time() + .02
                    break
            except (OSError, ValueError, KeyError, psutil.NoSuchProcess):
                pass
            if time.monotonic() > deadline:
                raise TimeoutError('No gated native startup receipt')
            time.sleep(.2)
        r.update(session=session, readiness=ready, bootstrap=bootstrap,
                 engine_created_unix=engine.create_time())
        with Page() as page:
            # Inspect the page opened by the launcher. Do not navigate/reload it.
            page.wait_for_function('typeof appState!=="undefined"&&appState&&typeof atlasState!=="undefined"&&atlasState&&!pending', timeout=30000)
            ui = page.evaluate('({url:location.href,title:document.title,mode:appState.mode,text:document.body.innerText.slice(0,600)})')
            assert ui['url'] == 'http://127.0.0.1:4700/' and ui['title'].startswith('Cosmos2')
            assert 'ERR_CONNECTION_REFUSED' not in ui['text'] and 'COSMOS2' in ui['text']
            r['ui_without_manual_navigation'] = ui
        helper = SourceFileLoader('startup_native_helpers', str(ROOT / 'scripts/benchmark-body-points-native.py')).load_module()
        screenshots = ROOT / 'user/screenshots'
        previous = set(screenshots.rglob('*.png'))
        helper.native('openspace.takeScreenshot();return {requested=true}')
        deadline = time.monotonic() + 20
        while True:
            fresh = set(screenshots.rglob('*.png')) - previous
            if fresh:
                assert len(fresh) == 1
                original = fresh.pop()
                try:
                    with Image.open(original) as im:
                        assert im.size == (1920, 1080)
                        im.verify()
                    break
                except OSError:
                    pass
            if time.monotonic() > deadline:
                raise TimeoutError('Startup screenshot did not finish')
            time.sleep(.1)
        image = ROOT / ('evidence/cosmos2-ui-startup-' + args.label + '.png')
        assert not image.exists()
        shutil.copy2(original, image)
        assert sha(original) == sha(image)
        r['capture'] = dict(path=image.relative_to(ROOT).as_posix(), sha256=sha(image), method='Raw native framebuffer')
        r['completed'] = True
    except Exception:
        r['failure'] = traceback.format_exc()
    finally:
        try:
            if engine is not None and engine.is_running():
                if helper is None:
                    helper = SourceFileLoader('startup_cleanup_helpers', str(ROOT / 'scripts/benchmark-body-points-native.py')).load_module()
                helper.native('openspace.toggleShutdown();return {closing=true}')
                r['engine_exit'] = engine.wait(timeout=40)
            if helper is not None and helper._socket:
                helper._socket.close()
            if launch is not None:
                r['launcher_exit'] = launch.wait(timeout=40)
            if server is not None:
                r['server_exit'] = server.wait(timeout=10)
            assert r.get('engine_exit') == r.get('server_exit') == r.get('launcher_exit') == 0
            assert sha(ROOT / 'user/sessions/latest.json') == r['owner_sha256']
            assert all(sha(ROOT / p) == seal for p, seal in installed.items())
            assert all(sha(ROOT / p) == seal for p, seal in sources.items())
            for name in ['local-ui-readiness.json', 'local-ui-readiness.log', 'bootstrap-ui.json', 'bootstrap-ui.log', 'bootstrap-ui-errors.log', 'session.json', 'server.log', 'server-errors.log', 'engine-errors.log']:
                original = ROOT / 'output' / name
                if original.is_file():
                    target = folder / name
                    shutil.copy2(original, target)
                    r['source_sha256'][target.relative_to(ROOT).as_posix()] = sha(target)
            r['accepted'] = r['completed'] and not r.get('failure')
        except Exception:
            r['cleanup_failure'] = traceback.format_exc()
        log.close()
        persist()
        driver.write_text(json.dumps(dict(pid=os.getpid(), completed=True, accepted=r['accepted']), indent=2) + '\n')
    print(json.dumps(dict(accepted=r['accepted'], completed=r['completed'], failure=r.get('failure'), cleanup_failure=r.get('cleanup_failure'))))
    return 0 if r['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
