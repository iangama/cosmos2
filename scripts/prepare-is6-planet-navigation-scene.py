"""Prepare six physical globe nodes and an isolated absolute-path profile."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is6-planet-catalog-product0.23.1/app'
STAGE = ROOT / 'output/is6-planet-navigation-staging'
sys.path.insert(0, str(APP))
import atlas

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def lua(value):
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (float, int)):
        return format(value, '.17g')
    if isinstance(value, list):
        return '{' + ','.join(lua(item) for item in value) + '}'
    if isinstance(value, dict):
        return '{' + ','.join(key + '=' + lua(item) for key, item in value.items()) + '}'
    raise ValueError('Unsupported Lua scene value')


def main():
    destination = STAGE / 'planet_scene.json'
    if destination.exists():
        raise FileExistsError('Preserve prepared scene')
    model_path = ROOT / 'output/is6-planet-catalog-model-20261110a/catalog-data.json'
    model = json.loads(model_path.read_text(encoding='utf8'))
    visuals_path = ROOT / 'evidence/is6-planet-visuals-20261111a.json'
    visuals = json.loads(visuals_path.read_text(encoding='utf8'))
    decoded_path = ROOT / 'evidence/is6-planet-visuals-decode-20261111a.json'
    assert visuals['completed'] and json.loads(decoded_path.read_text())['completed']
    assert all(sha(ROOT / item['path']) == item['sha256'] for item in visuals['maps'].values())
    atlas.initialize()
    legacy = {b['scene_node']: b for b in atlas.states(utc='2026-10-11T12:00:00Z')['bodies']}
    bodies, nodes = {}, []
    for item in model['bodies']:
        node, target = item['node'], item['naif_id']
        radii = (atlas.SPICE.bodvrd(target, 'RADII', 3)[1] * 1000).tolist()
        if node in legacy and legacy[node]['shape']:
            old = legacy[node]['shape']
            radii = old.get('radii_m', [old.get('radius_m')] * 3)
        bodies[node] = dict(name=item['name'], target=target, kind=item['body_kind'],
                            radii_m=radii, frame=item['rotation_frame'])
        if node not in visuals['maps']:
            continue
        visual = visuals['maps'][node]
        bodies[node]['texture'] = visual
        nodes.append(dict(
            Identifier=node,
            Transform=dict(
                Translation=dict(Type='SpiceTranslation', Target=target, Observer='0', Frame='GALACTIC'),
                Rotation=dict(Type='SpiceRotation', SourceFrame=item['rotation_frame'], DestinationFrame='GALACTIC')),
            Renderable=dict(
                Type='RenderableGlobe', Radii=radii, PerformShading=True, LightSourceNode='Sun',
                Layers=dict(ColorLayers=[dict(Identifier='ReferenceMap', Name='Mapa visual OpenSpace',
                                               FilePath='__ROOT__/' + visual['path'], Enabled=True)])),
            GUI=dict(Name=item['name'], Path='/Cosmos2')
        ))
    assert len(nodes) == 6
    extra = [path for path in model['extra_spk'] if 'saturn-center' not in path]
    kernels = ['__ROOT__/' + path for path in extra]
    source = [
        'asset.require(openspace.absPath("${USER_ASSETS}/cosmos2/atlas.asset"))',
        'local project = openspace.absPath("${COSMOS2}")',
        'local kernels = ' + lua(kernels).replace('"__ROOT__/', 'project .. "/'),
        'local nodes = ' + lua(nodes).replace('"__ROOT__/', 'project .. "/'),
        'asset.onInitialize(function()',
        '  openspace.spice.loadKernel(kernels)',
        '  for _, node in ipairs(nodes) do openspace.addSceneGraphNode(node) end',
        'end)',
        'asset.onDeinitialize(function()',
        '  for index = #nodes, 1, -1 do openspace.removeSceneGraphNode(nodes[index].Identifier) end',
        '  openspace.spice.unloadKernel(kernels)',
        'end)',
        'asset.meta = {Name="Cosmos2 eight-planet scene",Author="Cosmos2 / JPL / OpenSpace",Description="Physical centers, fixed visual maps and general IAU rotations."}',
    ]
    asset = STAGE / 'planet_scene.asset'
    asset.write_text('\n'.join(source) + '\n', encoding='utf8')
    profile = json.loads((ROOT / 'user/data/profiles/cosmos2.profile').read_text())
    profile['assets'].append('${COSMOS2}/output/is6-planet-navigation-staging/planet_scene.asset')
    profile['meta'].update(name='Cosmos2 — oito planetas', version='0.24.0')
    profile_path = STAGE / 'atlas.profile'
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    cfg = (ROOT / 'config/cosmos2.cfg').read_text()
    cfg += '\nProfile = project .. "/output/is6-planet-navigation-staging/atlas.profile"\nPerProfileCache = false\n'
    (STAGE / 'cosmos2.cfg').write_text(cfg, encoding='utf8')
    result = dict(schema=1, bodies=bodies, coverage_utc=model['application_utc'],
                  visual_acquisition_sha256=sha(visuals_path), pixel_decode_sha256=sha(decoded_path),
                  scene_asset=dict(path=asset.relative_to(ROOT).as_posix(), sha256=sha(asset)),
                  profile_sha256=sha(profile_path), recipe_sha256=sha(Path(__file__)),
                  position_readback_budget='max(0.001m, 8 ULP of the maximum absolute component)')
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    atlas.SPICE.kclear()
    print(json.dumps(dict(prepared=True, new_globes=len(nodes), bodies=len(bodies))), flush=True)


if __name__ == '__main__':
    main()
