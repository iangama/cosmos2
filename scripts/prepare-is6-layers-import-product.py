"""Build isolated 0.21.0 after its CPU import proofs and the K4 profile."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
base = ROOT / 'output/is6-layers-product0.20.1'
target = ROOT / 'output/is6-layers-product0.21.0'
stage = ROOT / 'output/is6-layers-migration-staging'
if target.exists():
    raise FileExistsError('Preserve candidate')
parent = base / 'build-manifest.json'
manifest = json.loads(parent.read_text())
files = {p.relative_to(base / 'app').as_posix(): sha(p) for p in (base / 'app').rglob('*')
         if p.is_file() and '__pycache__' not in p.parts}
assert files == manifest['files_sha256'] and manifest['candidate'] == '0.20.1' and not manifest['promoted']
receipts = [ROOT / 'evidence/is6-layers-storage-cut-20261104f.json',
            ROOT / 'evidence/is6-layers-storage-profile-audit-20261104i.json',
            ROOT / 'evidence/is6-layers-profile-process-20261104i.json',
            ROOT / 'evidence/is6-layers-migration-20261104h.json',
            ROOT / 'evidence/is6-layers-import-store-20261104j2.json',
            ROOT / 'evidence/is6-layers-import-service-20261104l.json']
sources = dict(manifest['source_sha256'])
for path in [parent, Path(__file__), *receipts]:
    if path in receipts:
        proof = json.loads(path.read_text())
        assert proof['accepted'], path
        for name, seal in proof.get('source_sha256', {}).items():
            assert name not in sources or sources[name] == seal, name
            sources[name] = seal
    sources[path.relative_to(ROOT).as_posix()] = sha(path)
mapping = {'is6_layers_migration.py': 'is6_layers_migration.py',
           'is6_layers_import_store_v2.py': 'is6_layers_import_store_v2.py',
           'is6_layers_import_laboratory.py': 'is6_layers_laboratory.py',
           'server-import.py': 'server.py',
           'ui/is6-layers-panel.html': 'ui/is6-layers-panel.html',
           'ui/is6-layers.js': 'ui/is6-layers.js',
           'ui/is6-layers.css': 'ui/is6-layers.css'}
for name in mapping:
    path = stage / name
    sources[path.relative_to(ROOT).as_posix()] = sha(path)
assert all(sha(ROOT / name) == seal for name, seal in sources.items())
shutil.copytree(base / 'app', target / 'app', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
for name, destination in mapping.items():
    shutil.copy2(stage / name, target / 'app' / destination)
old_panel = (base / 'app/ui/is6-layers-panel.html').read_text()
new_panel = (stage / 'ui/is6-layers-panel.html').read_text()
index = target / 'app/ui/index.html'
text = index.read_text()
assert text.count(old_panel) == 1
index.write_text(text.replace(old_panel, new_panel, 1), encoding='utf8')
newfiles = {p.relative_to(target / 'app').as_posix(): sha(p) for p in (target / 'app').rglob('*')
            if p.is_file() and '__pycache__' not in p.parts}
changed = sorted(name for name, seal in newfiles.items() if files.get(name) != seal)
assert changed == sorted([*mapping.values(), 'ui/index.html'])
result = dict(candidate='0.21.0', accepted=False, promoted=False, source_sha256=sources,
              files_sha256=newfiles, base_manifest=parent.relative_to(ROOT).as_posix(),
              base_files_sha256=files, changed=changed,
              scope='Explicit compound import preview/branch/provenance only; native, restart, visual, HTTP and own performance proofs pending. Spatial-only conversion and full IS6/v1 remain open.')
(target / 'build-manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps(dict(prepared=True, candidate='0.21.0', changed=changed, accepted=False)))
