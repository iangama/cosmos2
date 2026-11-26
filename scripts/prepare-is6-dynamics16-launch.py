"""Prepare a detached launcher and view-preserving switch after isolated service acceptance."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
old=ROOT/'scripts/launch-is6-principal-moons-candidate-v2.py'
target=ROOT/'scripts/launch-is6-dynamics16-candidate.py'
switch=ROOT/'scripts/switch-is6-dynamics16-candidate.py'
assert not target.exists() and not switch.exists()
text=old.read_text(encoding='utf8')
text=text.replace('Launch the isolated principal-moons0.25.0 candidate','Launch the isolated sixteen-center dynamics0.26.0 candidate')
text=text.replace('is6-principal-moons-navigation-product0.25.1','is6-dynamics16-product0.26.0')
text=text.replace("def main():\n", "def main():\n    for kind in ['service','http']:\n        proof=json.loads((ROOT/f'evidence/is6-dynamics16-{kind}-20261112a.json').read_text(encoding='utf8'))\n        assert proof['accepted'] and proof['completed'], 'Service admission must pass before native launch'\n",1)
text=text.replace("IS6-Principal-Moons-0.25.1-unpromoted","IS6-Dynamics16-0.26.0-unpromoted")
text=text.replace("solarInitialFormat='solar_four_physical_centers/1.0.0'","solarInitialFormat='solar_sixteen_physical_centers/0.1.0'")
text=text.replace("        launch['is6PrincipalMoonsCandidate'] = True", "        launch['is6PrincipalMoonsCandidate'] = True\n        launch['is6Dynamics16Candidate'] = True")
compile(text,str(target),'exec');target.write_text(text,encoding='utf8')
text=(ROOT/'scripts/switch-is6-principal-moons-candidate-v2.py').read_text(encoding='utf8')
text=text.replace('is6-principal-moons-navigation-product0.25.1','is6-dynamics16-product0.26.0')
text=text.replace('launch-is6-principal-moons-candidate-v2.py','launch-is6-dynamics16-candidate.py')
text=text.replace('is6-principal-moons-switch-','is6-dynamics16-switch-')
text=text.replace("ROOT/'output/is6-principal-moons-navigation-product0.25.0/app/server.py'", "ROOT/'output/is6-principal-moons-navigation-product0.25.1/app/server.py'")
text=text.replace("    folder.mkdir()", "    for kind in ['service','http']:\n        assert json.loads((ROOT/f'evidence/is6-dynamics16-{kind}-20261112a.json').read_text())['accepted']\n    folder.mkdir()",1)
text=text.replace('Moon candidate','Dynamics16 candidate').replace('moon candidate','dynamics16 candidate')
compile(text,str(switch),'exec');switch.write_text(text,encoding='utf8')
print(json.dumps(dict(prepared=True,launcher=target.name,switch=switch.name)))
