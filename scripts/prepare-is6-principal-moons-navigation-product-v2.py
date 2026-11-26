"""Package only the favorites encoding correction as isolated candidate0.25.1."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/is6-principal-moons-navigation-product0.25.0'
TARGET=ROOT/'output/is6-principal-moons-navigation-product0.25.1'
STAGE=ROOT/'output/is6-principal-moons-navigation-staging-v2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    if TARGET.exists():raise FileExistsError('Preserve corrected candidate')
    parent_path=BASE/'build-manifest.json';parent=json.loads(parent_path.read_text())
    actual={p.relative_to(BASE/'app').as_posix():sha(p) for p in (BASE/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert actual==parent['files_sha256']
    proof=ROOT/'evidence/is6-principal-moons-favorites-20261111a.json';assert json.loads(proof.read_text())['accepted']
    sources=dict(parent['source_sha256'])
    inputs=[Path(__file__),parent_path,proof,ROOT/'scripts/revise-is6-principal-moons-favorites.py',ROOT/'scripts/verify-is6-principal-moons-favorites.py',ROOT/'scripts/launch-is6-principal-moons-candidate-v2.py']
    inputs.extend(p for p in STAGE.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for p in inputs:sources[p.relative_to(ROOT).as_posix()]=sha(p)
    assert all(sha(ROOT/name)==seal for name,seal in sources.items())
    shutil.copytree(BASE/'app',TARGET/'app',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copy2(STAGE/'moon_navigation.py',TARGET/'app/moon_navigation.py')
    shutil.copy2(STAGE/'planet_scene.json',TARGET/'app/planet_scene.json')
    app=TARGET/'app';files={p.relative_to(app).as_posix():sha(p) for p in app.rglob('*') if p.is_file()}
    manifest=dict(candidate='0.25.1',accepted=False,promoted=False,source_sha256=sources,files_sha256=files,
        changed=sorted(name for name,seal in files.items() if actual.get(name)!=seal),
        base_manifest=parent_path.relative_to(ROOT).as_posix(),scene_profile='output/is6-principal-moons-navigation-staging-v2/atlas.profile',
        scope='Sixteen-body Atlas with explicit UTF8 favorites and preserved legacy decoding; native journey, visual and own profile pending')
    (TARGET/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(prepared=True,candidate='0.25.1',changed=manifest['changed'])),flush=True)


if __name__=='__main__':main()
