"""Preserve sixteen-center dynamics sources, native originals and own profile locally; never push."""
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
patterns = ['output/is6-expanded-journey-reopen-*/*.png',
            'output/is6-expanded-journey-reopen-host-*/*.log',
            'output/is6-expanded-journey-native-host-recovery-*/*.log',
            'evidence/is6-expanded*.json',
            'output/is6-expanded-instruments-service-*/recipe-before-execution.json',
            'output/is6-expanded-instruments-service-*/orbital-worker/*.json',
            'output/is6-expanded-instruments-service-*/saved-sixteen/*.json',
            'output/is6-expanded-instruments-service-*/particle-*/worker/*.json',
            'output/is6-expanded-instruments-service-*/particle-*/checkpoints/**/*.json',
            'output/is6-expanded-instruments-service-*/layers-*/**/*.json',
            'output/is6-expanded-instruments-service-*/solar-zone/saved.json',
            'output/is6-expanded-instruments-service-*/solar-zone/branches/*.json',
            'output/is6-expanded-instruments-service-*/solar-zone/exports/*.json',
            'output/is6-expanded-journey-native-*/*.png',
            'output/is6-expanded-journey-native-*/stored-archives/**/*.json',
            'output/is6-expanded-journey-native-host-*/*.log',
            'output/is6-expanded-journey-product0.27.0/particle-checkpoints/**/*.json',
            'output/is6-expanded-journey-product0.27.0/layer-checkpoints/**/*.json',
            'output/is6-expanded-journey-product0.27.0/solar-zone-checkpoints/saved.json',
            'output/is6-expanded-journey-product0.27.0/solar-zone-checkpoints/branches/*.json',
            'output/is6-expanded-journey-product0.27.0/solar-zone-checkpoints/exports/*.json',
            'output/is6-expanded-journey-product0.27.0/gravity-sessions/**/*.json',
            'output/is6-expanded-journey-product0.27.0/gravity-sessions/**/*.bin',
            'output/is6-expanded-journey-product0.27.0/execution-logs/**/*',
            'output/handoff-archive/cota-20261113*.txt',
            'evidence/is6-expanded-journey*.json',
            'output/is6-expanded-journey-product0.27.0/app/**/*',
            'output/is6-expanded-journey-product0.27.0/*.json',
            'output/is6-expanded-journey-service-*/**/*.json',
            'PASSAGEM-COTA.txt', 'output/handoff-archive/cota-20261112b-8.txt',
            'output/is6-dynamics16-ui-staging/**/*',
            'output/is6-dynamics16-product0.26.*/app/**/*',
            'output/is6-dynamics16-product0.26.*/build-manifest.json',
            'output/is6-dynamics16-product0.26.*/gravity-sessions/*.json',
            'output/is6-dynamics16-product0.26.*/gravity-sessions/*.bin',
            'output/is6-dynamics16-product0.26.*/execution-logs/**/*',
            'output/is6-dynamics16-native-*/*.png',
            'output/is6-dynamics16-service-*/**/*.json',
            'output/is6-dynamics16-http-*/**/*.json',
            'output/is6-dynamics16-gpu-adapter-*/*.json',
            'output/is6-dynamics16-switch-*/*.log',
            'output/is6-dynamics16-profile-*/*.json',
            'output/is6-dynamics16-profile-*/*.log',
            'Abrir-Dinamica16.cmd', '*.md', 'Abrir-Planetas.cmd', 'Abrir-Planetas-e-Luas.cmd',
            'evidence/is6-dynamics16*.json',
            'output/is6-dynamics16-staging/*.py',
            'output/is6-dynamics16-verification-*/*.json',
            'output/is6-dynamics16-numerics-*/*.json',
            'evidence/is6-moons-layers*.json',
            'output/is6-moons-layers-native-*/*.png',
            'output/is6-moons-layers-native-*/stored-snapshots/**/*.json',
            'output/is6-moons-layers-native-cycle-*/*.log',
            'output/is6-moons-layers-profile-*/*.json',
            'output/is6-moons-layers-profile-*/*.log',
            'output/is6-moons-layers-profile-*/persisted-before/**/*.json',
            'output/is6-principal-moons-navigation-product0.25.1/layer-checkpoints/**/*.json',
            'evidence/is6-principal-moons*.json',
            'output/is6-principal-moons-navigation-staging*/**/*',
            'output/is6-principal-moons-navigation-product0.25.*/app/**/*',
            'output/is6-principal-moons-navigation-product0.25.*/build-manifest.json',
            'output/is6-principal-moons-navigation-native-*/*.png',
            'output/is6-principal-moons-navigation-profile-*/*.log',
            'output/is6-principal-moons-navigation-reopen-*/*.log',
            'output/is6-principal-moons-catalog-native-*/*.png',
            'output/is6-principal-moons-favorites-*/*/*.json',
            'output/is6-principal-moons-switch-*/*.log',
            'output/is6-principal-moons-switch-*/original-utf8-favorites.json',
            'output/is6-principal-moons-horizons-*/*.json',
            'output/is6-principal-moons-visuals-*/*',
            'output/is6-principal-moons-navigation-product0.25.*/execution-logs/**/*',
            'evidence/is6-planet-navigation*.json',
            'evidence/is6-planet-journey*.json',
            'evidence/is6-principal-moons*.json',
            'output/is6-principal-moons-verification-*/*.json',
            'output/is6-principal-moons-acquisition-*/*.cmt',
            'output/is6-principal-moons-acquisition-*/*.mrg',
            'output/is6-principal-moons-acquisition-*/aa_checksums.txt',
            'output/is6-principal-moons-data-*/*.bsp',
            'output/is6-principal-moons-data-*/*.comments.txt',
            'output/is6-principal-moons-model-*/*.json',
            'output/is6-principal-moons-model-*/*.py',
            'output/is6-planet-navigation-reopen-*/*.log',
            'evidence/is6-planet-visuals*.json',
            'output/is6-planet-navigation-staging/**/*',
            'output/is6-planet-navigation-product0.24.*/app/**/*',
            'output/is6-planet-navigation-product0.24.*/build-manifest.json',
            'output/is6-planet-navigation-native-*/*.png',
            'output/is6-planet-navigation-native-*/*.log',
            'output/is6-planet-navigation-profile-*/*.log',
            'output/is6-planet-navigation-product0.24.*/execution-logs/**/*',
            'output/is6-planet-visuals-*/*', 'scripts/*.py', 'scripts/*.ps1', 'scripts/*.sh',
            'data/spice/*.bsp',
            'data/spice/*.tpc',
            'data/spice/*.tls',
            'data/spice/de442_tech-comments.txt',
            'output/solar-integration-staging/*.bsp',
            'output/jupiter-acquisition-20261023/jup365.cmt',
            'output/saturn-acquisition/sat459.cmt',
            'output/is6-planet-catalog-acquisition-*/*.cmt',
            'output/is6-planet-catalog-acquisition-*/*.mrg',
            'output/is6-planet-catalog-acquisition-*/aa_checksums.txt',
            'evidence/is6-k5-hitch*.json',
            'evidence/is6-planet-catalog*.json',
            'evidence/github-source-*202611*.json',
            'output/is6-k5-hitch-native-*/*.log',
            'output/is6-planet-catalog-staging/*',
            'output/is6-planet-catalog-data-*/*.bsp',
            'output/is6-planet-catalog-data-*/*.comments.txt',
            'output/is6-planet-catalog-model-*/*.json',
            'output/is6-planet-catalog-verification-*/*.json',
            'output/is6-planet-catalog-horizons-*/*.json',
            'output/is6-planet-catalog-native-*/*.png',
            'output/is6-planet-catalog-native-*/*.log',
            'output/is6-planet-catalog-product0.23.*/app/**/*',
            'output/is6-planet-catalog-product0.23.*/build-manifest.json',
            'output/is6-layers-product0.21.1/execution-logs/1793897449417504900/*',
            'evidence/gpu-pdh*.json',
            'evidence/owned-process-classification*.json',
            'evidence/owned-process-preparation*.json',
            'evidence/is6-layers-import-profile-*20261105*.json',
            'output/is6-layers-import-profile-*20261105*/*.json',
            'output/is6-layers-import-profile-*20261105*/persisted-before/**/*.json',
            'evidence/is6-gpu-pdh*.json',
            'output/is6-spatial-import-profile-plan-*/*.json',
            'output/is6-spatial-import-profile-*/*.json',
            'output/is6-spatial-import-profile-*/persisted-before/**/*.json',
            'output/handoff-archive/before-20261105p3-final.md',
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
            parsed = json.loads(source.read_text(encoding='utf-8-sig'))
        except (ValueError, OSError):
            if name in old:
                rows.append(old[name])
            continue
        if (name.startswith('evidence/is6-principal-moons-acquisition-')
                and not parsed.get('completed') and not parsed.get('failure')):
            # A live download receipt is still changing; final evidence goes in the next snapshot.
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
