"""Consolidate only the accepted functional/visual 0.19.1 slice."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=ROOT/'evidence/is6-layers-product-cut-20261103b.json'
if out.exists():raise FileExistsError('Preserve consolidated evidence')
receipts=[ROOT/'evidence/is6-layers-native-20261103b.json',ROOT/'evidence/is6-layers-visual-20261103b.json',
          ROOT/'evidence/is6-layers-native-process-20261103b.json']
sources={}
for path in receipts:
    r=json.loads(path.read_text())
    assert r['accepted'] and r['completed']
    for name,seal in r['source_sha256'].items():
        assert name not in sources or sources[name]==seal
        sources[name]=seal
    sources[path.relative_to(ROOT).as_posix()]=sha(path)
sources[Path(__file__).relative_to(ROOT).as_posix()]=sha(Path(__file__))
manifest_path=ROOT/'output/is6-layers-product0.19.1/build-manifest.json'
m=json.loads(manifest_path.read_text());assert m['candidate']=='0.19.1' and not m['promoted']
app=manifest_path.parent/'app'
actual={p.relative_to(app).as_posix():sha(p) for p in app.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
assert actual==m['files_sha256']
assert all(sha(ROOT/n)==seal for n,seal in sources.items())
native=json.loads(receipts[0].read_text());visual=json.loads(receipts[1].read_text())
assert len(native['cases'])==2 and len(native['refusals'])==14 and len(visual['captures'])==6
assert any(a['cancel_reply'] and a['create_reply']['status']==400 for a in native['cancellation_attempts'])
assert sha(ROOT/'user/sessions/latest.json')==native['owner_sha256']
result=dict(accepted=True,completed=True,candidate='0.19.1',promoted=False,source_sha256=sources,
    receipts=[p.relative_to(ROOT).as_posix() for p in receipts],bodies=2,visibility_combinations=8,refusals=14,reviewed_images=6,
    owner_sha256=native['owner_sha256'],
    scope='Functional/visual coordinated-layer slice only. No final UI profile, composite persistence, migration, promotion or whole IS6/v1 acceptance.')
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'}))
