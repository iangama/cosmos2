"""Freeze numeric timing candidate after its own three profiles; never install."""
from pathlib import Path
import hashlib
import io
import json
import tarfile

ROOT=Path(__file__).resolve().parents[1];CANDIDATE=ROOT/'output/c212-em-time-product'
DEST=ROOT/'evidence/c212-em-time-candidate-20261021.tar.gz'
MANIFEST=ROOT/'evidence/c212-em-time-candidate-frozen-check.json'
assert not DEST.exists() and not MANIFEST.exists()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(name):return json.loads((ROOT/name).read_bytes())

runtime=read('evidence/built-runtime-topic-cleanup.json');assert sha(ROOT/'.runtime-topic-cleanup/bin/OpenSpace.exe')==runtime['engine_sha256']
for name,digest in runtime['preserved_sha256'].items():assert sha(ROOT/name)==digest,name
base=read('evidence/c212-em-cloud-native-candidate-frozen-check.json')
for name,digest in base['files_sha256'].items():
    normalized=name.replace('\\','/')
    if normalized.startswith('output/c212-em-cloud-native-product/'):
        assert sha(ROOT/normalized)==digest,normalized
baseline=read('evidence/c212-em-candidate-baseline.json')
for name,digest in baseline['installed_app_sha256'].items():assert sha(ROOT/'app'/name)==digest,name
functional=['em-time-worker-revised-check','em-time-native-ui-release-check','em-time-restart-resilience-check']
for name in functional:
    report=read('evidence/'+name+'.json');assert report['owner_pointer_preserved']
    for source,digest in report['source_sha256'].items():
        candidate=ROOT/source.replace('\\','/')
        if source.replace('\\','/')=='scripts/verify-em-time-native-ui.py':candidate=ROOT/'output/em-time-native-ui-release-source.py'
        assert sha(candidate)==digest,source
profiles=['native-em128-c212time128a','native-em128-c212timepota','native-emcloud-c212timesrcc','native-emcloud-c212timesrcd']
for name in profiles:
    raw=read('evidence/'+name+'.json');review=read('evidence/'+name+'-review.json')
    assert raw['completed'] and review['accepted'] and raw['engine_sha256']==runtime['engine_sha256']
    assert sha(ROOT/'evidence'/(name+'.json'))==review['benchmark_sha256']
    assert sha(ROOT/raw['frozen_source_archive']['path'])==raw['frozen_source_archive']['sha256']
    for name,digest in raw['configuration_sha256'].items():
        normalized=name.replace('\\','/')
        if any(normalized.startswith('output/c212-em-time-product/'+folder+'/') for folder in ('app','em','em-cloud')):
            assert sha(ROOT/normalized)==digest,normalized

files=[p for folder in ('app','em','em-cloud')for p in (CANDIDATE/folder).rglob('*')if p.is_file() and '__pycache__'not in p.parts]
names=['evidence/built-runtime-topic-cleanup.json','evidence/c212-topic-cleanup-candidate-frozen-check.json',
       'evidence/c212-em-cloud-native-candidate-frozen-check.json','evidence/em-time-candidate-prepared.json',
       'evidence/em-time-controls-ui-visual-review.json','evidence/cosmos2-em-time-controls-ui-release.png',
       'evidence/em-cloud-source128-intense-refinement-frozen-check.json',
       'evidence/native-emcloud-c212timesrca-interrupted-source-check.json',
       'evidence/native-emcloud-c212timesrcb.json','evidence/native-emcloud-c212timesrcb-review.json',
       'evidence/em-cloud-live-rate-afterb1.json','evidence/em-cloud-live-rate-afterb2.json',
       'evidence/em-cloud-thread-scaling-afterb1.json','output/em-cloud-live-rate-afterb1-source.py',
       'scripts/diagnose-em-cloud-live-rate.py','scripts/diagnose-em-cloud-thread-scaling.py',
       'scripts/prepare-em-time-candidate.py','scripts/start-c212-em-time-candidate.ps1',
       'scripts/verify-em-time-worker.py','scripts/verify-em-time-native-ui.py','scripts/verify-em-time-restart-resilience.py',
       'scripts/benchmark-em128-new-runtime-native.py','scripts/benchmark-em128-potential-native.py',
       'scripts/review-em128-new-runtime-benchmark.py','scripts/benchmark-em-cloud-source128-native.py',
       'scripts/review-em-cloud-source128-benchmark.py','scripts/collect-em128-candidate-gpu-memory.ps1',
       'scripts/collect-em-potential-gpu-memory.ps1','scripts/collect-em-cloud-gpu-memory.ps1',
       'scripts/cef_page.py','output/em-time-native-ui-release-source.py',
       'output/c212-em-time-restart-expected.json',str(Path(__file__).relative_to(ROOT)).replace('\\','/')]
names += ['evidence/'+name+'.json'for name in functional]
names += [str(p.relative_to(ROOT)).replace('\\','/')for p in files]
names += ['output/c212-em-time-product/c212-em-worker/product/ui-phase'+suffix for suffix in ('.json','.view.json','.timing.json')]
references={}
for receipt_name in ('evidence/c212-topic-cleanup-candidate-frozen-check.json','evidence/c212-em-cloud-native-candidate-frozen-check.json','evidence/em-cloud-source128-intense-refinement-frozen-check.json','evidence/native-emcloud-c212timesrca-interrupted-source-check.json'):
    receipt=read(receipt_name);assert sha(ROOT/receipt['archive'])==receipt['archive_sha256'];references[receipt['archive']]=receipt['archive_sha256']
failed=read('evidence/native-emcloud-c212timesrcb.json');rejection=read('evidence/native-emcloud-c212timesrcb-review.json')
assert failed['completed'] and not rejection['accepted']
assert sha(ROOT/'evidence/native-emcloud-c212timesrcb.json')==rejection['benchmark_sha256']
assert sha(ROOT/failed['frozen_source_archive']['path'])==failed['frozen_source_archive']['sha256']
references[failed['frozen_source_archive']['path']]=failed['frozen_source_archive']['sha256']
for name in profiles:
    raw=read('evidence/'+name+'.json');names += ['evidence/'+name+'.json','evidence/'+name+'-review.json']
    names += [run['gpu_report'].replace('\\','/')for run in raw['runs']]
    references[raw['frozen_source_archive']['path'].replace('\\','/')]=raw['frozen_source_archive']['sha256']
digests={name:sha(ROOT/name)for name in sorted(set(names))}
description=('Cosmos2 C2-12 partial candidate: numeric timestep, requested/effective rate and manual step.\n'
             'Scientific core0.4 unchanged. Execution protocol2 identifies worker/timing helper separately.\n'
             'Numeric step edits preserve phase/editor/conservation reference; bounded64-event numeric history.\n'
             'Sealed preferences preflighted before physical restore; legacy default rate1 explicit.\n'
             'Save reports checkpoint/view/time preferences separately; real partial I/O failures tested.\n'
             'Three declared profiles independently audited;128-body profiles include full64-event history.\n'
             'Cloud profiles C and D both required, including a fresh process and subsequent process reuse.\n'
             'Earlier cloud B remains rejected at rate0.843525526 on route2. Cause not established; not reproduced in two45s diagnostics.\n'
             'These are bounded captured-profile acceptances, not a guarantee against scheduling stalls or full robustness acceptance.\n'
             'No installed promotion,10k intense-source throughput, arbitrary-source geometry, planetary/GR or whole C2-12 acceptance.\n')
with tarfile.open(DEST,'w:gz')as tar:
    for name,digest in digests.items():
        data=(ROOT/name).read_bytes();assert hashlib.sha256(data).hexdigest()==digest
        entry=tarfile.TarInfo(name);entry.size=len(data);tar.addfile(entry,io.BytesIO(data))
    for name,data in [('README.txt',description.encode()),('referenced-artifacts.json',(json.dumps(references,indent=2)+'\n').encode())]:
        entry=tarfile.TarInfo(name);entry.size=len(data);tar.addfile(entry,io.BytesIO(data))
manifest={'status':'numeric_timing_candidate_three_profiles_and_functional_proofs_frozen','archive':str(DEST.relative_to(ROOT)),
          'archive_sha256':sha(DEST),'files_sha256':digests,'referenced_artifacts_sha256':references,
          'installed_product_files_preserved':len(baseline['installed_app_sha256']),'owner_pointer_preserved':True,'promotion':False,'scope':description}
MANIFEST.write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'archive':str(DEST),'sha256':manifest['archive_sha256'],'files':len(digests)}),flush=True)
