"""First native EM128 diagnostic; preserves failures and never grants formal acceptance."""
from pathlib import Path
import hashlib
import itertools
import json
import math
import subprocess
import sys
import time
import urllib.request
import uuid
import numpy as np
from cef_page import Page
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parents[1];V03='--v03' in sys.argv
CANDIDATE=ROOT/('output/c212-em-v03-product' if V03 else 'output/c212-em-product');sys.path.insert(0,str(CANDIDATE/'em'));sys.path.insert(0,str(CANDIDATE/'app'))
from em_fields import K_E
from em_mutual import System,Phase
from em_experiment import Experiment
from em_native import normalize
owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes();report_path=ROOT/('evidence/em-v03-128-native-preprofile.json' if V03 else 'evidence/em128-native-preprofile.json')
memory_label='c212emv03128pre' if V03 else 'c212em128pre'
assert not report_path.exists(),'Preserve prior profile; use a new labelled runner instead'
storage=CANDIDATE/'c212-em-worker/product';name='profile128-'+uuid.uuid4().hex[:12]
xs=tuple(itertools.islice(itertools.product((-4,-2,0,2,4),repeat=3),125))+((-6,0,0),(6,0,0),(0,6,0))
q=.01*math.sqrt(1/K_E);charges=tuple(q*(-1)**i for i in range(128))
ex=Experiment('mutual_electrostatic',System(tuple(map(str,range(128))),charges,(1.,)*128,(.01,)*128),Phase(xs,((0.,0.,0.),)*128),.001,{'acting':True})
ex.save(storage/(name+'.json'))
def state():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/em/state',timeout=10))
def guard():
    s=state()['state'];return {k:s[k] for k in ('system_id','edit_token','revision','frame')}|{'expected_time_s':s['time_s']}
def command(name,**value):
    request=urllib.request.Request('http://127.0.0.1:4700/api/em/command',data=json.dumps({'command':name,**value}).encode(),headers={'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(request,timeout=20))
def mechanical(payload):
    x=payload['phase']['position_m'];v=payload['phase']['velocity_m_s'];m=payload['system']['mass_kg'];c=payload['system']['charge_C']
    kinetic=math.fsum(.5*mass*math.fsum(a*a for a in vel) for mass,vel in zip(m,v))
    potential=math.fsum(K_E*c[i]*c[j]/math.dist(x[i],x[j]) for i,j in itertools.combinations(range(len(x)),2))
    return kinetic+potential,kinetic+abs(potential)
ws=connect('ws://127.0.0.1:4682',open_timeout=3,close_timeout=.2,ping_interval=None,max_size=4*1024*1024);topic=0
ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
def native(code):
    global topic
    topic+=1;ws.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True}}));reply=json.loads(ws.recv(timeout=15));assert reply.get('topic')==topic;return normalize(reply['payload']['1'])
report={'status':'running_first_EM128_native_diagnostic_not_formal_acceptance','warmup_s':5,'capture_requested_s':20,'requested_model_s_per_wall_s':1.,
        'fixture':{'active_charges':128,'dt_s':.001,'abs_charge_C':q,'mass_kg':1.,'exclusion_radius_m':.01,'seed':'alternating charges on125 lattice positions plus3 exterior points'},
        'formal_acceptance':False,'scope':'One20s warm native run,97 field samples and5 pauses. Not three formal60s routes, no complete WDDM/VRAM resource coverage or10k EM particles. Frame/rate observations and failure criteria are preserved.'}
report['session']=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
report['engine_sha256']=hashlib.sha256((ROOT/'.runtime-cloud/bin/OpenSpace.exe').read_bytes()).hexdigest()
def persist():report_path.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
persist()
try:
    with Page() as page:
        previous=page.evaluate('location.href');page.locator('#em-lab').click();page.wait_for_function('location.pathname==="/em.html"&&nativeState?.confirmation?.state==="accepted"&&!pending',timeout=30000)
        ack=command('load',**guard(),file=name);assert 'display' not in ack,ack
        value=state();assert len(value['native']['confirmation']['objects'])==128
        page.wait_for_function('state.experiment.mode==="mutual_electrostatic"&&state.experiment.system.ids.length===128')
        page.locator('#measure').click();page.wait_for_function('!pending&&map!==null',timeout=30000)
        page.locator('#native-frame').click();page.wait_for_function('!pending',timeout=30000)
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/measure-product-memory.ps1'),'-Label',memory_label+'-before'],check=True,capture_output=True)
        command('resume');time.sleep(5)
        native('openspace.cosmos2BeginFrameCapture(12000);return {started=true}')
        began=time.perf_counter();initial=state();marks=[]
        for i,pos in enumerate(((0,-24e9,16e9),(24e9,0,16e9),(0,-18e9,22e9))):
            if i:native('openspace.navigation.setNavigationState({Anchor="C2EMCamera",ReferenceFrame="C2EMRoot",Position={'+','.join(map(str,pos))+'},Up={0,0,1}});return {queued=true}')
            marks.append({'offset_s':time.perf_counter()-began,'native_state':state()['native']['confirmation']['metadata'],
                          'engine_memory':native('return openspace.cosmos2MemoryMetrics()')})
            remaining=began+(i+1)*20/3-time.perf_counter()
            if remaining>0:time.sleep(remaining)
        captured=native('return openspace.cosmos2EndFrameCapture()');wall=time.perf_counter()-began;final=state()
        raw=captured.pop('samples_s');frames=np.array(raw[1:]);assert len(frames)>1 and captured['width']==1920 and captured['height']==1080 and not captured['capacity_reached']
        assert abs(float(frames.sum())-20)<.5
        stats={'frames':len(frames),'measured_interval_s':float(frames.sum()),'median_ms':float(np.median(frames)*1000),
               'p95_ms':float(np.quantile(frames,.95)*1000),'p99_ms':float(np.quantile(frames,.99)*1000),'over100ms':int(np.sum(frames>.1))}
        measured=(final['state']['time_s']-initial['state']['time_s'])/wall
        pauses=[]
        for i in range(5):
            began_pause=time.perf_counter();ack=command('pause');pauses.append((time.perf_counter()-began_pause)*1000)
            value=state();assert value['state']['paused'] and len(value['native']['confirmation']['objects'])==128
            assert value['native']['confirmation']['metadata']['time_s']==value['state']['time_s']
            if i<4:command('resume');time.sleep(.1)
        end=state();e0,scale0=mechanical(ex.payload());energy,_=mechanical(end['state']['experiment']);error=abs(energy-e0)/scale0
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/measure-product-memory.ps1'),'-Label',memory_label+'-after'],check=True,capture_output=True)
        report.update(status='first_EM128_native_diagnostic_completed_not_formal_acceptance',frame_times_s=frames.tolist(),statistics=stats,capture=captured,
                      observed_model_s_per_wall_s=measured,model_interval_s=final['state']['time_s']-initial['state']['time_s'],capture_wall_s=wall,
                      native_marks=marks,pause_samples_ms=pauses,energy_error_over_initial_K_plus_abs_U=error,elapsed_model_s=end['state']['time_s'],
                      criteria_observed={'frame_limits_on_this_short_run':stats['median_ms']<=16.7 and stats['p95_ms']<=25 and stats['p99_ms']<=50 and stats['over100ms']==0,
                                         'requested_rate_reached_on_this_short_run':measured>=.9,'pause_under250ms':max(pauses)<250,'energy_under1e_6':error<1e-6},
                      source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (CANDIDATE/'app/em_native.py',CANDIDATE/'app/em_laboratory.py',CANDIDATE/'em/em_worker.py',CANDIDATE/'em/em_mutual.py',Path(__file__))},
                      owner_pointer_preserved=owner.read_bytes()==original)
        persist();print(json.dumps({k:report[k] for k in ('status','statistics','observed_model_s_per_wall_s','pause_samples_ms','energy_error_over_initial_K_plus_abs_U','criteria_observed')},indent=2))
        page.locator('#native-return').click();page.wait_for_function('location.pathname==="/"&&typeof appState!=="undefined"&&appState!==null',timeout=30000)
except Exception as error:
    report.update(status='EM128_native_diagnostic_interrupted_no_acceptance',error=type(error).__name__+': '+str(error));persist();raise
finally:
    ws.close()
    if 'previous' in locals():
        with Page() as cleanup:cleanup.call('Page.navigate',{'url':previous})
    assert owner.read_bytes()==original
