"""Same-process paused128 A/B overlay diagnostic; not a formal acceptance."""
from pathlib import Path
import json
import argparse
import subprocess
import time
import urllib.request
import numpy as np
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--running',action='store_true');args=parser.parse_args()
destination=ROOT/('evidence/field-draw-cost-running-diagnostic.json' if args.running else 'evidence/field-draw-cost-diagnostic.json')
if destination.exists():raise RuntimeError('Preserve the previous diagnostic.')


def get():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/state',timeout=20))


def command(name,**parameters):
    request=urllib.request.Request('http://127.0.0.1:4700/api/command',data=json.dumps({'command':name,**parameters}).encode(),headers={'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(request,timeout=20))


socket=connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.2,ping_interval=None,max_size=4*1024*1024)
socket.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}));serial=0


def lua(code):
    global serial
    serial+=1;socket.send(json.dumps({'topic':serial,'type':'luascript','payload':{'script':code,'return':True}}))
    answer=json.loads(socket.recv(timeout=15));assert answer['topic']==serial and '1' in answer.get('payload',{}),answer
    return answer['payload']['1']


report={'scope':'Same-process128-body state with569 frozen samples; visible/hidden pairs, physical phase advances only in --running mode; not formal acceptance','running':args.running,'windows':[]}
try:
    command('enter');command('reset',count=128);state=get()['physics']
    cfg=state['field_layers']['settings'];cfg.update(center_mode='follow',body_id=state['bodies'][0]['id'],shell_count=128,cut_resolution=21,cut_orientation_deg=[30.,-20.,15.],cut_offset_m=3e9)
    guard={k:state[k] for k in ('system_id','edit_token','revision')};guard.update(expected_time=state['time'],frame=state['contract']['frame'],fields_revision=0)
    command('configure_fields',**guard,settings=cfg);guard['fields_revision']=1;command('sample_fields',**guard)
    before=get();frame=before['fields_preview']['render']['frame_node'];d=before['fields_preview']['render']['view_distance_m']
    lua('openspace.navigation.setNavigationState({Anchor='+json.dumps(frame)+',Position={0,'+str(-d)+','+str(.6*d)+'},Up={0,0,1}});return {ready=true}')
    focus=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/focus-cosmos2.ps1')],capture_output=True,text=True,check=True)
    report['foreground']=json.loads(focus.stdout)
    command('rate',value=1)
    if args.running:command('resume')
    for visible in (True,False,True,False):
        command('set_fields_visible',visible=visible);time.sleep(2.)
        lua('openspace.cosmos2BeginFrameCapture(12000);return {ready=true}');time.sleep(10.)
        captured=lua('return openspace.cosmos2EndFrameCapture()');raw=captured.pop('samples_s')
        samples=np.array(raw if isinstance(raw,list) else [raw[str(i)] for i in range(1,len(raw)+1)])[1:]
        assert not captured['capacity_reached'] and captured['invalid_samples']==0
        after=get()
        if not args.running:
            assert after['physics']['bodies']==before['physics']['bodies'] and after['physics']['time']==before['physics']['time']
        row={'visible':visible,'physical_time':after['physics']['time'],'effective_rate':after['physics']['effective_rate'],'frames_s':samples.tolist(),'capture':captured,'median_ms':float(np.median(samples)*1000),'p95_ms':float(np.quantile(samples,.95)*1000),'p99_ms':float(np.quantile(samples,.99)*1000),'over100ms':int(sum(samples>.1))}
        report['windows'].append(row);destination.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in row.items() if k!='frames_s'}),flush=True)
    report['physical_state_and_time_exact']=not args.running
finally:
    try:command('atlas')
    finally:socket.close();destination.write_text(json.dumps(report,indent=2)+'\n')
