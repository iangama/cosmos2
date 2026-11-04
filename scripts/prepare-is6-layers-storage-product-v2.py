"""Prepare 0.20.1 with readable storage buttons; preserve executed 0.20.0."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=ROOT/'output/is6-layers-product0.20.0';target=ROOT/'output/is6-layers-product0.20.1'
if target.exists():raise FileExistsError('Preserve candidate')
parent=base/'build-manifest.json';m=json.loads(parent.read_text())
files={p.relative_to(base/'app').as_posix():sha(p) for p in (base/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
assert files==m['files_sha256']
shutil.copytree(base/'app',target/'app',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for name in ['ui/is6-layers-panel.html','ui/index.html']:
 p=target/'app'/name;s=p.read_text()
 for ident in ['layers-save','layers-load']:
  old=f'<button id="{ident}" type="button">';new=f'<button id="{ident}" class="wide" type="button">'
  assert s.count(old)==1;s=s.replace(old,new,1)
 p.write_text(s,encoding='utf8')
newfiles={p.relative_to(target/'app').as_posix():sha(p) for p in (target/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
changed=sorted(k for k in newfiles if newfiles[k]!=files[k]);assert changed==['ui/index.html','ui/is6-layers-panel.html']
sources=dict(m['source_sha256']);sources[parent.relative_to(ROOT).as_posix()]=sha(parent);sources[Path(__file__).relative_to(ROOT).as_posix()]=sha(Path(__file__))
assert all(sha(ROOT/k)==v for k,v in sources.items())
result=dict(candidate='0.20.1',accepted=False,promoted=False,source_sha256=sources,files_sha256=newfiles,base_manifest=parent.relative_to(ROOT).as_posix(),base_files_sha256=files,changed=changed,scope='Contrast correction only; native functional/visual/restart/performance acceptance all pending for this exact candidate. Preserve 0.20.0 evidence.')
(target/'build-manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(prepared=True,candidate='0.20.1',changed=changed,accepted=False)))
