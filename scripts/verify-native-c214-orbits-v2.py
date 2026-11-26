"""Detached native CEF functional run; preserve failed evidence and restore owner."""
import argparse
import ctypes as ct
import datetime as dt
import hashlib
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
import zipfile

import psutil
from PIL import Image
from cef_page_v2 import Page
from expanded_residency_processes import RetainedProcesses

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / 'output/c214-orbits-product0.28.1'
h = SourceFileLoader('c214_native_helpers', str(ROOT / 'scripts/benchmark-body-points-native.py')).load_module()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and len(args.label) <= 20 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
    folder = ROOT / f'output/c214-orbits-native-{args.label}'
    out = ROOT / f'evidence/c214-orbits-native-{args.label}.json'
    assert not folder.exists() and not out.exists()
    manifest_path = CANDIDATE / 'build-manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf8'))
    sources = manifest['source_sha256'].copy()
    for tree, key in [('app', 'files_sha256'), ('data', 'data_sha256')]:
        sources.update({(CANDIDATE / tree / name).relative_to(ROOT).as_posix(): seal for name, seal in manifest[key].items()})
    for path in [manifest_path, Path(__file__).resolve(), ROOT / 'scripts/cef_page_v2.py', ROOT / 'scripts/expanded_residency_processes.py']:
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
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
            if name.startswith(CANDIDATE.relative_to(ROOT).as_posix() + '/') or name in ['scripts/verify-native-c214-orbits.py', 'scripts/cef_page_v2.py', 'scripts/expanded_residency_processes.py', 'C2-14-ORBITAS-NATIVO-CONTRATO-20261114.md']:
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
            page.goto('http://127.0.0.1:4700/')
            page.wait_for_function('appState?.mode==="atlas"&&!pending', timeout=60000)
        h.native('openspace.toggleShutdown();return {closing=true}')
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

    def complete(page):
        page.wait_for_function('!pending&&response?.result.timelike&&document.getElementById("force-status").textContent.startsWith("Cálculo concluído")', timeout=30000)
        assert not page.evaluate('document.getElementById("force-status").classList.contains("error")')
        return page.evaluate('({fingerprint:response.physics_sha256,parameters:response.configuration.parameters,model:response.result.timelike.configuration,kind:response.result.timelike.trajectory_kind,clock:response.result.timelike.clock_kind,measurements:response.result.measurements})')

    def capture(page, name, scale):
        page.evaluate('document.body.style.zoom=' + json.dumps(scale) + ';document.querySelector("article").scrollIntoView({block:"start"});draw()')
        time.sleep(.5)
        layout = page.evaluate('({zoom:getComputedStyle(document.body).zoom,scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,canvas:{width:canvas.width,height:canvas.height},view:byId("timelike-view").value})')
        assert float(layout['zoom']) == scale and layout['scroll'] <= layout['client']
        before = set((ROOT / 'user/screenshots').rglob('*.png'))
        h.native('openspace.takeScreenshot();return {requested=true}')
        deadline = time.monotonic() + 20
        while True:
            fresh = set((ROOT / 'user/screenshots').rglob('*.png')) - before
            if fresh:
                assert len(fresh) == 1
                source = fresh.pop()
                try:
                    with Image.open(source) as img:
                        assert img.size == (1920, 1080)
                        img.load()
                    break
                except (OSError, SyntaxError):
                    pass
            assert time.monotonic() < deadline
            time.sleep(.1)
        target = folder / f'{name}-{int(scale*100)}.png'
        shutil.copy2(source, target)
        assert sha(source) == sha(target)
        result['captures'].append(dict(path=target.relative_to(ROOT).as_posix(), sha256=sha(target), native_original=source.relative_to(ROOT).as_posix(), layout=layout, method='Unedited original OpenSpace framebuffer'))
        persist()

    try:
        session = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
        assert Path(session['serverScript']).resolve() == ROOT / 'output/is6-expanded-journey-product0.27.0/app/server.py'
        original = retain(session)
        assert h.get('/api/state')['mode'] == 'atlas'
        result['original_navigation'] = h.get('/api/navigation/state')
        result['original_favorites'] = h.get('/api/navigation/favorites')['views']
        views = h.post('/api/navigation/save', dict(name='Retorno após órbitas C2-14'))['navigation']['views']
        favorite = next(row['id'] for row in views if row['id'] not in {v['id'] for v in result['original_favorites']})
        result.update(temporary_favorite=favorite, state='closing_owner')
        persist()
        close(original)
        owner_closed = True
        with (folder / 'candidate.log').open('xb') as stream:
            wrapper = subprocess.Popen([sys.executable, '-u', '-Xutf8', str(ROOT / 'scripts/launch-c214-orbits-candidate-v2.py')], cwd=ROOT,
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
        with Page() as page:
            page.on('pageerror', lambda error: result['javascript_errors'].append(error))
            page.goto('http://127.0.0.1:4700/forces.html#timelike-orbits')
            baseline = complete(page)
            assert page.evaluate('response.result.time_s.length===1025&&Number(byId("time-index").max)===1024')
            for index in [0, 512, 1024]:
                page.locator('#time-index').select_option(str(index))
                assert page.evaluate('byId("timelike-readings").textContent.includes("Raio areal")')
            result['groups'].append(dict(name='native_compute_timeline', baseline=baseline))
            for scale in [1, 1.5]:
                page.locator('#timelike-view').select_option('orbits')
                capture(page, 'orbits', scale)
                page.locator('#timelike-view').select_option('clocks')
                assert page.evaluate('byId("reference-entry").textContent.includes("Relógio GR")')
                capture(page, 'clocks', scale)
            page.evaluate('document.body.style.zoom=1')
            page.locator('input[data-force="gravity"][data-control="visible"]').set_checked(False)
            invisible = complete(page)
            assert invisible['fingerprint'] == baseline['fingerprint']
            assert page.evaluate('byId("reference-entry").hidden')
            page.locator('input[data-force="gravity"][data-control="visible"]').set_checked(True)
            complete(page)
            combinations = []
            for orbit, clock in [(False, True), (False, False), (True, False), (True, True)]:
                page.locator('input[data-effect="orbital_acceleration"]').set_checked(orbit)
                complete(page)
                page.locator('input[data-effect="proper_clock_rate"]').set_checked(clock)
                value = complete(page)
                assert page.evaluate('response.result.timelike.orbit_effect_applied') == orbit
                assert page.evaluate('response.result.timelike.clock_effect_applied') == clock
                combinations.append(dict(orbit=orbit, clock=clock, value=value))
            result['groups'].append(dict(name='visibility_and_operators', combinations=combinations))
            page.locator('#parameters select[name="orbit_kind"]').select_option('circular')
            page.locator('#calculate').click()
            circle = complete(page)
            assert page.evaluate('response.result.timelike.apsides.length===0&&response.result.measurements[0].value===null&&document.querySelector("[data-parameter=eccentricity]").hidden')
            result['groups'].append(dict(name='circular_undefined_precession', value=circle))
            previous = page.evaluate('response.physics_sha256')
            page.evaluate('for(const [key,value] of Object.entries({mass_solar:8.37,semi_latus_rectum_rs:1e8,orbit_kind:"eccentric",eccentricity:.8,radial_cycles:16})){byId("parameters").elements[key].value=value;}updateTimelikeParameters();byId("calculate").click()')
            page.wait_for_function('timelikeJob!==null&&!byId("cancel-timelike").disabled')
            page.locator('#cancel-timelike').click()
            page.wait_for_function('!pending&&byId("force-status").textContent.startsWith("Cálculo cancelado")', timeout=30000)
            assert page.evaluate('response.physics_sha256') == previous
            assert h.get('/api/timelike/state')['phase'] == 'cancelled'
            result['groups'].append(dict(name='actual_ui_cancellation', last_complete_preserved=True))
            page.evaluate('config=structuredClone(response.configuration);buildControls();buildParameters();byId("calculate").click()')
            saved = complete(page)
            page.locator('#save-forces').click()
            page.wait_for_function('byId("force-status").textContent.startsWith("Condições, controles")')
            page.locator('#load-forces').click()
            page.wait_for_function('!pending&&byId("restoration-note").dataset.state==="same_generation"&&!byId("restoration-note").hidden', timeout=30000)
            assert page.evaluate('response.physics_sha256') == saved['fingerprint']
            page.locator('#export-forces').click()
            page.wait_for_function('!pending&&lastForcesExport!==null', timeout=30000)
            exported = page.evaluate('lastForcesExport')
            result['groups'].append(dict(name='private_save_resume_export', export=exported))
            (folder / 'last-result.json').write_text(json.dumps(page.evaluate('response'), ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
            assert not result['javascript_errors'], result['javascript_errors']
        close(active)
        candidate_closed = True
        result.update(accepted=True, completed=True)
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
                    opened = subprocess.run([sys.executable, '-Xutf8', str(ROOT / 'scripts/open-expanded-journey-app.py')], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, timeout=360)
                assert opened.returncode == 0
                restored = h.post('/api/navigation/restore', dict(id=favorite))['navigation']
                h.post('/api/navigation/delete', dict(id=favorite))
                before = result['original_navigation']
                assert restored['et'] == before['et'] and restored['target'] == before['target']
                for key, value in before['navigation'].items():
                    assert all(abs(x-y) <= 1e-12 for x,y in zip(value,restored['navigation'][key],strict=True)) if key == 'Up' else value == restored['navigation'][key]
                assert h.get('/api/navigation/favorites')['views'] == result['original_favorites']
                result['owner_restored'] = True
            assert all(sha(ROOT / name) == seal for name, seal in sources.items())
        except Exception:
            result['cleanup_failure'] = traceback.format_exc()
            result['accepted'] = False
        for tracker, rows, _ in retained:
            for row in rows.values():
                tracker.kernel.CloseHandle(row['handle'])
        result['state'] = 'complete' if result['accepted'] else 'failed'
        persist()
    print(json.dumps({key: result.get(key) for key in ['accepted', 'state', 'failure', 'cleanup_failure']}), flush=True)
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
