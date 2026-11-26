"""Native Windows fixtures for retained birth/exit, RAM and raw polling cadence."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time
import traceback

from owned_process_history_v2 import History,FILES
import owned_process_memory as memory
import expanded_residency_history_audit_v2 as audit

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'output/c214-history-v2-fixtures-20261121a'
OUT=ROOT/'evidence/c214-history-v2-fixtures-20261121a.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not FOLDER.exists() and not OUT.exists();FOLDER.mkdir()
    proof=dict(accepted=False,completed=False,checks=[],sources={p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),*FILES]},
      scope='Real Windows fixture processes only, separate from Cosmos2: retain native identity and signal/time proof, read RAM on retained handle, refuse deliberate exit7, rederive observer cadence from every raw poll. No GPU gauges, product frames or performance acceptance.')
    root=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
    session=dict(app=os.getpid(),server=root.pid)
    tracker=None
    try:
        folder=FOLDER/'normal';folder.mkdir();tracker=History(session,folder/'process-history.jsonl');tracker.start()
        first=tracker.snapshot();ram={};memory.collect(memory.Reader(tracker),first['owned'],ram)
        assert ram['sum_working_set_bytes']>0 and all(row['api_called'] and row['api_return'] for row in ram['processes'])
        child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(.3)'])
        assert child.pid in {row['pid'] for row in tracker.snapshot()['owned']}
        assert child.wait(timeout=5)==0
        final=tracker.snapshot();history=tracker.export();known=audit.records(history,session)
        assert known[child.pid]['exit']['code']==0 and known[child.pid]['last_native']['wait']==0
        assert known[child.pid]['identity']['parent_created_filetime']==known[os.getpid()]['identity']['created_filetime']
        deadline=time.monotonic()+2
        while time.monotonic()<deadline:tracker.snapshot();time.sleep(.025)
        history=tracker.export();tracker.close();tracker=None
        polls=[json.loads(line) for line in (folder/'process-polls.jsonl').read_text().splitlines()]
        gaps=[row['started_monotonic_s']-before['started_monotonic_s'] for before,row in zip(polls,polls[1:])]
        assert all(row['completed'] and row['index']==i and row['finished_filetime']>=row['started_filetime'] for i,row in enumerate(polls))
        assert abs(max(gaps)-history['maximum_poll_gap_s'])<1e-8 and max(gaps)<=.25
        assert len(polls)==history['polls'] and polls[0]['gap_s'] is None
        proof['checks'].append(dict(name='native-identity-ram-zero-exit-and-initial-inclusive-cadence',polls=len(polls),maximum_gap_s=max(gaps),first_poll_s=polls[0]['duration_s'],RAM=ram))
        folder=FOLDER/'exit7';folder.mkdir();tracker=History(session,folder/'process-history.jsonl');tracker.start()
        child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(.3);raise SystemExit(7)'])
        assert child.pid in {row['pid'] for row in tracker.snapshot()['owned']}
        assert child.wait(timeout=5)==7
        refused=False
        try:tracker.snapshot()
        except AssertionError as error:
            refused='nonzero' in str(error);proof['exit7_refusal']=str(error)
        assert refused,'A nonzero owned exit must refuse the observer'
        proof['checks'].append(dict(name='deliberate-nonzero-exit-is-refused',exit_code=7))
        proof.update(accepted=True,completed=True)
    except Exception:proof['failure']=traceback.format_exc()
    finally:
        if tracker:tracker.close()
        if root.poll() is None:root.terminate();root.wait(timeout=5)
        proof['raw_sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in FOLDER.rglob('*.jsonl')}
        OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:proof.get(k) for k in ['accepted','completed','failure','exit7_refusal']}))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
