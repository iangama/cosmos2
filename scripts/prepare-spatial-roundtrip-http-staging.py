"""Prepare isolated versioned spatial HTTP/UI wiring; do not select a working product."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'output/original-flow-hotfix-product0.27.6'
TARGET=ROOT/'output/spatial-roundtrip-http-staging-v1'
SOURCE=ROOT/'scripts/spatial-roundtrip-v2'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not TARGET.exists()
    checks=json.loads((ROOT/'evidence/spatial-roundtrip-v2-offline-20261121a.json').read_text(encoding='utf8'))
    assert checks['accepted'] and checks['completed'] and len(checks['checks'])==9
    assert all(sha(ROOT/name)==digest for name,digest in checks['source_sha256_files'].items())
    parent=json.loads((PARENT/'build-manifest.json').read_text(encoding='utf8'))
    assert all(sha(PARENT/name)==digest for name,digest in parent['files_sha256'].items())
    for folder in ['app','data']:shutil.copytree(PARENT/folder,TARGET/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for source in SOURCE.glob('*.py'):shutil.copy2(source,TARGET/'app'/source.name)
    server=TARGET/'app/server.py';text=server.read_text(encoding='utf8')
    assert 'from is6_spatial_import_laboratory import SpatialLaboratory' in text and 'import is6_spatial_import as spatial_migration' in text
    text=text.replace('from is6_spatial_import_laboratory import SpatialLaboratory','from is6_spatial_import_laboratory_v2 import SpatialLaboratory').replace('import is6_spatial_import as spatial_migration','import is6_spatial_import_v2 as spatial_migration')
    server.write_text(text,encoding='utf8')
    layers=TARGET/'app/ui/is6-layers.js';text=layers.read_text(encoding='utf8')
    before="const value=JSON.parse(source_text);spatial=value?.schema===1&&value.kind==='is6_spatial_body_mesh_checkpoint';"
    after="const value=JSON.parse(source_text.replace(/^\\uFEFF/,''));spatial=(value?.schema===1&&value.kind==='is6_spatial_body_mesh_checkpoint')||(value?.schema===2&&value.kind==='is6_spatial_body_mesh_checkpoint_with_origin');"
    assert before in text;layers.write_text(text.replace(before,after),encoding='utf8')
    files={p.relative_to(TARGET).as_posix():sha(p) for folder in ['app','data'] for p in (TARGET/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    unchanged={name:digest for name,digest in parent['files_sha256'].items() if name.endswith('.py') and name not in ['app/server.py','app/artifacts.py']}
    assert len(unchanged)==137 and all(files[name]==digest for name,digest in unchanged.items())
    changed=[name for name,digest in files.items() if name in parent['files_sha256'] and parent['files_sha256'][name]!=digest]
    added=[name for name in files if name not in parent['files_sha256']]
    assert sorted(changed)==['app/server.py','app/ui/is6-layers.js']
    assert len(added)==3 and all(name.endswith('_v2.py') for name in added)
    proof=dict(accepted=True,completed=True,selected=False,native_user_flow_accepted=False,scientific_python_unchanged=137,
      source_parent_manifest_sha256=sha(PARENT/'build-manifest.json'),files_sha256=files,changed_app_files=changed,added_app_files=added,
      script_sha256=sha(Path(__file__)),scope='Isolated HTTP/UI staging only. Three versioned persistence/import modules added; all137 existing non-server Python modules unchanged. No live renderer, session migration, working-version selection or scientific promotion.')
    (TARGET/'preparation.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(prepared=True,changed=changed,added=added,selected=False)))


if __name__=='__main__':main()
