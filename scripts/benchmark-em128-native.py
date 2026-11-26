"""Three native EM128 routes with complete resource windows; approval is separate."""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import hashlib
import io
import itertools
import json
import math
import subprocess
import sys
import tarfile
import time
import urllib.request
import uuid
import numpy as np
from websockets.sync.client import connect
from cef_page import Page
import native_product_memory as ram

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
assert 1<=len(args.label)<=18 and all(c.isalnum() or c in '_-' for c in args.label)
CANDIDATE=ROOT/'output/c212-em-v03-product'
sys.path.insert(0,str(CANDIDATE/'em'));sys.path.insert(0,str(CANDIDATE/'app'))
from em_fields import K_E
from em_mutual import System,Phase
from em_experiment import Experiment,generation
from em_native import normalize

destination=ROOT/f'evidence/native-em128-{args.label}.json';assert not destination.exists()
session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'));ram.session=session
assert session['emCandidate'] and session['emKernelVersion']=='0.3.0'
assert Path(session['serverScript']).resolve()==(CANDIDATE/'app/server.py').resolve()
owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes()
baseline=json.loads((ROOT/'evidence/c212-em-candidate-baseline.json').read_text())
positions=tuple(itertools.product((-4,-2,0,2,4),repeat=3))+((-6,0,0),(6,0,0),(0,6,0))
charge=.01*math.sqrt(1/K_E)
ex=Experiment('mutual_electrostatic',System(tuple(map(str,range(128))),tuple(charge*(-1)**i for i in range(128)),(1.,)*128,(.01,)*128),Phase(positions,((0.,0.,0.),)*128),.001,{'acting':True})
name='formal128-'+uuid.uuid4().hex[:12];ex.save(CANDIDATE/'c212-em-worker/product'/(name+'.json'))
configuration=[ROOT/'scripts/benchmark-em128-native.py',ROOT/'scripts/native_product_memory.py',ROOT/'scripts/collect-em-gpu-memory.ps1',ROOT/'scripts/start-c212-em-v03-candidate.ps1',ROOT/'scripts/select-runtime.ps1',ROOT/'evidence/built-runtime-cloud.json',ROOT/'config/cosmos2.cfg',ROOT/'config/window-1080.json',ROOT/'.runtime-cloud/openspace.cfg',ROOT/'user/data/profiles/cosmos2.profile',*sorted((ROOT/'user/data/assets/cosmos2').glob('*.asset'))]
configuration += [p for folder in ('em','app') for p in (CANDIDATE/folder).rglob('*') if p.is_file() and p.suffix in ('.py','.json','.html','.js','.css') and '__pycache__' not in p.parts]
report={'schema':1,'profile':'C2-12 EM128 native0.3, explicit pair Coulomb VelocityVerlet','session':session,
        'warmup_s':30,'route_duration_s':60,'requested_model_s_per_wall_s':1.,'dt_s':.001,
        'scientific_generation':generation(),'fixture':ex.payload(),'runs':[],'completed':False,
        'engine_sha256':hashlib.sha256((ROOT/'.runtime-cloud/bin/OpenSpace.exe').read_bytes()).hexdigest(),
        'configuration_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in configuration},
        'scope':'128 mutually acting charges plus97 frozen SI field samples, native CEF,3x60s routes each after30s warmup. Fixed weak signed lattice measures throughput/conservation and does not replace long eccentric-orbit convergence. No10k EM or planetary/GR acceptance. WDDM/process RAM sums may repeat shared allocations; engine DXGI budget is distinct.'}
def persist():
    temporary=destination.with_suffix('.tmp');temporary.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');temporary.replace(destination)
def state():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/em/state',timeout=10))
def guard():
    s=state()['state'];return {k:s[k] for k in ('system_id','edit_token','revision','frame')}|{'expected_time_s':s['time_s']}
def command(name,**values):
    req=urllib.request.Request('http://127.0.0.1:4700/api/em/command',data=json.dumps({'command':name,**values}).encode(),headers={'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(req,timeout=20))
socket=connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.2,ping_interval=None,max_size=4*1024*1024)
socket.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}));topic=0
def native(code):
    global topic
    topic+=1;socket.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True}}))
    reply=json.loads(socket.recv(timeout=15));assert reply.get('topic')==topic,reply
    return normalize(reply['payload']['1'])
routes=((0,-24e9,16e9),(24e9,0,16e9),(0,-18e9,22e9))
def navigate(position):
    began=time.perf_counter();native('openspace.navigation.setNavigationState({Anchor="C2EMCamera",ReferenceFrame="C2EMRoot",Position={'+','.join(map(str,position))+'},Up={0,0,1}});return {queued=true}')
    report.setdefault('camera_latency_ms',[]).append((time.perf_counter()-began)*1000)
def check_state(s):
    assert not s['paused'] and s['experiment']['mode']=='mutual_electrostatic' and len(s['experiment']['system']['ids'])==128
    assert s['experiment']['dt_s']==.001 and s['requested_model_s_per_wall_s']==1 and s['experiment']['controls']['acting']
    assert s['scientific_generation']==report['scientific_generation'] and s['notice'] is None
def mechanical(payload):
    x=payload['phase']['position_m'];v=payload['phase']['velocity_m_s'];m=payload['system']['mass_kg'];q=payload['system']['charge_C']
    k=math.fsum(.5*mass*math.fsum(c*c for c in vel) for mass,vel in zip(m,v))
    u=math.fsum(K_E*q[i]*q[j]/math.dist(x[i],x[j]) for i,j in itertools.combinations(range(128),2))
    p=[math.fsum(mass*vel[c] for mass,vel in zip(m,v)) for c in range(3)]
    angular=[math.fsum(mass*(pos[(c+1)%3]*vel[(c+2)%3]-pos[(c+2)%3]*vel[(c+1)%3]) for mass,pos,vel in zip(m,x,v)) for c in range(3)]
    pscale=math.fsum(mass*math.hypot(*vel) for mass,vel in zip(m,v))
    lscale=math.fsum(mass*math.hypot(*pos)*math.hypot(*vel) for mass,pos,vel in zip(m,x,v))
    return {'energy_J':k+u,'energy_scale_J':k+abs(u),'momentum':p,'angular':angular,'momentum_scale':pscale,'angular_scale':lscale}
def start_gpu(run):
    label=f'{args.label}-em-{run}';path=ROOT/f'evidence/gpu-memory-{label}.json';assert not path.exists()
    ready=ROOT/f'output/gpu-memory-ready-{label}.json';ready.unlink(missing_ok=True)
    job=subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/collect-em-gpu-memory.ps1'),'-Label',label,'-Samples','66','-ExpectedMode','em','-ExpectedWorker','running','-SignalReady'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        if job.poll() is not None:raise RuntimeError('GPU collector failed: '+job.communicate()[0])
        if ready.exists():
            value=json.loads(ready.read_text(encoding='utf-8-sig'));assert value['engine_pid']==session['app'] and value['label']==label
            return job,path
        time.sleep(.05)
    job.terminate();job.communicate(timeout=5);raise TimeoutError('GPU readiness timeout')
def freeze():
    archive=ROOT/f'evidence/native-em128-{args.label}-source.tar.gz';assert not archive.exists()
    with tarfile.open(archive,'w:gz') as tar:
        for path,digest in sorted(report['configuration_sha256'].items()):
            data=(ROOT/path).read_bytes();assert hashlib.sha256(data).hexdigest()==digest,path
            member=tarfile.TarInfo(path);member.size=len(data);tar.addfile(member,io.BytesIO(data))
    report['frozen_source_archive']={'path':str(archive.relative_to(ROOT)),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}

gpu_job=None;persist()
try:
    with Page() as page:
        previous=page.evaluate('location.href');page.call('Page.navigate',{'url':'http://127.0.0.1:4700/'})
        page.wait_for_function('typeof appState!=="undefined"&&appState!==null');page.locator('#em-lab').click()
        page.wait_for_function('location.pathname==="/em.html"&&nativeState?.confirmation?.state==="accepted"&&!pending',timeout=30000)
        command('load',**guard(),file=name)
        report['em_worker_pid']=state()['worker_pid']
        page.wait_for_function('state.experiment.mode==="mutual_electrostatic"&&state.experiment.system.ids.length===128')
        page.locator('#measure').click();page.wait_for_function('!pending&&map!==null',timeout=30000)
        report['frozen_field_map']=page.evaluate('map');assert len(report['frozen_field_map']['samples'])==97
        command('resume')
        for run in range(1,4):
            navigate(routes[0]);print(json.dumps({'phase':'warmup','run':run,'seconds':30}),flush=True);time.sleep(30)
            gpu_job,gpu_path=start_gpu(run)
            native('openspace.cosmos2BeginFrameCapture(12000);return {started=true}')
            began=time.perf_counter();capture_start=datetime.now(timezone.utc);initial=state()['state'];check_state(initial);marks=[]
            for part,pos in enumerate(routes):
                if part:navigate(pos)
                metrics=native('local m=openspace.cosmos2MemoryMetrics();if openspace.cosmos2ScriptLogStatus then m.script_log=openspace.cosmos2ScriptLogStatus() end;return m')
                s=state()['state'];check_state(s)
                marks.append({'offset_s':time.perf_counter()-began,'ram':ram.product_memory(),'engine_gpu':metrics,'physics':s,'first_frame':max(0,int(metrics['capture_samples'])-1) if part else 0})
                remaining=began+(part+1)*20-time.perf_counter()
                if remaining>0:time.sleep(remaining)
            captured=native('return openspace.cosmos2EndFrameCapture()');capture_end=datetime.now(timezone.utc);wall=time.perf_counter()-began
            final=state()['state'];check_state(final)
            record={'run':run,'capture_start_utc':capture_start.isoformat(),'capture_end_utc':capture_end.isoformat(),'wall_interval_s':wall,
                    'capture':captured,'initial':initial,'final':final,'memory':marks,'gpu_report':str(gpu_path.relative_to(ROOT))}
            report['pending_collection']=record;persist()
            output=gpu_job.communicate(timeout=15)[0];assert gpu_job.returncode==0,output;gpu_job=None
            gpu=json.loads(gpu_path.read_text(encoding='utf-8-sig'));stamps=[datetime.fromisoformat(s['utc'].replace('Z','+00:00')) for s in gpu['samples']]
            assert len(stamps)==66 and stamps[0]<=capture_start and stamps[-1]>=capture_end
            values=np.array(captured.pop('samples_s')[1:]);assert len(values)>1 and captured['width']==1920 and captured['height']==1080 and not captured['capacity_reached'] and captured['invalid_samples']==0
            assert abs(float(values.sum())-60)<.5 and abs(wall-60)<.5
            record.update(frame_times_s=values.tolist(),observed_model_s_per_wall_s=(final['time_s']-initial['time_s'])/wall,
                          statistics={'frames':len(values),'median_ms':float(np.median(values)*1000),'p95_ms':float(np.quantile(values,.95)*1000),'p99_ms':float(np.quantile(values,.99)*1000),'over100ms':int(np.sum(values>.1))},
                          gpu_sha256=hashlib.sha256(gpu_path.read_bytes()).hexdigest(),resource_window_covered=True,
                          independent_mechanics=mechanical(final['experiment']))
            report['runs'].append(record);report.pop('pending_collection');persist()
            print(json.dumps({'run':run,'rate':record['observed_model_s_per_wall_s'],**record['statistics']}),flush=True)
        report['pause_latency_samples']=[]
        for i in range(20):
            if i:command('resume')
            time.sleep(.12);began=time.perf_counter();ack=command('pause');wall=(time.perf_counter()-began)*1000
            value=state();assert value['state']['paused'] and value['native']['confirmation']['metadata']['time_s']==value['state']['time_s']
            report['pause_latency_samples'].append({'wall_ms':wall,'worker_elapsed_ms':ack['elapsed_ms']})
        report['initial_independent_mechanics']=mechanical(ex.payload())
        for path,digest in baseline['installed_app_sha256'].items():assert hashlib.sha256((ROOT/'app'/path).read_bytes()).hexdigest()==digest,path
        assert owner.read_bytes()==original
        report.update(completed=True,owner_pointer_preserved=True,installed_product_files_preserved=len(baseline['installed_app_sha256']))
        freeze();persist()
except BaseException as error:
    report['error']=type(error).__name__+': '+str(error);persist();raise
finally:
    if gpu_job is not None:
        if gpu_job.poll() is None:gpu_job.terminate()
        gpu_job.communicate(timeout=5)
    try:
        if state()['native']['active']:command('pause')
        with Page() as page:page.call('Page.navigate',{'url':'http://127.0.0.1:4700/'})
    finally:socket.close()
print(json.dumps({'report':str(destination),'completed':report['completed']}),flush=True)
