"""Prepare isolated 0.22.0 from accepted spatial CPU proofs and frozen 0.21.1."""
from pathlib import Path
from html.parser import HTMLParser
import ast
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'output/is6-layers-product0.21.1'
TARGET = ROOT / 'output/is6-spatial-import-product0.22.0'
STAGING = ROOT / 'output/is6-spatial-import-staging'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
if TARGET.exists():
    raise FileExistsError('Preserve spatial import candidate')
anchor = ROOT / 'evidence/is6-spatial-import-service-20261104c2.json'
proof = json.loads(anchor.read_text())
assert proof['accepted'] and proof['completed'] and proof['native_calls'] == 0 and len(proof['imports']) == 6
parent = BASE / 'build-manifest.json'
manifest = json.loads(parent.read_text())
files = {p.relative_to(BASE / 'app').as_posix(): sha(p) for p in (BASE / 'app').rglob('*')
         if p.is_file() and '__pycache__' not in p.parts}
assert files == manifest['files_sha256']
sources = dict(manifest['source_sha256'])
for name, seal in proof['source_sha256'].items():
    assert name not in sources or sources[name] == seal, name
    sources[name] = seal
modules = ['is6_spatial_import.py', 'is6_spatial_import_store.py', 'is6_spatial_import_laboratory.py',
           'is6_spatial_import_scene.py', 'server.py']
inputs = [Path(__file__), anchor, parent, *[STAGING / name for name in modules],
          *[STAGING / 'ui' / name for name in ['is6-spatial.js', 'is6-layers.js', 'spatial-panel.html']]]
for path in inputs:
    sources[path.relative_to(ROOT).as_posix()] = sha(path)
assert all(sha(ROOT / name) == seal for name, seal in sources.items())
for name in modules:
    ast.parse((STAGING / name).read_text())
shutil.copytree(BASE / 'app', TARGET / 'app', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
for name in modules:
    shutil.copy2(STAGING / name, TARGET / 'app' / name)
for name in ['is6-spatial.js', 'is6-layers.js']:
    shutil.copy2(STAGING / 'ui' / name, TARGET / 'app/ui' / name)
page = TARGET / 'app/ui/index.html'
text = page.read_text()
start = text.index('<section id="spatial-panel"')
end = text.index('<section id="spatial-caption"', start)
text = text[:start] + (STAGING / 'ui/spatial-panel.html').read_text() + text[end:]
needle = '<p id="layers-import-reading"'
position = text.index(needle)
text = text[:position] + '<button id="layers-spatial-route" type="button" class="wide" hidden>Abrir Malha espacial</button>\n    ' + text[position:]
page.write_text(text, encoding='utf8')
class Identifiers(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
    def handle_starttag(self, tag, attributes):
        self.ids.extend(value for key, value in attributes if key == 'id')
parser = Identifiers()
parser.feed(text)
assert len(parser.ids) == len(set(parser.ids)), 'Duplicate product HTML identifiers'
newfiles = {p.relative_to(TARGET / 'app').as_posix(): sha(p) for p in (TARGET / 'app').rglob('*')
            if p.is_file() and '__pycache__' not in p.parts}
changed = sorted(name for name, seal in newfiles.items() if files.get(name) != seal)
assert changed == sorted([*modules, 'ui/is6-spatial.js', 'ui/is6-layers.js', 'ui/index.html'])
result = dict(candidate='0.22.0', kind='spatial-source-import', accepted=False, promoted=False,
              base_manifest=parent.relative_to(ROOT).as_posix(), source_sha256=sources,
              base_files_sha256=files, files_sha256=newfiles, changed=changed,
              scope='Prepared spatial legacy-import HTTP/UI integration only; CPU foundation/store/actor accepted. HTTP, native restore/restart/cancel/visual review and own 1–8Rref profile pending.')
(TARGET / 'build-manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
print(json.dumps(dict(prepared=True, candidate='0.22.0', changed=changed, accepted=False)))
