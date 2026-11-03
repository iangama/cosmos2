"""Start the own spatial diagnostic host with durable Windows output files."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
base=ROOT/('output/is6-host-'+args.label);receipt=base.with_suffix('.json')
if receipt.exists() or base.with_suffix('.log').exists():raise FileExistsError('Preserve host launch evidence')
launcher=ROOT/'scripts/launch-is6-spatial-revision-c.py';python=ROOT/'.tooling/python/Scripts/python.exe'
with base.with_suffix('.log').open('wb') as out,base.with_name(base.name+'-errors').with_suffix('.log').open('wb') as err:
    child=subprocess.Popen([str(python),'-u','-Xutf8',str(launcher)],cwd=ROOT,stdout=out,stderr=err,creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP)
record=dict(pid=child.pid,started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),launcher_sha256=hashlib.sha256(launcher.read_bytes()).hexdigest(),driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
receipt.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(record))
