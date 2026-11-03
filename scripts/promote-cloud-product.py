"""Install only the fully reviewed candidate, preserving the previous app and owner data."""
from pathlib import Path
import argparse
import ctypes
from ctypes import wintypes as wt
from datetime import datetime,timezone
import hashlib
import json
import re
import shutil
import subprocess
import sys
import uuid

assert sys.platform=='win32'
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--cloud-label',default='c211cloud4');parser.add_argument('--p256-label',default='c211p256c1');args=parser.parse_args()
assert all(re.fullmatch('[a-z0-9_-]{1,18}',s) for s in (args.cloud_label,args.p256_label))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,data):
    path=Path(path);temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temporary.replace(path)
def files(folder):
    return {p.relative_to(folder).as_posix():sha(p) for p in folder.rglob('*') if p.is_file() and p.suffix in ('.py','.js','.html','.css')}
approval_path=ROOT/'evidence/c211-cloud-validated.json'
assert not approval_path.exists(),'Preserve the existing approval; inspect its installed state before another promotion'
launch=read(ROOT/'output/session.json')
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.OpenProcess.argtypes=[wt.DWORD,wt.BOOL,wt.DWORD];kernel.OpenProcess.restype=wt.HANDLE
kernel.GetExitCodeProcess.argtypes=[wt.HANDLE,ctypes.POINTER(wt.DWORD)];kernel.CloseHandle.argtypes=[wt.HANDLE]
for pid in (launch['app'],launch['server']):
    handle=kernel.OpenProcess(0x1000,False,pid)
    if handle:
        try:
            code=wt.DWORD();assert kernel.GetExitCodeProcess(handle,ctypes.byref(code))
            assert code.value!=259,'Close the native app and wait for launcher cleanup before promotion'
        finally:kernel.CloseHandle(handle)
# A closed Windows loopback port may time out instead of returning RST.
# Inspect the native listener table, in addition to the process exit checks.
listeners=subprocess.check_output(['powershell.exe','-NoProfile','-Command',
    'Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in @(4682,4700) } | Select-Object LocalAddress,LocalPort,OwningProcess | ConvertTo-Json -Compress'],text=True).strip()
assert not listeners,'The previous local runtime/server is still listening: '+listeners
source=ROOT/'output/c211-cloud-product/app';manifest=read(ROOT/'evidence/cloud-final-candidate-files.json')
assert files(source)==manifest
regression=read(ROOT/'evidence/cloud-final-regressions-check.json')
assert regression['status']=='all_nine_final_candidate_regression_suites_verified'
for path,value in regression['source_sha256'].items():assert sha(ROOT/path)==value,path
for case in regression['cases']:assert case['exit_code']==0 and sha(ROOT/case['receipt'])==case['receipt_sha256']
for name in ('cloud-product-candidate-check.json','cloud-legacy-query-ui-check.json','cloud-legacy-baseline-ui-check.json'):
    proof=read(ROOT/'evidence'/name);assert proof['owner_pointer_preserved'] and not proof['javascript_errors']
engine=sha(ROOT/'.runtime-cloud/bin/OpenSpace.exe')
profiles={}
for kind,label,flag in [('cloud',args.cloud_label,'three_cloud10k_routes_verified'),('p256',args.p256_label,'three_P256_routes_verified')]:
    benchmark=ROOT/f'evidence/native-benchmark-{label}.json';review=ROOT/f'evidence/native-benchmark-{label}-review.json'
    b=read(benchmark);r=read(review)
    assert b['completed'] and len(b['runs'])==3 and r[flag] is True
    assert r['benchmark_sha256']==sha(benchmark) and r['engine_sha256']==engine
    assert r['over_100ms_total']==0 and r['p95_ms_max']<=25 and r['p99_ms_max']<=50
    assert r['pause_API_wall_max_ms']<=250 and r['measured_rate_min']>=.9
    for path,value in b['configuration_sha256'].items():assert sha(ROOT/path)==value,path
    archived=b['frozen_source_archive'];assert sha(ROOT/archived['path'])==archived['sha256']
    profiles[kind]={'benchmark':benchmark.relative_to(ROOT).as_posix(),'benchmark_sha256':sha(benchmark),
        'review':review.relative_to(ROOT).as_posix(),'review_sha256':sha(review),'source_archive':archived}
phase=read(ROOT/f'evidence/cloud-profile-phase-{args.cloud_label}-check.json')
assert phase['count']==10000 and phase['maximum_relative_position_error']<1e-8
assert phase['benchmark_sha256']==profiles['cloud']['benchmark_sha256']
pointer=ROOT/'user/sessions/latest.json';before_owner=pointer.read_bytes()
preserved_engines={name:sha(ROOT/name/'bin/OpenSpace.exe') for name in ('.runtime-built','.runtime-perf-query')}
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
backup=ROOT/('output/c211-pre-cloud-'+stamp);backup.mkdir()
temporary=ROOT/('output/c211-install-cloud-'+uuid.uuid4().hex)
shutil.copytree(source,temporary,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
assert files(temporary)==manifest
(ROOT/'app').rename(backup/'app')
try:temporary.rename(ROOT/'app')
except BaseException:
    if not (ROOT/'app').exists():(backup/'app').rename(ROOT/'app')
    raise
assert files(ROOT/'app')==manifest and pointer.read_bytes()==before_owner
assert all(sha(ROOT/name/'bin/OpenSpace.exe')==value for name,value in preserved_engines.items())
approval={'schema':1,'status':'3_13_science_worker_native_migration_P256_and_10000_profile_approved',
    'performance_approved':True,'runtime_variant':'cloud','engine_sha256':engine,
    'created_utc':datetime.now(timezone.utc).isoformat(),'cloud_profile':profiles['cloud'],'p256_profile':profiles['p256'],
    'app_files_sha256':manifest,'previous_app':(backup/'app').relative_to(ROOT).as_posix(),
    'regressions':{'receipt':'evidence/cloud-final-regressions-check.json','sha256':sha(ROOT/'evidence/cloud-final-regressions-check.json')},
    'owner_pointer_sha256':hashlib.sha256(before_owner).hexdigest(),'preserved_engine_sha256':preserved_engines,
    'scope':'Local3.13 promotion: one active source plus up to10000 massless circular test particles;256 mutually gravitating masses measured separately. Existing J2/tide/resonance domains retained. Default installed boot/UI have followup receipts.'}
write(approval_path,approval)
write(ROOT/'evidence/c211-cloud-promotion.json',{'installed':True,'approval':approval_path.relative_to(ROOT).as_posix(),
    'approval_sha256':sha(approval_path),'backup':str(backup.relative_to(ROOT)),'owner_pointer_preserved':True,
    'preserved_engine_sha256':preserved_engines,'installed_files':len(manifest)})
print(json.dumps({'installed':True,'approval':str(approval_path),'backup':str(backup),'installed_files':len(manifest),'owner_pointer_preserved':True}),flush=True)
