"""Repair only the test fixture and require its fresh receipt before revision launch."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
files=[]
for src,dst in [('verify-is6-dynamics16-service-v2.py','verify-is6-dynamics16-service-v3.py'),
                ('verify-is6-dynamics16-http-v2.py','verify-is6-dynamics16-http-v3.py'),
                ('launch-is6-dynamics16-candidate-v3.py','launch-is6-dynamics16-candidate-v4.py'),
                ('switch-is6-dynamics16-candidate-v3.py','switch-is6-dynamics16-candidate-v4.py')]:
    target=ROOT/'scripts'/dst;assert not target.exists()
    text=(ROOT/'scripts'/src).read_text(encoding='utf8')
    if dst=='verify-is6-dynamics16-service-v3.py':
        old="bridge=Laboratory.__new__(Laboratory);bridge.mode='experiment'";assert text.count(old)==1
        text=text.replace(old,old+";bridge.cloud_supported=False")
    if dst=='verify-is6-dynamics16-http-v3.py':text=text.replace('verify-is6-dynamics16-service-v2.py','verify-is6-dynamics16-service-v3.py')
    if 'candidate-v4' in dst:text=text.replace('20261112b.json','20261112c.json').replace('launch-is6-dynamics16-candidate-v3.py','launch-is6-dynamics16-candidate-v4.py')
    compile(text,str(target),'exec');target.write_text(text,encoding='utf8');files.append(dst)
print(json.dumps(dict(prepared=True,files=files,scope='Test adapter lacked cloud_supported; no product file changed.')))
