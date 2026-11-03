"""Preserve J own profiles and measured viewport slice with declared integration scope."""
from pathlib import Path
import hashlib
import io
import json
import tarfile

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / 'output/c212-em-viewport-product'
DEST = ROOT / 'evidence/c212-em-viewport-candidate-20261022.tar.gz'
MANIFEST = ROOT / 'evidence/em-viewport-candidate-frozen-check.json'
assert not DEST.exists() and not MANIFEST.exists()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def path(name):
    return ROOT / name.replace('\\', '/')


def read(name):
    return json.loads(path(name).read_bytes())


baseline = read('evidence/c212-em-candidate-baseline.json')
for name, digest in baseline['installed_app_sha256'].items():
    assert sha(ROOT / 'app' / name) == digest, name
assert sha(ROOT / 'user/sessions/latest.json') == 'ee9c4cc86e0696afde128ec319f98f6ad5b3932f27f8b5bd6a25d57a4025b825'
for folder in ('em', 'em-cloud'):
    base = ROOT / 'output/c212-em-integration-product' / folder
    for source in base.rglob('*'):
        if source.is_file() and '__pycache__' not in source.parts:
            assert source.read_bytes() == (PRODUCT / folder / source.relative_to(base)).read_bytes(), source
references = {}
base = read('evidence/em-framing-candidate-frozen-check.json')
references[base['archive']] = base['archive_sha256']
runtime = read('evidence/built-runtime-topic-cleanup.json')
assert sha(ROOT / '.runtime-topic-cleanup/bin/OpenSpace.exe') == runtime['engine_sha256']
profiles = ('native-em128-c212j128a', 'native-em128-c212jpota', 'native-emcloud-c212jsrca')
names = set()
for prefix in profiles:
    raw = read('evidence/' + prefix + '.json')
    review = read('evidence/' + prefix + '-review.json')
    assert raw['completed'] and review['accepted'] and not review['criteria_failures']
    assert raw['viewport_profile'] and raw['framing_profile'] and raw['engine_sha256'] == runtime['engine_sha256']
    assert sha(ROOT / 'evidence' / (prefix + '.json')) == review['benchmark_sha256']
    artifact = raw['frozen_source_archive']
    references[artifact['path']] = artifact['sha256']
    for source, digest in raw['configuration_sha256'].items():
        assert sha(path(source)) == digest, source
    names.update(path(run['gpu_report']) for run in raw['runs'])
for report in ('em-viewport-ui-release4-check','em-viewport-cloud-ui-release1-check','em-viewport-restart-check','em-viewport-cloud-restart-check','em-viewport-five-scenes-release3-check'):
    proof = read('evidence/' + report + '.json')
    assert not proof['JS_errors'] and proof.get('completed', True)
    assert proof.get('owner_pointer_preserved', proof.get('owner_and_saved_phase_preferences_preserved', False))
    for source, digest in proof['source_sha256'].items():
        if source.replace('\\', '/').startswith('output/c212-em-viewport-product/app/'):
            assert sha(path(source)) == digest, source
    for image, digest in proof.get('screenshots_sha256', {}).items():
        assert sha(ROOT / 'evidence' / image) == digest, image
for pattern in ('em-viewport*.json','native-em128-c212j*.json','native-emcloud-c212j*.json','cosmos2-j-*.png','cosmos2-em-viewport-*.png'):
    names.update((ROOT / 'evidence').glob(pattern))
for pattern in ('*em-viewport*.py', 'start-c212-em-viewport-candidate.ps1', 'benchmark-em128-*.py', 'benchmark-em-cloud-source128-native.py', 'review-em128-new-runtime-benchmark.py', 'review-em-cloud-source128-benchmark.py', 'cef_page.py', 'wait-cosmos2-ready.py'):
    names.update((ROOT / 'scripts').glob(pattern))
for folder in ('app', 'em', 'em-cloud'):
    names.update(p for p in (PRODUCT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
for folder in ('scripts/em-framing-ui', 'scripts/em-framing-sampler'):
    names.update(p for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
for pattern in ('em-viewport-*-expected.json','em-viewport-*-source.py','em-viewport-header-pixel-probe.py','em-viewport-visual-contact.py'):
    names.update((ROOT / 'output').glob(pattern))
for folder in ('c212-em-worker/product', 'c212-em-cloud-worker/product'):
    names.update(p for p in (PRODUCT / folder).glob('ui-phase*') if p.is_file())
names.update(ROOT / name for name in ('LEIA-PRIMEIRO.md', 'C2-12-INTEGRACAO.md', 'evidence/built-runtime-topic-cleanup.json', 'evidence/em-framing-candidate-frozen-check.json'))
names.add(PRODUCT / 'LEIA-CANDIDATA.md')
for pattern in ('em-viewport*.tar.gz',):
    for artifact in (ROOT / 'output').glob(pattern):
        references[str(artifact.relative_to(ROOT))] = sha(artifact)
for name, digest in references.items():
    assert sha(path(name)) == digest, name
digests = {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in sorted(names)}
# Bind saved phase/view files to their real-restart oracles, not only to current bytes.
for oracle_name,folder in (('em-viewport-restart-expected.json','c212-em-worker/product'),('em-viewport-cloud-restart-expected.json','c212-em-cloud-worker/product')):
    oracle=read('output/'+oracle_name)
    for suffix,digest in oracle['files_sha256'].items():
        assert sha(PRODUCT/folder/('ui-phase'+suffix))==digest
for review_name in ('em-viewport-five-scenes-visual-review.json','em-viewport-cloud-visual-review.json'):
    proof=read('evidence/'+review_name)
    for image,digest in proof['screenshots_sha256'].items():
        assert sha(ROOT/'evidence'/image)==digest
scope = ('Partial J candidate: own128-charge,potential1089/128-source and10k/128weak-source profiles independently approved.\n'
         'Same scientific core0.4,helperABI1,static provider,2s and scientific/frame/resource limits as I.\n'
         'Native perspective camera fits actual available viewport; minimum graphic marker radius on framing/restore, SI centers unchanged.\n'
         'Compact scene legend, complete potential details via panel; five actual layered experiences in native/canvas100/150 reviewed.\n'
         'Own functional edit/save/legacy/refusals/real partialIO and normal restart of both labs with777exact futures verified.\n'
         'Four-force16combination navigation passed. Earlier preparation/harness mistakes and false header-clipping hypothesis preserved and corrected.\n'
         'Cloud editor100/150 reviewed; cloud whole-window small framing and final integrated product decision remain distinct from this viewport slice.\n'
         'No installation promotion, wholeC2-12 acceptance,10k intense/arbitrary-source approval, planetary-field or GR-mesh approval.\n')
with tarfile.open(DEST, 'w:gz') as tar:
    for name, digest in digests.items():
        data = path(name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest
        info = tarfile.TarInfo(name)
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    for name, data in (('README.txt', scope.encode()), ('referenced-artifacts.json', json.dumps(references, indent=2).encode())):
        info = tarfile.TarInfo(name)
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
manifest = {'status': 'J_three_own_profiles_and_reviewed_viewport_slice_frozen', 'promotion': False, 'whole_C2_12_accepted': False,
            'archive': str(DEST.relative_to(ROOT)), 'archive_sha256': sha(DEST), 'files_sha256': digests,
            'referenced_artifacts_sha256': references, 'installed_product_files_preserved': len(baseline['installed_app_sha256']),
            'owner_pointer_preserved': True, 'scope': scope}
MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'archive': manifest['archive'], 'sha256': manifest['archive_sha256'], 'files': len(digests)}), flush=True)
