"""Windows fixture: real retained child RAM, then explicit zero-exit exclusion; owner app untouched."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import zipfile

import psutil

from owned_process_history import History
from owned_process_memory import Reader, collect
import expanded_residency_memory_audit as audit

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and len(args.label) <= 20 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
    folder = ROOT / f'output/is6-owned-memory-fixture-{args.label}'
    out = ROOT / f'evidence/is6-owned-memory-fixture-{args.label}.json'
    assert not folder.exists() and not out.exists()
    names = ['scripts/verify-owned-process-memory-v3.py', 'scripts/owned_process_memory.py',
             'scripts/owned_process_history.py', 'scripts/owned_process_snapshot.py',
             'scripts/expanded_residency_memory_audit.py', 'IS-6-PERCURSO-AMPLIADO16-RESIDENCIA-REVISAO-G.md']
    sources = {name: sha(ROOT / name) for name in names}
    folder.mkdir()
    with zipfile.ZipFile(folder / 'executed-sources.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for name in sources:
            archive.write(ROOT / name, name)
    result = dict(accepted=False, completed=False, source_sha256=sources, witnesses=[],
                  scope='Controlled own-child native memory fixture only, no application journey or performance acceptance.')
    children, tracker = [], None
    try:
        def child(megabytes):
            code = 'import sys; block=bytearray(' + str(megabytes) + '*1024*1024);print("ready",flush=True);sys.stdin.buffer.read(1)'
            p = subprocess.Popen([psutil.Process().exe(), '-u', '-c', code], cwd=ROOT, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            children.append(p)
            assert p.stdout.readline().strip() == b'ready'
            return p

        anchor, target = child(1), child(20)
        session = dict(app=os.getpid(), server=anchor.pid)
        tracker = History(session, folder / 'process-history.jsonl')
        tracker.start()
        reader = Reader(tracker)
        identity = next(row for row in tracker.snapshot()['owned'] if row['pid'] == target.pid)
        before = tracker.clock()
        measured = collect(reader, [identity], {})
        result['pending_ram'] = measured
        after = tracker.clock()
        witness = tracker.export()
        by_pid = {record['identity']['pid']: record for record in witness['records']}
        summary = audit.admit(measured, {target.pid: identity}, by_pid, before, after)
        assert summary['measured'] == 1 and summary['completed_before_read'] == 0
        # Committed/private bytes and residency differ; the OS can keep zero pages nonresident.
        assert measured['processes'][0]['private_bytes'] >= 20 * 2**20
        assert measured['processes'][0]['working_set_bytes'] > 0
        result['witnesses'].append(dict(name='live-child-20MiB', ram=copy.deepcopy(measured), summary=summary,
                                        interval=[before, after], identity=identity, native_history=witness))
        target.stdin.write(b'x'); target.stdin.flush()
        assert target.wait(timeout=15) == 0
        before = tracker.clock()
        ended = collect(reader, [identity], {})
        after = tracker.clock()
        witness = tracker.export()
        by_pid = {record['identity']['pid']: record for record in witness['records']}
        summary = audit.admit(ended, {target.pid: identity}, by_pid, before, after)
        assert summary['completed_before_read'] == 1 and not ended['processes'] and ended['sum_working_set_bytes'] == 0
        assert ended['completed_before_read'][0]['api_called'] is False
        result['witnesses'].append(dict(name='signaled-zero-child-excluded-without-reading', ram=ended,
                                       summary=summary, interval=[before, after], identity=identity, native_history=witness))
        assert all(sha(ROOT / name) == seal for name, seal in sources.items())
        result.pop('pending_ram', None)
        result.update(accepted=True, completed=True)
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        if tracker:
            tracker.close()
        result['child_exits'] = []
        for p in children:
            try:
                if p.poll() is None:
                    p.stdin.write(b'x'); p.stdin.flush()
                code = p.wait(timeout=15)
                result['child_exits'].append(dict(pid=p.pid, code=code))
                assert code == 0
            except Exception:
                result['cleanup_failure'] = traceback.format_exc()
                result.update(accepted=False, completed=False)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(accepted=result['accepted'], completed=result['completed'], child_exits=result['child_exits'],
                          failure=result.get('failure'), cleanup_failure=result.get('cleanup_failure'))), flush=True)
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
