"""Durable Windows K2 collector and independent audit; never replaces receipts."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import traceback

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    base = ROOT / ('output/is6-pair-profile-' + args.label + '-driver')
    receipt = base.with_suffix('.json')
    python = ROOT / '.tooling/python/Scripts/python.exe'
    if not args.worker:
        if receipt.exists() or base.with_suffix('.log').exists():
            raise FileExistsError('Preserve driver evidence')
        with base.with_suffix('.log').open('wb') as out, base.with_name(base.name + '-errors').with_suffix('.log').open('wb') as err:
            child = subprocess.Popen([str(python), '-u', '-Xutf8', str(Path(__file__)), '--label', args.label, '--worker'],
                cwd=ROOT, stdout=out, stderr=err, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        receipt.write_text(json.dumps(dict(pid=child.pid, completed=False, started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
            driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()), indent=2) + '\n', encoding='utf8')
        print(json.dumps(dict(pid=child.pid)))
        return
    r = dict(pid=os.getpid(), completed=False)
    try:
        work = subprocess.run([str(python), '-u', '-Xutf8', str(ROOT / 'scripts/benchmark-is6-layer-pair-native.py'), '--label', args.label], cwd=ROOT)
        r['verification_exit'] = work.returncode
        if work.returncode == 0:
            audit = subprocess.run([str(python), '-u', '-Xutf8', str(ROOT / 'scripts/audit-is6-layer-pair-profile.py'), '--label', args.label], cwd=ROOT)
            r['audit_exit'] = audit.returncode
        r['completed'] = True
    except Exception:
        r['failure'] = traceback.format_exc()
        raise
    finally:
        receipt.write_text(json.dumps(r, indent=2) + '\n', encoding='utf8')


if __name__ == '__main__':
    main()
