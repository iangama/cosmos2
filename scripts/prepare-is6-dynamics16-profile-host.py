"""Prepare own profile lifecycle driver and detached opener; no measurement."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
opener=ROOT/'scripts/open-dynamics16-app.py';driver=ROOT/'scripts/run-is6-dynamics16-profile.py'
assert not opener.exists() and not driver.exists()
text=(ROOT/'scripts/open-moons-app.py').read_text(encoding='utf8')
text=text.replace('is6-principal-moons-navigation-product0.25.1','is6-dynamics16-product0.26.2').replace('launch-is6-principal-moons-candidate-v2.py','launch-is6-dynamics16-candidate-v5.py')
text=text.replace('0.25.1','0.26.2').replace('is6-principal-moons-open-','is6-dynamics16-open-').replace('planetas e luas principais','dinâmica dos16corpos')
compile(text,str(opener),'exec');opener.write_text(text,encoding='utf8')
text=(ROOT/'scripts/run-is6-moons-layers-profile.py').read_text(encoding='utf8')
text=text.replace('is6-moons-layers-profile','is6-dynamics16-profile').replace('profile-is6-moons-layers.py','profile-is6-dynamics16.py').replace('audit-is6-moons-layers-profile.py','audit-is6-dynamics16-profile.py')
text=text.replace('is6-principal-moons-navigation-product0.25.1','is6-dynamics16-product0.26.2').replace('launch-is6-principal-moons-candidate-v2.py','launch-is6-dynamics16-candidate-v5.py').replace('open-moons-app.py','open-dynamics16-app.py')
compile(text,str(driver),'exec');driver.write_text(text,encoding='utf8')
print(json.dumps(dict(prepared=True,opener=opener.name,driver=driver.name,measurement_executed=False)))
