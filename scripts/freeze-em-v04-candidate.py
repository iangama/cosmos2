"""Freeze verified EM0.4 candidate, receipts and exact test/build sources."""
from pathlib import Path
import hashlib
import io
import json
import tarfile

ROOT=Path(__file__).resolve().parents[1];CANDIDATE=ROOT/'output/c212-em-v04-product'
archive=ROOT/'evidence/c212-em-v04-candidate-20261018.tar.gz'
manifest=ROOT/'evidence/c212-em-v04-candidate-frozen-check.json'
if archive.exists() or manifest.exists():raise ValueError('Preserve the previous frozen candidate')
names=('em-v04-kernel-check.json','em-v04-mutual-dynamics-check.json','em-v04-prepared-check.json',
       'em-v04-editor-candidate-ui-check.json','em-v04-native-scene-check.json','em-v04-native-resilience-check.json',
       'em-v04-lines-native-ui-check.json','em-v04-restart-check.json','em-v04-editor-visual-review.json',
       'native-em128-c212em04a-review.json')
files={};receipt_hashes={}
def add(path,expected=None):
    path=Path(str(path).replace('\\','/'));path=path if path.is_absolute() else ROOT/path
    name=str(path.relative_to(ROOT)).replace('\\','/');data=path.read_bytes();digest=hashlib.sha256(data).hexdigest()
    if expected is not None and digest!=expected:raise ValueError('Receipt does not match current bytes: '+name)
    if name in files and files[name][1]!=digest:raise ValueError('Conflicting source digests: '+name)
    files[name]=(data,digest)
for name in names:
    path=ROOT/'evidence'/name;record=json.loads(path.read_bytes());add(path);receipt_hashes[name]=files[str(path.relative_to(ROOT)).replace('\\','/')][1]
    for source,digest in record.get('source_sha256',{}).items():add(source,digest)
    if 'javascript_errors' in record:assert record['javascript_errors']==[]
    if name=='native-em128-c212em04a-review.json':
        assert record['accepted'] and record['three_EM128_routes_measured_and_integrity_verified']
        add(record['benchmark'],record['benchmark_sha256']);add(record['frozen_source_archive']['path'],record['frozen_source_archive']['sha256'])
        benchmark=json.loads((ROOT/record['benchmark']).read_bytes())
        for run in benchmark['runs']:add(run['gpu_report'],run['gpu_sha256'])
    if name=='em-v04-editor-visual-review.json':assert record['reviewed'];add(record['image'],record['sha256'])
for folder in ('app','em'):
    for path in (CANDIDATE/folder).rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix!='.pyc':add(path)
for path in (CANDIDATE/'LEIA-CANDIDATA.md',ROOT/'scripts/start-c212-em-v04-candidate.ps1',ROOT/'scripts/build-em-pair-kernel.ps1',ROOT/'output/c212-em-native-kernel-staging/CMakeLists.txt',ROOT/'scripts/review-em128-benchmark.py',Path(__file__)):add(path)
baseline=json.loads((ROOT/'evidence/c212-em-candidate-baseline.json').read_bytes())
for name,digest in baseline['installed_app_sha256'].items():assert hashlib.sha256((ROOT/'app'/name).read_bytes()).hexdigest()==digest,name
assert hashlib.sha256((ROOT/'user/sessions/latest.json').read_bytes()).hexdigest()==baseline['owner_sha256']
with tarfile.open(archive,'w:gz') as tar:
    for name,(data,digest) in sorted(files.items()):
        member=tarfile.TarInfo(name);member.size=len(data);tar.addfile(member,io.BytesIO(data))
# Inspect the actual archive, not just its construction inputs.
with tarfile.open(archive,'r:gz') as tar:
    assert {m.name for m in tar.getmembers()}==set(files)
    for name,(_,digest) in files.items():assert hashlib.sha256(tar.extractfile(name).read()).hexdigest()==digest,name
report={'status':'separate_EM0_4_functional_candidate_and_EM128_native_profile_frozen',
        'archive':str(archive.relative_to(ROOT)),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
        'files_sha256':{name:digest for name,(_,digest) in sorted(files.items())},'receipts_sha256':receipt_hashes,
        'installed_product_files_preserved':len(baseline['installed_app_sha256']),'owner_pointer_preserved':True,
        'scope':'Candidate0.4 and its fixed128-charge profile only. No installed promotion,10k EM, potential overlay, planetary catalogue, GR mesh or completeC2-12 acceptance. Separate archives preserve0.2/0.3; owner checkpoint contents are not included.'}
manifest.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('files_sha256','receipts_sha256')},indent=2))
