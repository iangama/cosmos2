"""Verify the eight-planet candidate attached to the owner's visible native app."""
import argparse
import copy
import datetime as dt
import hashlib
from importlib.machinery import SourceFileLoader
import json
import math
from pathlib import Path
import shutil
import time
import traceback
import zipfile

import numpy as np
from PIL import Image
from cef_page_v2 import Page

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is6-principal-moons-navigation-product0.25.1/app'
h = SourceFileLoader('navigation_native_helpers', str(ROOT / 'scripts/benchmark-body-points-native.py')).load_module()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
EPOCHS = ['1995-01-01T00:00:00Z', '2000-01-01T12:00:00Z', '2026-10-11T12:00:00Z',
          '2030-06-15T18:30:00Z', '2049-12-30T23:59:59Z']
NEW = ['Io','Europa','Ganymede','Callisto','Enceladus','Titan']
PHYSICAL = ['Mercury','Venus','Earth','Moon','Mars','Jupiter','Saturn','Uranus','Neptune',*NEW]


def lua(value):
    if isinstance(value, str): return json.dumps(value)
    if isinstance(value, bool): return str(value).lower()
    if isinstance(value, (float, int)): return format(value, '.17g')
    if isinstance(value, list): return '{' + ','.join(map(lua, value)) + '}'
    if isinstance(value, dict): return '{' + ','.join(k + '=' + lua(v) for k, v in value.items()) + '}'
    raise TypeError(value)


def array(value):
    return np.array([value[str(i)] for i in range(1, len(value) + 1)] if isinstance(value, dict) else value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    label = parser.parse_args().label
    if not label or len(label) > 20 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
        parser.error('Invalid label')
    folder = ROOT / 'output' / ('is6-principal-moons-navigation-native-' + label)
    receipt = ROOT / 'evidence' / ('is6-principal-moons-navigation-native-' + label + '.json')
    if folder.exists() or receipt.exists(): raise FileExistsError('Preserve executed native checks')
    folder.mkdir()
    scene = json.loads((APP / 'planet_scene.json').read_text(encoding='utf8'))
    protected = [ROOT / 'user/sessions/latest.json', ROOT / 'Iniciar-Cosmos2.cmd']
    protected_sha = {p.relative_to(ROOT).as_posix(): sha(p) for p in protected}
    files = [p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [Path(__file__), ROOT / 'scripts/cef_page_v2.py',
              ROOT / 'scripts/benchmark-body-points-native.py', ROOT / 'IS-6-LUAS-NAVEGACAO-CONTRATO.md']
    files += [p for p in (ROOT / 'output/is6-principal-moons-navigation-staging-v2').iterdir() if p.is_file()]
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in files}
    archive = folder / 'executed-sources.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in files: z.write(p, p.relative_to(ROOT).as_posix())
    result = dict(completed=False, functional_accepted=False, page_errors=[], epochs=[], journey=[],
                  geometry=[], captures=[], controls={}, source_sha256=hashes,
                  source_archive=archive.relative_to(ROOT).as_posix(), source_archive_sha256=sha(archive),
                  started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                  session=json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig')),
                  limits_before_execution=dict(position_m='max(0.001,8ULP(max absolute component))',
                                               orientation_element=1e-12, inferred_semiaxis_m=.02),
                  scope='Attached native functional checks. Raw captures require visual review. Own profile and lifecycle exits remain pending while owner window stays open.')
    original_id = None
    previous_scale = '1'

    def persist():
        receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')

    def nav(action, **payload):
        return h.post('/api/navigation/' + action, payload)['navigation']

    def click(page, selector):
        page.locator(selector).click()
        page.wait_for_function('!navigationBusy&&!pending&&!atlasPending', timeout=70000)

    def capture(page, target, scale):
        page.locator('#ui-scale').select_option(scale)
        page.evaluate('document.getElementById("visual-controls").open=true')
        if scale == '1.5' and not page.evaluate('document.body.classList.contains("details-open")'):
            page.locator('#panel-toggle').click()
        page.evaluate('document.getElementById("atlas-details").scrollTop=0;document.getElementById("atlas-panel").scrollTop=0')
        time.sleep(1)
        ui = page.evaluate('({title:$("object-name").textContent,notice:$("notice").textContent,scale:$("ui-scale").value,width:innerWidth,height:innerHeight,scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,selected:selectedTarget,anchor:navigationState.navigation.Anchor,limitation:$("content-limit").textContent})')
        assert ui['selected'] == ui['anchor'] == target, ui
        assert ui['scroll'] <= ui['client'], ui
        existing = set((ROOT / 'user/screenshots').rglob('*.png'))
        h.native('openspace.takeScreenshot();return {requested=true}')
        deadline = time.monotonic() + 20
        while True:
            fresh = set((ROOT / 'user/screenshots').rglob('*.png')) - existing
            if fresh:
                assert len(fresh) == 1
                source = next(iter(fresh))
                try:
                    with Image.open(source) as im:
                        assert im.size == (1920, 1080), im.size
                        im.load()
                    break
                except (OSError, SyntaxError): pass
            if time.monotonic() > deadline: raise TimeoutError('Native framebuffer PNG not complete')
            time.sleep(.1)
        path = folder / (target.lower() + '-' + str(int(float(scale) * 100)) + '.png')
        shutil.copy2(source, path)
        assert sha(source) == sha(path)
        result['captures'].append(dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path),
                                      native_original=source.relative_to(ROOT).as_posix(), target=target,
                                      scale=scale, method='openspace.takeScreenshot, unedited framebuffer', ui=ui))
        persist()

    persist()
    try:
        assert result['session']['is6PrincipalMoonsCandidate']
        assert Path(result['session']['serverScript']).resolve() == APP / 'server.py'
        assert h.get('/api/state')['mode'] == 'atlas'
        before = h.get('/api/navigation/favorites')['views']
        saved = nav('save', name='Verificação temporária · vista inicial')['views']
        original_id = next(row['id'] for row in saved if row['id'] not in {r['id'] for r in before})
        result['original_navigation'] = h.get('/api/navigation/state')
        result['original_favorites'] = copy.deepcopy(before)
        for utc in EPOCHS:
            reference = h.post('/api/atlas/epoch', {'utc': utc})['atlas']
            native = h.get('/api/navigation/state')
            assert native['et'] == reference['epoch']['et_tdb_s'] and native['paused']
            matrix = np.array(reference['j2000_to_render_frame'])
            row = dict(utc=utc, et=native['et'], bodies=[])
            for body in reference['bodies']:
                node = body['scene_node']
                expected = np.array(body['position_render_m'])
                error = float(np.max(np.abs(array(native['positions'][node]) - expected)))
                budget = max(.001, 8 * math.ulp(float(np.max(np.abs(expected)))))
                check = dict(node=node, position_error_m=error, position_budget_m=budget)
                assert error <= budget, check
                if node in PHYSICAL:
                    actual = array(native['rotations'][node]).reshape(3, 3, order='F')
                    rotation = matrix @ np.array(body['body_to_j2000'])
                    rotation_error = float(np.max(np.abs(actual - rotation)))
                    check['orientation_error'] = rotation_error
                    assert rotation_error <= 1e-12, check
                row['bodies'].append(check)
            result['epochs'].append(row); persist()
            print(json.dumps(dict(phase='epoch', utc=utc, bodies=len(row['bodies']))), flush=True)
        h.post('/api/atlas/epoch', {'utc': EPOCHS[2]})
        confirmed = h.get('/api/atlas/state')
        for bad in ['1994-12-31T23:59:59Z', '2049-12-31T00:00:00Z', '2026-02-30T12:00:00Z', True]:
            assert not h.post('/api/atlas/epoch', {'utc': bad}, expected=400)['ok']
            after = h.get('/api/atlas/state')
            assert after['epoch'] == confirmed['epoch'] and after['bodies'] == confirmed['bodies']
        result['controls']['four_transactional_epoch_refusals'] = True
        with Page() as page:
            page.on('pageerror', result['page_errors'].append)
            page.goto('http://127.0.0.1:4700/')
            page.wait_for_function('atlasState&&navigationState&&appState?.mode==="atlas"&&!pending')
            previous_scale = page.locator('#ui-scale').page.evaluate('$("ui-scale").value')
            page.locator('#ui-scale').select_option('1')
            page.locator('#smooth-flight').set_checked(False)
            for target in PHYSICAL:
                click(page, '#destinations [data-target="' + target + '"]')
                click(page, '#visit-target')
                page.wait_for_function('navigationState.navigation.Anchor===' + json.dumps(target))
                state = h.get('/api/navigation/state')
                assert state['navigation']['Anchor'] == target and not state['flying']
                result['journey'].append(dict(target=target, title=page.locator('#object-name').inner_text(),
                                              camera=state['navigation']))
                if target in NEW:
                    page.evaluate('document.getElementById("visual-controls").open=true')
                    for preset in ['terminator', 'polar', 'detail', 'overview']:
                        click(page, '[data-viewpoint="' + preset + '"]')
                        assert h.get('/api/navigation/state')['navigation']['Anchor'] == target
                    for scale in ['1', '1.5']: capture(page, target, scale)
                    page.locator('#ui-scale').select_option('1')
                persist()
            # Recover all three actual renderer semiaxes from native geodetic altitude.
            reference = h.get('/api/atlas/state')
            matrix = np.array(reference['j2000_to_render_frame'])
            for target in PHYSICAL:
                body = next(b for b in reference['bodies'] if b['scene_node'] == target)
                rotation = matrix @ np.array(body['body_to_j2000'])
                axes = scene['bodies'][target]['radii_m']
                row = dict(target=target, expected_radii_m=axes, axes=[])
                for axis in range(3):
                    direction = np.eye(3)[axis]
                    offset = rotation @ (direction * max(axes) * 4)
                    up = rotation @ np.eye(3)[(axis + 1) % 3]
                    pose = dict(Anchor=target, ReferenceFrame='Root', Position=offset.tolist(), Up=up.tolist())
                    h.native('openspace.navigation.setNavigationState(' + lua(pose) + ');return {queued=true}')
                    time.sleep(.08)
                    raw = h.native('local geo=openspace.globebrowsing.geoPositionForCamera();return {geographic=geo,nav=openspace.navigation.getNavigationState("Root"),radius=openspace.boundingSphere(' + lua(target) + ')}')
                    measured = float(np.linalg.norm(array(raw['nav']['Position']))) - array(raw['geographic'])[2]
                    error = abs(measured - axes[axis])
                    row['axes'].append(dict(axis=axis, inferred_radius_m=measured, error_m=error, raw=raw))
                    assert error <= .02, row
                    assert raw['radius'] >= max(axes), row
                    if target != 'Saturn': assert raw['radius'] == max(axes), row
                if target in NEW:
                    texture = h.native('return {path=openspace.propertyValue("Scene.' + target + '.Renderable.Layers.ColorLayers.ReferenceMap.TileProvider.FilePath"),enabled=openspace.propertyValue("Scene.' + target + '.Renderable.Layers.ColorLayers.ReferenceMap.Enabled")}')
                    path = texture['path'].replace('${COSMOS2}', ROOT.as_posix())
                    assert Path(path).resolve() == (ROOT / scene['bodies'][target]['texture']['path']).resolve(), texture
                    assert sha(Path(path)) == scene['bodies'][target]['texture']['sha256'] and texture['enabled']
                    row['texture'] = texture
                result['geometry'].append(row); persist()
            nav('visit', target='Titan', sunlit=True)
            saved = nav('save', name='Verificação temporária · Titã')['views']
            test_id = next(row['id'] for row in saved if row['id'] not in {r['id'] for r in before} | {original_id})
            nav('visit', target='Mercury', sunlit=True)
            restored = nav('restore', id=test_id)
            assert restored['navigation']['Anchor'] == restored['target'] == 'Titan'
            nav('delete', id=test_id)
            result['controls']['candidate_favorite_roundtrip'] = True
            for mode in ['follow', 'free', 'orbit']:
                s = nav('mode', mode=mode)
                assert s['mode'] == mode
                assert (s['navigation']['Anchor'] == 'CosmosFreeAnchor') == (mode == 'free')
                if mode == 'free':
                    old = np.array(s['camera']['position_render_m'])
                    nav('move', translation=[0, 0, 1], look=[0, 0, 0], speed=1e7, dt=.1)
                    new = h.get('/api/navigation/state')['camera']['position_render_m']
                    assert abs(float(np.linalg.norm(np.array(new) - old)) - 1e6) <= .02
            nav('clock', rate=3600, paused=False)
            t0 = h.get('/api/navigation/state')['et']; time.sleep(.3)
            stopped = nav('clock', rate=3600, paused=True)
            assert stopped['et'] > t0
            result['controls']['camera_modes_free_move_and_clock'] = True
            h.post('/api/atlas/epoch', {'utc': EPOCHS[2]})
            for selector, count in [('#copy-atlas', 3), ('#copy-solar', 4)]:
                click(page, selector)
                page.wait_for_function('appState?.mode==="experiment"&&appState.physics.bodies.length===' + str(count), timeout=70000)
                state = h.get('/api/state')['physics']
                assert state['paused'] and len(state['bodies']) == count and state['time'] == 0
                assert h.test.positions(state) <= .001
                lab = h.native('return {origin=openspace.worldPosition("LabRoot"),anchor=openspace.navigation.getNavigationState().Anchor}')
                assert np.linalg.norm(array(lab['origin'])) >= 1e14
                result['controls']['legacy_copy_' + str(count)] = dict(bodies=[b['reference_id'] for b in state['bodies']], lab=lab)
                click(page, '#atlas')
                page.wait_for_function('appState?.mode==="atlas"&&!pending')
            assert not result['page_errors'], result['page_errors']
            page.locator('#ui-scale').select_option(previous_scale)
        result.update(completed=True, functional_accepted=True)
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        try:
            if h.get('/api/state')['mode'] != 'atlas': h.post('/api/command', dict(command='atlas'))
            if original_id:
                result['restored_owner_view'] = nav('restore', id=original_id)
                nav('delete', id=original_id)
                with Page() as page:
                    page.locator('#ui-scale').select_option(previous_scale)
                    page.evaluate('selectTarget(' + json.dumps(result['restored_owner_view']['target']) + ',true)')
            result['protected_unchanged'] = {p.relative_to(ROOT).as_posix(): sha(p) == protected_sha[p.relative_to(ROOT).as_posix()] for p in protected}
            assert all(result['protected_unchanged'].values())
            result['owner_app_kept_open'] = h.get('/api/state')['mode'] == 'atlas'
        except Exception:
            result['cleanup_failure'] = traceback.format_exc(); result['functional_accepted'] = False
        persist()
    print(json.dumps(dict(completed=result['completed'], functional_accepted=result['functional_accepted'],
                          epochs=len(result['epochs']), journey=len(result['journey']), captures=len(result['captures']),
                          geometry=len(result['geometry']), failure=result.get('failure'), cleanup_failure=result.get('cleanup_failure'))), flush=True)
    return 0 if result['functional_accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
