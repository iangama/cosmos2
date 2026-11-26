"""Bounded diagnostic capture: native frames, engine RTT, CPU and CEF long tasks.

This changes the camera and instruments CEF functions in memory. It is not a
formal performance acceptance run and never changes scientific parameters.
"""
from pathlib import Path
import argparse,ctypes,json,time,urllib.request
from ctypes import wintypes as W
import subprocess
from datetime import datetime,timezone
from websockets.sync.client import connect
from cef_page import Page
ROOT=Path(__file__).resolve().parents[1]
a=argparse.ArgumentParser();a.add_argument('--seconds',type=int,default=60);a.add_argument('--label',required=True);a.add_argument('--stage-tracing',action='store_true');a.add_argument('--churn-cycles',type=int,default=0);a.add_argument('--count',type=int,choices=(32,128),default=32);a.add_argument('--lab-view',action='store_true');args=a.parse_args()
if not 10<=args.seconds<=120 or not args.label.isalnum() or not 0<=args.churn_cycles<=12:raise ValueError('Bounded diagnostic label/duration required')
path=ROOT/('evidence/frame-diagnostic-'+args.label+'.json')
if path.exists():raise RuntimeError('Preserve previous capture')
def post(data):return json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:4700/api/command',data=json.dumps(data).encode(),headers={'Content-Type':'application/json'}),timeout=20))
ws=connect('ws://127.0.0.1:4682',ping_interval=None,close_timeout=1);ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}));topic=0
def lua(code):
 global topic
 topic+=1;ws.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True}}));reply=json.loads(ws.recv(timeout=15));assert reply['topic']==topic;return reply['payload']['1']
session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
k=ctypes.WinDLL('kernel32',use_last_error=True);k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE;k.GetProcessTimes.argtypes=[W.HANDLE,*([ctypes.POINTER(W.FILETIME)]*4)];k.CloseHandle.argtypes=[W.HANDLE]
handles=[]
def inventory():
    command='Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name | ConvertTo-Json -Compress'
    processes=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-Command',command],text=True))
    owned={session['app'],session['server']}
    while True:
        children={p['ProcessId'] for p in processes if p['ParentProcessId'] in owned}
        if children<=owned:break
        owned|=children
    return [(p['ProcessId'],p['Name'],k.OpenProcess(0x1000,False,p['ProcessId'])) for p in processes if p['ProcessId'] in owned]

def cpu():
 result=[]
 for pid,name,handle in handles:
  f=[W.FILETIME() for _ in range(4)]
  if handle and k.GetProcessTimes(handle,*[ctypes.byref(x) for x in f]):result.append({'pid':pid,'name':name,'kernel_s':((f[2].dwHighDateTime<<32)+f[2].dwLowDateTime)*1e-7,'user_s':((f[3].dwHighDateTime<<32)+f[3].dwLowDateTime)*1e-7})
 return result
report={'scope':'Instrumented diagnostic, not acceptance or isolated causal proof; native DXGI/log query once per second adds explicit diagnostic overhead','session':session,'samples':[],'native_memory_metrics':[],
 'runtime_receipt':json.loads((ROOT/'evidence/built-runtime.json').read_text()),'diagnostic_script_sha256':__import__('hashlib').sha256(Path(__file__).read_bytes()).hexdigest(),'scene_churn':[]}
try:
 post({'command':'enter'})
 for index,count in enumerate([128,32]*args.churn_cycles):
  started=time.perf_counter();post({'command':'reset','count':count});record={'index':index,'count':count,'wall_s':time.perf_counter()-started};report['scene_churn'].append(record);print(json.dumps(record),flush=True)
 post({'command':'reset','count':args.count});post({'command':'rate','value':1});post({'command':'resume'})
 lua('openspace.navigation.setNavigationState({Anchor="LabRoot",Position={0,-5e10,6e10},Up={0,0,1}});return true' if args.lab_view else 'openspace.navigation.setNavigationState({Anchor="Earth",Position={16000000,-17000000,10000000},Up={0,0,1}});return true')
 with Page() as page:
  page.goto('http://127.0.0.1:4700/');page.wait_for_function('appState?.physics?.bodies.length==='+str(args.count))
  page.evaluate('''window.__hitch={longtasks:[],functions:[]};window.__hitchObserver=new PerformanceObserver(list=>{for(const e of list.getEntries())__hitch.longtasks.push({start_utc_ms:performance.timeOrigin+e.startTime,duration_ms:e.duration,name:e.name})});__hitchObserver.observe({type:'longtask',buffered:true});for(const name of ['updateState','updateBodyEditor','updateBodyAttributes','updateOrbitEditor','updateGravityExperience','updateGravityProbe']){const original=window[name];if(typeof original!=='function')continue;window[name]=function(...args){const start=performance.now();const value=original.apply(this,args);const end=()=>{const duration=performance.now()-start;if(duration>5)__hitch.functions.push({name,start_utc_ms:performance.timeOrigin+start,duration_ms:duration})};if(value&&value.then)value.then(end, end);else end();return value;}}''')
  handles=inventory();time.sleep(5);
  if args.stage_tracing:lua('openspace.cosmos2BeginStageTrace();return true')
  report['script_log_before']=lua('if openspace.cosmos2ScriptLogStatus then return openspace.cosmos2ScriptLogStatus() end;return {initialized=false}')
  report['physics_before']=json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/state',timeout=5))['physics']
  lua('openspace.cosmos2BeginFrameCapture(12000);return true');began=time.perf_counter();report['start_utc']=datetime.now(timezone.utc).isoformat();next_route=1;next_memory=0
  while time.perf_counter()-began<args.seconds:
   offset=time.perf_counter()-began
   if next_route<3 and offset>=next_route*args.seconds/3:
    anchor,position=(('LabRoot',[5e10,0,6e10]) if next_route==1 else ('LabRoot',[0,-3e10,2e10])) if args.lab_view else (('Moon',[4500000,-5000000,3000000]) if next_route==1 else ('MilkyWayVolume',[0,-8e20,9e20]));lua('openspace.navigation.setNavigationState({Anchor='+json.dumps(anchor)+',Position={'+','.join(str(x) for x in position)+'},Up={0,0,1}});return true');next_route+=1
   if offset>=next_memory:
    query_started=time.perf_counter();metrics=lua('local m=openspace.cosmos2MemoryMetrics();if openspace.cosmos2ScriptLogStatus then m.script_log=openspace.cosmos2ScriptLogStatus() end;return m')
    report['native_memory_metrics'].append({'offset_s':offset,'utc':datetime.now(timezone.utc).isoformat(),'query_wall_ms':(time.perf_counter()-query_started)*1000,'metrics':metrics});next_memory=offset+1
   before=time.perf_counter();lua('return true');report['samples'].append({'offset_s':offset,'utc':datetime.now(timezone.utc).isoformat(),'renderer_RTT_ms':(time.perf_counter()-before)*1000,'process_CPU':cpu()});time.sleep(.1)
  report['capture_wall_s']=time.perf_counter()-began
  report['frames']=lua('return openspace.cosmos2EndFrameCapture()');
  if args.stage_tracing:report['stages']=lua('return openspace.cosmos2EndStageTrace()')
  report['script_log_after']=lua('if openspace.cosmos2ScriptLogStatus then return openspace.cosmos2ScriptLogStatus() end;return {initialized=false}')
  report['end_utc']=datetime.now(timezone.utc).isoformat();report['CEF']=page.evaluate('window.__hitchObserver.disconnect();window.__hitch');report['completed']=True
finally:
 path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
 for _,_,h in handles:
  if h:k.CloseHandle(h)
 post({'command':'atlas'});ws.close()
print(json.dumps({'report':str(path),'completed':report.get('completed',False)},indent=2))
