"""Build the isolated 0.20.0 compound-store candidate from frozen components."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=ROOT/'output/is6-layers-product0.19.1';target=ROOT/'output/is6-layers-product0.20.0'
stage=ROOT/'output/is6-layers-product-staging-k4';io=ROOT/'output/is6-layers-persistence-staging'
if target.exists():raise FileExistsError('Preserve candidate')
parent=base/'build-manifest.json';m=json.loads(parent.read_text())
assert {p.relative_to(base/'app').as_posix():sha(p) for p in (base/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}==m['files_sha256']
anchors=[ROOT/'evidence/is6-layers-product-cut-20261103b.json',ROOT/'evidence/is6-layers-profile-audit-20261104a.json',
         ROOT/'evidence/is6-layers-profile-process-20261104a.json',ROOT/'evidence/is6-layers-store-20261104a.json',
         ROOT/'evidence/is6-layers-service-admission-20261104b.json']
sources=dict(m['source_sha256'])
for path in anchors:
    r=json.loads(path.read_text());assert r['accepted'],path;sources.update(r.get('source_sha256',{}))
profile=ROOT/'evidence/is6-layers-profile-20261104a.json';r=json.loads(profile.read_text());assert r['completed'] and not r.get('failure') and not r.get('cleanup_failure')
sources.update(r['source_sha256']);sources[profile.relative_to(ROOT).as_posix()]=sha(profile)
assert all(sha(ROOT/p)==seal for p,seal in sources.items())
shutil.copytree(base/'app',target/'app',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
staged=[p for p in stage.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
for path in staged:
    dest=target/'app'/path.relative_to(stage);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
io_files=[io/name for name in ['is6_layers_checkpoint_v2.py','is6_layers_store.py','is6_layers_saved_scene.py']]
for path in io_files:shutil.copy2(path,target/'app'/path.name)
index=target/'app/ui/index.html';text=index.read_text();old=(base/'app/ui/is6-layers-panel.html').read_text()
assert text.count(old)==1;index.write_text(text.replace(old,(stage/'ui/is6-layers-panel.html').read_text(),1),encoding='utf8')
files={p.relative_to(target/'app').as_posix():sha(p) for p in (target/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
changed=sorted(p for p in files if files[p]!=m['files_sha256'].get(p))
assert changed==sorted(['is6_layers_laboratory.py','is6_layers_checkpoint_v2.py','is6_layers_store.py','is6_layers_saved_scene.py','ui/index.html','ui/is6-layers-panel.html','ui/is6-layers.js'])
for path in [Path(__file__),parent,*anchors,*staged,*io_files,ROOT/'IS-6-COEXISTENCIA-PERSISTENCIA-NATIVA-K4-CONTRATO.md',
             ROOT/'scripts/launch-is6-layers-storage-candidate.py',ROOT/'scripts/start-is6-layers-storage-background.py']:
    sources[path.relative_to(ROOT).as_posix()]=sha(path)
assert all(sha(ROOT/p)==seal for p,seal in sources.items())
manifest=dict(candidate='0.20.0',accepted=False,promoted=False,source_sha256=sources,files_sha256=files,base_manifest=parent.relative_to(ROOT).as_posix(),
              base_files_sha256=m['files_sha256'],changed=changed,scope='Compound store/service/UI candidate; own native save/restart/visual/profile required. No implicit legacy migration, promotion or full IS6/v1 acceptance.')
(target/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(prepared=True,candidate='0.20.0',changed=changed,accepted=False)))
