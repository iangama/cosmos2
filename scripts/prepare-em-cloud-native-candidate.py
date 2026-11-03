"""Fork the frozen cloud candidate with independently checked native science."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'output/c212-em-cloud-product'
STAGE = ROOT/'output/c212-em-cloud-native-staging'
DEST = ROOT/'output/c212-em-cloud-native-product'
assert not DEST.exists()
original = (ROOT/'user/sessions/latest.json').read_bytes()
frozen = json.loads((ROOT/'evidence/c212-em-cloud-v02-candidate-frozen-check.json').read_bytes())
for name, digest in frozen['files_sha256'].items():
    if name.startswith('output/c212-em-cloud-product/'):
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest, name
receipts = []
for name in ('em-cloud-native-helper-e-core-check.json', 'em-cloud-native-contract-e-check.json',
             'em-cloud-native-e-futures-check.json', 'em-cloud-native-worker-check.json'):
    path = ROOT/'evidence'/name
    receipt = json.loads(path.read_bytes())
    for source, digest in receipt['source_sha256'].items():
        assert hashlib.sha256((ROOT/source.replace('\\', '/')).read_bytes()).hexdigest() == digest, source
    receipts.append({'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
for folder in ('app', 'em'):
    shutil.copytree(BASE/folder, DEST/folder, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
(DEST/'em-cloud').mkdir()
for path in STAGE.iterdir():
    if path.is_file():
        shutil.copy2(path, DEST/'em-cloud'/path.name)
for folder in ('c212-em-cloud-worker/product', 'c212-em-worker/product', 'gravity-sessions'):
    (DEST/folder).mkdir(parents=True)
subprocess.run(['cmd.exe', '/c', 'mklink', '/J', str(DEST/'data'), str(ROOT/'data')], check=True)
launcher = (ROOT/'scripts/start-c212-em-cloud-candidate.ps1').read_text()
launcher = launcher.replace('c212-em-cloud-product', 'c212-em-cloud-native-product')
launcher = launcher.replace('explicit-unapproved-EM-cloud-candidate', 'explicit-unapproved-EM-cloud-native-helper-candidate')
launcher = launcher.replace('emCloudCandidate = $true;', 'emCloudCandidate = $true; emCloudNativeCandidate = $true;')
(ROOT/'scripts/start-c212-em-cloud-native-candidate.ps1').write_text(launcher)
assert (ROOT/'user/sessions/latest.json').read_bytes() == original
record = {'status': 'separate_native_helper_cloud_candidate_prepared_not_yet_native_validated',
          'base_archive_sha256': frozen['archive_sha256'], 'verified_helper_receipts': receipts,
          'owner_pointer_preserved': True, 'old_v2_checkpoints_auto_migrated': False,
          'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for folder in ('app', 'em', 'em-cloud') for p in (DEST/folder).rglob('*')
                            if p.is_file() and '__pycache__' not in p.parts},
          'scope': 'Own storage and science generation. Same experimental GPU receiver; no installed promotion, native/UI/performance or full C2-12 approval.'}
(ROOT/'evidence/em-cloud-native-helper-candidate-prepared.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps({k: v for k, v in record.items() if k != 'source_sha256'}, indent=2))
