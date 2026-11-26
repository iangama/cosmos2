"""Sequential science checks before the candidate's final native profiles."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'output/c211-cloud-final-regressions'
folder.mkdir(exist_ok=True)
cases=[
 ('session','scripts/verify-cloud-session-prototype.py',[],'cloud-session-prototype-check.json'),
 ('worker','scripts/verify-cloud-worker-prototype.py',[],'cloud-worker-prototype-check.json'),
 ('transport','scripts/verify-cloud-transport-prototype.py',[],'cloud-transport-prototype-check.json'),
 ('windows-lock','scripts/verify-cloud-windows-publication.py',[],'cloud-windows-publication-check.json'),
 ('spherical','scripts/verify-gravity-spherical-attraction.py',['--candidate'],'gravity-spherical-candidate-check.json'),
 ('j2','output/c211-cloud-regression-scripts/verify-j2-session-prototype.py',[],'cloud-regression-j2-session-prototype-check.json'),
 ('tides','output/c211-cloud-regression-scripts/verify-tides-session-prototype.py',[],'cloud-regression-tides-session-prototype-check.json'),
 ('resonance','output/c211-cloud-regression-scripts/verify-resonance-session-prototype.py',[],'cloud-regression-resonance-session-prototype-check.json'),
 ('migration','output/c211-cloud-regression-scripts/verify-migration.py',[],'cloud-regression-real-migration-check.json')]
report={'status':'running','source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
    for p in (ROOT/'output/c211-cloud-product/app').glob('*.py')},'cases':[]}
destination=ROOT/'evidence/cloud-final-regressions-check.json'
for name,script,args,receipt in cases:
    path=ROOT/'evidence'/receipt
    if path.exists() and not (folder/('previous-'+receipt)).exists():shutil.copy2(path,folder/('previous-'+receipt))
    began=time.perf_counter()
    with (folder/(name+'.log')).open('w',encoding='utf-8') as log:
        result=subprocess.run([sys.executable,'-X','utf8',str(ROOT/script),*args],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    row={'case':name,'exit_code':result.returncode,'elapsed_s':time.perf_counter()-began,
        'log':str((folder/(name+'.log')).relative_to(ROOT))}
    if result.returncode==0:
        row.update(receipt=str(path.relative_to(ROOT)),receipt_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    report['cases'].append(row)
    if result.returncode:report['status']='failed'
    destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(row),flush=True)
    if result.returncode:raise SystemExit(result.returncode)
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==value for p,value in report['source_sha256'].items())
report['status']='all_nine_final_candidate_regression_suites_verified'
destination.write_text(json.dumps(report,indent=2)+'\n')
print(report['status'],flush=True)
