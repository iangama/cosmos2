"""Persist a detached Windows benchmark and its subsequent independent audit."""
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
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    base=ROOT/('output/is3-points-profile-'+args.label+'-driver')
    receipt=base.with_suffix('.json');python=ROOT/'.tooling/python/Scripts/python.exe'
    if not args.worker:
        if receipt.exists() or base.with_suffix('.log').exists():raise FileExistsError('Preserve driver evidence.')
        stdout=base.with_suffix('.log').open('wb');stderr=base.with_name(base.name+'-errors').with_suffix('.log').open('wb')
        process=subprocess.Popen([str(python),'-Xutf8',str(Path(__file__)), '--label',args.label,'--worker'],cwd=ROOT,
            stdout=stdout,stderr=stderr,creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP)
        receipt.write_text(json.dumps({'pid':process.pid,'started_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'completed':False},indent=2)+'\n',encoding='utf-8')
        stdout.close();stderr.close();print(json.dumps({'pid':process.pid}));return
    try:
        benchmark=subprocess.run([str(python),'-Xutf8',str(ROOT/'scripts/benchmark-body-points-native.py'),'--label',args.label],cwd=ROOT)
        result={'pid':os.getpid(),'benchmark_exit':benchmark.returncode,'completed':True}
        if benchmark.returncode==0:
            audit=subprocess.run([str(python),'-Xutf8',str(ROOT/'scripts/audit-body-points-profile.py'),'--label',args.label],cwd=ROOT)
            result['audit_exit']=audit.returncode
        receipt.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    except Exception:
        receipt.write_text(json.dumps({'pid':os.getpid(),'completed':False,'failure':traceback.format_exc()},indent=2)+'\n',encoding='utf-8');raise


if __name__=='__main__':main()
