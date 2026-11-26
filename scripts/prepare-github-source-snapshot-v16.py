"""Extend local backup to the prepared expanded journey and its first service receipts."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'scripts/sync-github-source-snapshot-v16.py';assert not target.exists()
text=(ROOT/'scripts/sync-github-source-snapshot-v15.py').read_text(encoding='utf8')
old="patterns = ['PASSAGEM-COTA.txt',"
new="patterns = ['evidence/is6-expanded-journey*.json',\n            'output/is6-expanded-journey-product0.27.0/app/**/*',\n            'output/is6-expanded-journey-product0.27.0/*.json',\n            'output/is6-expanded-journey-service-*/**/*.json',\n            'PASSAGEM-COTA.txt',"
assert text.count(old)==1;text=text.replace(old,new)
compile(text,str(target),'exec');target.write_text(text,encoding='utf8')
print(json.dumps(dict(prepared=True,backup_executed=False,push=False)))
