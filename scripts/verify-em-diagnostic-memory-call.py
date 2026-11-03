"""Verify the actual Windows memory call used by V2 before another formal profile."""
from pathlib import Path
import hashlib
import json
import urllib.request
import zipfile
import native_product_memory as ram

ROOT=Path(__file__).resolve().parents[1]
receipt=ROOT/'evidence/em-diagnostic-memory-call-20261023.json'
if receipt.exists():raise FileExistsError('Preserve verification.')
session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert session['emViewportCandidate']
forks=json.loads((ROOT/'evidence/em-diagnostic-profile-forks-v2-20261023.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert all(sha(ROOT/p)==digest for p,digest in forks['source_sha256'].items())
expected={session['app'],session['server']}
for family in ['em','em-cloud']:
    state=json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/'+family+'/state',timeout=10))
    if state.get('worker_pid') is not None:expected.add(state['worker_pid'])
readings=[]
for _ in range(3):
    reading=ram.product_memory(session)
    assert expected<={p['pid'] for p in reading['processes']}
    assert reading['sum_working_set_bytes']==sum(p['working_set_bytes'] for p in reading['processes'])
    assert 0<reading['sum_working_set_bytes']<=8*2**30
    readings.append(reading)
report={'schema':1,'accepted':True,'session':session,'expected_product_pids':sorted(expected),
    'readings':readings,'source_sha256':forks['source_sha256']|{'scripts/verify-em-diagnostic-memory-call.py':sha(Path(__file__))},
    'scope':'Three actual Win32 GetProcessMemoryInfo calls with explicit current session; exact sum and root/live-worker coverage. No sustained profile, independent hardware calibration or historical C completion.'}
with zipfile.ZipFile(ROOT/'output/em-diagnostic-profile-forks-v2-20261023/memory-call-verification-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in report['source_sha256']:z.write(ROOT/name,name)
receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'accepted':True,'required_pids':len(expected),'max_working_set_GiB':max(r['sum_working_set_bytes'] for r in readings)/2**30}))
