"""Preserve H and all its measured/refused scope; this is NOT an acceptance freeze."""
from pathlib import Path
import hashlib
import io
import json
import tarfile
ROOT=Path(__file__).resolve().parents[1];H=ROOT/'output/c212-em-cloud-editor-product'
DEST=ROOT/'evidence/c212-em-cloud-editor-incomplete-candidate-20261021.tar.gz'
MANIFEST=ROOT/'evidence/em-cloud-editor-incomplete-archive-check.json'
assert not DEST.exists() and not MANIFEST.exists()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads((ROOT/p).read_bytes())
base=read('evidence/c212-em-integration-candidate-frozen-check.json')
assert sha(ROOT/base['archive'])==base['archive_sha256']
for folder in ('em','em-cloud'):
    for p in (ROOT/'output/c212-em-integration-product'/folder).rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:assert p.read_bytes()==(H/folder/p.relative_to(ROOT/'output/c212-em-integration-product'/folder)).read_bytes()
baseline=read('evidence/c212-em-candidate-baseline.json')
for name,digest in baseline['installed_app_sha256'].items():assert sha(ROOT/'app'/name)==digest
assert sha(ROOT/'user/sessions/latest.json')=='ee9c4cc86e0696afde128ec319f98f6ad5b3932f27f8b5bd6a25d57a4025b825'
references={base['archive']:base['archive_sha256']}
for prefix in ('native-em128-c212h128a','native-em128-c212hpota','native-em128-c212hpotb'):
    raw=read('evidence/'+prefix+'.json')
    if prefix.endswith('128a'):
        review=read('evidence/'+prefix+'-review.json');assert review['accepted'] and raw['completed']
        a=raw['frozen_source_archive'];references[a['path']]=a['sha256']
    else:
        assert not raw['completed'] and not raw['runs']
        a='evidence/'+prefix+'-interrupted-source.tar.gz';references[a]=sha(ROOT/a)
    for name,digest in raw['configuration_sha256'].items():
        if name.startswith('output/c212-em-cloud-editor-product/'):assert sha(ROOT/name)==digest,name
for name in ('em-cloud-editor-ui-release1-check','em-cloud-editor-restart-check','em-cloud-editor-five-experiences-check'):
    r=read('evidence/'+name+'.json');assert not r['JS_errors'] and r['owner_pointer_preserved']
    for source,digest in r['source_sha256'].items():
        if source.replace('\\','/').startswith('output/c212-em-cloud-editor-product/app/'):assert sha(ROOT/source)==digest,source
for review in ('em-cloud-editor-workspace-visual-review','em-cloud-editor-five-experiences-visual-review'):
    for name,digest in read('evidence/'+review+'.json')['screenshots_sha256'].items():assert sha(ROOT/'evidence'/name)==digest
api=read('evidence/em-cloud-editor-api-fix-prepared.json');references[api['before_archive']]=api['before_archive_sha256']
for name,digest in references.items():assert sha(ROOT/name)==digest,name
names=[p for folder in ('app','em','em-cloud') for p in (H/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
for pattern in ('em-cloud-editor*.json','native-em128-c212h*.json','cosmos2-em-cloud-editor-*.png','cosmos2-h-*.png','gpu-memory-c212h128a-*.json'):
    names+=list((ROOT/'evidence').glob(pattern))
for pattern in ('*em-cloud-editor*.py','diagnose-em-potential*.py','add-em-cloud-editor-profile.py','benchmark-em128-*.py','review-em128-new-runtime-benchmark.py','benchmark-em-cloud-source128-native.py','review-em-cloud-source128-benchmark.py','start-c212-em-cloud-editor-candidate.ps1'):
    names+=list((ROOT/'scripts').glob(pattern))
names+=[p for p in (ROOT/'scripts/em-cloud-editor-ui').iterdir() if p.is_file()]
names+=list((ROOT/'output').glob('em-cloud-editor-*-source.py'))
names+=[ROOT/'output/em-cloud-editor-restart-expected.json',ROOT/'LEIA-PRIMEIRO.md',ROOT/'C2-12-INTEGRACAO.md',H/'LEIA-CANDIDATA.md',Path(__file__)]
names+=[H/'c212-em-cloud-worker/product'/('ui-phase'+s) for s in ('.json','.view.json')]
digests={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted(set(names))}
scope=('Incomplete H source editor candidate. NOT approved, NOT promoted.\n'
       'Core/worker bytes equal frozen G/F. Own functional CEF, normal restart and128-charge native profile passed.\n'
       'Potential A/B stopped before frames; B and live/post-restart diagnostics hit original2s sampling bound.\n'
       'Own cloud128-source profile remains unmeasured. Final framing/trajectory/layer experience not accepted.\n'
       'Previous G/F acceptances do not approve this incomplete candidate; failures and harness mistakes preserved.\n')
with tarfile.open(DEST,'w:gz') as tar:
    for name,digest in digests.items():
        b=(ROOT/name).read_bytes();assert hashlib.sha256(b).hexdigest()==digest
        info=tarfile.TarInfo(name);info.size=len(b);tar.addfile(info,io.BytesIO(b))
    for name,b in [('README.txt',scope.encode()),('referenced-artifacts.json',json.dumps(references,indent=2).encode())]:
        info=tarfile.TarInfo(name);info.size=len(b);tar.addfile(info,io.BytesIO(b))
manifest={'status':'H_incomplete_candidate_archived_after_potential_sampling_refusal','accepted':False,'promotion':False,
          'archive':str(DEST.relative_to(ROOT)).replace('\\','/'),'archive_sha256':sha(DEST),'files_sha256':digests,
          'referenced_artifacts_sha256':references,'installed_product_files_preserved':82,'owner_pointer_preserved':True,'scope':scope}
MANIFEST.write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'archive':manifest['archive'],'sha256':manifest['archive_sha256'],'files':len(digests),'accepted':False}),flush=True)
