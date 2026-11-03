"""One-file UI refinement; preserve every executed 0.19.0 source."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
base = ROOT / 'output/is6-layers-product0.19.0'
target = ROOT / 'output/is6-layers-product0.19.1'
stage = ROOT / 'output/is6-layers-product-staging-b'
if target.exists():
    raise FileExistsError('Preserve candidate')
parent = base / 'build-manifest.json'
m = json.loads(parent.read_text())
assert {p.relative_to(base/'app').as_posix():sha(p) for p in (base/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts} == m['files_sha256']
sources = dict(m['source_sha256'])
anchors = [ROOT/'evidence/is6-layers-native-20261103a.json', ROOT/'evidence/is6-layers-native-process-20261103a.json']
for p in anchors:
    r = json.loads(p.read_text())
    assert r['accepted'] and r['completed']
    sources.update(r['source_sha256'])
visual = ROOT/'evidence/is6-layers-visual-20261103a.json'
v = json.loads(visual.read_text())
assert v['completed'] and v['reviewed_count'] == 4 and v['accepted'] is False
assert all(sha(ROOT/p) == seal for p,seal in sources.items())
shutil.copytree(base/'app', target/'app', ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
shutil.copy2(stage/'ui/is6-layers.js', target/'app/ui/is6-layers.js')
files = {p.relative_to(target/'app').as_posix():sha(p) for p in (target/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
assert sorted(p for p in files if files[p] != m['files_sha256'].get(p)) == ['ui/is6-layers.js']
for p in [Path(__file__), parent, visual, *anchors, stage/'ui/is6-layers.js', ROOT/'IS-6-COEXISTENCIA-PRODUTO-REVISAO-B.md',
          ROOT/'scripts/launch-is6-layers-candidate-v2.py', ROOT/'scripts/start-is6-layers-background-v2.py']:
    sources[p.relative_to(ROOT).as_posix()] = sha(p)
r = dict(candidate='0.19.1', accepted=False, promoted=False, files_sha256=files, source_sha256=sources,
         base_manifest=parent.relative_to(ROOT).as_posix(), base_files_sha256=m['files_sha256'], changed=['ui/is6-layers.js'],
         scope='Clock-deficit readout only; own six-image journey required. Science, service, renderer and native owner unchanged. No final UI profile or composite persistence acceptance.')
(target/'build-manifest.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(prepared=True,candidate='0.19.1',changed=['ui/is6-layers.js'],accepted=False)))
