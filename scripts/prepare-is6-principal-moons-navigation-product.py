"""Package the isolated sixteen-body Atlas while retaining the accepted planet candidate."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/is6-planet-navigation-product0.24.0'
TARGET=ROOT/'output/is6-principal-moons-navigation-product0.25.0'
STAGE=ROOT/'output/is6-principal-moons-navigation-staging'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    if TARGET.exists():raise FileExistsError('Preserve candidate0.25.0')
    parent_path=BASE/'build-manifest.json';parent=json.loads(parent_path.read_text())
    actual={p.relative_to(BASE/'app').as_posix():sha(p) for p in (BASE/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert actual==parent['files_sha256']
    receipts=['is6-principal-moons-navigation-et-20261111a','is6-principal-moons-verification-20261111a',
        'is6-principal-moons-horizons-20261111b','is6-planet-navigation-profile-audit-20261111a',
        'is6-planet-navigation-visual-20261111a','is6-planet-navigation-reopen-20261111a']
    for name in receipts:assert json.loads((ROOT/f'evidence/{name}.json').read_text())['accepted']
    visual_path=ROOT/'evidence/is6-principal-moons-visuals-20261111a.json';visuals=json.loads(visual_path.read_text());assert visuals['completed']
    sources=dict(parent['source_sha256'])
    inputs=[Path(__file__),parent_path,visual_path,ROOT/'scripts/launch-is6-principal-moons-candidate.py',
        ROOT/'scripts/prepare-is6-principal-moons-navigation.py',ROOT/'IS-6-LUAS-NAVEGACAO-CONTRATO.md',
        ROOT/'output/is6-principal-moons-model-20261111a/catalog-data.json']
    inputs.extend(ROOT/f'evidence/{name}.json' for name in receipts)
    inputs.extend(p for p in STAGE.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    model=json.loads((ROOT/'output/is6-principal-moons-model-20261111a/catalog-data.json').read_text())
    for name,seal in model['runtime_sha256'].items():assert sha(ROOT/name)==seal;sources[name]=seal
    for item in visuals['maps'].values():inputs.extend([ROOT/item['path'],ROOT/item['upstream_asset']])
    for p in inputs:sources[p.relative_to(ROOT).as_posix()]=sha(p)
    assert all(sha(ROOT/name)==seal for name,seal in sources.items())
    shutil.copytree(BASE/'app',TARGET/'app',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for p in STAGE.glob('*.py'):shutil.copy2(p,TARGET/'app'/p.name)
    shutil.copy2(STAGE/'planet_scene.json',TARGET/'app/planet_scene.json')
    for p in (STAGE/'ui').iterdir():shutil.copy2(p,TARGET/'app/ui'/p.name)
    server=TARGET/'app/server.py';source=server.read_text()
    assert source.count('from planet_atlas import Atlas')==source.count('from planet_navigation import Navigation')==1
    source=source.replace('from planet_atlas import Atlas','from moon_atlas import Atlas').replace('from planet_navigation import Navigation','from moon_navigation import Navigation')
    assert source.count('from is6_planet_catalog import states')==2
    source=source.replace('from is6_planet_catalog import states','from is6_principal_moons_catalog import states')
    server.write_text(source)
    app=TARGET/'app';files={p.relative_to(app).as_posix():sha(p) for p in app.rglob('*') if p.is_file()}
    manifest=dict(candidate='0.25.0',accepted=False,promoted=False,source_sha256=sources,files_sha256=files,
        changed=sorted(name for name,seal in files.items() if actual.get(name)!=seal),
        base_manifest=parent_path.relative_to(ROOT).as_posix(),scene_profile='output/is6-principal-moons-navigation-staging/atlas.profile',
        scope='Eight planets and seven moons in reference Atlas; native journey, visual review and own profile pending')
    (TARGET/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(prepared=True,candidate='0.25.0',changed=len(manifest['changed']))),flush=True)


if __name__=='__main__':main()
