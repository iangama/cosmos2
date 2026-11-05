"""Own the gated K5 host, retain real handles, close it, then audit."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import argparse
import json
import subprocess
import sys
import traceback
from is6_owned_profile_host import Host
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);parser.add_argument('--plan-label',required=True);args=parser.parse_args()
for label in [args.label,args.plan_label]:
    if not label or len(label)>20 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):parser.error('Invalid label')
folder=ROOT/('output/is6-layers-import-profile-'+args.label+'-host')
receipt=ROOT/('evidence/is6-layers-import-profile-'+args.label+'.json')
if folder.exists() or receipt.exists():raise FileExistsError('Preserve owned K5 host')
folder.mkdir()
module=SourceFileLoader('k5_owned_profile',str(ROOT/'scripts/benchmark-is6-layers-import-native-v4.py')).load_module()
host=Host(folder,module.h,candidate='output/is6-layers-product0.21.1',launcher='scripts/launch-is6-layers-import-candidate-v3.py')
status=1
try:
    host.start()
    sys.argv=[str(module.__file__),'--label',args.label,'--plan-label',args.plan_label]
    status=module.main()
finally:
    closure={}
    try:closure['processes']=host.close()
    except Exception:closure['cleanup_failure']=traceback.format_exc();status=1
    if receipt.exists():
        data=json.loads(receipt.read_text());data.update(closure)
        if closure.get('cleanup_failure'):data['completed']=False
        receipt.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (folder/'closure.json').write_text(json.dumps(closure,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
if status==0:
    status=subprocess.run([sys.executable,'-Xutf8',str(ROOT/'scripts/audit-is6-layers-import-profile-v4.py'),'--label',args.label],cwd=ROOT).returncode
raise SystemExit(status)
