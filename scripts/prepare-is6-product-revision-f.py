"""Build a separate four-file UI revision, preserving every accepted source."""
from pathlib import Path
import hashlib
import json
import shutil
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=ROOT/'output/is6-spatial-product0.18.4';target=ROOT/'output/is6-spatial-product0.18.5'
if target.exists():raise FileExistsError('Preserve candidate')
parent=base/'build-manifest.json';m=json.loads(parent.read_text())
assert all(sha(ROOT/n)==v for n,v in m['source_sha256'].items())
assert {p.relative_to(base/'app').as_posix():sha(p) for p in (base/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}==m['files_sha256']
visual=ROOT/'evidence/is6-journey-layout-diagnostic-20261102a.json';v=json.loads(visual.read_text());assert v['completed'] and v['observation']['panel']['scroll']>v['observation']['panel']['client']
shutil.copytree(base/'app',target/'app',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
changed=['ui/is5-zone.css']
stage=ROOT/'output/is6-product-staging-f'
for name in changed:shutil.copy2(stage/name,target/'app'/name)
files={p.relative_to(target/'app').as_posix():sha(p) for p in (target/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
assert sorted(n for n in files if files[n]!=m['files_sha256'].get(n))==changed
sources=dict(m['source_sha256'])
for p in [Path(__file__),parent,visual,ROOT/'IS-6-PRODUTO-REVISAO-F.md',ROOT/'scripts/launch-is6-spatial-revision-f.py',*[stage/n for n in changed]]:sources[p.relative_to(ROOT).as_posix()]=sha(p)
assert all(sha(ROOT/n)==v for n,v in sources.items())
r=dict(candidate='0.18.5',accepted=False,promoted=False,files_sha256=files,source_sha256=sources,base_files_sha256=m['files_sha256'],base_manifest=parent.relative_to(ROOT).as_posix(),changed=changed,scope='One CSS revision after four UI files; own integrated journey and visual verification required. Science/services/renderer unchanged. Existing profile evidence keeps its original candidate scope.')
(target/'build-manifest.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(prepared=True,candidate='0.18.5',changed=changed,accepted=False)))
