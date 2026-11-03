"""Real branch records: cache reuse, invalidation, and snapshot isolation."""
from pathlib import Path
import hashlib
import json
import os
import sys
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is6-spatial-product0.18.2/app'
sys.path.insert(0,str(APP))
from is6_laboratory import SpatialLaboratory,artifact
folder=ROOT/'output/is6-catalog-cache-20261102a';receipt=ROOT/'evidence/is6-catalog-cache-20261102a.json'
if folder.exists() or receipt.exists():raise FileExistsError('Preserve evidence')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((APP.parent/'build-manifest.json').read_text());hashes=dict(manifest['source_sha256'])
hashes.update({(APP/n).relative_to(ROOT).as_posix():v for n,v in manifest['files_sha256'].items()})
fixture=ROOT/'output/is6-body-fixtures-20261101a/fixtures-before-execution.json'
for p in [Path(__file__),fixture,APP.parent/'build-manifest.json']:hashes[p.relative_to(ROOT).as_posix()]=sha(p)
assert all(sha(ROOT/n)==v for n,v in hashes.items());folder.mkdir()
with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
    for n in hashes:z.write(ROOT/n,n)
r=dict(accepted=False,completed=False,source_sha256=hashes,scope='Real branch catalog cache only; no native/performance acceptance.')
instrument=None
try:
    phase=json.loads(fixture.read_text())['phases'][0]
    run=artifact.Run.create(phase,dict(body_id=phase['bodies'][0]['id'],source_guard=artifact.body.guard(phase)),artifact.DEFAULT_CONFIGURATION)
    store=artifact.Store(folder/'checkpoints');branch=store.save(run,run.default_view(),name='Primeiro')['branch']['id']
    class Lab:
        def status(self):return dict(mode='experiment',physics=phase)
    instrument=SpatialLaboratory(Lab(),storage=store.folder,native=lambda _:None)
    calls=[0];original=instrument.store.catalog
    def counted():calls[0]+=1;return original()
    instrument.store.catalog=counted
    for _ in range(20):assert instrument._catalog()[0]['name']=='Primeiro'
    assert calls[0]==0
    outside=instrument._catalog();outside[0]['name']='Changed outside';assert instrument._catalog()[0]['name']=='Primeiro'
    path=store.branches/(branch+'.json');before=path.read_bytes();stat=path.stat();bad=json.loads(before);bad['branch']['name']='Alterado sem seal'
    path.write_text(json.dumps(bad));os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns+10**9))
    assert not instrument._catalog()[0]['valid'] and calls[0]==1
    path.write_bytes(before);assert instrument._catalog()[0]['valid'] and calls[0]==2
    second=store.save(run,run.default_view(),name='Segundo',parent=branch)['branch']['id']
    rows=instrument._catalog();assert {p['id'] for p in rows}=={branch,second} and calls[0]==3
    run_restored,v,parent=store.load(second);assert run_restored.payload==run.payload and parent==second
    instrument.close();instrument=None
    assert all(sha(ROOT/n)==v for n,v in hashes.items())
    r.update(accepted=True,completed=True,unchanged_queries=20,full_catalog_reads=3,
             checks=['Unchanged files avoid repeated generation/seal work','Returned catalog does not share mutable state','Changed invalid seal and repair both invalidate cache','New branch appears and full scientific restore still validates'])
except Exception:r['failure']=traceback.format_exc()
finally:
    if instrument:
        try:instrument.close()
        except Exception:r['cleanup_failure']=traceback.format_exc();r['accepted']=False
receipt.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in r.items() if k!='source_sha256'},ensure_ascii=False))
raise SystemExit(0 if r['accepted'] else 1)
