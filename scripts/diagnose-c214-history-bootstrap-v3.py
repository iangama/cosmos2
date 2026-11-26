"""Single discovery-only preflight on the live owner tree; no GPU gauges or UI actions."""
from pathlib import Path
import hashlib
import json
import traceback
import urllib.request

from owned_process_history_v2 import History,FILES
import windows_gpu_pdh_v2 as pdh
import expanded_residency_timing as timing
import c214_profile_history_v3 as raw_history

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'output/c214-history-bootstrap-20261121a'
OUT=ROOT/'evidence/c214-history-bootstrap-20261121a.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def get(path):return json.load(urllib.request.urlopen('http://127.0.0.1:4700'+path,timeout=10))
def scenario():
    s=get('/api/state');n=get('/api/navigation/state')
    return dict(mode=s['mode'],renderer_confirmed=bool(n['navigation']['Anchor']),anchor=n['navigation']['Anchor'],et=n['et'])


def main():
    assert not FOLDER.exists() and not OUT.exists();FOLDER.mkdir()
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    proof=dict(accepted=False,completed=False,session=session,initialization={},
      source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),*FILES,Path(raw_history.__file__)]},
      scope='Discovery-only tooling preflight on the current owned process tree. No PDH gauge collection, CEF navigation or product commands. All initial/native polls count, strict0.25s/10s bounds retained. No C2-14 performance acceptance.')
    before=get('/api/state')
    tracker=History(session,FOLDER/'process-history.jsonl')
    try:
        tracker.start()
        timing.initialize(proof['initialization'],lambda:dict(kind='prepare'),scenario,tracker,pdh.Query)
        proof['bootstrap_admission']=timing.admit_bootstrap(proof['initialization'],session)
        tracker.snapshot()
        assert get('/api/state')==before,'Owner state changed during read-only diagnosis'
    except Exception:proof['failure']=traceback.format_exc()
    finally:
        tracker.close();proof['native_history']=tracker.export()
        polls=[json.loads(line) for line in (FOLDER/'process-polls.jsonl').read_text().splitlines()]
        try:
            proof['raw_poll_admission']=raw_history.admit(polls,proof['native_history'],proof['initialization'])
            if not proof.get('failure'):proof.update(accepted=True,completed=True)
        except Exception:proof['raw_poll_failure']=traceback.format_exc()
        proof['raw_sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in FOLDER.rglob('*.jsonl')}
        OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:proof.get(k) for k in ['accepted','completed','bootstrap_admission','raw_poll_admission','failure','raw_poll_failure']}))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
