"""Launcher CLI: wait for the owned HTTP server, recording a clear failure."""
from pathlib import Path
import argparse
import hashlib
import json
import psutil
import sys
from native_ui_readiness import wait_for_ui

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server-pid', type=int, required=True)
    parser.add_argument('--timeout', type=float, default=240)
    parser.add_argument('--receipt', default='output/local-ui-readiness.json')
    args = parser.parse_args()
    out = Path(args.receipt)
    out = (out if out.is_absolute() else ROOT / out).resolve()
    if not out.is_relative_to((ROOT / 'output').resolve()):
        parser.error('Readiness receipts must remain under output')
    r = dict(accepted=False, completed=False, server_pid=args.server_pid,
             source_sha256={p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in [Path(__file__), ROOT / 'scripts/native_ui_readiness.py']})
    try:
        process = psutil.Process(args.server_pid)
        created = process.create_time()
        def alive():
            try:
                current = psutil.Process(args.server_pid)
                return current.create_time() == created and current.is_running() and current.status() != psutil.STATUS_ZOMBIE
            except psutil.NoSuchProcess:
                return False
        r.update(wait_for_ui(timeout_s=args.timeout, child_alive=alive), accepted=True, completed=True,
                 server_created_unix=created)
    except Exception as error:
        r.update(completed=True, error=type(error).__name__ + ': ' + str(error))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(r, ensure_ascii=False))
    return 0 if r['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
