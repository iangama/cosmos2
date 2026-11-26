"""First real K3 API/CEF journeys with scientific and native ownership checks."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import argparse
import copy
import hashlib
import itertools
import json
import math
import subprocess
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
import zipfile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is6-layers-product0.19.1/app'
sys.path.insert(0, str(APP))
import is6_layer_contract as contract
import body_field_scene
from cef_page import Page
h = SourceFileLoader('layers_native_helpers', str(ROOT / 'scripts/benchmark-body-points-native.py')).load_module()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    folder = ROOT / ('output/is6-layers-native-' + args.label)
    out = ROOT / ('evidence/is6-layers-native-' + args.label + '.json')
    if out.exists() or folder.exists():
        raise FileExistsError('Preserve native evidence')
    manifest_path = APP.parent / 'build-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    assert manifest['candidate'] == '0.19.1' and manifest['promoted'] is False
    hashes = dict(manifest['source_sha256'])
    for name, seal in manifest['files_sha256'].items():
        hashes[(APP / name).relative_to(ROOT).as_posix()] = seal
    for path in [Path(__file__), manifest_path, ROOT / 'scripts/cef_page.py', ROOT / 'scripts/benchmark-body-points-native.py',
                 ROOT / 'scripts/verify-native-solar-integration.py', ROOT / 'scripts/capture-window.ps1', ROOT / 'scripts/run-is6-layers-verification-background-v2.py']:
        hashes[path.relative_to(ROOT).as_posix()] = sha(path)
    assert all(sha(ROOT / p) == seal for p, seal in hashes.items())
    session = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
    assert session['is6LayersCandidate'] and Path(session['serverScript']).resolve() == APP / 'server.py'
    folder.mkdir()
    with zipfile.ZipFile(folder / 'executed-sources.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for p in hashes:
            z.write(ROOT / p, p)
    r = dict(accepted=False, completed=False, source_sha256=hashes, session=session,
             owner_sha256=sha(ROOT / 'user/sessions/latest.json'), cases=[], refusals=[], captures=[], cancellation_attempts=[], page_errors=[],
             scope='K3 first coordinated-layer UI/API only; frozen source, independent models. No composite persistence, migration, final UI performance or whole IS6/v1 acceptance.')
    def persist():
        out.write_text(json.dumps(r, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    def state():
        return h.get('/api/layers/state')
    def command(name, **fields):
        return h.post('/api/layers/command', dict(command=name, guard=state()['guard'], **fields))
    def click(page, selector):
        page.evaluate('(()=>{const e=document.querySelector(' + json.dumps(selector) + ');for(let p=e.parentElement;p;p=p.parentElement)if(p.tagName==="DETAILS")p.open=true;})()')
        page.wait_for_function('!document.querySelector(' + json.dumps(selector) + ').disabled', timeout=30000)
        page.locator(selector).click()
        page.wait_for_function('!layerInstrument.pending&&!layerInstrument.snapshot?.busy', timeout=70000)
    def same_context(a, b):
        assert a['flags'] == b['flags']
        assert a['camera'].keys() == b['camera'].keys()
        for key, value in a['camera'].items():
            if key == 'Up':
                assert all(abs(x-y) <= 1e-12 for x, y in zip(value, b['camera'][key], strict=True))
            else:
                assert value == b['camera'][key], key
    def context(phase):
        names = ['LabGrid', 'LabBarycenter', 'LabProbe']
        for b in phase['bodies']:
            names.extend(b[k] for k in ['scene_node', 'label_node', 'shape_node', 'spin_node'] if b.get(k))
        return h.native('local f={};for _,n in ipairs(' + lua(names) + ') do if openspace.hasSceneGraphNode(n) then local ok,v=pcall(openspace.propertyValue,"Scene."..n..".Renderable.Enabled");if ok and type(v)=="boolean" then f[n]=v end end end;return {camera=openspace.navigation.getNavigationState("Root"),flags=f}')
    def capture(page, target, scale):
        page.locator('#ui-scale').select_option(scale)
        if target.endswith('-magnetic'):
            page.evaluate('document.getElementById("layers-magnetic-reading").scrollIntoView({block:"center"})')
        else:
            page.evaluate('document.getElementById("layers-panel").scrollTop=0')
        time.sleep(.2)
        name = 'cosmos2-is6-layers-' + args.label + '-' + target + '-' + str(int(float(scale)*100)) + '.png'
        subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT / 'scripts/capture-window.ps1'), '-Name', name], check=True, capture_output=True)
        path, rgb = ROOT / 'evidence' / name, folder / name
        im = Image.open(path)
        assert im.size == (1920, 1080)
        im.convert('RGB').save(rgb)
        layout = page.evaluate('(()=>{const p=document.getElementById("layers-panel"),r=p.getBoundingClientRect(),e=document.getElementById("layers-leave"),b=e.getBoundingClientRect();return {scroll:p.scrollWidth,client:p.clientWidth,leave:{top:b.top,bottom:b.bottom},panel:{top:r.top,bottom:r.bottom},error:layerInstrument.error};})()')
        assert layout['scroll'] == layout['client'] and not layout['error'], layout
        assert layout['panel']['top'] <= layout['leave']['top'] < layout['leave']['bottom'] <= layout['panel']['bottom'], layout
        if target.endswith('-magnetic'):
            reading = page.evaluate('(()=>{const r=document.getElementById("layers-magnetic-reading").getBoundingClientRect();return {top:r.top,bottom:r.bottom};})()')
            assert layout['panel']['top'] <= reading['top'] < reading['bottom'] <= layout['leave']['top'], (layout,reading)
            layout['magnetic_reading'] = reading
        r['captures'].append(dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), RGB=rgb.relative_to(ROOT).as_posix(), RGB_sha256=sha(rgb), layout=layout))
        persist()
    persist()
    try:
        from is6_product_scene import lua
        with Page() as page:
            page.on('pageerror', lambda e: r['page_errors'].append(e))
            page.goto(h.test.BASE + '/')
            page.wait_for_function('appState&&atlasState&&layerInstrument.snapshot&&!pending')
            assert h.get('/api/state')['mode'] == 'atlas'
            click(page, '#open-layers')
            click(page, '#layers-copy')
            page.wait_for_function('appState.physics?.bodies.length===4&&!pending', timeout=70000)
            phase = h.get('/api/state')['physics']
            held = h.test.phase(copy.deepcopy(phase))
            r['source_phase'] = phase
            for target in ['399', '599']:
                before = context(phase)
                body = next(b for b in phase['bodies'] if b['reference_id'] == 'sol:naif:' + target)
                page.locator('#layers-body').select_option(body['id'])
                click(page, '#layers-create')
                assert state()['active'] and not state()['error']
                assert 'Déficit do relógio:' in page.locator('#layers-spatial-reading').inner_text()
                assert state()['artifact']['spatial_sample']['metric']['static_clock_deficit'] > 0
                s = state()
                full = command('get_artifact')['result']
                scientific = full['scientific']
                assert full['sha256'] == contract.digest(scientific) == s['artifact']['sha256']
                assert contract.magnetic(phase, scientific['magnetic']) == scientific['magnetic']
                restored = contract.artifact.Run.restore(scientific['spatial'])
                assert contract.compose(phase, restored.payload, scientific['magnetic'], dict(spatial=True, magnetic=True)) == scientific['admission']
                scene = s['scene']
                item = dict(body=target, artifact=scientific, combinations=[])
                for spatial, magnetic in itertools.product([False, True], repeat=2):
                    for selector, desired in [('#layers-spatial-visible', spatial), ('#layers-magnetic-visible', magnetic)]:
                        if page.evaluate('document.querySelector(' + json.dumps(selector) + ').checked') != desired:
                            click(page, selector)
                    current = state()
                    visible = dict(spatial=spatial, magnetic=magnetic)
                    assert current['artifact']['visible'] == visible and current['artifact']['sha256'] == full['sha256']
                    actual = h.native('local m={};for _,n in ipairs(' + lua(scene['magnetic_nodes']) + ') do m[n]=openspace.propertyValue("Scene."..n..".Renderable.DrawElements") end;return {spatial=openspace.propertyValue("Scene.' + scene['spatial_wire'] + '.Renderable.DrawElements"),magnetic=m}')
                    assert actual['spatial'] is spatial and all(v is magnetic for v in actual['magnetic'].values())
                    assert h.test.phase(h.get('/api/state')['physics']) == held
                    item['combinations'].append(dict(visible=visible, readback=actual))
                geometry = body_field_scene.build(scientific['magnetic'])
                point = h.native('return {local_point=openspace.propertyValue("Scene.' + scene['magnetic_frame'] + '_probe.Translation.Position"),center=openspace.worldPosition(' + lua(scene['magnetic_frame']) + '),point=openspace.worldPosition(' + lua(scene['magnetic_frame'] + '_probe') + ')}')
                expected = body_field_scene.product(geometry['body_to_render'], geometry['point_model_m'])
                assert max(abs(x-y) for x,y in zip(point['local_point'], expected, strict=True)) <= .001
                assert all(abs((p-c)-e) <= math.ulp(p)+math.ulp(c)+.001 for p,c,e in zip(point['point'], point['center'], expected, strict=True))
                item['point_confirmation'] = point
                for path, request in [('/api/command', dict(command='resume')), ('/api/command', dict(command='atlas')),
                    ('/api/spatial/command', dict(command='leave')), ('/api/particles/command', dict(command='leave')),
                    ('/api/solar-zone/command', dict(command='leave')), ('/api/solar/experiment', dict(utc=scientific['magnetic']['epoch']['utc'])),
                    ('/api/navigation/visit', dict(target='sol:naif:399'))]:
                    guard = state()['guard']
                    response = h.post(path, request, expected=400)
                    assert response['ok'] is False and state()['guard'] == guard and h.test.phase(h.get('/api/state')['physics']) == held
                    r['refusals'].append(dict(body=target, path=path, error=response['error']))
                for scale in ['1', '1.5']:
                    capture(page, target, scale)
                capture(page, target+'-magnetic', '1.5')
                page.locator('#ui-scale').select_option('1')
                click(page, '#layers-leave')
                assert not state()['active'] and not state()['recovery_required']
                after = context(phase)
                same_context(before, after)
                nodes = [scene['spatial_frame'], scene['spatial_wire'], scene['spatial_frame'].replace('SpatialFrame_', 'SpatialFocus_'), scene['magnetic_frame'],
                         *scene['magnetic_nodes'], *[scene['magnetic_frame']+suffix for suffix in ['_basis', '_probe', '_display_probe']]]
                absent = h.native('local r={};for _,n in ipairs(' + lua(nodes) + ') do r[n]=openspace.hasSceneGraphNode(n) end;return r')
                assert not any(absent.values())
                item['cleanup'] = dict(before=before, after=after, nodes=absent)
                r['cases'].append(item)
                persist()
            # Race a genuine HTTP create with cancellation while hidden preparation
            # is published. No artificial physics or successful native stub is used.
            body = next(b for b in phase['bodies'] if b['reference_id'] == 'sol:naif:399')
            cancelled = False
            for attempt in range(5):
                before = context(phase)
                payload = dict(command='create', guard=state()['guard'], source_guard=contract.artifact.body.guard(phase), body_id=body['id'],
                    configuration={**contract.artifact.DEFAULT_CONFIGURATION, 'outer_radius_boundary_units': 3.},
                    magnetic=dict(model='IGRF14', latitude_deg=-23.55, longitude_deg=-46.63, altitude_m=1000.))
                replies = []
                def create():
                    request = urllib.request.Request(h.test.BASE+'/api/layers/command', data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'})
                    try:
                        response = urllib.request.urlopen(request, timeout=70)
                    except urllib.error.HTTPError as error:
                        response = error
                    replies.append(dict(status=response.status, body=json.load(response)))
                worker = threading.Thread(target=create)
                worker.start()
                deadline = time.monotonic()+3
                cancellation = None
                cancel_refusal = None
                while worker.is_alive() and time.monotonic() < deadline:
                    tx = state()['transaction']
                    if tx and tx['cancellable']:
                        try:
                            cancellation = h.post('/api/layers/cancel', dict(transaction_id=tx['id']))
                        except AssertionError as error:
                            # The transaction may have entered commit after this read;
                            # preserve the failed attempt and retry a fresh real create.
                            cancellation = None
                            cancel_refusal = str(error)
                        break
                    time.sleep(.005)
                worker.join(timeout=70)
                assert not worker.is_alive() and len(replies) == 1
                r['cancellation_attempts'].append(dict(attempt=attempt, create_reply=replies[0], cancel_reply=cancellation, cancel_refusal=cancel_refusal))
                if cancellation:
                    assert cancellation['ok'] and replies[0]['status'] == 400 and not state()['active'] and not state()['recovery_required']
                    same_context(before, context(phase))
                    cancelled = True
                    break
                if state()['active']:
                    command('leave')
                same_context(before, context(phase))
            assert cancelled, 'No cancellable real preparation was observed; do not claim cancellation acceptance'
            assert h.test.phase(h.get('/api/state')['physics']) == held and not r['page_errors']
            assert sha(ROOT/'user/sessions/latest.json') == r['owner_sha256']
            assert all(sha(ROOT/p) == seal for p,seal in hashes.items())
            r.update(accepted=True, completed=True)
    except Exception:
        r['failure'] = traceback.format_exc()
    finally:
        try:
            if state()['active'] or state()['recovery_required']:
                command('leave')
            h.post('/api/command', dict(command='atlas'))
            h.native('openspace.toggleShutdown();return {closing=true}')
        except Exception:
            r['cleanup_failure'] = traceback.format_exc()
            r['accepted'] = False
        persist()
        if h._socket:
            h._socket.close()
    print(json.dumps(dict(accepted=r['accepted'], bodies=len(r['cases']), captures=len(r['captures']), refusals=len(r['refusals']), failure=r.get('failure', '').splitlines()[-1:])), flush=True)
    return 0 if r['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
