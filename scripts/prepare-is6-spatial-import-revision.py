"""0.22.1: keep the bridged file in its actual input and name its source body."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'output/is6-spatial-import-product0.22.0'
TARGET = ROOT / 'output/is6-spatial-import-product0.22.1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
if TARGET.exists():
    raise FileExistsError('Preserve UI candidate')
parent = BASE / 'build-manifest.json'
manifest = json.loads(parent.read_text())
sources = dict(manifest['source_sha256'])
proofs = [ROOT / 'evidence/is6-spatial-import-native-20261105c.json',
          ROOT / 'evidence/is6-spatial-import-native-20261105d.json']
for path in proofs:
    assert json.loads(path.read_text())['accepted']
visual = ROOT / 'evidence/is6-spatial-import-visual-20261105c.json'
assert json.loads(visual.read_text())['accepted'] is False
files = {p.relative_to(BASE / 'app').as_posix():sha(p) for p in (BASE / 'app').rglob('*')
         if p.is_file() and '__pycache__' not in p.parts}
assert files == manifest['files_sha256']
for path in [Path(__file__),parent,visual,*proofs]:
    sources[path.relative_to(ROOT).as_posix()] = sha(path)
assert all(sha(ROOT / name) == seal for name,seal in sources.items())
shutil.copytree(BASE / 'app',TARGET / 'app',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
ui = TARGET / 'app/ui/is6-spatial.js'
text = ui.read_text()
old = "state.importMessage='';el('import-file').value='';"
new = "state.importMessage='';const transfer=new DataTransfer();transfer.items.add(file);el('import-file').files=transfer.files;"
assert text.count(old) == 1
text = text.replace(old,new)
old = 'preview?`Sol · ${preview.epoch.utc}'
new = "preview?`${({'sol:naif:10':'Sol','sol:naif:399':'Terra','sol:naif:301':'Lua','sol:naif:599':'Júpiter'})[preview.body_reference_id]||preview.body_reference_id} · ${preview.epoch.utc}"
assert text.count(old) == 1
text = text.replace(old,new)
ui.write_text(text,encoding='utf8')
newfiles = {p.relative_to(TARGET / 'app').as_posix():sha(p) for p in (TARGET / 'app').rglob('*')
            if p.is_file() and '__pycache__' not in p.parts}
assert [name for name,seal in newfiles.items() if files.get(name) != seal] == ['ui/is6-spatial.js']
result = dict(candidate='0.22.1',kind='spatial-source-import',accepted=False,promoted=False,
    source_sha256=sources,files_sha256=newfiles,base_files_sha256=files,
    base_manifest=parent.relative_to(ROOT).as_posix(),changed=['ui/is6-spatial.js'],
    scope='UI-only bridge/body-label correction; backend bytes identical to0.22.0. Own native/UI proof and1–8Rref performance profile pending.')
(TARGET / 'build-manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(prepared=True,candidate='0.22.1',changed=result['changed'])))
