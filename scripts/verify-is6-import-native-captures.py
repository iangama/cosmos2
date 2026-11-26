"""Read-only K5 native framebuffer inspection from the accepted S/T records."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import argparse
import copy
import hashlib
import itertools
import json
import math
import shutil
import sys
import time
import traceback
import urllib.request
from PIL import Image
from cef_page_v2 import Page

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is6-layers-product0.21.1/app'
sys.path.insert(0, str(APP))
from is6_product_scene import lua
import body_field_scene
import is6_layer_contract as contract

h = SourceFileLoader('capture_helpers', str(ROOT / 'scripts/benchmark-body-points-native.py')).load_module()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    out = ROOT / ('evidence/is6-import-native-captures-' + args.label + '.json')
    if out.exists():
        raise FileExistsError('Preserve capture evidence')
    manifest_path = APP.parent / 'build-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    assert manifest['candidate'] == '0.21.1' and manifest['promoted'] is False
    hashes = dict(manifest['source_sha256'])
    hashes.update({(APP / p).relative_to(ROOT).as_posix(): v for p, v in manifest['files_sha256'].items()})
    files = [Path(__file__), manifest_path, ROOT / 'scripts/run-is6-import-native-captures.py',
             ROOT / 'scripts/cef_page_v2.py', ROOT / 'scripts/benchmark-body-points-native.py',
             ROOT / 'IS-6-COEXISTENCIA-MIGRACAO-NATIVA-K5-REVISAO-C.md']
    receipts = {}
    for label in ['20261104s', '20261104t']:
        path = ROOT / ('evidence/is6-layers-import-native-' + label + '.json')
        process = ROOT / ('evidence/is6-layers-import-native-process-' + label + '.json')
        receipts[label] = json.loads(path.read_text())
        assert receipts[label]['accepted'] and json.loads(process.read_text())['accepted']
        files.extend([path, process])
    hashes.update({p.relative_to(ROOT).as_posix(): sha(p) for p in files})
    assert all(sha(ROOT / p) == v for p, v in hashes.items())
    seed = receipts['20261104s']
    assert seed['sciences'] == receipts['20261104t']['sciences']
    store = APP.parent / 'layer-checkpoints'
    inventory = lambda: {p.relative_to(store).as_posix(): sha(p) for p in store.rglob('*.json')}
    before = inventory()
    launch = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
    assert Path(launch['serverScript']).resolve() == APP / 'server.py'
    r = dict(accepted=False, completed=False, candidate='0.21.1', session=launch,
             source_sha256=hashes, owner_sha256=sha(ROOT / 'user/sessions/latest.json'),
             captures=[], checks=[], replacement_mapping=[], persisted_before=before,
             scope='Native framebuffer and unchanged-state verification only; manual pixel review, own profile and promotion remain separate.')
    persist = lambda: out.write_text(json.dumps(r, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    state = lambda: h.get('/api/layers/state')
    def command(operation, **fields):
        return h.post('/api/layers/command', dict(command=operation, guard=state()['guard'], **fields))
    def click(page, selector):
        page.evaluate('(()=>{let e=document.querySelector(' + json.dumps(selector) + ');for(let p=e.parentElement;p;p=p.parentElement)if(p.tagName==="DETAILS")p.open=true})()')
        page.wait_for_function('!layerInstrument.pending&&!layerInstrument.readingFile&&!layerInstrument.snapshot.busy&&!document.querySelector(' + json.dumps(selector) + ').disabled', timeout=80000)
        page.locator(selector).click()
        page.wait_for_function('!layerInstrument.pending&&!layerInstrument.readingFile&&!layerInstrument.snapshot.busy', timeout=80000)
        assert not page.evaluate('layerInstrument.error') and not state()['error']
    def visibility(page, flags):
        for key, value in flags.items():
            selector = '#layers-' + key + '-visible'
            if page.evaluate('document.querySelector(' + json.dumps(selector) + ').checked') is not value:
                click(page, selector)
        assert state()['artifact']['visible'] == flags
    def context(phase):
        names = ['LabGrid', 'LabBarycenter', 'LabProbe']
        for body in phase['bodies']:
            names.extend(body[k] for k in ['scene_node', 'label_node', 'shape_node', 'spin_node'] if body.get(k))
        return h.native('local f={};for _,n in ipairs(' + lua(names) + ') do if openspace.hasSceneGraphNode(n) then local ok,v=pcall(openspace.propertyValue,"Scene."..n..".Renderable.Enabled");if ok and type(v)=="boolean" then f[n]=v end end end;return {camera=openspace.navigation.getNavigationState("Root"),flags=f}')
    def same_context(a, b):
        assert a['flags'] == b['flags'] and a['camera'].keys() == b['camera'].keys()
        for key, value in a['camera'].items():
            if key == 'Up':
                assert all(abs(x-y) <= 1e-12 for x, y in zip(value, b['camera'][key], strict=True))
            else:
                assert value == b['camera'][key], key
    def confirm(phase, target):
        s = state()
        artifact = command('get_artifact')['result']
        scientific = artifact['scientific']
        assert scientific == seed['sciences'][target]
        assert artifact['sha256'] == contract.digest(scientific) == s['artifact']['sha256']
        assert s['artifact']['origin'] == seed['imports'][target]['origin']
        assert s['artifact']['archived'] and s['artifact']['live_source_guard']['system_id'] == phase['system_id']
        scene = s['scene']
        native = h.native('local f={};for _,n in ipairs(' + lua(scene['magnetic_nodes']) + ') do f[n]={draw=openspace.propertyValue("Scene."..n..".Renderable.DrawElements"),file=openspace.propertyValue("Scene."..n..".Renderable.File")} end;return {spatial=openspace.propertyValue("Scene.' + scene['spatial_wire'] + '.Renderable.DrawElements"),magnetic=f,point=openspace.worldPosition(' + lua(scene['magnetic_frame'] + '_probe') + '),center=openspace.worldPosition(' + lua(scene['magnetic_frame']) + '),local_point=openspace.propertyValue("Scene.' + scene['magnetic_frame'] + '_probe.Translation.Position")}')
        flags = s['artifact']['visible']
        assert native['spatial'] is flags['spatial']
        assert all(v['draw'] is flags['magnetic'] for v in native['magnetic'].values())
        assert any(Path(v['file']).stem == 'reference_grid' for v in native['magnetic'].values())
        geometry = body_field_scene.build(scientific['magnetic'])
        expected = body_field_scene.product(geometry['body_to_render'], geometry['point_model_m'])
        assert max(abs(x-y) for x, y in zip(native['local_point'], expected, strict=True)) <= .001
        assert all(abs((p-c)-e) <= math.ulp(p)+math.ulp(c)+.001 for p, c, e in zip(native['point'], native['center'], expected, strict=True))
        assert h.test.phase(h.get('/api/state')['physics']) == h.test.phase(phase)
        check = dict(target=target, guard=s['guard'], scientific_sha256=artifact['sha256'], visible=flags, native=native)
        r['checks'].append(check)
        return check
    def capture(page, target, scale, section, phase):
        page.locator('#ui-scale').select_option(scale)
        if section == 'import':
            page.evaluate('document.getElementById("layers-import").open=true;document.getElementById("layers-import-fields").scrollIntoView({block:"start"})')
        elif section == 'storage':
            page.evaluate('document.getElementById("layers-storage").open=true;document.getElementById("layers-storage-fields").scrollIntoView({block:"start"})')
        else:
            page.evaluate('document.getElementById("layers-import").open=false;document.getElementById("layers-storage").open=false;document.getElementById("layers-panel").scrollTop=0')
        time.sleep(.75)
        page.evaluate('window.c2TextMutations=0;window.c2TextObserver=new MutationObserver(rows=>{window.c2TextMutations+=rows.length});for(const id of ["layers-panel","layers-caption","notice"])window.c2TextObserver.observe(document.getElementById(id),{childList:true,characterData:true,subtree:true})')
        time.sleep(1.2)
        mutations = page.evaluate('window.c2TextObserver.disconnect();window.c2TextMutations')
        assert mutations == 0
        check = confirm(phase, target)
        snapshot = state()
        ui = page.evaluate('(()=>{const e=document.getElementById("layers-panel"),p=e.getBoundingClientRect(),b=document.getElementById("layers-leave").getBoundingClientRect();return {caption:document.getElementById("layers-caption-visible").textContent,notice:document.getElementById("notice").textContent,preview:document.getElementById("layers-import-reading").textContent,scroll:e.scrollWidth,client:e.clientWidth,panel:{top:p.top,bottom:p.bottom},leave:{top:b.top,bottom:b.bottom},error:layerInstrument.error}})()')
        assert ui['scroll'] == ui['client'] and not ui['error']
        assert ui['panel']['top'] <= ui['leave']['top'] < ui['leave']['bottom'] <= ui['panel']['bottom']
        flags = snapshot['artifact']['visible']
        bits = str(int(flags['spatial'])) + str(int(flags['magnetic']))
        path = ROOT / ('evidence/cosmos2-is6-import-' + args.label + '-' + target + '-' + section + '-' + bits + '-' + str(int(float(scale)*100)) + '.png')
        if path.exists():
            raise FileExistsError(path)
        screenshots = ROOT / 'user/screenshots'
        existing = set(screenshots.rglob('*.png'))
        h.native('openspace.takeScreenshot();return {requested=true}')
        deadline = time.monotonic() + 20
        while True:
            fresh = set(screenshots.rglob('*.png')) - existing
            if fresh:
                assert len(fresh) == 1
                source = next(iter(fresh))
                try:
                    with Image.open(source) as im:
                        assert im.size == (1920, 1080)
                        im.verify()
                    break
                except (OSError, SyntaxError):
                    pass
            if time.monotonic() > deadline:
                raise TimeoutError('Native PNG did not finish')
            time.sleep(.1)
        shutil.copy2(source, path)
        assert sha(source) == sha(path)
        assert state()['guard'] == snapshot['guard'] and state()['artifact'] == snapshot['artifact']
        assert h.test.phase(h.get('/api/state')['physics']) == h.test.phase(phase)
        r['captures'].append(dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path),
            native_original=source.relative_to(ROOT).as_posix(), native_original_sha256=sha(source),
            method='openspace.takeScreenshot: raw native framebuffer PNG, unedited', target=target,
            section=section, scale=scale, check=check, text_mutations_during_idle=mutations,
            ui=ui, artifact=copy.deepcopy(snapshot['artifact'])))
        persist()
    persist()
    try:
        deadline = time.monotonic() + 240
        while True:
            try:
                urllib.request.urlopen(h.test.BASE + '/health', timeout=3).close()
                break
            except OSError:
                if time.monotonic() > deadline:
                    raise TimeoutError('API readiness')
                time.sleep(1)
        with Page() as page:
            page.goto(h.test.BASE + '/')
            page.wait_for_function('appState&&atlasState&&layerInstrument.snapshot&&!pending')
            click(page, '#open-layers')
            click(page, '#layers-copy')
            page.wait_for_function('appState.physics?.bodies.length===4&&!pending', timeout=70000)
            phase = h.get('/api/state')['physics']
            r['source_phase'] = phase
            assert phase['system_id'] != seed['source_phase']['system_id']
            baseline = context(phase)
            r['base_context'] = baseline
            for target in ['399', '599']:
                if not state()['active']:
                    click(page, '#layers-load-saved')
                page.locator('#layers-branches').select_option(seed['imports'][target]['branch_id'])
                click(page, '#layers-branch-load')
                for spatial, magnetic in itertools.product([False, True], repeat=2):
                    visibility(page, dict(spatial=spatial, magnetic=magnetic))
                    capture(page, target, '1', 'overview', phase)
                capture(page, target, '1.5', 'overview', phase)
                capture(page, target, '1.5', 'storage', phase)
                original = ROOT / seed['imports'][target]['source']
                visibility(page, seed['imports'][target]['origin']['visible'])
                document = page.call('DOM.getDocument')['root']['nodeId']
                node = page.call('DOM.querySelector', dict(nodeId=document, selector='#layers-import-file'))['nodeId']
                page.call('DOM.setFileInputFiles', dict(nodeId=node, files=[str(original)]))
                page.evaluate('document.getElementById("layers-import-file").dispatchEvent(new Event("change",{bubbles:true}))')
                guard = state()['guard']
                click(page, '#layers-import-preview')
                assert state()['import_preview']['source_sha256'] == sha(original)
                for scale in ['1', '1.5']:
                    capture(page, target, scale, 'import', phase)
                click(page, '#layers-import-cancel')
                assert state()['guard'] == guard and inventory() == before
                scene = state()['scene']
                click(page, '#layers-leave')
                same_context(baseline, context(phase))
                nodes = [scene['spatial_frame'], scene['spatial_wire'], scene['magnetic_frame'], *scene['magnetic_nodes']]
                absent = h.native('local r={};for _,n in ipairs(' + lua(nodes) + ') do r[n]=openspace.hasSceneGraphNode(n) end;return r')
                assert not any(absent.values())
                r.setdefault('cleanups', []).append(dict(target=target, nodes=absent, restored_context=context(phase)))
            for label, receipt in receipts.items():
                for old in receipt['captures']:
                    name = Path(old['path']).stem
                    target = old['artifact']['source']['body_reference_id'].split(':')[-1]
                    section = next(v for v in ['overview', 'storage', 'import'] if '-' + v + '-' in name)
                    scale = str(int(name.rsplit('-', 1)[-1]) / 100).rstrip('0').rstrip('.')
                    flags = old['artifact']['visible']
                    matching = [v for v in r['captures'] if v['target'] == target and v['section'] == section and float(v['scale']) == float(scale) and v['artifact']['visible'] == flags]
                    assert len(matching) == 1, (name, flags)
                    new = matching[0]
                    assert new['artifact']['sha256'] == old['artifact']['sha256']
                    assert new['artifact']['origin'] == old['artifact']['origin']
                    assert sha(ROOT / old['path']) == old['sha256']
                    r['replacement_mapping'].append(dict(original=old['path'], original_sha256=old['sha256'], replacement=new['path'], replacement_sha256=new['sha256'], reason='Native framebuffer reinspection of the same archived science, origin, flags, section and UI scale; original PrintWindow pixels remain preserved.'))
            assert len(r['captures']) == 16 and len(r['replacement_mapping']) == 15
            assert inventory() == before
            assert sha(ROOT / 'user/sessions/latest.json') == r['owner_sha256']
            assert all(sha(ROOT / p) == v for p, v in hashes.items())
            r.update(accepted=True, completed=True, persisted_after=inventory())
    except Exception:
        r['failure'] = traceback.format_exc()
    finally:
        try:
            deadline = time.monotonic() + 90
            while state()['busy']:
                if time.monotonic() > deadline:
                    raise TimeoutError('Busy during cleanup')
                time.sleep(.1)
            preview = state().get('import_preview')
            if preview:
                command('import_cancel', preview_id=preview['id'])
            if state()['active'] or state()['recovery_required']:
                command('leave')
            h.post('/api/command', dict(command='atlas'))
            h.native('openspace.toggleShutdown();return {closing=true}')
            assert inventory() == before and sha(ROOT / 'user/sessions/latest.json') == r['owner_sha256']
        except Exception:
            r['cleanup_failure'] = traceback.format_exc()
            r['accepted'] = False
        persist()
        if h._socket:
            h._socket.close()
    print(json.dumps(dict(accepted=r['accepted'], completed=r['completed'], captures=len(r['captures']), mappings=len(r['replacement_mapping']), failure=r.get('failure', '').splitlines()[-2:])))
    return 0 if r['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
