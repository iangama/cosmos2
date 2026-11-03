"""Freeze the EMcloudv2 candidate, successful profile and preserved incidents."""
from pathlib import Path
import hashlib
import io
import json
import tarfile

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT/'output/c212-em-cloud-product'
archive = ROOT/'evidence/c212-em-cloud-v02-candidate-20261020.tar.gz'
manifest = ROOT/'evidence/c212-em-cloud-v02-candidate-frozen-check.json'
assert not archive.exists() and not manifest.exists()
files, historical = {}, []

def add(path, expected=None):
    path = Path(str(path).replace('\\', '/'))
    path = path if path.is_absolute() else ROOT/path
    name = str(path.relative_to(ROOT)).replace('\\', '/')
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if expected is not None:
        assert digest == expected, name
    if name in files:
        assert files[name][1] == digest, name
    files[name] = data, digest

review = json.loads((ROOT/'evidence/native-emcloud-c212em10kc-review.json').read_bytes())
assert review['accepted'] and review['three_EM10000_routes_measured_and_integrity_verified']
add('scripts/review-em-cloud-benchmark.py', review['audit_script_sha256'])
add(review['benchmark'], review['benchmark_sha256'])
add(review['frozen_source_archive']['path'], review['frozen_source_archive']['sha256'])
benchmark = json.loads((ROOT/Path(review['benchmark'].replace('\\', '/'))).read_bytes())
for path, digest in benchmark['configuration_sha256'].items():
    add(path, digest)
for run in benchmark['runs']:
    add(run['gpu_report'], run['gpu_sha256'])
for path in sorted((ROOT/'evidence').glob('em-cloud-*.json')):
    add(path)
    receipt = json.loads(path.read_bytes())
    if 'JS_errors' in receipt:
        assert receipt['JS_errors'] == []
    sources = receipt.get('source_sha256', {})
    for name, digest in (sources.items() if isinstance(sources, dict) else ()):
        current = ROOT/name.replace('\\', '/')
        if current.is_file() and hashlib.sha256(current.read_bytes()).hexdigest() == digest:
            add(name, digest)
        else:
            # Earlier native receipts predate opacity/marker fixes and remain
            # historical. Final CEF/persistence/profile bytes are checked below.
            historical.append({'receipt': str(path.relative_to(ROOT)), 'source': name,
                               'historical_sha256': digest})
for name in ('em-cloud-native-ui-check.json', 'em-cloud-persistence-resilience-check.json'):
    receipt = json.loads((ROOT/'evidence'/name).read_bytes())
    for path, digest in receipt['source_sha256'].items():
        add(path, digest)
visual = json.loads((ROOT/'evidence/em-cloud-native-ui-visual-review.json').read_bytes())
assert visual['status'] == 'native_CEF_final_marker_size_visual_review_passed'
add(visual['image'], visual['image_sha256'])
for path in sorted((ROOT/'evidence').glob('native-emcloud-c212em10k*')):
    if path.is_file():
        add(path)
for path in sorted((ROOT/'output').glob('gpu-memory-journal-c212em10kc*.jsonl')):
    add(path)
for folder in ('app', 'em', 'em-cloud'):
    for path in (CANDIDATE/folder).rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            add(path)
for path in (CANDIDATE/'LEIA-CANDIDATA.md', Path(__file__),
             ROOT/'scripts/start-c212-em-cloud-candidate.ps1'):
    add(path)
baseline = json.loads((ROOT/'evidence/c212-em-candidate-baseline.json').read_bytes())
for name, digest in baseline['installed_app_sha256'].items():
    assert hashlib.sha256((ROOT/'app'/name).read_bytes()).hexdigest() == digest, name
assert hashlib.sha256((ROOT/'user/sessions/latest.json').read_bytes()).hexdigest() == baseline['owner_sha256']
with tarfile.open(archive, 'w:gz') as tar:
    for name, (data, _) in sorted(files.items()):
        member = tarfile.TarInfo(name)
        member.size = len(data)
        tar.addfile(member, io.BytesIO(data))
with tarfile.open(archive, 'r:gz') as tar:
    assert {m.name for m in tar.getmembers()} == set(files)
    for name, (_, digest) in files.items():
        assert hashlib.sha256(tar.extractfile(name).read()).hexdigest() == digest, name
result = {'status': 'separate_EMcloud_v2_candidate_and_uniform_B_10000_profile_frozen',
          'archive': str(archive.relative_to(ROOT)), 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
          'files_sha256': {name: digest for name, (_, digest) in sorted(files.items())},
          'historical_receipts_with_superseded_source_bytes': historical,
          'installed_product_files_preserved': len(baseline['installed_app_sha256']), 'owner_pointer_preserved': True,
          'scope': review['scope'], 'promotion': False}
manifest.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({k: v for k, v in result.items() if k not in ('files_sha256', 'historical_receipts_with_superseded_source_bytes')}, indent=2))
