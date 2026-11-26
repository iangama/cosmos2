"""Real Windows short-child debug-event fixture, separate from the native product."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback
import zipfile

from windows_debug_process_observer import Observer

ROOT = Path(__file__).resolve().parents[1]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and all(ch in 'abcdefghijklmnopqrstuvwxyz0123456789-' for ch in args.label)
    folder = ROOT / f'output/is6-debug-observer-fixture-{args.label}'
    out = ROOT / f'evidence/is6-debug-observer-fixture-{args.label}.json'
    assert not folder.exists() and not out.exists()
    folder.mkdir()
    child = folder / 'short-child-fixture.py'
    child.write_text('import subprocess,sys\nfor code in [0,7,0]:\n p=subprocess.run([sys.executable,"-c","import sys;sys.exit("+str(code)+")"])\n assert p.returncode==code\n', encoding='utf8')
    sources = {path.relative_to(ROOT).as_posix(): sha(path) for path in [Path(__file__), ROOT / 'scripts/windows_debug_process_observer.py', child]}
    with zipfile.ZipFile(folder / 'executed-sources.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for name in sources:
            archive.write(ROOT / name, name)
    result = dict(accepted=False, completed=False, source_sha256=sources, scope='Own short Python processes only; native engine untouched. Proves exact native creation/exit evidence including a deliberately nonzero exit7; not a product/performance acceptance.')
    observer = None
    try:
        with (folder / 'events.jsonl').open('x', encoding='utf8') as stream, (folder / 'child.log').open('xb') as log:
            def emit(row):
                stream.write(json.dumps(row, ensure_ascii=False) + '\n'); stream.flush()
            observer = Observer(emit)
            pid = observer.start([sys.executable, '-Xutf8', str(child)], ROOT, log)
            deadline = time.monotonic()+45
            while not observer.finished():
                assert time.monotonic() < deadline, 'Debug fixture timeout'
                observer.pump()
            records = list(observer.records.values())
            assert observer.child.wait(timeout=3) == 0
            all_short = [record for record in records if '-c' in record['command_line']]
            short_parents = {record['parent'] for record in all_short}
            short = [record for record in all_short if record['pid'] not in short_parents]
            assert len(short) == 3 and sorted(record['exit']['code'] for record in short) == [0,0,7]
            assert all(record['exit']['exited_filetime'] >= record['created_filetime'] for record in records)
            assert all(sha(ROOT / name) == seal for name, seal in sources.items())
            result.update(accepted=True, completed=True, root_pid=pid, records=records, events=observer.events,
                          data_sha256=sha(folder / 'events.jsonl'))
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        if observer:
            observer.close()
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({key:result.get(key) for key in ['accepted','completed','events','failure']}), flush=True)
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
