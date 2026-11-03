"""Scoped warm camera/content regression; not a replacement for the nine G0 routes."""
from pathlib import Path
import argparse
import hashlib
import json
import runpy
import time
import urllib.request
import numpy as np
from cef_page import Page
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--label',required=True);args=p.parse_args()
if not args.label.isalnum():raise ValueError('Use um identificador alfanumérico.')
destination=ROOT/f'evidence/atlas-route-{args.label}.json'
if destination.exists():raise ValueError('Preserve o relatório anterior; escolha outro identificador.')
socket=connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.2,ping_interval=None,max_size=4*1024*1024)
socket.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}));topic=0
def lua(code):
    global topic
    topic+=1;socket.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True}}));reply=json.loads(socket.recv(timeout=15));assert reply['topic']==topic
    return reply['payload']['1']
def visit(target):
    request=urllib.request.Request('http://127.0.0.1:4700/api/navigation/visit',data=json.dumps({'target':target,'sunlit':True}).encode(),headers={'Content-Type':'application/json'})
    response=json.load(urllib.request.urlopen(request));assert response['ok'];return response
report={'schema':1,'scope':'Three warm 15s Atlas views with real application UI/polling. SGCT intervals including VSync; engine memory only, not total product. Does not replace G0.','session':json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig')),'code_sha256':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in ['app/atlas.py','app/navigation.py','app/ui/app.js','app/ui/navigation.js','app/ui/style.css','user/data/assets/cosmos2/atlas.asset','user/data/assets/cosmos2/atmosphere.asset']},'runs':[]}
with Page() as page:
    page.goto('http://127.0.0.1:4700/');page.wait_for_function('navigationState!==null');page.locator('#ui-scale').select_option('1')
    try:
        for target in ['Earth','Moon','Saturn']:
            visit(target);page.evaluate('selectTarget('+json.dumps(target)+')');time.sleep(2)
            lua('openspace.cosmos2BeginFrameCapture(6000);return {ok=true}')
            time.sleep(15)
            capture=lua('return openspace.cosmos2EndFrameCapture()');memory=lua('return openspace.cosmos2MemoryMetrics()')
            raw=capture.pop('samples_s');values=np.array(raw if isinstance(raw,list) else [raw[str(i)] for i in range(1,len(raw)+1)])[1:]
            assert [capture['width'],capture['height']]==[1920,1080] and len(values)>100
            row={'target':target,'frame_times_s':values.tolist(),'capture':capture,'engine_memory':memory,'statistics':{'frames':len(values),'interval_s':float(sum(values)),'median_fps':float(1/np.median(values)),'p95_ms':float(np.quantile(values,.95)*1000),'p99_ms':float(np.quantile(values,.99)*1000),'over_100ms':int(sum(values>.1))}}
            report['runs'].append(row);destination.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'target':target,**row['statistics']}),flush=True)
    finally:visit('Earth');socket.close()
assert all(r['statistics']['median_fps']>=60 and r['statistics']['p99_ms']<50 and r['statistics']['over_100ms']==0 for r in report['runs'])
report['passed']=True;destination.write_text(json.dumps(report,indent=2)+'\n')
