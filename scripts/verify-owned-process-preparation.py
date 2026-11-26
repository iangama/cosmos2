"""Exercise admission and rejection with a virtual clock, without a native host."""
from pathlib import Path
import argparse
import hashlib
import json
from owned_process_preparation import stabilize

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
    parser.error('Invalid label')
out=ROOT/('evidence/owned-process-preparation-'+args.label+'.json')
if out.exists():raise FileExistsError('Preserve preparation verification')

class Clock:
    def __init__(self):self.now=0
    def time(self):return self.now
    def sleep(self,seconds):self.now+=seconds

A=[dict(pid=12,created_filetime=100)]
B=[dict(pid=13,created_filetime=200)]
checks=[]

def execute(items,expected_count,expected_error=None,late=False):
    clock=Clock();observations=[];calls=[]
    def inventory():
        item=items[min(len(calls),len(items)-1)];calls.append(item)
        if late:clock.now+=46
        if isinstance(item,Exception):raise item
        return item
    try:
        result=stabilize(inventory,observations.append,clock=clock.time,sleep=clock.sleep)
    except Exception as error:
        assert expected_error is not None and isinstance(error,expected_error),repr(error)
        result=None
    else:
        assert expected_error is None
        assert result['consecutive_stable']==5
    assert len(calls)==expected_count,(len(calls),expected_count)
    return observations,result

rows,result=execute([A],5);assert len(rows)==5 and result['elapsed_s']==4
checks.append('five equal valid snapshots before admission')
rows,result=execute([A]*4+[ValueError('Unresolved candidate in owned snapshot: pid=33 parent=12')]+[A]*5,10)
assert rows[4]['consecutive_stable']==0 and rows[-1]['consecutive_stable']==5
checks.append('transient refusal resets the consecutive count and is retained')
rows,result=execute([A]*4+[B]*5,9);assert rows[4]['consecutive_stable']==1
checks.append('identity change restarts the count')
rows,result=execute([OSError('native candidate vanished')],45,TimeoutError)
assert len(rows)==45 and all(row['consecutive_stable']==0 for row in rows)
checks.append('persistent native refusal reaches deadline without admission')
rows,result=execute([ValueError('Cycle in owned Windows process snapshot')],1,ValueError)
assert rows==[]
checks.append('structural failure propagates immediately')
rows,result=execute([A],1,TimeoutError,late=True);assert len(rows)==1
checks.append('late inventory cannot pass the deadline')
rows,result=execute([ValueError('Restart after owned process reader source changes')],1,ValueError)
assert rows==[]
checks.append('changed source generation is not retried')
result=dict(accepted=True,completed=True,checks=checks,native_calls=0,
 source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),ROOT/'scripts/owned_process_preparation.py',ROOT/'IS-6-IMPORTACAO-ESPACIAL-PREPARACAO-V4.md']})
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(accepted=True,checks=len(checks),native_calls=0)))
