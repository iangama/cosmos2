"""Update the authorized public source backup without runtimes or personal data."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT.parent / 'cosmos2-github-snapshot-20261103'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument('--label', required=True)
args = parser.parse_args()
if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
    parser.error('Invalid label')
receipt = ROOT / ('evidence/github-source-sync-' + args.label + '.json')
if receipt.exists():
    raise FileExistsError('Preserve sync receipt')
assert (TARGET / '.git').is_dir()
inventory_path = TARGET / 'snapshot-inventory.json'
inventory = json.loads(inventory_path.read_text())
old = {item['path']: item for item in inventory['files']}
selected = set(old)
patterns = ['*.md', 'scripts/*.py', 'scripts/*.ps1', 'scripts/*.sh',
            'output/is6-layers-migration-staging/**/*.py',
            'output/is6-layers-migration-staging/ui/*',
            'output/is6-layers-migration-20261104h/*.json',
            'output/is6-layers-storage-native-20261104e/stored-snapshots/**/*.json',
            'output/is6-layers-storage-native-20261104f/stored-snapshots/**/*.json',
            'output/is6-layers-storage-profile-20261104*/input-*.json',
            'output/is6-layers-storage-profile-20261104*/persisted-before/**/*.json',
            'evidence/is6-layers-storage-*20261104*.json',
            'evidence/is6-layers-native-process-*20261104*.json',
            'evidence/is6-layers-profile-process-*20261104*.json',
            'evidence/is6-layers-migration-*20261104*.json',
            'evidence/is6-layers-import-store-*20261104*.json',
            'evidence/is6-layers-import-service-*20261104*.json',
            'evidence/gpu-memory-is6-k4-20261104*.json',
            'evidence/cosmos2-is6-storage-20261104e-*.png',
            'evidence/cosmos2-is6-storage-20261104f-*.png',
            'output/is6-layers-product0.21.*/app/**/*',
            'output/is6-layers-product0.21.*/build-manifest.json',
            'evidence/is6-layers-import-native-*20261104*.json',
            'evidence/is6-layers-import-visual-*20261104*.json',
            'evidence/is6-layers-import-cut-*20261104*.json',
            'evidence/is6-layers-import-recovery-*20261104*.json',
            'evidence/is6-layers-import-profile-*20261104*.json',
            'evidence/cosmos2-is6-import-20261104q-*.png',
            'evidence/cosmos2-is6-import-20261104r-*.png',
            'evidence/cosmos2-is6-import-20261104s-*.png',
            'evidence/cosmos2-is6-import-20261104t-*.png',
            'evidence/cosmos2-is6-import-diagnostic-m-*.png',
            'evidence/is6-import-caption-*.json',
            'evidence/is6-import-capture-*.json',
            'evidence/is6-import-native-captures-*.json',
            'evidence/is6-layers-import-capture-process-*.json',
            'evidence/cosmos2-is6-caption-v-*.png',
            'evidence/cosmos2-is6-import-20261104w-*.png',
            'output/is6-native-framebuffer-RGB-20261104w/*.png',
            'output/is6-caption-inspection-20261104w/*.png',
            'output/is6-layers-import-native-20261104s/cosmos2-*.png',
            'output/is6-layers-import-native-20261104t/cosmos2-*.png',
            'output/is6-layers-import-native-20261104*/stored-snapshots/**/*.json',
            'output/is6-layers-import-profile-20261104*/input-*.json',
            'output/is6-layers-import-profile-20261104*/persisted-before/**/*.json',
            'evidence/gpu-memory-is6-k5-20261104*.json',
            'evidence/local-ui*.json',
            'evidence/is6-ui-startup*.json',
            'evidence/is6-profile-preparation-closed*.json',
            'evidence/cosmos2-ui-startup*.png',
            'output/local-ui-native-startup-*/original-entry.cmd',
            'output/local-ui-native-startup-*/local-ui-readiness.json',
            'output/local-ui-native-startup-*/bootstrap-ui.json',
            'output/is6-spatial-import-staging/*.py',
            'output/is6-spatial-import-staging/ui/*',
            'output/is6-spatial-import-product0.22.*/app/**/*',
            'output/is6-spatial-import-product0.22.*/build-manifest.json',
            'output/is6-spatial-import-native-*/**/*.png',
            'output/is6-spatial-import-native-*/stored-snapshots/**/*.json',
            'output/is6-spatial-import-native-*/local-ui-readiness.json',
            'output/handoff-archive/before-20261104n.md',
            'output/is6-spatial-import-20261104a/*.json',
            'evidence/is6-spatial-import-*.json',
            'output/is6-spatial-import-store-*/expected-before-reopen.json',
            'evidence/github-source-*2026110[45]*.json']
for pattern in patterns:
    selected.update(p.relative_to(ROOT).as_posix() for p in ROOT.glob(pattern)
                    if p.is_file() and '__pycache__' not in p.parts)
changed, missing, rows, staged = [], [], [], []
for name in sorted(selected):
    relative = Path(name)
    assert not relative.is_absolute() and '..' not in relative.parts
    assert not any(part in {'user', '.git', '.tooling', '.upstream', '__pycache__'}
                   or part.startswith('.runtime') for part in relative.parts)
    assert relative.suffix.lower() not in {'.pem', '.key', '.pyc', '.zip', '.exe', '.dll'}
    assert not relative.name.startswith('.env')
    source, destination = ROOT / relative, TARGET / relative
    if not source.is_file():
        assert destination.is_file(), name
        missing.append(name)
        rows.append(dict(path=name, bytes=destination.stat().st_size, sha256=sha(destination)))
        continue
    if relative.suffix == '.json':
        try:
            json.loads(source.read_text(encoding='utf-8-sig'))
        except (ValueError, OSError):
            if name in old:
                rows.append(old[name])
            continue
    seal = sha(source)
    if destination.exists():
        existing = sha(destination)
        if existing != seal:
            assert name in old and existing == old[name]['sha256'], 'Preserve local backup edits: ' + name
            staged.append((source, destination, seal))
            changed.append(name)
    else:
        staged.append((source, destination, seal))
        changed.append(name)
    rows.append(dict(path=name, bytes=source.stat().st_size, sha256=seal))
for source, destination, seal in staged:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    assert sha(source) == sha(destination) == seal, source
inventory['files'] = rows
inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
assert all(sha(TARGET / item['path']) == item['sha256'] for item in rows)
result = dict(accepted=True, completed=True, destination=TARGET.as_posix(), files=len(rows),
              changed=changed, preserved_missing_sources=missing, inventory_sha256=sha(inventory_path),
              script_sha256=sha(Path(__file__)),
              scope='Partial source/evidence backup only; excludes runtimes, personal sessions, binary archives and most generated records. Does not install the product or constitute full reproducibility.')
receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps(dict(accepted=True, files=len(rows), changed=len(changed), preserved_missing_sources=len(missing))))
