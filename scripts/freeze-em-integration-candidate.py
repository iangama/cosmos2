"""Freeze separate G only after its own functional, visual and native profiles."""
from pathlib import Path
import hashlib
import io
import json
import tarfile

ROOT=Path(__file__).resolve().parents[1];G=ROOT/'output/c212-em-integration-product'
DEST=ROOT/'evidence/c212-em-integration-candidate-20261021.tar.gz'
MANIFEST=ROOT/'evidence/c212-em-integration-candidate-frozen-check.json'
assert not DEST.exists() and not MANIFEST.exists()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(name):return json.loads((ROOT/name).read_bytes())

base=read('evidence/c212-em-time-candidate-frozen-check.json')
assert sha(ROOT/base['archive'])==base['archive_sha256']
for name,digest in base['files_sha256'].items():
    normalized=name.replace('\\','/')
    for folder in ('em','em-cloud'):
        prefix='output/c212-em-time-product/'+folder+'/'
        if normalized.startswith(prefix):
            assert sha(ROOT/normalized)==digest,name
            assert sha(G/folder/normalized[len(prefix):])==digest,name
baseline=read('evidence/c212-em-candidate-baseline.json')
for name,digest in baseline['installed_app_sha256'].items():assert sha(ROOT/'app'/name)==digest,name
assert sha(ROOT/'user/sessions/latest.json')=='ee9c4cc86e0696afde128ec319f98f6ad5b3932f27f8b5bd6a25d57a4025b825'

functional=['em-integration-measurements-polish1-check','em-integration-native-ui-release2-check',
            'em-integration-navigation-release1-check','em-integration-restart-check']
for name in functional:
    r=read('evidence/'+name+'.json')
    if name.startswith('em-integration-measurements'):assert len(r['checks'])==20 and r['snapshot_preserved']
    elif name=='em-integration-restart-check':assert r['scientific_future_exact'] and r['saved_native_camera_restored'] and r['owner_pointer_preserved']
    else:assert r['completed'] and not r['JS_errors'] and r['owner_pointer_preserved']
    for source,digest in r['source_sha256'].items():assert sha(ROOT/source)==digest,source
oracle=read('output/em-integration-restart-expected.json')
for ending,digest in oracle['files_sha256'].items():assert sha(G/'c212-em-worker/product'/('ui-phase'+ending))==digest
visual=read('evidence/em-integration-workspace-visual-review.json')
for name,digest in visual['screenshots_sha256'].items():assert sha(ROOT/'evidence'/name)==digest

runtime=read('evidence/built-runtime-topic-cleanup.json')
assert sha(ROOT/'.runtime-topic-cleanup/bin/OpenSpace.exe')==runtime['engine_sha256']
profiles=['native-em128-c212g128a','native-em128-c212gpota','native-emcloud-c212gsrca']
references={base['archive']:base['archive_sha256']}
names=['evidence/c212-em-time-candidate-frozen-check.json','evidence/built-runtime-topic-cleanup.json',
       'evidence/em-integration-candidate-prepared.json','evidence/em-integration-workspace-prepared.json',
       'evidence/em-integration-polish-prepared.json','evidence/em-integration-workspace-visual-review.json',
       'output/em-integration-restart-expected.json','output/c212-em-integration-product/LEIA-CANDIDATA.md',
       'evidence/em-integration-native-ui-initial-check.json','output/em-integration-native-ui-initial-source.py',
       'evidence/em-integration-navigation-initial-check.json','output/em-integration-navigation-initial-source.py',
       'evidence/em-integration-restart-initial-attempt.json','output/em-integration-restart-initial-source.py',
       'scripts/prepare-em-integration-candidate.py','scripts/refine-em-integration-workspace.py',
       'scripts/refine-em-integration-polish.py','scripts/start-c212-em-integration-candidate.ps1',
       'scripts/verify-em-integration-measurements.py','scripts/verify-em-integration-native-ui.py',
       'scripts/verify-em-integration-navigation.py','scripts/verify-em-integration-restart.py',
       'scripts/benchmark-em128-new-runtime-native.py','scripts/benchmark-em128-potential-native.py',
       'scripts/benchmark-em-cloud-source128-native.py','scripts/review-em128-new-runtime-benchmark.py',
       'scripts/review-em-cloud-source128-benchmark.py','scripts/cef_page.py',
       'C2-12-INTEGRACAO.md','C2-12-DIAGNOSTICO-TAXA-20261021.md',
       str(Path(__file__).relative_to(ROOT)).replace('\\','/')]
polish=read('evidence/em-integration-polish-prepared.json')
assert sha(ROOT/polish['before_archive'])==polish['before_archive_sha256']
references[polish['before_archive']]=polish['before_archive_sha256']
names += ['evidence/'+name+'.json' for name in functional]
names += ['evidence/'+name for name in visual['screenshots_sha256']]
for name in profiles:
    raw=read('evidence/'+name+'.json');review=read('evidence/'+name+'-review.json')
    assert raw['completed'] and review['accepted'] and raw['integration_profile']
    assert raw['engine_sha256']==runtime['engine_sha256']
    assert sha(ROOT/'evidence'/(name+'.json'))==review['benchmark_sha256']
    artifact=raw['frozen_source_archive'];assert sha(ROOT/artifact['path'])==artifact['sha256']
    references[artifact['path']]=artifact['sha256']
    for source,digest in raw['configuration_sha256'].items():
        normalized=source.replace('\\','/')
        if any(normalized.startswith('output/c212-em-integration-product/'+folder+'/') for folder in ('app','em','em-cloud')):
            assert sha(ROOT/normalized)==digest,source
    names += ['evidence/'+name+'.json','evidence/'+name+'-review.json']
    names += [run['gpu_report'].replace('\\','/') for run in raw['runs']]
names += [str(p.relative_to(ROOT)).replace('\\','/') for folder in ('app','em','em-cloud') for p in (G/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
names += [str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'scripts/em-integration-ui').iterdir() if p.is_file()]
names += ['output/c212-em-integration-product/c212-em-worker/product/ui-phase'+ending for ending in ('.json','.view.json','.timing.json')]
digests={name:sha(ROOT/name) for name in sorted(set(names))}
description=('Cosmos2 C2-12 partial G candidate. Separate storage; installed3.13 preserved.\n'
    'Small/cloud scientific and worker sources byte-identical to frozen F.\n'
    'Small workspace: one panel, persistent pause,100/125/150% scale, test-particle editor and CODATA2022 charge/mass references.\n'
    'Read-only SI force, instantaneous electric power and matter energy; work is static-potential difference, not a sum of numerical per-step work.\n'
    'Functional CEF, four-stage navigation, normal restart/777-step future and three own declared profiles verified.\n'
    'Former harness failures and pre-localization executed source preserved; earlier F cloud B throughput rejection remains documented in base archive.\n'
    'Visual review is limited to the small paused workspace; cloud layout and final integrated experience remain pending.\n'
    'No installation promotion,10k intense/arbitrary-source performance, planetary fields, GR mesh or whole C2-12 acceptance.\n')
with tarfile.open(DEST,'w:gz') as tar:
    for name,digest in digests.items():
        data=(ROOT/name).read_bytes();assert hashlib.sha256(data).hexdigest()==digest
        info=tarfile.TarInfo(name);info.size=len(data);tar.addfile(info,io.BytesIO(data))
    for name,data in [('README.txt',description.encode()),('referenced-artifacts.json',(json.dumps(references,indent=2)+'\n').encode())]:
        info=tarfile.TarInfo(name);info.size=len(data);tar.addfile(info,io.BytesIO(data))
manifest={'status':'G_small_workspace_and_own_three_profiles_frozen_partial_candidate',
          'archive':str(DEST.relative_to(ROOT)).replace('\\','/'),'archive_sha256':sha(DEST),
          'files_sha256':digests,'referenced_artifacts_sha256':references,
          'installed_product_files_preserved':len(baseline['installed_app_sha256']),
          'owner_pointer_preserved':True,'promotion':False,'scope':description}
MANIFEST.write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'archive':manifest['archive'],'sha256':manifest['archive_sha256'],'files':len(digests)}),flush=True)
