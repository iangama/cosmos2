"""Stage the explicit sixteen-center parser and stable IDs; no app switch or service launch."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/is6-principal-moons-navigation-product0.25.1/app'
FOUNDATION=ROOT/'output/is6-dynamics16-staging'
TARGET=ROOT/'output/is6-dynamics16-ui-staging'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((ROOT/'evidence/is6-dynamics16-audit-20261112b.json').read_text())['accepted']
assert not TARGET.exists(),'Preserve prepared staging'
registry=(BASE/'body_registry.py').read_text(encoding='utf8')
old='(?:10|399|301|599)'
new='(?:10|199|299|399|301|499|599|699|799|899|501|502|503|504|602|606)'
assert registry.count(old)==1
registry=registry.replace(old,new)
dispatch=(BASE/'import_dispatch.py').read_text(encoding='utf8')
anchor='def validate(value):\n'
assert dispatch.count(anchor)==1
dispatch=dispatch.replace(anchor,anchor+"    if isinstance(value, dict) and value.get('kind') == 'solar_sixteen_physical_centers':\n        from system16_import import validate as sixteen_validate\n        return sixteen_validate(value)\n")
TARGET.mkdir()
for name,value in [('body_registry.py',registry),('import_dispatch.py',dispatch)]:
    compile(value,name,'exec')
    (TARGET/name).write_text(value,encoding='utf8')
for name in ['system16_import.py','system16_frames.py']:
    shutil.copy2(FOUNDATION/name,TARGET/name)
sources=[Path(__file__),BASE/'body_registry.py',BASE/'import_dispatch.py',
         FOUNDATION/'system16_import.py',FOUNDATION/'system16_frames.py',
         ROOT/'IS-6-DINAMICA16-INTERFACE-CONTRATO.md',ROOT/'evidence/is6-dynamics16-audit-20261112b.json']
r=dict(prepared=True,accepted=False,promoted=False,
       source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in sources},
       files_sha256={p.name:sha(p) for p in TARGET.glob('*.py')},
       pending=['Session generation metadata and sixteen-body contribution reading','Dedicated UTC API','UI control and model/domain text','Service/persistence/legacy tests','Own native journey, visual and profile'],
       scope='Staged source only; incomplete product, no service launched and owner app unchanged.')
(TARGET/'backend-preparation.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(prepared=True,files=len(r['files_sha256']),service_executed=False)))
