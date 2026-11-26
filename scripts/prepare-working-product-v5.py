"""Freeze the editable species suggestions after isolated checks, preserving0.27.4."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'output/original-flow-hotfix-product0.27.4'
TARGET=ROOT/'output/original-flow-hotfix-product0.27.5'
UI=ROOT/'scripts/editable-options-ui'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not TARGET.exists()
    checks=json.loads((ROOT/'evidence/editable-options-ui-20261120b.json').read_text(encoding='utf8'))
    assert checks['accepted'] and checks['completed']
    parent=json.loads((PARENT/'build-manifest.json').read_text(encoding='utf8'))
    assert all(sha(PARENT/name)==digest for name,digest in parent['files_sha256'].items())
    for name in ['app','data']:shutil.copytree(PARENT/name,TARGET/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for file in UI.iterdir():shutil.copy2(file,TARGET/'app/ui'/file.name)
    html=TARGET/'app/ui/nuclear-energy.html';text=html.read_text(encoding='utf8')
    html.write_text(text.replace('</body>','<script src="editable-options.js"></script>\n</body>').replace('<body>','<link rel="stylesheet" href="editable-options.css">\n<body>'),encoding='utf8')
    css=TARGET/'app/ui/nuclear-energy.css';text=css.read_text(encoding='utf8')
    css.write_text(text.replace('input[list]','input[list],input[data-c2-list]'),encoding='utf8')
    files={f.relative_to(TARGET).as_posix():sha(f) for folder in ['app','data'] for f in (TARGET/folder).rglob('*') if f.is_file() and '__pycache__' not in f.parts}
    assert all(files[name]==digest for name,digest in parent['files_sha256'].items() if name.endswith('.py'))
    changed=[name for name,digest in files.items() if parent['files_sha256'].get(name)!=digest]
    assert all(name.startswith('app/ui/') for name in changed)
    manifest=dict(schema=1,candidate='0.27.5',promoted=False,native_user_flow_accepted=False,
      scientific_python_unchanged=137,files_sha256=files,changed_app_files=changed,
      parent_manifest_sha256=sha(PARENT/'build-manifest.json'),preparation_script_sha256=sha(Path(__file__)),
      ui_source_sha256={f.name:sha(f) for f in UI.iterdir()},
      scope='Editable species suggestions rendered in the page, retaining free text, original form fields and scientific modules. Native owner-entry verification pending.')
    (TARGET/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(prepared=True,selected=False,changed=changed)))


if __name__=='__main__':main()
