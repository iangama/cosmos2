"""Prepare an isolated correction; never install, launch a renderer or change shortcuts."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / 'output/original-forces-hotfix-staging'
TARGET = ROOT / 'output/original-flow-hotfix-staging-v2'
UI = ROOT / 'scripts/original-flow-hotfix-ui'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(folder):
    return {p.relative_to(folder).as_posix(): sha(p) for p in sorted(folder.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def main():
    if TARGET.exists():
        raise FileExistsError('Preserve the prepared review. Use a new revision.')
    parent_before = {name: inventory(PARENT / name) for name in ['app', 'data']}
    TARGET.mkdir()
    for name in ['app', 'data']:
        shutil.copytree(PARENT / name, TARGET / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for source in sorted(UI.iterdir()):
        if source.is_file():
            shutil.copy2(source, TARGET / 'app/ui' / source.name)
    texture = ROOT / 'data/textures/earth.jpg'
    (TARGET / 'data/textures').mkdir(exist_ok=True)
    shutil.copy2(texture, TARGET / 'data/textures/earth.jpg')
    server_path = TARGET / 'app/server.py'
    server = server_path.read_text()
    old = "            content=texture.read_bytes()"
    new = """            try:
                content=texture.read_bytes()
            except OSError:
                return self.json_response({'ok':False,'error':'A textura local da Terra está indisponível. Repare os dados visuais e tente novamente.'},503)"""
    assert server.count(old) == 1
    server_path.write_text(server.replace(old, new), encoding='utf8')
    original = inventory(PARENT / 'app')
    final = inventory(TARGET / 'app')
    scientific = {name: digest for name, digest in original.items()
                  if name.endswith('.py') and name not in {'server.py', 'artifacts.py'}}
    assert len(scientific) == 137
    assert all(final[name] == digest for name, digest in scientific.items())
    assert parent_before == {name: inventory(PARENT / name) for name in ['app', 'data']}
    changed = [name for name, digest in final.items() if original.get(name) != digest]
    result = dict(prepared=True, accepted=False, promoted=False, installed=False,
                  native_user_flow_accepted=False,
                  parent='output/original-forces-hotfix-staging', product_parent='0.27.0',
                  scope='Offline review of existing separate panels and the geomagnetic texture. No final visual integration or native acceptance.',
                  scientific_python_unchanged=scientific, changed_app_files=changed,
                  texture_sha256=sha(texture), preparation_script_sha256=sha(Path(__file__)),
                  ui_source_sha256=inventory(UI), app_sha256=final, data_sha256=inventory(TARGET / 'data'))
    (TARGET / 'preparation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(prepared=True, scientific_python_unchanged=len(scientific), changed_app_files=changed)))


if __name__ == '__main__':
    main()
