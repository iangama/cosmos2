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
        '*.md','PASSAGEM-CURADORIA-20261121.txt','*.cmd','config/local-working-product.json',
        'scripts/sync-github-source-snapshot-v29.py','scripts/append-source-backup-receipt-v3.py',
        'scripts/ordinary_native_input_v9.py','scripts/ordinary_option_input_v3.py','scripts/ordinary_file_dialog_input*.py',
        'scripts/preserve-native-reference-curation.py','scripts/verify-native-import-picker*.py',
        'scripts/verify-native-layer-import*.py','scripts/verify-native-import-action-visible.py',
        'scripts/record-reference-file-binding-delivery.py','scripts/verify-native-spatial-roundtrip-repro.py',
        'scripts/reference-file-binding-ui/*','scripts/verify-reference-file-binding.cjs',
        'scripts/prepare-working-product-v6.py','scripts/switch-working-product-0276.py',
        'evidence/native*20261121*.json','evidence/reference-file-binding*20261121*.json',
        'evidence/original-flow-entry-import-20261121a.json','evidence/working-product-switch-20261121a.json',
        'evidence/github-source-local-20261120d.json','evidence/github-source-sync-20261120g.json',
        'output/original-flow-hotfix-product0.27.6/app/**/*','output/original-flow-hotfix-product0.27.6/data/**/*',
        'output/original-flow-hotfix-product0.27.6/build-manifest.json',
        'output/native-reference-import-20261121a/*preview*.png',
        'output/native-reference-import-20261121a/*branch*.png',
        'output/native-reference-import-20261121a/*button*.png',
        'output/native-spatial-roundtrip-20261121a/*.png','output/original-flow-native-import-20261121a/*.png',
        'output/handoff-archive/antes-20261121-file-binding-entregue.txt',
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
                  scope='Incremental local source/evidence backup only. Selected files rehashed; other inventory entries preserved from v28 without rerunning full drivers. No runtimes, personal sessions, binary archives, promotion or publication.')
    receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    path_list = ROOT / 'output/original-flow-hotfix-review-20261120a/backup-paths.txt'
    path_list.write_text('\n'.join(changed + ['snapshot-inventory.json'])+'\n', encoding='utf8')
    print(json.dumps(dict(accepted=True, files=len(rows), selected=len(selected), changed=len(changed), unchanged=len(unchanged))))


if __name__ == '__main__':
    main()
