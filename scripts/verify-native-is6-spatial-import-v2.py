"""Owned Python host: actual spatial import UI, archived restore and cleanup."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import argparse
import copy
import ctypes
import hashlib
import json
import shutil
import subprocess
import sys
import threading
import time
import traceback
import psutil
from PIL import Image
from cef_page_v2 import Page

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is6-spatial-import-product0.22.0/app'
sys.path.insert(0, str(APP))
import is6_spatial_import_store as storage
from is6_product_scene import lua
artifact = storage.artifact
h = SourceFileLoader('spatial_native_helpers', str(ROOT / 'scripts/benchmark-body-points-native.py')).load_module()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    parser.add_argument('--seed-label')
    args = parser.parse_args()
    for label in [args.label, *([args.seed_label] if args.seed_label else [])]:
        if not label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
            parser.error('Invalid label')
    folder = ROOT / ('output/is6-spatial-import-native-' + args.label)
    out = ROOT / ('evidence/is6-spatial-import-native-' + args.label + '.json')
    if folder.exists() or out.exists():
        raise FileExistsError('Preserve spatial native evidence')
    manifest_path = APP.parent / 'build-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    assert manifest['candidate'] == '0.22.0' and manifest['promoted'] is False
    sources = dict(manifest['source_sha256'])
    for name, seal in manifest['files_sha256'].items():
        sources[(APP / name).relative_to(ROOT).as_posix()] = seal
    launcher = ROOT / 'scripts/launch-is6-spatial-import-candidate.py'
    for path in [Path(__file__), manifest_path, launcher, ROOT / 'scripts/cef_page_v2.py',
                 ROOT / 'scripts/benchmark-body-points-native.py', ROOT / 'scripts/bootstrap-native-ui-v2.py',
                 ROOT / 'scripts/native_ui_readiness.py', ROOT / 'evidence/is6-spatial-import-http-20261105a.json']:
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
    seed = None
    if args.seed_label:
        path = ROOT / ('evidence/is6-spatial-import-native-' + args.seed_label + '.json')
        seed = json.loads(path.read_text())
        assert seed['accepted'] and seed['processes']['engine_exit'] == seed['processes']['server_exit'] == seed['processes']['launcher_exit'] == 0
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
    assert all(sha(ROOT / name) == seal for name, seal in sources.items())
    http = json.loads((ROOT / 'evidence/is6-spatial-import-http-20261105a.json').read_text())
    assert http['accepted']
    for p in psutil.process_iter(['name', 'exe']):
        try:
            assert not (p.info['name'].lower() == 'openspace.exe' and Path(p.info['exe']).is_relative_to(ROOT)), 'An own engine is already running'
        except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError):
            continue
    folder.mkdir()
    result = dict(accepted=False, completed=False, phase='restart' if seed else 'first', source_sha256=sources,
        owner_sha256=sha(ROOT / 'user/sessions/latest.json'), checks=[], refusals=[], captures=[], page_errors=[],
        processes={}, scope='Native 0.22.0 spatial-source UI/restore slice. Explicit first/restart receipts; no GPU/frame profile, shortcut activation, promotion or IS6/v1 acceptance.')
    store = storage.Store(APP.parent / 'is6-spatial-import-service-records')
    handles, launch, logs = {}, None, []
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    kernel.GetExitCodeProcess.restype = ctypes.c_bool
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    def persist():
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
    def state():
        return h.get('/api/spatial/state')
    def command(operation, **fields):
        return h.post('/api/spatial/command', dict(command=operation, guard=state()['guard'], **fields))
    def click(page, selector, instrument='spatial'):
        page.evaluate('(()=>{let e=document.querySelector('+json.dumps(selector)+');for(let p=e.parentElement;p;p=p.parentElement)if(p.tagName==="DETAILS")p.open=true;})()')
        ready = '!'+instrument+'Instrument.pending&&!'+instrument+'Instrument.readingFile&&!'+instrument+'Instrument.snapshot?.busy'
        page.wait_for_function(ready+'&&!document.querySelector('+json.dumps(selector)+').matches(":disabled")', timeout=70000)
        page.locator(selector).click()
        page.wait_for_function(ready, timeout=70000)
        assert not page.evaluate(instrument+'Instrument.error'), page.evaluate(instrument+'Instrument.error')
    def choose_file(page, selector, path):
        document = page.call('DOM.getDocument')['root']['nodeId']
        node = page.call('DOM.querySelector', dict(nodeId=document, selector=selector))['nodeId']
        page.call('DOM.setFileInputFiles', dict(nodeId=node, files=[str(path)]))
        page.evaluate('document.querySelector('+json.dumps(selector)+').dispatchEvent(new Event("change",{bubbles:true}))')
    def context(phase):
        names = ['LabGrid','LabBarycenter','LabProbe']
        for body in phase['bodies']:
            names.extend(body[k] for k in ['scene_node','label_node','shape_node','spin_node'] if body.get(k))
        return h.native('local f={};for _,n in ipairs('+lua(names)+') do if openspace.hasSceneGraphNode(n) then local ok,v=pcall(openspace.propertyValue,"Scene."..n..".Renderable.Enabled");if ok and type(v)=="boolean" then f[n]=v end end end;return {camera=openspace.navigation.getNavigationState("Root"),flags=f}')
    def same_context(before, after):
        assert before['flags'] == after['flags']
        for key, value in before['camera'].items():
            if key == 'Up':
                assert all(abs(a-b) <= 1e-12 for a,b in zip(value,after['camera'][key],strict=True))
            else:
                assert value == after['camera'][key], key
    def capture(page, section, scale):
        page.locator('#ui-scale').select_option(scale)
        page.evaluate('document.getElementById("spatial-panel").hidden=false')
        target = {'import':'spatial-import-reading','source':'spatial-source','probe':'spatial-reading'}[section]
        page.evaluate('(()=>{const e=document.getElementById('+json.dumps(target)+');for(let p=e.parentElement;p;p=p.parentElement)if(p.tagName==="DETAILS")p.open=true;e.scrollIntoView({block:"center"});})()')
        time.sleep(.75)
        screenshot_folder = ROOT / 'user/screenshots'
        before = set(screenshot_folder.rglob('*.png'))
        h.native('openspace.takeScreenshot();return {requested=true}')
        deadline = time.monotonic()+20
        while True:
            fresh = set(screenshot_folder.rglob('*.png'))-before
            if len(fresh) == 1:
                original = fresh.pop()
                try:
                    with Image.open(original) as im:
                        assert im.size == (1920,1080)
                        pixels = im.convert('RGB')
                    break
                except OSError:
                    pass
            if time.monotonic() > deadline:
                raise TimeoutError('Native screenshot incomplete')
            time.sleep(.1)
        path = folder / (section+'-'+str(int(float(scale)*100))+'.png')
        shutil.copy2(original, path)
        rgb = path.with_stem(path.stem+'-RGB')
        pixels.save(rgb)
        layout = page.evaluate('(()=>{const p=document.getElementById("spatial-panel");return {width:p.clientWidth,scroll:p.scrollWidth,error:spatialInstrument.error}})()')
        assert layout['scroll'] == layout['width'] and not layout['error']
        result['captures'].append(dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), RGB=rgb.relative_to(ROOT).as_posix(), RGB_sha256=sha(rgb), layout=layout))
        persist()
    persist()
    try:
        logs = [(folder / name).open('wb') for name in ['launcher.log','launcher-errors.log']]
        launch = subprocess.Popen([sys.executable,'-u','-Xutf8',str(launcher)], cwd=ROOT, stdout=logs[0], stderr=logs[1])
        deadline = time.monotonic()+300
        while True:
            if launch.poll() is not None:
                raise RuntimeError('Native launcher exited: '+str(launch.returncode))
            try:
                session = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
                ready = json.loads((ROOT / 'output/local-ui-readiness.json').read_text())
                launcher_pids = {launch.pid, *[p.pid for p in psutil.Process(launch.pid).children(recursive=True) if any(str(launcher).lower() == a.lower() for a in p.cmdline())]}
                if session.get('launcher') in launcher_pids and Path(session['serverScript']).resolve() == APP / 'server.py' and ready['server_pid'] == session['server']:
                    app = psutil.Process(session['app'])
                    if (ROOT / 'output/bootstrap-ui.json').stat().st_mtime >= app.create_time():
                        break
            except (OSError, ValueError, KeyError, psutil.NoSuchProcess):
                pass
            if time.monotonic() > deadline:
                raise TimeoutError('No own gated native startup')
            time.sleep(.2)
        result['session'] = session
        result['launcher_wrapper_pid'] = launch.pid
        persist()
        for role in ['app','server','launcher']:
            handle = kernel.OpenProcess(0x100000 | 0x1000,False,session[role])
            if not handle:
                raise ctypes.WinError(ctypes.get_last_error())
            handles['engine' if role == 'app' else role] = handle
        assert ready['ready'] and ready['http_ready_before_engine_start'] and ready['checked_root_page']
        for name in ['local-ui-readiness.json','bootstrap-ui.json','session.json']:
            shutil.copy2(ROOT / 'output' / name, folder / name)
        source = ROOT / 'output/is6-spatial-import-20261104a/saved-0-source.json'
        package = storage.migration.preview(source.read_bytes())
        result['source_sha256'][source.relative_to(ROOT).as_posix()] = sha(source)
        result['artifact_sha256'] = package['artifact_sha256']
        with Page() as page:
            page.on('pageerror', lambda error: result['page_errors'].append(error))
            page.wait_for_function('typeof spatialInstrument!=="undefined"&&spatialInstrument.snapshot&&typeof appState!=="undefined"&&appState&&!pending',timeout=70000)
            assert page.evaluate('location.href') == 'http://127.0.0.1:4700/' and not state()['active']
            click(page,'#open-layers','layer')
            choose_file(page,'#layers-import-file',source)
            click(page,'#layers-import-preview','layer')
            page.wait_for_function('!document.getElementById("layers-spatial-route").hidden')
            assert page.evaluate('layerInstrument.snapshot.import_preview') is None
            click(page,'#layers-spatial-route','layer')
            click(page,'#spatial-import-preview')
            before_preview = state()
            assert before_preview['import_preview']['valid'] and not before_preview['active']
            capture(page,'import','1')
            capture(page,'import','1.5')
            click(page,'#spatial-import-cancel')
            assert state()['guard'] == before_preview['guard'] and state()['import_preview'] is None
            click(page,'#spatial-import-preview')
            old_ids = {row['id'] for row in state()['branches']}
            click(page,'#spatial-import-commit')
            imported = next(row for row in state()['branches'] if row['id'] not in old_ids)
            assert imported['branch']['parent'] is None and not state()['active']
            result['imported_branch'] = imported['id']
            click(page,'#spatial-copy')
            page.wait_for_function('appState.physics?.bodies.length===4&&!pending',timeout=70000)
            phase = h.get('/api/state')['physics']
            result['live_phase'] = phase
            baseline = context(phase)
            assert baseline['flags'] and any(baseline['flags'].values())
            assert phase['system_id'] != package['artifact']['phase']['system_id']
            if seed:
                assert phase['system_id'] != seed['live_phase']['system_id']
                before_bytes = store.path.read_bytes()
                click(page,'#spatial-load-saved')
                assert state()['active'] and store.path.read_bytes() == before_bytes
                assert command('get_artifact')['result'] == package['artifact']
                result['checks'].append('Fresh host restored latest from closed instrument with new live IDs')
                click(page,'#spatial-leave')
                same_context(baseline, context(phase))
            guard = state()['guard']
            rejected = h.post('/api/spatial/command',dict(command='branch_load',guard=guard,branch_id=imported['id'],source_guard=artifact.body.guard(package['artifact']['phase'])),expected=400)
            assert rejected['ok'] is False and state()['guard'] == guard and not state()['active']
            result['refusals'].append(rejected['error'])
            page.locator('#spatial-branches').select_option(imported['id'])
            click(page,'#spatial-branch-load')
            confirmed = state()
            assert confirmed['active'] and confirmed['artifact']['archived']
            assert confirmed['artifact']['view'] == package['view'] and command('get_artifact')['result'] == package['artifact']
            assert confirmed['artifact']['sha256'] == package['artifact_sha256']
            assert confirmed['artifact']['live_source_guard'] == artifact.body.guard(phase)
            assert confirmed['artifact']['origin']['original_view'] == package['view']
            scene = confirmed['scene']
            raw = h.native('return {center=openspace.propertyValue("Scene.'+scene['frame']+'.Translation.Position"),draw=openspace.propertyValue("Scene.'+scene['wire']+'.Renderable.DrawElements")}')
            assert raw['center'] == package['artifact']['binding']['center_render_m'] and raw['draw'] is False
            assert all(value is False for value in context(phase)['flags'].values())
            result['checks'].append('Closed branch restore preserved archived science and hid current live nodes')
            click(page,'#spatial-visible')
            for key, value in [('radial',3),('azimuth',7),('reference',64)]:
                page.evaluate('document.getElementById('+json.dumps('spatial-'+key)+').value='+json.dumps(str(value)))
            click(page,'#spatial-sample')
            changed = state()['artifact']['view']
            assert changed == dict(visible=True,selected_radial_index=3,selected_azimuth_index=7,reference_radial_index=64)
            assert state()['artifact']['sample'] == artifact.Run.restore(package['artifact']).sample(changed)
            for scale in ['1','1.5']:
                capture(page,'probe',scale)
                capture(page,'source',scale)
            click(page,'#spatial-save')
            assert store.load().origin == package and store.load().view == changed
            page.evaluate('document.getElementById("spatial-branch-name").value="Filho espacial nativo"')
            click(page,'#spatial-branch-create')
            child_id = state()['branch_parent']
            assert store.load(child_id).branch['parent'] == imported['id']
            result['child_branch'] = child_id
            exports_before = set(store.exports.glob('*.json'))
            click(page,'#spatial-export')
            exports = set(store.exports.glob('*.json'))-exports_before
            assert len(exports) == 1
            exported = storage.decode(exports.pop().read_bytes())
            assert exported.origin == package and exported.view == changed and exported.lineage_parent == child_id
            result['checks'].append('Explicit view/save/child/export retained the complete source capsule')
            # Public cancellation of a real restore; no fake native adapter.
            before = state()
            replies = []
            def restore():
                replies.append(h.post('/api/spatial/command',dict(command='branch_load',guard=before['guard'],branch_id=imported['id'],source_guard=artifact.body.guard(phase)),expected=400))
            worker = threading.Thread(target=restore)
            worker.start()
            deadline = time.monotonic()+10
            cancelled = None
            while worker.is_alive() and time.monotonic() < deadline:
                transaction = state().get('transaction')
                if transaction and transaction['cancellable']:
                    cancelled = h.post('/api/spatial/cancel',dict(transaction_id=transaction['id']))
                    break
                time.sleep(.01)
            worker.join(timeout=70)
            assert not worker.is_alive() and cancelled and cancelled['ok'] and replies[0]['ok'] is False
            after = state()
            assert after['guard'] == before['guard'] and after['scene'] == before['scene'] and after['artifact'] == before['artifact']
            result['checks'].append('Public restore cancellation retained the confirmed scene and view')
            nodes = [scene['frame'],scene['wire'],scene['focus']]
            click(page,'#spatial-leave')
            assert not state()['active']
            same_context(baseline,context(phase))
            absent = h.native('local r={};for _,n in ipairs('+lua(nodes)+') do r[n]=openspace.hasSceneGraphNode(n) end;return r')
            assert not any(absent.values())
            result['checks'].append('Leave removed candidate nodes and restored live camera/flags')
            assert not result['page_errors']
        result['completed'] = True
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        try:
            if 'session' in result:
                if state()['active'] or state()['recovery_required']:
                    command('leave')
                h.native('openspace.toggleShutdown();return {closing=true}')
                if h._socket:
                    h._socket.close()
                result['processes']['launcher_wrapper_exit'] = launch.wait(timeout=60)
                assert result['processes']['launcher_wrapper_exit'] == 0
                for role, handle in handles.items():
                    code = ctypes.c_ulong()
                    assert kernel.GetExitCodeProcess(handle,ctypes.byref(code))
                    result['processes'][role+'_exit'] = code.value
                assert result['processes']['engine_exit'] == result['processes']['server_exit'] == result['processes']['launcher_exit'] == 0
            elif launch is not None and launch.poll() is None:
                launch.terminate()
                result['processes']['launcher_exit'] = launch.wait(timeout=10)
            for path in store.folder.rglob('*.json'):
                target = folder / 'stored-snapshots' / path.relative_to(store.folder)
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(path,target)
            assert sha(ROOT / 'user/sessions/latest.json') == result['owner_sha256']
            assert all(sha(ROOT / name) == seal for name, seal in sources.items())
            result['accepted'] = result['completed'] and not result.get('failure')
        except Exception:
            result['cleanup_failure'] = traceback.format_exc()
        for handle in handles.values():
            kernel.CloseHandle(handle)
        for log in logs:
            log.close()
        persist()
    print(json.dumps(dict(accepted=result['accepted'],checks=len(result['checks']),captures=len(result['captures']),failure=result.get('failure'),cleanup_failure=result.get('cleanup_failure'))),flush=True)
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
