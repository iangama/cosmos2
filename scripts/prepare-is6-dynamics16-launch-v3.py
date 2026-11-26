"""Prepare launcher/switch for revision0.26.1, preserving the0.26.0 receipts."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'scripts/launch-is6-dynamics16-candidate-v3.py'
switch=ROOT/'scripts/switch-is6-dynamics16-candidate-v3.py'
assert not target.exists() and not switch.exists()
text=(ROOT/'scripts/launch-is6-dynamics16-candidate-v2.py').read_text(encoding='utf8')
text=text.replace('0.26.0','0.26.1').replace('20261112a.json','20261112b.json')
compile(text,str(target),'exec');target.write_text(text,encoding='utf8')
text=(ROOT/'scripts/switch-is6-dynamics16-candidate-v2.py').read_text(encoding='utf8')
text=text.replace('0.26.0','0.26.1').replace('launch-is6-dynamics16-candidate-v2.py','launch-is6-dynamics16-candidate-v3.py').replace('20261112a.json','20261112b.json')
anchor="ROOT/'output/is6-principal-moons-navigation-product0.25.1/app/server.py',TARGET/'app/server.py'"
assert text.count(anchor)==1
text=text.replace(anchor,"ROOT/'output/is6-principal-moons-navigation-product0.25.1/app/server.py',ROOT/'output/is6-dynamics16-product0.26.0/app/server.py',TARGET/'app/server.py'")
compile(text,str(switch),'exec');switch.write_text(text,encoding='utf8')
print(json.dumps(dict(prepared=True,version='0.26.1',launcher=target.name,switch=switch.name)))
