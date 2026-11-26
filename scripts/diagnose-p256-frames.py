"""Short causal sampling of paused/running256 scene; never a formal acceptance."""
from pathlib import Path
import json,runpy,time,urllib.request
import numpy as np
ROOT=Path(__file__).resolve().parents[1];execute=runpy.run_path(str(ROOT/'scripts/engine-command.py'))['execute']
def command(name,**kw):
 return json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:4700/api/command',data=json.dumps({'command':name,**kw}).encode(),headers={'Content-Type':'application/json'}),timeout=65))
def lua(script):return execute(script)['payload']['1']
rows=[]
try:
 command('enter')
 current=json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/state'))['physics']
 if len(current['bodies'])!=256:command('reset',count=256)
 command('pause');time.sleep(2)
 state=json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/state'))['physics'];assert len(state['bodies'])==256
 for mode in ('paused','running','paused_again'):
  command('resume' if mode=='running' else 'pause');time.sleep(1)
  lua('openspace.cosmos2BeginStageTrace();openspace.cosmos2BeginFrameCapture(12000);return {ready=true}');time.sleep(10)
  data=lua('return openspace.cosmos2EndFrameCapture()');raw=data.pop('samples_s');raw=[raw[k] for k in sorted(raw,key=int)] if isinstance(raw,dict) else raw;values=np.array(raw[1:])*1000
  stages=lua('return openspace.cosmos2EndStageTrace()')
  row={'mode':mode,'median_ms':float(np.median(values)),'p95_ms':float(np.quantile(values,.95)),'p99_ms':float(np.quantile(values,.99)),'frames':len(values),'capture':data,'stages':stages};rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='stages'}),flush=True)
finally:command('pause')
(ROOT/'evidence/p256-frame-diagnostic.json').write_text(json.dumps({'scope':'Short causal sample only; no formal acceptance','rows':rows},indent=2)+'\n')
