"""Freeze helperE, its declared source128 profile, science and preserved rejections."""
from pathlib import Path
import hashlib
import io
import json
import tarfile

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT/'output/c212-em-cloud-native-product'
archive = ROOT/'evidence/c212-em-cloud-native-candidate-20261020.tar.gz'
manifest = ROOT/'evidence/c212-em-cloud-native-candidate-frozen-check.json'
assert not archive.exists() and not manifest.exists()
files = {}
def add(path, digest=None):
    p = Path(str(path).replace('\\', '/'))
    p = p if p.is_absolute() else ROOT/p
    name = str(p.relative_to(ROOT)).replace('\\', '/')
    data = p.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if digest is not None: assert actual == digest, name
    if name in files: assert files[name][1] == actual, name
    files[name] = data, actual

review_path = ROOT/'evidence/native-emcloud-c212src128a-review.json'
review = json.loads(review_path.read_bytes())
assert review['accepted'] and review['three_EM10000_routes_measured_and_integrity_verified']
add(review_path)
add('scripts/review-em-cloud-source128-benchmark.py', review['audit_script_sha256'])
add(review['benchmark'], review['benchmark_sha256'])
add(review['frozen_source_archive']['path'], review['frozen_source_archive']['sha256'])
benchmark = json.loads(files[str(review['benchmark']).replace('\\', '/')][0])
for source, digest in benchmark['configuration_sha256'].items(): add(source, digest)
for run in benchmark['runs']: add(run['gpu_report'], run['gpu_sha256'])
receipts = ('em-cloud-native-helper-e-core-check.json', 'em-cloud-native-contract-e-check.json',
            'em-cloud-native-e-futures-check.json', 'em-cloud-native-worker-check.json',
            'em-cloud-native-source128-dynamics-check.json', 'em-cloud-helper-native-check.json',
            'em-cloud-helper-native-ui-check.json', 'em-cloud-helper-persistence-resilience-check.json',
            'em-cloud-helper-native-ui-visual-review.json')
for name in receipts:
    path = ROOT/'evidence'/name
    record = json.loads(path.read_bytes())
    if name == 'em-cloud-native-source128-dynamics-check.json': assert record['accepted']
    if 'JS_errors' in record: assert record['JS_errors'] == []
    add(path)
    for source, digest in record.get('source_sha256', {}).items(): add(source, digest)
    for source, digest in record.get('reference_implementation_sha256', {}).items(): add(source, digest)
    if 'image' in record: add(record['image'], record['image_sha256'])
for source, digest in review['reference_sources_sha256'].items(): add(source, digest)
for pattern in ('em-cloud-native-helper-*-20261020.tar.gz', 'em-cloud-native-helper-*-frozen.json',
                'em-cloud-source128-strong-fixture-*', 'em-cloud-source128-reference-first-failure.json',
                'em-cloud-native-thread-profile-d.json', 'em-cloud-native-helper-candidate-prepared.json'):
    for path in (ROOT/'evidence').glob(pattern): add(path)
for path in (ROOT/'output').glob('gpu-memory-journal-c212src128a*.jsonl'): add(path)
for folder in ('app', 'em', 'em-cloud'):
    for path in (DEST/folder).rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts: add(path)
for path in (DEST/'LEIA-CANDIDATA.md', Path(__file__), ROOT/'scripts/prepare-em-cloud-native-candidate.py',
             ROOT/'scripts/start-c212-em-cloud-native-candidate.ps1'): add(path)
baseline = json.loads((ROOT/'evidence/c212-em-candidate-baseline.json').read_bytes())
for name, digest in baseline['installed_app_sha256'].items():
    assert hashlib.sha256((ROOT/'app'/name).read_bytes()).hexdigest() == digest, name
assert hashlib.sha256((ROOT/'user/sessions/latest.json').read_bytes()).hexdigest() == baseline['owner_sha256']
with tarfile.open(archive, 'w:gz') as tar:
    for name, (data, _) in sorted(files.items()):
        member = tarfile.TarInfo(name); member.size = len(data)
        tar.addfile(member, io.BytesIO(data))
with tarfile.open(archive, 'r:gz') as tar:
    assert {m.name for m in tar.getmembers()} == set(files)
    for name, (_, digest) in files.items():
        assert hashlib.sha256(tar.extractfile(name).read()).hexdigest() == digest, name
result = {'status': 'isolated_helperE_and_declared_weak_source128_native_profile_frozen',
          'archive': str(archive.relative_to(ROOT)), 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
          'files_sha256': {name: digest for name, (_, digest) in sorted(files.items())},
          'owner_pointer_preserved': True, 'installed_product_files_preserved': len(baseline['installed_app_sha256']),
          'promotion': False, 'scope': review['scope']}
manifest.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({k: v for k, v in result.items() if k != 'files_sha256'}, indent=2))
