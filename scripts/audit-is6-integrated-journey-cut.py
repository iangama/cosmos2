"""Seal the sequential0.18.5 journey without extending older performance scope."""
from pathlib import Path
import hashlib
import json
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=ROOT/'evidence/is6-integrated-journey-cut-20261102a.json'
folder=ROOT/'output/is6-integrated-journey-cut-20261102a'
if out.exists() or folder.exists():raise FileExistsError('Preserve cut')
paths=[ROOT/('evidence/is6-integrated-journey'+suffix+'-20261102e.json') for suffix in ['', '-visual','-process']]
r,v,p=[json.loads(x.read_text()) for x in paths]
assert all(x['accepted'] and x['completed'] for x in [r,v,p])
assert len(r['groups'])==3 and len(r['refusals'])==7 and len(r['native_cleanup'])==5 and not r['page_errors']
assert len(v['captures'])==v['reviewed_count']==10 and v['captures']==r['captures']
assert p['receipt_sha256']==sha(paths[0]) and p['process_result']==dict(app_exit=0,server_exit=0) and not p['processes_still_running']
assert all(x['layout'][k]['scroll']<=x['layout'][k]['client']+1 for x in r['probe_layouts'] for k in ['panel','probe'])
hashes=dict(r['source_sha256'])
for item in r['captures']:
    for key,seal in [('path','sha256'),('RGB','RGB_sha256')]:hashes[item[key]]=item[seal]
assert all(sha(ROOT/n)==value for n,value in hashes.items())
assert sha(ROOT/'user/sessions/latest.json')==r['owner_sha256']
base=json.loads((ROOT/'output/is6-spatial-product0.18.3/build-manifest.json').read_text())
current=json.loads((ROOT/'output/is6-spatial-product0.18.5/build-manifest.json').read_text())
changed=sorted(n for n,value in current['files_sha256'].items() if base['files_sha256'].get(n)!=value)
assert changed==['ui/is4-particle.js','ui/is5-zone.css','ui/is5-zone.js','ui/is6-spatial.js']
for path in [Path(__file__),*paths]:hashes[path.relative_to(ROOT).as_posix()]=sha(path)
folder.mkdir();report=ROOT/'IS-6-PERCURSO-INTEGRADO-RESULTADO-20261102.md'
snapshot=folder/'report-snapshot.md';snapshot.write_bytes(report.read_bytes())
hashes[snapshot.relative_to(ROOT).as_posix()]=sha(snapshot)
archive=folder/'sequential-sources-and-evidence.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for name in hashes:z.write(ROOT/name,name)
result=dict(accepted=True,completed=True,candidate='0.18.5',promoted=False,source_sha256=hashes,
    groups=3,refusals=7,native_cleanups=5,captures_reviewed=10,process_result=p['process_result'],
    changed_from_0_18_3=changed,owner_sha256=r['owner_sha256'],archive=archive.relative_to(ROOT).as_posix(),archive_sha256=sha(archive),
    scope='Sequential four-force instrument journey and limited UI corrections only. No simultaneous layers, composite checkpoint/migration, own0.18.5 performance or full IS6/v1 acceptance.')
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},ensure_ascii=False))
