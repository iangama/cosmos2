"""Exercise the actual Windows shortcut and confirm reuse of the accepted native app."""
import hashlib
import json
from pathlib import Path
import subprocess
import traceback

ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'evidence/is6-dynamics16-opener-20261112a.json';assert not out.exists()
assert json.loads((ROOT/'evidence/is6-dynamics16-reopen-20261112a.json').read_text())['accepted']
before=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert Path(before['serverScript']).resolve()==ROOT/'output/is6-dynamics16-product0.26.2/app/server.py'
result=dict(accepted=False,shortcut_sha256=hashlib.sha256((ROOT/'Abrir-Dinamica16.cmd').read_bytes()).hexdigest(),before=before)
try:
    test=subprocess.run(['cmd.exe','/c',str(ROOT/'Abrir-Dinamica16.cmd')],cwd=ROOT,stdin=subprocess.DEVNULL,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=45)
    after=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert test.returncode==0 and before==after,(test.returncode,test.stdout,test.stderr)
    result.update(accepted=True,reused_app=before['app'],stdout=test.stdout,stderr=test.stderr,exit=test.returncode)
except Exception:result['failure']=traceback.format_exc()
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:result.get(k) for k in ['accepted','reused_app','failure']}),flush=True)
raise SystemExit(0 if result['accepted'] else 1)
