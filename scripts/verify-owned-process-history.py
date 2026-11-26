"""Real short-child identity/zero-exit proof and deliberate nonzero refusal, away from the product."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
import zipfile

from owned_process_history import History, FILES

ROOT = Path(__file__).resolve().parents[1]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and all(ch in 'abcdefghijklmnopqrstuvwxyz0123456789-' for ch in args.label)
    folder = ROOT / f'output/is6-owned-history-fixture-{args.label}'
    out = ROOT / f'evidence/is6-owned-history-fixture-{args.label}.json'
    assert not folder.exists() and not out.exists()
    folder.mkdir()
    fixture = folder / 'fixture.py'
    fixture.write_text('''import json,subprocess,sys,time
from pathlib import Path
folder=Path(sys.argv[1]);last=None
while not (folder/'stop.json').exists():
 p=folder/'command.json'
 if p.exists():
  command=json.loads(p.read_text())
  if command['id']!=last:
   last=command['id']
   child=subprocess.Popen([sys.executable,'-c','import time,sys;time.sleep(.2);sys.exit('+str(command['code'])+')'])
   child.wait()
   (folder/('done-'+str(last)+'.json')).write_text(json.dumps({'code':child.returncode}))
 time.sleep(.01)
''', encoding='utf8')
    sources = {p.relative_to(ROOT).as_posix(): sha(p) for p in [Path(__file__), *FILES, fixture]}
    with zipfile.ZipFile(folder / 'executed-sources.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for name in sources:
            archive.write(ROOT / name, name)
    answer = dict(accepted=False, completed=False, source_sha256=sources, refusals=[],
                  scope='Own fixture roots only, native product untouched. All zero-code child lifetimes retained and a later code7 must invalidate the observer.')
    roots, histories, streams = [], [], []
    try:
        for name in ['a', 'b']:
            sub = folder / name; sub.mkdir()
            stream = (sub / 'child.log').open('xb'); streams.append(stream)
            roots.append(subprocess.Popen([sys.executable, '-Xutf8', str(fixture), str(sub)], cwd=ROOT,
                                          stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT))
        session = dict(app=roots[0].pid, server=roots[1].pid)
        history = History(session, folder / 'events.jsonl'); histories.append(history); history.start()
        before = history.snapshot()
        (folder / 'a/command.json').write_text(json.dumps(dict(id=1, code=0)))
        deadline = time.monotonic()+10
        while not (folder / 'a/done-1.json').exists():
            assert time.monotonic() < deadline
            history.snapshot(); time.sleep(.01)
        time.sleep(.1)
        positive = history.export()
        exited = [record for record in positive['records'] if record['exit'] is not None]
        assert len(exited) >= 1 and all(record['exit']['code'] == 0 and
                                       record['exit']['exited_filetime'] >= record['identity']['created_filetime'] for record in exited)
        assert any('-c' in (record['command_line'] or []) for record in exited)
        assert {row['pid'] for row in before['owned']} <= {record['identity']['pid'] for record in positive['records']}
        answer['positive_history'] = positive
        (folder / 'a/command.json').write_text(json.dumps(dict(id=2, code=7)))
        deadline = time.monotonic()+10
        while history.failure is None:
            assert time.monotonic() < deadline
            time.sleep(.01)
        assert 'exited nonzero' in history.failure and '/7' in history.failure
        try:
            history.snapshot()
        except AssertionError as error:
            assert 'exited nonzero' in str(error)
            answer['refusals'].append(dict(name='nonzero-owned-child', failure=history.failure))
        else:
            raise AssertionError('Nonzero child history accepted')
        assert all(sha(ROOT / name) == seal for name, seal in sources.items())
        answer.update(accepted=True, completed=True)
    except Exception:
        answer['failure'] = traceback.format_exc()
    finally:
        for history in histories:
            history.close()
        for name in ['a', 'b']:
            (folder / name / 'stop.json').write_text('{}')
        for process in roots:
            assert process.wait(timeout=10) == 0
        for stream in streams:
            stream.close()
        out.write_text(json.dumps(answer, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({key:answer.get(key) for key in ['accepted','completed','failure']}), flush=True)
    return 0 if answer['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
