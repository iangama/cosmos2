"""Preserve I's three approved profiles without claiming final visual acceptance."""
from pathlib import Path
import hashlib
import io
import json
import tarfile

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / 'output/c212-em-framing-product'
DEST = ROOT / 'evidence/c212-em-framing-candidate-20261022.tar.gz'
MANIFEST = ROOT / 'evidence/em-framing-candidate-frozen-check.json'
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
base = read('evidence/em-cloud-editor-incomplete-archive-check.json')
references[base['archive']] = base['archive_sha256']
runtime = read('evidence/built-runtime-topic-cleanup.json')
assert sha(ROOT / '.runtime-topic-cleanup/bin/OpenSpace.exe') == runtime['engine_sha256']
profiles = ('native-em128-c212i128a', 'native-em128-c212ipota', 'native-emcloud-c212isrca')
names = set()
for prefix in profiles:
    raw = read('evidence/' + prefix + '.json')
    review = read('evidence/' + prefix + '-review.json')
    assert raw['completed'] and review['accepted'] and not review['criteria_failures']
    assert raw['framing_profile'] and raw['engine_sha256'] == runtime['engine_sha256']
    assert sha(ROOT / 'evidence' / (prefix + '.json')) == review['benchmark_sha256']
    artifact = raw['frozen_source_archive']
    references[artifact['path']] = artifact['sha256']
    for source, digest in raw['configuration_sha256'].items():
        assert sha(path(source)) == digest, source
    names.update(path(run['gpu_report']) for run in raw['runs'])
for report in ('em-framing-ui-release1-check', 'em-framing-cloud-ui-release1-check', 'em-framing-restart-check', 'em-framing-cloud-restart-check', 'em-framing-five-scenes-check'):
    proof = read('evidence/' + report + '.json')
    assert not proof['JS_errors'] and proof.get('completed', True)
    assert proof.get('owner_pointer_preserved', proof.get('owner_and_saved_phase_preferences_preserved', False))
    for source, digest in proof['source_sha256'].items():
        if source.replace('\\', '/').startswith('output/c212-em-framing-product/app/'):
            assert sha(path(source)) == digest, source
    for image, digest in proof.get('screenshots_sha256', {}).items():
        assert sha(ROOT / 'evidence' / image) == digest, image
for pattern in ('em-framing*.json', 'native-em128-c212i*.json', 'native-emcloud-c212i*.json', 'cosmos2-i-*.png', 'cosmos2-em-framing-*.png'):
    names.update((ROOT / 'evidence').glob(pattern))
for pattern in ('*em-framing*.py', 'start-c212-em-framing-candidate.ps1', 'benchmark-em128-*.py', 'benchmark-em-cloud-source128-native.py', 'review-em128-new-runtime-benchmark.py', 'review-em-cloud-source128-benchmark.py', 'cef_page.py', 'wait-cosmos2-ready.py'):
    names.update((ROOT / 'scripts').glob(pattern))
for folder in ('app', 'em', 'em-cloud'):
    names.update(p for p in (PRODUCT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
for folder in ('scripts/em-framing-ui', 'scripts/em-framing-sampler'):
    names.update(p for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
for pattern in ('em-framing-*-expected.json', 'em-framing-*-source.py'):
    names.update((ROOT / 'output').glob(pattern))
for folder in ('c212-em-worker/product', 'c212-em-cloud-worker/product'):
    names.update(p for p in (PRODUCT / folder).glob('ui-phase*') if p.is_file())
names.update(ROOT / name for name in ('LEIA-PRIMEIRO.md', 'C2-12-INTEGRACAO.md', 'evidence/built-runtime-topic-cleanup.json', 'evidence/em-cloud-editor-incomplete-archive-check.json'))
names.add(PRODUCT / 'LEIA-CANDIDATA.md')
for pattern in ('em-framing*.tar.gz',):
    for artifact in (ROOT / 'output').glob(pattern):
        references[str(artifact.relative_to(ROOT))] = sha(artifact)
for name, digest in references.items():
    assert sha(path(name)) == digest, name
digests = {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in sorted(names)}
scope = ('Partial I candidate: own128-charge,potential1089/128-source and10k/128weak-source profiles independently approved.\n'
         'Static read-only provider ABI1 with worker0.4 snapshot fences;2s and scientific/frame/resource limits preserved.\n'
         'Functional editor/save/legacy/refusals and two normal restarts with777exact future steps passed.\n'
         'Twenty layered five-experience native/canvas100/150% captures; final visual acceptance NOT granted.\n'
         'Native fit leaves excessive empty space; detailed potential legend reduces150% canvas height.\n'
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
manifest = {'status': 'I_three_own_profiles_frozen_partial_visual_scope', 'promotion': False, 'whole_C2_12_accepted': False,
            'archive': str(DEST.relative_to(ROOT)), 'archive_sha256': sha(DEST), 'files_sha256': digests,
            'referenced_artifacts_sha256': references, 'installed_product_files_preserved': len(baseline['installed_app_sha256']),
            'owner_pointer_preserved': True, 'scope': scope}
MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'archive': manifest['archive'], 'sha256': manifest['archive_sha256'], 'files': len(digests)}), flush=True)
