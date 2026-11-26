"""Record candidate identity failures with the original Toolhelp names; no performance acceptance."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import time
import traceback
import zipfile

import owned_process_snapshot_diagnostic as reader

ROOT = Path(__file__).resolve().parents[1]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and all(ch in 'abcdefghijklmnopqrstuvwxyz0123456789-' for ch in args.label)
    folder = ROOT / f'output/is6-expanded-process-diagnosis-{args.label}'
    out = ROOT / f'evidence/is6-expanded-process-diagnosis-{args.label}.json'
    assert not folder.exists() and not out.exists()
    session_path = ROOT / 'output/session.json'
    session = json.loads(session_path.read_text(encoding='utf-8-sig'))
    assert Path(session['serverScript']).resolve() == ROOT / 'output/is6-expanded-journey-product0.27.0/app/server.py'
    sources = {path.relative_to(ROOT).as_posix(): sha(path) for path in [Path(__file__), Path(reader.__file__), *reader.FILES[1:]]}
    folder.mkdir()
    with zipfile.ZipFile(folder / 'executed-sources.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for name in sources:
            archive.write(ROOT / name, name)
    result = dict(completed=False, diagnostic_only=True, profile_accepted=False, session=session, source_sha256=sources,
                  samples=0, errors=0, scope='120 seconds of two native ownership snapshots per second in the existing Atlas; captures raw Toolhelp entries on failure, never substitutes a valid inventory or accepts GPU residence.')
    began = time.monotonic()
    with (folder / 'snapshots.jsonl').open('x', encoding='utf8') as stream:
        for index in range(240):
            remaining = began + index * .5 - time.monotonic()
            if remaining > 0:
                time.sleep(remaining)
            row = dict(index=index, utc=dt.datetime.now(dt.timezone.utc).isoformat())
            try:
                row['snapshot'] = reader.snapshot(session)
            except Exception as error:
                row.update(failure=traceback.format_exc(), toolhelp_entries=getattr(error, 'toolhelp_entries', None))
                result['errors'] += 1
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')
            stream.flush()
            result['samples'] = index + 1
            if index % 20 == 0:
                out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    assert json.loads(session_path.read_text(encoding='utf-8-sig')) == session
    assert all(sha(ROOT / name) == seal for name, seal in sources.items())
    result.update(completed=True, data_sha256=sha(folder / 'snapshots.jsonl'), wall_s=time.monotonic()-began)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
