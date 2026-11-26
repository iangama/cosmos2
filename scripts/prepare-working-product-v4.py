"""Freeze a new UI revision for manual option selection; never edit previous products."""
from pathlib import Path
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / 'output/original-flow-hotfix-product0.27.2'
TARGET = ROOT / 'output/original-flow-hotfix-product0.27.4'
UI = ROOT / 'scripts/option-controls-ui-v2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not TARGET.exists(), 'Preserve prepared revisions'
    parent = json.loads((PARENT / 'build-manifest.json').read_text(encoding='utf8'))
    assert parent['scientific_python_unchanged'] == 137
    assert all(sha(PARENT / name) == digest for name,digest in parent['files_sha256'].items())
    for name in ['app', 'data']:
        shutil.copytree(PARENT / name, TARGET / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for source in UI.iterdir():
        shutil.copy2(source, TARGET / 'app/ui' / source.name)
    pages = []
    for page in sorted((TARGET / 'app/ui').glob('*.html')):
        text = page.read_text(encoding='utf8')
        if '<html' not in text.lower():
            continue
        link = '<link rel="stylesheet" href="option-controls.css">\n'
        if '</head>' in text:
            text = text.replace('</head>', link+'</head>')
        else:
            assert re.search(r'<body\b', text, re.I), page
            text = re.sub(r'(<body\b)', link+r'\1', text, count=1, flags=re.I)
        script = '<script src="option-controls.js"></script>\n'
        text = text.replace('</body>', script+'</body>') if '</body>' in text else text+'\n'+script
        page.write_text(text, encoding='utf8')
        pages.append(page.name)
    navigation = TARGET / 'app/ui/navigation.js'
    text = navigation.read_text(encoding='utf8')
    assert "closest('input,select,textarea,[contenteditable]')" in text
    navigation.write_text(text.replace("closest('input,select,textarea,[contenteditable]')",
                                      "closest('input,select,textarea,[contenteditable],[role=combobox],[role=listbox]')"), encoding='utf8')
    files = {file.relative_to(TARGET).as_posix():sha(file) for name in ['app','data']
             for file in (TARGET / name).rglob('*') if file.is_file() and '__pycache__' not in file.parts}
    changed = [name for name,digest in files.items() if parent['files_sha256'].get(name) != digest]
    assert all(name.startswith('app/ui/') for name in changed)
    assert all(files[name] == digest for name,digest in parent['files_sha256'].items() if name.endswith('.py'))
    manifest = dict(schema=1, candidate='0.27.4', promoted=False, native_user_flow_accepted=False,
                    scientific_python_unchanged=137, files_sha256=files, changed_app_files=changed,
                    parent_manifest_sha256=sha(PARENT / 'build-manifest.json'),
                    preparation_script_sha256=sha(Path(__file__)), pages=pages,
                    ui_source_sha256={file.name:sha(file) for file in UI.iterdir()},
                    scope='Manual option selection in the page, without CEF popup surfaces. Static preparation only; native mouse selection not yet accepted.')
    (TARGET / 'build-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(prepared=True, scientific_python_unchanged=137, changed=changed, selected=False)))


if __name__ == '__main__':
    main()
