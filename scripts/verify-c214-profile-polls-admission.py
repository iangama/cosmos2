"""Raw-poll regression cases from the real short tooling diagnosis, no new measurement."""
import copy
import hashlib
import json
from pathlib import Path
import c214_profile_history_v3 as admission

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out=ROOT/'evidence/c214-profile-polls-admission-20261121a.json';assert not out.exists()
    source=ROOT/'evidence/c214-history-bootstrap-20261121a.json';diagnosis=json.loads(source.read_text())
    assert diagnosis['accepted'] and diagnosis['completed']
    path=ROOT/'output/c214-history-bootstrap-20261121a/process-polls.jsonl'
    polls=[json.loads(line) for line in path.read_text().splitlines()]
    result=admission.admit(polls,diagnosis['native_history'],diagnosis['initialization'])
    refused=[]
    def check(name,changed,history=None):
        try:admission.admit(changed,history or diagnosis['native_history'],diagnosis['initialization'])
        except (ValueError,KeyError,TypeError):refused.append(name)
        else:raise AssertionError('Unexpected poll admission: '+name)
    check('discarded-initial-poll',polls[1:])
    changed=copy.deepcopy(polls);changed[0]['completed']=False;check('failed-initial-poll',changed)
    changed=copy.deepcopy(polls);changed[1]['gap_s']=.01;check('forged-gap-summary',changed)
    changed=copy.deepcopy(polls);changed[0]['duration_s']=.251;check('overlong-initial-poll',changed)
    changed=copy.deepcopy(diagnosis['native_history']);changed['maximum_poll_gap_s']=.001;check('forged-maximum',polls,changed)
    changed=copy.deepcopy(polls);changed[1]['started_monotonic_s']=changed[0]['started_monotonic_s']+.251;changed[1]['gap_s']=.251;check('unfiltered-slow-poll',changed)
    changed=copy.deepcopy(polls);changed[1]['started_filetime']=changed[0]['finished_filetime']-1;check('overlapping-native-witness',changed)
    check('dropped-final-poll',polls[:-1])
    proof=dict(accepted=True,completed=True,original_admission=result,refusals=refused,
      source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),Path(admission.__file__),source,path]},
      scope='Regression admission only. Uses actual short diagnostic raw polls and explicitly mutated refusal cases; no frames, gauges, product or C2-14 performance acceptance.')
    out.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(dict(accepted=True,refusals=len(refused))))


if __name__=='__main__':main()
