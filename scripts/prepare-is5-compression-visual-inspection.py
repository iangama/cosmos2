"""Preserve original captures and create exact RGB inspection copies."""
from pathlib import Path
import argparse
import hashlib
import json
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    receipt=ROOT/f'evidence/is5-native-compression-{args.label}.json'
    native=json.loads(receipt.read_text());assert native['accepted'] and native['completed']
    captures=list(native['captures']);additional=[]
    supplement=ROOT/f'evidence/is5-compression-visual-supplement-{args.label}.json'
    if supplement.exists():
        extra=json.loads(supplement.read_text());assert extra['accepted'] and extra['completed']
        captures.extend(extra['captures'])
        additional.append(dict(path=supplement.relative_to(ROOT).as_posix(),sha256=sha(supplement)))
    assert len({r['path'] for r in captures})==len(captures)
    folder=ROOT/f'output/is5-compression-visual-review-{args.label}'
    if folder.exists():raise FileExistsError('Preserve visual inspection copies')
    folder.mkdir();rows=[]
    for row in captures:
        source=ROOT/row['path'];assert sha(source)==row['sha256']
        image=Image.open(source);assert image.size==(1920,1080)
        target=folder/source.name
        image.convert('RGB').save(target)
        assert Image.open(target).tobytes()==image.convert('RGB').tobytes()
        rows.append(dict(original=row['path'],original_sha256=row['sha256'],
                         inspection=target.relative_to(ROOT).as_posix(),inspection_sha256=sha(target),
                         original_mode=image.mode,RGB_unchanged=True))
    manifest=dict(accepted=False,scope='Exact RGB inspection copies of Win32 captures; originals unchanged. A separate visual review is required.',
                  native_receipt=receipt.relative_to(ROOT).as_posix(),native_receipt_sha256=sha(receipt),
                  additional_receipts=additional,
                  script_sha256=sha(Path(__file__)),captures=rows)
    (folder/'inspection-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(prepared=True,accepted=False,captures=len(rows),folder=str(folder))))


if __name__=='__main__':main()
