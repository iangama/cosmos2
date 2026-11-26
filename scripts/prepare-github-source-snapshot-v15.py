"""Extend the existing local-only backup recipe to the sixteen-center product/evidence."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'scripts/sync-github-source-snapshot-v15.py';assert not target.exists()
text=(ROOT/'scripts/sync-github-source-snapshot-v14.py').read_text(encoding='utf8')
anchor="patterns = ['*.md',"
extra="patterns = ['output/is6-dynamics16-ui-staging/**/*',\n            'output/is6-dynamics16-product0.26.*/app/**/*',\n            'output/is6-dynamics16-product0.26.*/build-manifest.json',\n            'output/is6-dynamics16-product0.26.*/execution-logs/**/*',\n            'output/is6-dynamics16-native-*/*.png',\n            'output/is6-dynamics16-service-*/**/*.json',\n            'output/is6-dynamics16-http-*/**/*.json',\n            'output/is6-dynamics16-gpu-adapter-*/*.json',\n            'output/is6-dynamics16-switch-*/*.log',\n            'output/is6-dynamics16-profile-*/*.json',\n            'output/is6-dynamics16-profile-*/*.log',\n            'Abrir-Dinamica16.cmd', '*.md',"
assert text.count(anchor)==1;text=text.replace(anchor,extra)
text=text.replace('Preserve the expanded scene compound journeys, original captures and own profile locally.',
                  'Preserve sixteen-center dynamics sources, native originals and own profile locally; never push.')
compile(text,str(target),'exec');target.write_text(text,encoding='utf8')
print(json.dumps(dict(prepared=True,script=target.name,backup_executed=False,remote_push=False)))
