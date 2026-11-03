"""Native UTF8/order/read-only logging, optionally draining the actual app on shutdown."""
from pathlib import Path
import argparse,ctypes,hashlib,json,runpy,time,urllib.request,uuid
ROOT=Path(__file__).resolve().parents[1];a=argparse.ArgumentParser();a.add_argument('--shutdown',action='store_true');args=a.parse_args()
execute=runpy.run_path(str(ROOT/'scripts/engine-command.py'))['execute']
def lua(code):return execute(code)['payload']['1']
def state():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/state',timeout=10))
def tail():
 with (ROOT/'output/logs/ScriptLog.txt').open('rb') as f:f.seek(0,2);size=f.tell();f.seek(max(0,size-1024*1024));return f.read()
before=state()['physics'];assert before is None or before['paused']
status=lua('return openspace.cosmos2ScriptLogStatus()');assert status['initialized'] and status['dropped']==0 and not status['failed']
token=uuid.uuid4().hex;markers=['Log órbita "\\ '+token+' '+str(i) for i in range(3)];sources=[]
for marker in markers:
 code='local marker='+json.dumps(marker,ensure_ascii=False)+';return {marker=marker}';assert lua(code)['marker']==marker;sources.append(code.encode('utf8'))
end=time.monotonic()+10
while time.monotonic()<end:
 data=tail()
 if all(data.count(s)==1 for s in sources):break
 time.sleep(.05)
else:raise AssertionError('Accepted log entries missing/duplicated in actual file')
positions=[data.index(s) for s in sources];assert positions==sorted(positions) and state()['physics']==before
status=lua('return openspace.cosmos2ScriptLogStatus()');assert status['dropped']==0 and not status['failed']
report={'engine_receipt':json.loads((ROOT/'evidence/built-runtime.json').read_text()),'UTF8_quote_backslash_roundtrip':True,'ordered_native_file_entries_exact_once':True,'physics_unchanged_by_logging_queries':True,'script_log_status':status,'shutdown_drain_tested':args.shutdown}
if args.shutdown:
 pid=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))['app'];k=ctypes.WinDLL('kernel32');k.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];k.OpenProcess.restype=ctypes.c_void_p;k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong];k.CloseHandle.argtypes=[ctypes.c_void_p];handle=k.OpenProcess(0x100000,False,pid);assert handle
 try:
  lua('openspace.toggleShutdown();return true');assert k.WaitForSingleObject(handle,20000)==0,'Native app did not finish a normal shutdown'
 finally:k.CloseHandle(handle)
 data=tail();assert all(data.count(s)==1 for s in sources) and [data.index(s) for s in sources]==sorted(data.index(s) for s in sources)
 report['ordered_entries_preserved_after_actual_app_shutdown']=True
(ROOT/'evidence/native-script-log-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='engine_receipt'},indent=2))
