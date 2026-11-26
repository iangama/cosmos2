"""Persist long Windows verification independently of a terminal cell lifetime."""
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
    parser=argparse.ArgumentParser();parser.add_argument('--kind',choices=['native','profile'],required=True);parser.add_argument('--label',required=True);parser.add_argument('--acceptance-label',default='20261102f');parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    for label in [args.label,args.acceptance_label]:
        if not label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):parser.error('Invalid label')
    base=ROOT/('output/is6-'+args.kind+'-'+args.label+'-driver');receipt=base.with_suffix('.json');python=ROOT/'.tooling/python/Scripts/python.exe'
    if not args.worker:
        if receipt.exists() or base.with_suffix('.log').exists():raise FileExistsError('Preserve driver evidence')
        stdout=base.with_suffix('.log').open('wb');stderr=base.with_name(base.name+'-errors').with_suffix('.log').open('wb')
        process=subprocess.Popen([str(python),'-Xutf8',str(Path(__file__)),'--kind',args.kind,'--label',args.label,'--acceptance-label',args.acceptance_label,'--worker'],cwd=ROOT,stdout=stdout,stderr=stderr,creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP)
        receipt.write_text(json.dumps(dict(pid=process.pid,completed=False,started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n',encoding='utf-8')
        stdout.close();stderr.close();print(json.dumps(dict(pid=process.pid)));return
    try:
        script='verify-native-is6-product-v5.py' if args.kind=='native' else 'benchmark-is6-spatial-native.py'
        argv=[str(python),'-u','-Xutf8',str(ROOT/'scripts'/script),'--label',args.label]
        if args.kind=='profile':argv+=['--acceptance-label',args.acceptance_label]
        work=subprocess.run(argv,cwd=ROOT)
        result=dict(pid=os.getpid(),kind=args.kind,completed=True,verification_exit=work.returncode)
        if args.kind=='profile' and work.returncode==0:
            audit=subprocess.run([str(python),'-u','-Xutf8',str(ROOT/'scripts/audit-is6-spatial-profile.py'),'--label',args.label],cwd=ROOT)
            result['audit_exit']=audit.returncode
        receipt.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    except Exception:
        receipt.write_text(json.dumps(dict(pid=os.getpid(),completed=False,failure=traceback.format_exc()),indent=2)+'\n',encoding='utf-8');raise


if __name__=='__main__':main()
