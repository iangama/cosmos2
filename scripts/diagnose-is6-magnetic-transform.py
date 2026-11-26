"""Compare native float rotation with a direct SI point, without changing models."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import argparse
import hashlib
import json
import math
import sys
import time
import traceback
import uuid

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is6-spatial-product0.18.5/app'
sys.path[:0] = [str(ROOT / 'output/is6-layer-coordination-staging'), str(APP)]
from cef_page import Page
import is6_layer_contract as contract
from is6_product_scene import lua
import body_field_scene
h = SourceFileLoader('is6_transform_helpers', str(ROOT / 'scripts/verify-native-solar-integration.py')).load_module()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    out = ROOT / ('evidence/is6-magnetic-transform-diagnostic-' + args.label + '.json')
    if out.exists():
        raise FileExistsError('Preserve diagnostic evidence')
    paths = [Path(__file__), APP / 'body_field_geometry.py', APP / 'body_field_scene.py',
             ROOT / '.upstream/openspace/modules/base/rotation/staticrotation.cpp',
             ROOT / '.upstream/openspace/modules/base/rotation/staticrotation.h']
    r = dict(completed=False, accepted=False, runs=[], owner_sha256=sha(ROOT / 'user/sessions/latest.json'),
             source_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in paths},
             scope='Diagnostic only: native float Euler rotation versus an SI point translated directly; no scientific, product or performance acceptance.')
    nodes = []
    def persist():
        out.write_text(json.dumps(r, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    persist()
    try:
        with Page() as page:
            page.goto(h.BASE + '/')
            page.wait_for_function('appState&&atlasState&&!pending')
            assert h.get('/api/state')['mode'] == 'atlas'
            page.locator('#copy-solar').click()
            page.wait_for_function('appState.physics?.bodies.length===4&&!pending', timeout=70000)
            phase = h.get('/api/state')['physics']
            held = h.phase(phase)
            for target in ['399', '599']:
                b = next(b for b in phase['bodies'] if b['reference_id'] == 'sol:naif:' + target)
                reading = (contract.earth_magnetism.read(phase, b['id'], -23.55, -46.63, 1000.) if target == '399'
                           else contract.jupiter_magnetism.read(phase, b['id'], 1.5 * 71492000., 0., 0., 13))
                _, prepared = body_field_scene.prepare(reading, 'vector')
                g, render = prepared['geometry'], prepared['render']
                token = 'IS6TransformDiagnostic_' + uuid.uuid4().hex
                frame, basis, rotated, direct = [token + suffix for suffix in ['', '_basis', '_rotated', '_direct']]
                unit = g['reference_radius_m']
                expected = body_field_scene.product(g['body_to_render'], g['point_model_m'])
                definitions = [dict(Identifier=frame, Parent='LabRoot', Transform=dict(Translation=dict(Type='StaticTranslation', Position=g['center_render_m']))),
                    dict(Identifier=basis, Parent=frame, Transform=dict(Rotation=dict(Type='StaticRotation', Rotation=render['model_to_render_rotation_euler_rad']), Scale=dict(Type='StaticScale', Scale=unit))),
                    dict(Identifier=rotated, Parent=basis, Transform=dict(Translation=dict(Type='StaticTranslation', Position=[x / unit for x in g['point_model_m']]))),
                    dict(Identifier=direct, Parent=frame, Transform=dict(Translation=dict(Type='StaticTranslation', Position=expected)))]
                nodes += [d['Identifier'] for d in definitions]
                h.native(''.join('openspace.addSceneGraphNode(' + lua(d) + ');' for d in definitions) + 'return {queued=true}')
                time.sleep(.1)
                native = h.native('return {center_world=openspace.worldPosition(' + lua(frame) + '),rotated_world=openspace.worldPosition(' + lua(rotated) + '),direct_world=openspace.worldPosition(' + lua(direct) + '),direct_local=openspace.propertyValue("Scene.' + direct + '.Translation.Position"),angles=openspace.propertyValue("Scene.' + basis + '.Rotation.Rotation")}')
                for kind in ['rotated', 'direct']:
                    native[kind + '_relative_m'] = [p - c for p, c in zip(native[kind + '_world'], native['center_world'], strict=True)]
                    native[kind + '_error_m'] = [a - e for a, e in zip(native[kind + '_relative_m'], expected, strict=True)]
                    native[kind + '_ULP_limits_m'] = [math.ulp(p) + math.ulp(c) + .001 for p, c in zip(native[kind + '_world'], native['center_world'], strict=True)]
                assert native['direct_local'] == expected
                assert all(abs(e) <= limit for e, limit in zip(native['direct_error_m'], native['direct_ULP_limits_m'], strict=True))
                bounds = [m['conservative_display_position_error_bound_m'] for m in render['meshes']]
                assert max(abs(x) for x in native['rotated_error_m']) <= max(bounds)
                r['runs'].append(dict(body=target, expected_relative_m=expected, requested_angles=render['model_to_render_rotation_euler_rad'],
                                      native=native, existing_mesh_display_error_bounds_m=bounds))
                persist()
            assert h.phase(h.get('/api/state')['physics']) == held
            r.update(completed=True, accepted=True)
    except Exception:
        r['failure'] = traceback.format_exc()
    finally:
        try:
            h.native(''.join('if openspace.hasSceneGraphNode(' + lua(n) + ') then openspace.removeSceneGraphNode(' + lua(n) + ') end;' for n in reversed(nodes)) + 'return {removed=true}')
            r['nodes_after_cleanup'] = h.native('local r={};for _,n in ipairs(' + lua(nodes) + ') do r[n]=openspace.hasSceneGraphNode(n) end;return r')
            assert not any(r['nodes_after_cleanup'].values())
            h.post('/api/command', dict(command='atlas'))
            h.native('openspace.toggleShutdown();return {closing=true}')
            assert sha(ROOT / 'user/sessions/latest.json') == r['owner_sha256']
            assert all(sha(ROOT / p) == seal for p, seal in r['source_sha256'].items())
        except Exception:
            r['cleanup_failure'] = traceback.format_exc()
            r['accepted'] = False
        persist()
    print(json.dumps(dict(accepted=r['accepted'], bodies=len(r['runs']), failure=r.get('failure', '').splitlines()[-1:])))
    return 0 if r['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
