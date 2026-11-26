"""Preserve large own JSONL byte-for-byte in bounded chunks for the local source snapshot."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 40 * 2**20


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(2**20), b''):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--source', required=True)
    args = parser.parse_args()
    assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
    source = (ROOT / args.source).resolve()
    assert source.is_relative_to(ROOT / 'output') and source.suffix == '.jsonl'
    folder = ROOT / f'output/github-source-chunks-{args.label}'
    assert not folder.exists()
    folder.mkdir()
    original = digest(source)
    rows, destination, handle, size, line_count = [], None, None, 0, 0
    try:
        with source.open('rb') as stream:
            for line in stream:
                assert line.endswith(b'\n') and len(line) <= LIMIT, 'Incomplete/oversized JSONL line'
                if handle is None or size+len(line) > LIMIT:
                    if handle:
                        handle.close()
                        rows.append(dict(path=destination.relative_to(ROOT).as_posix(), bytes=size, lines=line_count, sha256=digest(destination)))
                    destination = folder / f'part-{len(rows):04d}.jsonl'
                    handle = destination.open('xb')
                    size, line_count = 0, 0
                handle.write(line)
                size += len(line)
                line_count += 1
        assert handle is not None
        handle.close()
        rows.append(dict(path=destination.relative_to(ROOT).as_posix(), bytes=size, lines=line_count, sha256=digest(destination)))
    finally:
        if handle:
            handle.close()
    combined = hashlib.sha256()
    for item in rows:
        with (ROOT / item['path']).open('rb') as stream:
            for block in iter(lambda: stream.read(2**20), b''):
                combined.update(block)
    assert combined.hexdigest() == original == digest(source)
    assert sum(item['bytes'] for item in rows) == source.stat().st_size
    result = dict(accepted=True, completed=True, source=source.relative_to(ROOT).as_posix(),
                  source_sha256=original, source_bytes=source.stat().st_size, chunks=rows,
                  concatenation_sha256=combined.hexdigest(), lines=sum(item['lines'] for item in rows),
                  script_sha256=digest(Path(__file__)),
                  reconstruction='Concatenate chunk bytes in the listed order; the result must match source_sha256.')
    (folder / 'manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps({k: v for k, v in result.items() if k != 'chunks'}), flush=True)


if __name__ == '__main__':
    main()
