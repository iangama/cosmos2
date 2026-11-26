"""Prepare 0.21.1 with stable polled text; preserve executed 0.21.0."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
base = ROOT / 'output/is6-layers-product0.21.0'
target = ROOT / 'output/is6-layers-product0.21.1'
if target.exists():
    raise FileExistsError('Preserve candidate')
parent = base / 'build-manifest.json'
manifest = json.loads(parent.read_text())
files = {p.relative_to(base / 'app').as_posix(): sha(p) for p in (base / 'app').rglob('*')
         if p.is_file() and '__pycache__' not in p.parts}
assert files == manifest['files_sha256']
sources = dict(manifest['source_sha256'])
proofs = [ROOT / ('evidence/is6-layers-import-native-' + label + '.json') for label in ['20261104q', '20261104r']]
proofs += [ROOT / ('evidence/is6-layers-import-native-process-' + label + '.json') for label in ['20261104q', '20261104r']]
for path in proofs:
    proof = json.loads(path.read_text())
    assert proof['accepted'] and proof['completed']
    for name, seal in proof['source_sha256'].items():
        assert name not in sources or sources[name] == seal
        sources[name] = seal
    sources[path.relative_to(ROOT).as_posix()] = sha(path)
refusal = ROOT / 'evidence/is6-layers-import-visual-refusal-20261104r.json'
assert json.loads(refusal.read_text())['accepted'] is False
ui = ROOT / 'output/is6-layers-migration-staging/ui/is6-layers-v2.js'
for path in [parent, refusal, ui, Path(__file__)]:
    sources[path.relative_to(ROOT).as_posix()] = sha(path)
assert all(sha(ROOT / name) == seal for name, seal in sources.items())
shutil.copytree(base / 'app', target / 'app', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
shutil.copy2(ui, target / 'app/ui/is6-layers.js')
newfiles = {p.relative_to(target / 'app').as_posix(): sha(p) for p in (target / 'app').rglob('*')
            if p.is_file() and '__pycache__' not in p.parts}
changed = sorted(name for name, seal in newfiles.items() if files.get(name) != seal)
assert changed == ['ui/is6-layers.js']
result = dict(candidate='0.21.1', accepted=False, promoted=False, source_sha256=sources,
              files_sha256=newfiles, base_manifest=parent.relative_to(ROOT).as_posix(),
              base_files_sha256=files, changed=changed,
              scope='Avoid redundant UI text mutations; same backend/model bytes. Native first/restart, complete visual review and own profile pending for this exact revision.')
(target / 'build-manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps(dict(prepared=True, candidate='0.21.1', changed=changed, accepted=False)))
