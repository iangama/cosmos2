"""Freeze the verified spatial-compatibility staging as a new local revision."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'output/original-flow-hotfix-product0.27.6'
STAGING=ROOT/'output/spatial-roundtrip-http-staging-v1'
TARGET=ROOT/'output/original-flow-hotfix-product0.27.7'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not TARGET.exists(), 'Preserve prepared revisions'
    cpu=json.loads((ROOT/'evidence/spatial-roundtrip-v2-offline-20261121a.json').read_text(encoding='utf8'))
    http=json.loads((ROOT/'evidence/spatial-roundtrip-http-20261121a.json').read_text(encoding='utf8'))
    preparation=json.loads((STAGING/'preparation.json').read_text(encoding='utf8'))
    parent=json.loads((PARENT/'build-manifest.json').read_text(encoding='utf8'))
    assert cpu['accepted'] and http['accepted'] and http['completed']
    assert all(sha(ROOT/name)==digest for name,digest in cpu['source_sha256_files'].items())
    assert all(sha(ROOT/name)==digest for name,digest in http['source_sha256'].items())
    assert all(sha(STAGING/name)==digest for name,digest in preparation['files_sha256'].items())
    assert all(sha(PARENT/name)==digest for name,digest in parent['files_sha256'].items())
    for folder in ['app','data']:
        shutil.copytree(STAGING/folder,TARGET/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    files={p.relative_to(TARGET).as_posix():sha(p) for folder in ['app','data']
           for p in (TARGET/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert files==preparation['files_sha256']
    manifest=dict(schema=1,candidate='0.27.7',promoted=False,native_user_flow_accepted=False,
      scientific_python_unchanged=137,files_sha256=files,
      changed_app_files=preparation['changed_app_files'],added_app_files=preparation['added_app_files'],
      parent_manifest_sha256=sha(PARENT/'build-manifest.json'),staging_preparation_sha256=sha(STAGING/'preparation.json'),
      proof_sha256={name:sha(ROOT/name) for name in ['evidence/spatial-roundtrip-v2-offline-20261121a.json','evidence/spatial-roundtrip-http-20261121a.json']},
      preparation_script_sha256=sha(Path(__file__)),
      scope='Current and legacy spatial checkpoint import with exact original bytes, science, view and nested provenance. Three versioned Python modules added; server imports and Layers format routing changed. All137 pre-existing non-server scientific modules preserved. Local static preparation; native owner-path acceptance pending.')
    (TARGET/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(prepared=True,candidate='0.27.7',selected=False,changed=manifest['changed_app_files'],added=manifest['added_app_files'])))


if __name__=='__main__':main()
