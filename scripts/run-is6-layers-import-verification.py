"""Durable first/restart K4 UI verification without overwriting evidence."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import traceback

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);parser.add_argument('--phase',choices=['first','restart'],required=True);parser.add_argument('--seed-label',default='20261104m');parser.add_argument('--seed-process-label');parser.add_argument('--worker',action='store_true');args=parser.parse_args();args.seed_process_label=args.seed_process_label or args.seed_label
    for label in [args.label,args.seed_label,args.seed_process_label]:
        if not label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):parser.error('Invalid label')
    base=ROOT/('output/is6-layers-import-native-'+args.label+'-driver');receipt=base.with_suffix('.json');python=ROOT/'.tooling/python/Scripts/python.exe'
    common=['--label',args.label,'--phase',args.phase,'--seed-label',args.seed_label,'--seed-process-label',args.seed_process_label]
    if not args.worker:
        if receipt.exists() or base.with_suffix('.log').exists():raise FileExistsError('Preserve driver evidence')
        with base.with_suffix('.log').open('wb') as out,base.with_name(base.name+'-errors').with_suffix('.log').open('wb') as err:
            child=subprocess.Popen([str(python),'-u','-Xutf8',str(Path(__file__)),*common,'--worker'],cwd=ROOT,stdout=out,stderr=err,creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP)
        receipt.write_text(json.dumps(dict(pid=child.pid,completed=False,phase=args.phase,started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n',encoding='utf8')
        print(json.dumps(dict(pid=child.pid)));return
    r=dict(pid=os.getpid(),completed=False,phase=args.phase)
    try:
        result=subprocess.run([str(python),'-u','-Xutf8',str(ROOT/'scripts/verify-native-is6-layers-import.py'),*common],cwd=ROOT)
        r.update(completed=True,verification_exit=result.returncode)
    except Exception:r['failure']=traceback.format_exc();raise
    finally:receipt.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':main()
