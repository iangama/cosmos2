"""Preserve completed native point-lens delivery and current continuity; local backup only."""
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
    patterns = ['LEIA-PRIMEIRO.md', 'PASSAGEM-CURADORIA-20261121.txt', 'C2-14-LENTE-PONTUAL-RESULTADO-20261121.md', 'C2-14-PENDENCIAS-20261121.md', 'scripts/sync-github-source-snapshot-v33.py', 'scripts/record-point-lens-delivery.py', 'scripts/verify-native-point-lens-large-plot.py', 'evidence/github-source-sync-20261121h.json', 'evidence/github-source-local-20261121d.json', 'evidence/native-point-lens-20261121a.json', 'evidence/native-point-lens-large-plot-20261121a.json', 'evidence/point-lens-delivery-20261121a.json', 'output/native-point-lens-20261121a/*.png', 'output/native-point-lens-20261121a/created-point-lens-save.json', 'output/native-point-lens-large-plot-20261121a/*.png', 'output/continuity-checkpoint-20261121-lente.txt', 'output/handoff-archive/antes-20261121-entrega0290.txt']
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
                  scope='Incremental local source/evidence backup only. Selected files rehashed; other inventory entries preserved from v32 without rerunning full drivers. No runtimes, personal sessions, binary archives, promotion or publication.')
    receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    path_list = ROOT / 'output/point-lens-backup-20261121b-paths.txt'
    path_list.write_text('\n'.join(changed + ['snapshot-inventory.json'])+'\n', encoding='utf8')
    print(json.dumps(dict(accepted=True, files=len(rows), selected=len(selected), changed=len(changed), unchanged=len(unchanged))))


if __name__ == '__main__':
    main()
