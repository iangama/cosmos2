"""Remove exactly the temporary view left by failed switchB, keeping an audit receipt."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
identifier='47d2e011fe2f4be9b3ade85cb9e3e08b'
out=ROOT/'evidence/is6-dynamics16-switch-favorite-cleanup-20261112a.json'
assert not out.exists()
session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert Path(session['serverScript']).resolve()==ROOT/'output/is6-dynamics16-product0.26.0/app/server.py'
def get():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/navigation/favorites'))['views']
before=get();row=next((r for r in before if r['id']==identifier),None)
if row:
    assert row['name']=='Vista anterior à troca'
    request=urllib.request.Request('http://127.0.0.1:4700/api/navigation/delete',data=json.dumps(dict(id=identifier)).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=20) as response:assert json.load(response)['ok']
after=get();assert after==[r for r in before if r['id']!=identifier]
result=dict(accepted=True,removed_id=identifier if row else None,before=before,after=after,
            script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),reason='Only the test-created temporary view from refused switchB; no owner favorite selected.')
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(accepted=True,removed=bool(row))))
