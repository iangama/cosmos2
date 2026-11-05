"""Pure ownership admission; synthetic process cases do not claim native sampling."""
from pathlib import Path
import copy
import hashlib
import json
import owned_process_snapshot as ownership

ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'evidence/owned-process-classification-20261105a.json'
if out.exists():
    raise FileExistsError('Preserve ownership proof')
rows={1:dict(pid=1,parent=0,created_filetime=20),2:dict(pid=2,parent=1,created_filetime=21),
      3:dict(pid=3,parent=2,created_filetime=22),4:dict(pid=4,parent=1,created_filetime=10),
      5:dict(pid=5,parent=0,created_filetime=15)}
scope=ownership.classify(rows,{1},lambda pid:copy.deepcopy(rows[pid]))
assert [row['pid'] for row in scope['owned']]==[1,2,3]
assert [row['pid'] for row in scope['excluded_old_parent_links']]==[4]
assert ownership.classify(rows,{1,5},lambda pid:copy.deepcopy(rows[pid]))['owned'][-1]['pid']==5
refusals=[]
for name,edit,reader in [
    ('Missing root',lambda r:r.pop(1),None),
    ('Parent changed after snapshot',lambda r:None,lambda pid:{**rows[pid],'parent':99} if pid==2 else rows[pid]),
    ('Candidate disappeared',lambda r:None,lambda pid:(_ for _ in ()).throw(OSError('Gone')) if pid==2 else rows[pid]),
    ('Root cycle',lambda r:r[1].update(parent=3),None),
]:
    current=copy.deepcopy(rows)
    edit(current)
    try:
        ownership.classify(current,{1},reader or (lambda pid:copy.deepcopy(current[pid])))
    except (ValueError,OSError) as error:
        refusals.append(dict(case=name,error=str(error)))
    else:
        raise AssertionError('Invalid ownership accepted: '+name)
result=dict(accepted=True,completed=True,source_sha256={
    Path(__file__).relative_to(ROOT).as_posix():hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    **ownership.generation()['source_sha256']},owned=[1,2,3],excluded_old_parent=[4],refusals=refusals,
    scope='CPU synthetic ownership classification only; no native process enumeration, GPU sampling or performance acceptance.')
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(accepted=True,refusals=len(refusals))))
