"""Freeze the isolated engine correction and evidence; never install or promote."""
from pathlib import Path
import hashlib
import io
import json
import tarfile

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT/'evidence/c212-topic-cleanup-candidate-20261020.tar.gz'
MANIFEST = ROOT/'evidence/c212-topic-cleanup-candidate-frozen-check.json'
assert not DEST.exists() and not MANIFEST.exists()

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(name): return json.loads((ROOT/name).read_bytes())

runtime = read('evidence/built-runtime-topic-cleanup.json')
assert sha(ROOT/'.runtime-topic-cleanup/bin/OpenSpace.exe') == runtime['engine_sha256']
for name, digest in runtime['preserved_sha256'].items(): assert sha(ROOT/name) == digest, name
base = read('evidence/c212-em-cloud-native-candidate-frozen-check.json')
assert sha(ROOT/base['archive']) == base['archive_sha256']
for name, digest in base['files_sha256'].items():
    normalized = name.replace('\\','/')
    if any(normalized.startswith('output/c212-em-cloud-native-product/'+folder+'/') for folder in ('app','em','em-cloud')):
        assert sha(ROOT/normalized) == digest, normalized
baseline = read('evidence/c212-em-candidate-baseline.json')
for name, digest in baseline['installed_app_sha256'].items(): assert sha(ROOT/'app'/name) == digest, name
for name in ('topic-cleanup-native-lifecycle-check', 'em-cloud-helper-topic-cleanup-native-check',
             'em-cloud-helper-topic-cleanup-ui-check', 'em-cloud-helper-topic-cleanup-persistence-resilience-check',
             'em-potential-topic-cleanup-native-ui-check', 'em-potential-topic-cleanup-restart-check'):
    functional = read('evidence/'+name+'.json')
    assert functional['engine_sha256'] == runtime['engine_sha256'] and functional['owner_pointer_preserved']
profiles = ['native-em128-c212mutfixa', 'native-emcloud-c212src128fixa', 'native-em128-c212potfixa']
for name in profiles:
    report = read('evidence/'+name+'.json')
    audit = read('evidence/'+name+'-review.json')
    assert report['completed'] and audit['accepted'] and report['engine_sha256'] == runtime['engine_sha256']
    assert audit['benchmark_sha256'] == sha(ROOT/'evidence'/(name+'.json'))
    archive = ROOT/report['frozen_source_archive']['path']
    assert sha(archive) == report['frozen_source_archive']['sha256']

names = ['evidence/built-runtime-topic-cleanup.json', 'evidence/built-runtime-em-cloud.json',
         'evidence/c212-em-cloud-native-candidate-frozen-check.json',
         'evidence/topic-cleanup-runtime-build-incident.json',
         'evidence/potential-profile-audit-storage-incident.json',
         'evidence/native-em128-c212potfixa-review-attempt1.json',
         'output/review-em128-before-potential-raw-normalization.py',
         'evidence/native-topic-retention-original1.json', 'evidence/native-topic-retention-corrected1.json',
         'evidence/native-topic-retention-corrected-comparison.json', 'evidence/native-topic-retention-diagnosis.json',
         'evidence/topic-cleanup-native-lifecycle-check.json',
         'evidence/em-cloud-helper-topic-cleanup-native-check.json',
         'evidence/em-cloud-helper-topic-cleanup-ui-check.json',
         'evidence/em-cloud-helper-topic-cleanup-ui-visual-review.json',
         'evidence/em-cloud-helper-topic-cleanup-persistence-resilience-check.json',
         'evidence/em-potential-topic-cleanup-native-ui-check.json',
         'evidence/em-potential-topic-cleanup-ui-visual-review.json',
         'evidence/em-potential-topic-cleanup-restart-check.json',
         'evidence/cosmos2-em-cloud-helper-topic-cleanup-ui.png',
         'evidence/cosmos2-em-potential-topic-cleanup-native.png',
         'evidence/cosmos2-em-potential-topic-cleanup-canvas.png',
         'evidence/em-cloud-source128-strong-fixture-rejection.json',
         '.runtime-topic-cleanup/bin/OpenSpace.exe', runtime['patch'],
         'scripts/build-topic-cleanup-runtime.ps1', 'scripts/stage-topic-cleanup-runtime.py',
         'scripts/start-c212-topic-cleanup-candidate.ps1', 'scripts/verify-topic-cleanup-native.py',
         'scripts/diagnose-native-topic-retention.py', 'scripts/cef_page.py',
         'scripts/benchmark-em128-new-runtime-native.py', 'scripts/benchmark-em128-potential-native.py',
         'scripts/review-em128-new-runtime-benchmark.py', 'scripts/collect-em128-candidate-gpu-memory.ps1',
         'scripts/collect-em-potential-gpu-memory.ps1', 'scripts/benchmark-em-cloud-source128-native.py',
         'scripts/review-em-cloud-source128-benchmark.py', 'scripts/collect-em-cloud-gpu-memory.ps1',
         'scripts/verify-em-cloud-helper-native.py', 'scripts/verify-em-cloud-helper-ui.py',
         'scripts/verify-em-cloud-helper-persistence-resilience.py',
         'scripts/verify-em-potential-native-ui.py', 'scripts/verify-em-potential-restart.py',
         'output/c212-topic-cleanup-before/preserved-sha256.json',
         'output/c212-topic-cleanup-before/cef_page-before-navigation-fix.py',
         'output/c212-topic-cleanup-before/diagnose-native-topic-retention-original1.py']
for source in runtime['changed_source_sha256']:
    names += ['.upstream/openspace/'+source, 'output/c212-topic-cleanup-before/'+source]
references = {base['archive']: base['archive_sha256']}
for profile in profiles:
    names += ['evidence/'+profile+'.json', 'evidence/'+profile+'-review.json']
    report = read('evidence/'+profile+'.json')
    references[report['frozen_source_archive']['path'].replace('\\','/')] = report['frozen_source_archive']['sha256']
    names += [run['gpu_report'].replace('\\','/') for run in report['runs']]
names.append(str(Path(__file__).relative_to(ROOT)).replace('\\','/'))
files = {name: sha(ROOT/name) for name in sorted(set(names))}
readme = ('Cosmos2 C2-12: isolated completed-topic lifecycle correction.\n'
          'Same frozen helperE app/science; separate engine e3759077.\n'
          'Completed Lua topics retired at next preSync; pending callbacks and active subscriptions preserved.\n'
          'Three independently audited formal profiles:128 mutual charges,10k plus128weak static sources,128 plus1089 potential samples.\n'
          'Native/CEF controls, exact restart/future and lost-ACK recovery checked.\n'
          'Scientific limits and old failures remain; intense-source coarse steps rejected.\n'
          'No installed promotion, arbitrary-field throughput, planetary fields, GR mesh or whole C2-12 acceptance.\n'
          'This archive freezes the engine correction/evidence. Frozen base app and full per-profile source archives are referenced by SHA256.\n')
with tarfile.open(DEST,'w:gz') as tar:
    for name, digest in files.items():
        data = (ROOT/name).read_bytes(); assert hashlib.sha256(data).hexdigest() == digest
        member = tarfile.TarInfo(name); member.size = len(data); tar.addfile(member,io.BytesIO(data))
    for name, data in [('README.txt',readme.encode()), ('referenced-artifacts.json',(json.dumps(references,indent=2)+'\n').encode())]:
        member = tarfile.TarInfo(name);member.size=len(data);tar.addfile(member,io.BytesIO(data))
manifest = {'status':'isolated_completed_topic_cleanup_runtime_and_three_declared_profiles_frozen',
            'archive':str(DEST.relative_to(ROOT)), 'archive_sha256':sha(DEST), 'files_sha256':files,
            'referenced_artifacts_sha256':references, 'engine_sha256':runtime['engine_sha256'],
            'installed_product_files_preserved':len(baseline['installed_app_sha256']),
            'owner_pointer_preserved':True, 'promotion':False, 'scope':readme}
MANIFEST.write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'archive':str(DEST),'sha256':manifest['archive_sha256'],'files':len(files)}),flush=True)
