"""Prepare 0.27.6 statically; do not switch the running session or copy mutable state yet."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / 'output/original-flow-hotfix-product0.27.5'
TARGET = ROOT / 'output/original-flow-hotfix-product0.27.6'
UI = ROOT / 'scripts/reference-file-binding-ui'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not TARGET.exists(), 'Preserve prepared revisions'
    parent = json.loads((PARENT / 'build-manifest.json').read_text(encoding='utf8'))
    assert parent['candidate'] == '0.27.5' and parent['scientific_python_unchanged'] == 137
    assert all(sha(PARENT / name) == digest for name,digest in parent['files_sha256'].items())
    for name in ['app','data']:
        shutil.copytree(PARENT / name, TARGET / name, ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for source in UI.iterdir():
        assert source.suffix in {'.js','.css','.html'} and source.is_file()
        shutil.copy2(source, TARGET / 'app/ui' / source.name)
    files = {file.relative_to(TARGET).as_posix():sha(file) for name in ['app','data']
             for file in (TARGET / name).rglob('*') if file.is_file() and '__pycache__' not in file.parts}
    changed = [name for name,digest in files.items() if parent['files_sha256'].get(name) != digest]
    assert sorted(changed) == ['app/ui/is6-layers.js','app/ui/is6-spatial.js']
    scientific = {name:digest for name,digest in parent['files_sha256'].items()
                  if name.endswith('.py') and name not in ['app/server.py','app/artifacts.py']}
    assert len(scientific) == 137 and all(files[name] == digest for name,digest in scientific.items())
    manifest = dict(schema=1, candidate='0.27.6', promoted=False, native_user_flow_accepted=False,
                    scientific_python_unchanged=137, files_sha256=files, changed_app_files=changed,
                    parent_manifest_sha256=sha(PARENT / 'build-manifest.json'),
                    ui_source_sha256={file.name:sha(file) for file in UI.iterdir()},
                    preparation_script_sha256=sha(Path(__file__)),
                    scope='Native file re-selection no longer disables import or hides the validated origin. Exact source-content guards and all Python modules preserved. Static preparation only; native import/restore verification pending.')
    (TARGET / 'build-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(prepared=True, scientific_python_unchanged=137, changed=changed, selected=False)))


if __name__ == '__main__':
    main()
