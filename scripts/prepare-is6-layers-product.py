"""Build the isolated coordinated-layer candidate from accepted frozen components."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
base = ROOT / 'output/is6-spatial-product0.18.5'
stage = ROOT / 'output/is6-layers-product-staging'
target = ROOT / 'output/is6-layers-product0.19.0'
if target.exists():
    raise FileExistsError('Preserve the candidate; use another version for changes')
parent = base / 'build-manifest.json'
manifest = json.loads(parent.read_text())
assert all(sha(ROOT / p) == seal for p, seal in manifest['source_sha256'].items())
files = {p.relative_to(base / 'app').as_posix(): sha(p) for p in (base / 'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
assert files == manifest['files_sha256']
anchors = [ROOT / 'evidence/is6-native-layer-pair-20261103c.json',
           ROOT / 'evidence/is6-layer-pair-visual-20261103c.json',
           ROOT / 'evidence/is6-layer-pair-native-process-20261103c.json',
           ROOT / 'evidence/is6-pair-profile-audit-20261103a.json',
           ROOT / 'evidence/is6-layer-pair-profile-process-20261103a.json',
           ROOT / 'evidence/is6-layers-service-admission-20261103a.json']
sources = dict(manifest['source_sha256'])
for path in anchors:
    receipt = json.loads(path.read_text())
    assert receipt['accepted'], path
    sources.update(receipt.get('source_sha256', {}))
profile = ROOT / 'evidence/is6-pair-profile-20261103a.json'
profile_record = json.loads(profile.read_text())
assert profile_record['completed'] and not profile_record.get('failure') and not profile_record.get('cleanup_failure')
sources.update(profile_record['source_sha256'])
sources[profile.relative_to(ROOT).as_posix()] = sha(profile)
assert all(sha(ROOT / p) == seal for p, seal in sources.items())
shutil.copytree(base / 'app', target / 'app', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
staged = sorted(p for p in stage.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
for path in staged:
    relative = path.relative_to(stage)
    destination = target / 'app' / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)
index = target / 'app/ui/index.html'
text = index.read_text()
assert text.count('<script src="app.js">') == 1
index.write_text(text.replace('<script src="app.js">', (stage / 'ui/is6-layers-panel.html').read_text() + '\n<script src="app.js">'), encoding='utf8')
result = {p.relative_to(target / 'app').as_posix(): sha(p) for p in (target / 'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
changed = sorted(p.relative_to(stage).as_posix() for p in staged)
assert sorted(p for p in result if result[p] != files.get(p)) == changed
for path in [Path(__file__), parent, ROOT / 'IS-6-COEXISTENCIA-PRODUTO-K3-CONTRATO.md',
             ROOT / 'scripts/launch-is6-layers-candidate.py', ROOT / 'scripts/start-is6-layers-background.py', *anchors, *staged]:
    sources[path.relative_to(ROOT).as_posix()] = sha(path)
assert all(sha(ROOT / p) == seal for p, seal in sources.items())
r = dict(candidate='0.19.0', accepted=False, promoted=False, source_sha256=sources, files_sha256=result,
         base_manifest=parent.relative_to(ROOT).as_posix(), base_files_sha256=files, changed=changed,
         scope='First coordinated-layer API/UI candidate; frozen science and K1C owner. Own native journeys, visual inspection and profile required. Composite persistence remains pending.')
(target / 'build-manifest.json').write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps(dict(prepared=True, candidate='0.19.0', changed=changed, accepted=False)))
