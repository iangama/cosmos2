"""Consolidate separate spatial-cut and lifecycle evidence without version promotion."""
from pathlib import Path
import hashlib
import json
import shutil
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
folder=ROOT/'output/is6-spatial-cut-20261102a';out=ROOT/'evidence/is6-spatial-cut-20261102a.json'
if folder.exists() or out.exists():raise FileExistsError('Preserve consolidated evidence')
folder.mkdir()
gates={'baseline_service':'is6-product-service-20261102d.json','catalog_cache':'is6-catalog-cache-20261102a.json',
       'baseline_native':'is6-product-native-20261102f.json','baseline_visual':'is6-product-visual-review-20261102f.json',
       'baseline_persistence':'is6-persistence-native-20261102b.json','baseline_persistence_visual':'is6-persistence-visual-20261102b.json',
       'baseline_profile':'is6-spatial-profile-audit-20261102c.json','revised_service':'is6-product-service-20261102e.json',
       'revised_active_shutdown':'is6-active-shutdown-20261102b.json'}
r=dict(accepted=False,completed=False,baseline_candidate='0.18.2',lifecycle_candidate='0.18.3',promoted=False,
       derivative_has_own_performance_run=False,gate_receipts={},
       scope='First isolated spatial-reference cut0.18.2 plus separate lifecycle correction0.18.3. No full IS6, joint journey, simultaneous layers, composite persistence, derived0.18.3 frame profile, independent release package or promotion acceptance.')
try:
    hashes={Path(__file__).relative_to(ROOT).as_posix():sha(Path(__file__))};data={}
    for key,name in gates.items():
        path=ROOT/'evidence'/name;value=json.loads(path.read_text());assert value['accepted'],name
        data[key]=value;r['gate_receipts'][key]=dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path))
        for n,v in value.get('source_sha256',{}).items():
            assert n not in hashes or hashes[n]==v,n
            hashes[n]=v
        hashes[path.relative_to(ROOT).as_posix()]=sha(path)
    base=ROOT/'output/is6-spatial-product0.18.2';revised=ROOT/'output/is6-spatial-product0.18.3'
    manifests=[]
    for candidate in [base,revised]:
        path=candidate/'build-manifest.json';manifest=json.loads(path.read_text());assert not manifest['promoted']
        actual={p.relative_to(candidate/'app').as_posix():sha(p) for p in (candidate/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        assert actual==manifest['files_sha256']
        manifests.append(manifest);hashes[path.relative_to(ROOT).as_posix()]=sha(path)
    before,after=[m['files_sha256'] for m in manifests]
    assert set(before)==set(after)
    differences=sorted(n for n in before if before[n]!=after[n]);assert differences==['is6_laboratory.py','server.py']
    assert all(before[n]==after[n] for n in before if n.startswith('ui/'))
    lifecycle=data['revised_active_shutdown'];assert lifecycle['completed'] and lifecycle['process_result']==dict(app_exit=0,server_exit=0) and not lifecycle['processes_still_running'] and lifecycle['elapsed_s']<=20
    profile=data['baseline_profile'];raw_path=ROOT/profile['profile'];assert sha(raw_path)==profile['profile_sha256']
    raw=json.loads(raw_path.read_text());assert raw['completed'] and not raw.get('failure') and not raw.get('cleanup_failure')
    assert raw['session']['serverScript'].replace('\\','/').endswith('/output/is6-spatial-product0.18.2/app/server.py')
    assert len(profile['runs'])==4 and profile['exact_samples']==272
    owner=sha(ROOT/'user/sessions/latest.json');assert all(d['owner_sha256']==owner for d in data.values() if 'owner_sha256' in d)
    for p in [raw_path,ROOT/'IS-6-PRODUTO-REVISAO-D.md']:
        hashes[p.relative_to(ROOT).as_posix()]=sha(p)
    report=folder/'report-snapshot.md';shutil.copy2(ROOT/'IS-6-MALHA-PRODUTO-RESULTADO-20261102.md',report)
    hashes[report.relative_to(ROOT).as_posix()]=sha(report)
    assert all(sha(ROOT/n)==v for n,v in hashes.items())
    archive=folder/'consolidated-sources-and-receipts.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r.update(accepted=True,completed=True,source_sha256=hashes,archive_sha256=sha(archive),owner_sha256=owner,
             changed_in_lifecycle_revision=differences,UI_files_identical=True,baseline_frames=sum(w['frames'] for w in profile['runs']),
             baseline_exact_samples=profile['exact_samples'],baseline_RAM_peak_GiB=profile['RAM_peak_GiB'],baseline_GPU_peak_GiB=profile['GPU_peak_GiB'],
             revised_active_shutdown_elapsed_s=lifecycle['elapsed_s'])
except Exception:r['failure']=traceback.format_exc()
out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k not in {'source_sha256','gate_receipts'}},ensure_ascii=False))
raise SystemExit(0 if r['accepted'] else 1)
