"""Correct the launcher version gate; preserve the failed switch/launcher sources."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
old=ROOT/'scripts/launch-is6-dynamics16-candidate.py'
target=ROOT/'scripts/launch-is6-dynamics16-candidate-v2.py'
switch=ROOT/'scripts/switch-is6-dynamics16-candidate-v2.py'
assert not target.exists() and not switch.exists()
text=old.read_text(encoding='utf8')
assert text.count("manifest['candidate']=='0.25.1'")==1
text=text.replace("manifest['candidate']=='0.25.1'","manifest['candidate']=='0.26.0'")
compile(text,str(target),'exec');target.write_text(text,encoding='utf8')
text=(ROOT/'scripts/switch-is6-dynamics16-candidate.py').read_text(encoding='utf8')
text=text.replace('launch-is6-dynamics16-candidate.py','launch-is6-dynamics16-candidate-v2.py')
text=text.replace("    folder.mkdir()", "    packet=json.loads((TARGET/'build-manifest.json').read_text())\n    assert packet['candidate']=='0.26.0' and packet['promoted'] is False\n    assert all(sha(TARGET/'app'/n)==s for n,s in packet['files_sha256'].items())\n    folder.mkdir()",1)
compile(text,str(switch),'exec');switch.write_text(text,encoding='utf8')
print(json.dumps(dict(prepared=True,launcher=target.name,switch=switch.name,reason='Old launcher retained a0.25.1 version assertion; product service/UI files unchanged.')))
