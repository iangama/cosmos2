"""Incrementally preserve native curation, confirmed results and manual option controls; local backup only."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT.parent / 'cosmos2-github-snapshot-20261103'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    receipt = ROOT / ('evidence/github-source-sync-' + args.label + '.json')
    assert not receipt.exists(), 'Preserve sync receipt'
    inventory_path = TARGET / 'snapshot-inventory.json'
    before = sha(inventory_path)
    inventory = json.loads(inventory_path.read_text(encoding='utf8'))
    old = {row['path']: row for row in inventory['files']}
    selected = set()
    patterns = [
        'scripts/*working*cosmos2-v2.py', 'scripts/prepare-working-product-v*.py',
        'scripts/curation-native-preflight-v*.py', 'scripts/switch-working-product-*.py',
        'scripts/restore-working-session-*.py', 'scripts/preserve-working-session-for-upgrade.py',
        'scripts/*forces-confirmed*.py', 'scripts/*forces-confirmed*.cjs',
        'scripts/forces-confirmed-result-ui/*', 'scripts/prepare-forces-ui-fixtures.py',
        'scripts/option-controls-ui/*', 'scripts/option-controls-ui-v2/*', 'scripts/verify-option-controls*.cjs',
        'scripts/verify-native-option-controls*.py', 'scripts/verify-native-reference-options*.py', 'scripts/ordinary_option_input*.py', 'scripts/reproduce-native-option-popup.py', 'scripts/record-option-controls-delivery.py',
        'scripts/sync-github-source-snapshot-v27.py',
        'evidence/forces-confirmed*.json', 'evidence/forces-session-preservation*.json',
        'evidence/working-product-switch*.json', 'evidence/working-session-restored*.json',
        'evidence/github-source-sync-20261120c.json', 'evidence/github-source-local-20261120b.json',
        'evidence/github-source-sync-20261120d.json',
        'evidence/option-controls*.json', 'evidence/option-popup*.json',
        'output/forces-confirmed-ui-fixtures-20261120a/*.json',
        'output/forces-confirmed-ui-20261120*/*.png',
        'output/forces-confirmed-result-before-20261120a/*.png',
        'output/forces-confirmed-native-after-20261120a/*.png',
        'output/option-controls-ui-20261120*/*.png', 'output/option-controls-native-20261120*/*.png',
        'output/option-popup-before-20261120a/*.png',
        'output/option-controls-native-reference-20261120*/*.png',
        'output/forces-session-preservation-20261120a/*.png',
        'output/original-flow-native-selecao-20261120*/*.png',
        'output/original-flow-hotfix-product0.27.2/app/**/*',
        'output/original-flow-hotfix-product0.27.2/data/**/*',
        'output/original-flow-hotfix-product0.27.2/build-manifest.json',
        'output/original-flow-hotfix-product0.27.3/app/**/*',
        'output/original-flow-hotfix-product0.27.3/data/**/*',
        'output/original-flow-hotfix-product0.27.3/build-manifest.json',
        'output/original-flow-hotfix-product0.27.4/app/**/*',
        'output/original-flow-hotfix-product0.27.4/data/**/*',
        'output/original-flow-hotfix-product0.27.4/build-manifest.json',
        'output/working-product-switch-20261120*/entry-before/**/*',
        'output/handoff-archive/antes-20261120-*.txt',
        'output/continuity-checkpoint-20261120-*.txt',
        '*.md', 'PASSAGEM-COTA.txt', 'PASSAGEM-CURADORIA-20261120.txt', '*.cmd',
        'config/local-working-product.json',
        'scripts/*working*cosmos2.py', 'scripts/prepare-working-product.py',
        'scripts/curation-native-preflight.py', 'scripts/ordinary_native_input*.py',
        'scripts/observe-original-launcher.py', 'scripts/native-curation-action*.py',
        'scripts/verify-ordinary-native-journey*.py',
        'evidence/original-flow-native*.json', 'evidence/original-flow-entry*.json',
        'output/original-flow-native-20261120*/*.png',
        'output/original-flow-hotfix-product0.27.1/app/**/*',
        'output/original-flow-hotfix-product0.27.1/data/**/*',
        'output/original-flow-hotfix-product0.27.1/build-manifest.json',
        'output/continuity-checkpoint-20261120-native-7.txt',
        'scripts/prepare-original-flow-hotfix-v2.py',
        'scripts/verify-original-panels-ui-offline*.cjs',
        'scripts/verify-original-flow-hotfix-http-v2.py',
        'scripts/record-original-flow-hotfix-review.py',
        'scripts/sync-github-source-snapshot-v26.py',
        'scripts/original-flow-hotfix-ui/*',
        'evidence/original*20261120*.json',
        'evidence/original-forces-dependency-repair-20261114a.json',
        'output/original-flow-hotfix-staging-v2/app/**/*',
        'output/original-flow-hotfix-staging-v2/data/**/*',
        'output/original-flow-hotfix-staging-v2/preparation.json',
        'output/original-panels-ui-offline-20261120*/*.png',
        'output/original-flow-hotfix-http-20261120a/*.json',
        'output/original-flow-hotfix-http-20261120a/*.log',
        'output/original-flow-hotfix-review-20261120a/**/*',
        'output/is5-compression-product0.17.2/data/science/*',
        'output/is5-compression-product0.17.2/data/textures/earth.jpg',
        'output/is6-expanded-journey-product0.27.0/data/science/*',
        'output/is6-expanded-journey-product0.27.0/data/textures/earth.jpg',
    ]
    for pattern in patterns:
        for file in ROOT.glob(pattern):
            relative = file.relative_to(ROOT)
            if file.is_file() and file.suffix == '.json' and relative.parts[0] == 'evidence':
                try:
                    progress = json.loads(file.read_text(encoding='utf8'))
                except ValueError:
                    continue
                if 'completed' in progress and not progress.get('completed') and not progress.get('failure'):
                    continue
            if file.is_file() and file.suffix == '.png' and not file.read_bytes().endswith(b'IEND\xaeB`\x82'):
                continue
            if file.is_file() and not any(part in {'user', '.git', '.tooling', '.upstream', '__pycache__'}
                                          or part.startswith('.runtime') for part in relative.parts):
                assert relative.suffix.lower() not in {'.pem', '.key', '.pyc', '.zip', '.exe', '.dll'}
                assert not relative.name.startswith('.env')
                selected.add(relative.as_posix())
    planned, unchanged = [], []
    for name in sorted(selected):
        source, destination = ROOT / name, TARGET / name
        assert source.stat().st_size < 48 * 2**20, 'Use the established chunking workflow for large files'
        digest = sha(source)
        if destination.exists():
            current = sha(destination)
            if current != digest:
                assert name in old and current == old[name]['sha256'], 'Preserve local backup edits: ' + name
            else:
                unchanged.append(name)
                continue
        planned.append((name, source, destination, digest))
    for name, source, destination, digest in planned:
        assert sha(source) == digest, 'Source changed while planning: ' + name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        assert sha(source) == sha(destination) == digest
    rows = dict(old)
    for name in sorted(selected):
        file = TARGET / name
        assert sha(file) == sha(ROOT / name)
        rows[name] = dict(path=name, bytes=file.stat().st_size, sha256=sha(file))
    inventory['files'] = [rows[name] for name in sorted(rows)]
    inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    changed = [name for name, *_ in planned]
    result = dict(accepted=True, completed=True, destination=TARGET.as_posix(),
                  files=len(rows), selected=len(selected), changed=changed, unchanged=len(unchanged),
                  inventory_before_sha256=before, inventory_sha256=sha(inventory_path),
                  script_sha256=sha(Path(__file__)),
                  scope='Incremental local source/evidence backup only. Selected files rehashed; other inventory entries preserved from v26 without rerunning full drivers. No runtimes, personal sessions, binary archives, promotion or publication.')
    receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    path_list = ROOT / 'output/original-flow-hotfix-review-20261120a/backup-paths.txt'
    path_list.write_text('\n'.join(changed + ['snapshot-inventory.json'])+'\n', encoding='utf8')
    print(json.dumps(dict(accepted=True, files=len(rows), selected=len(selected), changed=len(changed), unchanged=len(unchanged))))


if __name__ == '__main__':
    main()
