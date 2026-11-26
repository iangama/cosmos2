"""Package the expanded Atlas with pinned scene, maps and backend sources."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'output/is6-planet-catalog-product0.23.1'
TARGET = ROOT / 'output/is6-planet-navigation-product0.24.0'
STAGE = ROOT / 'output/is6-planet-navigation-staging'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def change(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Expected one product source anchor: ' + old)
    return text.replace(old, new)


def main():
    if TARGET.exists():
        raise FileExistsError('Preserve navigation candidate')
    parent_path = BASE / 'build-manifest.json'
    parent = json.loads(parent_path.read_text())
    actual = {p.relative_to(BASE / 'app').as_posix(): sha(p) for p in (BASE / 'app').rglob('*')
              if p.is_file() and '__pycache__' not in p.parts}
    assert actual == parent['files_sha256']
    visual = ROOT / 'evidence/is6-planet-catalog-visual-20261111b.json'
    assert json.loads(visual.read_text())['accepted']
    sources = dict(parent['source_sha256'])
    inputs = [parent_path, Path(__file__), visual,
              ROOT / 'scripts/launch-is6-planet-navigation-candidate.py',
              ROOT / 'IS-6-NAVEGACAO-OITO-PLANETAS-CONTRATO.md',
              ROOT / 'evidence/is6-planet-navigation-et-20261111a.json',
              ROOT / 'evidence/is6-planet-visuals-20261111a.json',
              ROOT / 'evidence/is6-planet-visuals-decode-20261111a.json']
    inputs.extend(p for p in STAGE.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    visuals = json.loads((ROOT / 'evidence/is6-planet-visuals-20261111a.json').read_text())
    for item in visuals['maps'].values():
        inputs.extend([ROOT / item['path'], ROOT / item['upstream_asset']])
    for path in inputs:
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
    assert all(sha(ROOT / p) == seal for p, seal in sources.items())
    shutil.copytree(BASE / 'app', TARGET / 'app', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for path in STAGE.glob('*.py'):
        shutil.copy2(path, TARGET / 'app' / path.name)
    shutil.copy2(STAGE / 'planet_scene.json', TARGET / 'app/planet_scene.json')
    for path in (STAGE / 'ui').iterdir():
        shutil.copy2(path, TARGET / 'app/ui' / path.name)
    server_path = TARGET / 'app/server.py'
    source = server_path.read_text()
    source = change(source, 'from atlas import Atlas', 'from planet_atlas import Atlas')
    source = change(source, 'from navigation import Navigation', 'from planet_navigation import Navigation')
    source = change(source, 'NAVIGATION = Navigation(ATLAS)',
                    "NAVIGATION = Navigation(ATLAS, folder=Path(__file__).resolve().parents[1] / 'navigation')")
    server_path.write_text(source)
    app = TARGET / 'app'
    files = {p.relative_to(app).as_posix(): sha(p) for p in app.rglob('*') if p.is_file()}
    changed = sorted(p for p, seal in files.items() if actual.get(p) != seal)
    manifest = dict(candidate='0.24.0', accepted=False, promoted=False,
                    source_sha256=sources, files_sha256=files, changed=changed,
                    base_manifest=parent_path.relative_to(ROOT).as_posix(),
                    scene_profile='output/is6-planet-navigation-staging/atlas.profile',
                    scope='Eight physical planet destinations plus Moon; native science, journey, visual review and own profiles pending')
    (TARGET / 'build-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(prepared=True, candidate='0.24.0', changed=changed)), flush=True)


if __name__ == '__main__':
    main()
