"""Dedicated256 active-mass profile; historical128 runner unchanged."""
"""G0 warm native routes; raw SGCT intervals, process RAM and DXGI engine budget."""
from pathlib import Path
import argparse
import ctypes
from ctypes import wintypes as wt
from datetime import datetime, timezone
import hashlib
import io
import json
import re
import subprocess
import sys
import time
import tarfile
import urllib.request
from websockets.sync.client import connect

import numpy as np

if sys.platform != 'win32':
    raise RuntimeError('Benchmark exige Windows nativo, sem WSL/Xvfb.')
ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--runs', type=int, default=3)
parser.add_argument('--seconds', type=float, default=60)
parser.add_argument('--warmup', type=float, default=30)
parser.add_argument('--label',default='current')
parser.add_argument('--product-gpu',action='store_true')
parser.add_argument('--profile',choices=['p256'],default='p256')
parser.add_argument('--runtime-variant',choices=['baseline','query'],default='baseline')
args = parser.parse_args()
massive_profile=args.profile in ('p256','fields','history')
if not 1 <= args.runs <= 3 or not 5 <= args.seconds <= 60 or not 0 <= args.warmup <= 30:
    raise ValueError('Parâmetros fora do limite de medição.')
if not re.fullmatch(r'[a-z0-9_-]{1,18}',args.label):
    raise ValueError('Identificador de benchmark inválido.')
destination=ROOT/f'evidence/native-benchmark-{args.label}.json'
if destination.exists():
    raise RuntimeError('Use outro identificador para preservar o relatório anterior.')

session = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
runtime_path=ROOT/('.runtime-perf-query' if args.runtime_variant=='query' else '.runtime-built')
if Path(session.get('runtime','')).resolve()!=runtime_path.resolve():
    raise RuntimeError('Esta medição exige o motor compilado, com captura de frames.')

class Entry(ctypes.Structure):
    _fields_ = [('dwSize',wt.DWORD),('cntUsage',wt.DWORD),('pid',wt.DWORD),
                ('heap',ctypes.c_size_t),('module',wt.DWORD),('threads',wt.DWORD),
                ('parent',wt.DWORD),('priority',wt.LONG),('flags',wt.DWORD),('exe',wt.WCHAR*260)]
class Memory(ctypes.Structure):
    _fields_ = [('cb',wt.DWORD),('faults',wt.DWORD)]+[(name,ctypes.c_size_t) for name in
                ('peak_working','working','peak_paged','paged','peak_nonpaged','nonpaged',
                 'pagefile','peak_pagefile','private')]
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
psapi = ctypes.WinDLL('psapi', use_last_error=True)
kernel.CreateToolhelp32Snapshot.restype = wt.HANDLE
kernel.CreateToolhelp32Snapshot.argtypes = [wt.DWORD,wt.DWORD]
kernel.Process32FirstW.argtypes = [wt.HANDLE,ctypes.POINTER(Entry)]
kernel.Process32NextW.argtypes = [wt.HANDLE,ctypes.POINTER(Entry)]
kernel.OpenProcess.restype = wt.HANDLE
kernel.OpenProcess.argtypes = [wt.DWORD,wt.BOOL,wt.DWORD]
kernel.CloseHandle.argtypes = [wt.HANDLE]
psapi.GetProcessMemoryInfo.argtypes = [wt.HANDLE,ctypes.POINTER(Memory),wt.DWORD]

def product_memory():
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    processes = {}
    try:
        entry = Entry(); entry.dwSize = ctypes.sizeof(Entry)
        available = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while available:
            processes[entry.pid] = (entry.parent, entry.exe)
            available = kernel.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    owned = {session['app'], session['server']}
    while True:
        children = {pid for pid,(parent,_) in processes.items() if parent in owned}
        if children <= owned: break
        owned |= children
    entries = []
    for pid in sorted(owned):
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle: continue
        try:
            memory = Memory(); memory.cb = ctypes.sizeof(Memory)
            if psapi.GetProcessMemoryInfo(handle, ctypes.byref(memory), memory.cb):
                entries.append({'pid':pid,'name':processes.get(pid,(0,'unknown'))[1],
                                'working_set_bytes':memory.working,'private_bytes':memory.private})
        finally:
            kernel.CloseHandle(handle)
    if not any(item['pid'] == session['app'] for item in entries):
        raise RuntimeError('Motor ausente na leitura de memória.')
    return {'processes':entries,'sum_working_set_bytes':sum(e['working_set_bytes'] for e in entries),
            'method':'GetProcessMemoryInfo; sum of working sets can double-count shared DLL pages'}

socket = connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=1,ping_interval=None,max_size=4*1024*1024)
socket.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
topic = 0
def lua(script):
    global topic
    topic += 1
    socket.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':script,'return':True}}))
    reply = json.loads(socket.recv(timeout=15))
    if reply.get('topic') != topic: raise RuntimeError('Resposta de outra medição.')
    value = reply.get('payload', {}).get('1')
    if value is None: raise RuntimeError('Motor não retornou o resultado esperado.')
    return value

def command(name, **parameters):
    request = urllib.request.Request('http://127.0.0.1:4700/api/command',
              data=json.dumps({'command':name,**parameters}).encode(),headers={'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(request, timeout=65 if name in ('enter','reset','load','load_branch','restart_seed') else 20))

def navigate(anchor, position):
    began=time.perf_counter()
    result=lua('openspace.navigation.setNavigationState({Anchor='+json.dumps(anchor)+
               ',Position={'+','.join(str(v) for v in position)+'},Up={0,0,1}});return {ready=true}')
    if massive_profile:report.setdefault('camera_command_latency_ms',[]).append((time.perf_counter()-began)*1000)
    return result

def physics():
    return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/state',timeout=10))['physics']

routes = {
    'atlas': [('Earth',[16000000,-17000000,10000000]),('Moon',[4500000,-5000000,3000000]),
              ('MilkyWayVolume',[0,-8e20,9e20])],
    'p32': [('LabRoot',[0,-5e10,6e10]),('LabRoot',[5e10,0,6e10]),('LabRoot',[0,-3e10,2e10])],
}
routes['atlas_p32'] = routes['atlas']
routes['p256']=routes['p32']
routes['history128']=routes['p32']
report = {'schema':2,'session':session,'resolution_required':[1920,1080],
          'warmup_s':args.warmup,'route_duration_s':args.seconds,'runs':[],
          'vsync':'swapinterval=1; nominal and actual monitor rate recorded separately',
          'scope':'Native warm Atlas, Atlas with P32 updating in background, and visible P32; DXGI budget covers engine only. Optional product GPU counters include cross-process shared allocations and can overcount; adapter totals include other applications.',
          'runtime_variant':args.runtime_variant,
          'runtime_receipt':json.loads((ROOT/('evidence/built-runtime-query.json' if args.runtime_variant=='query' else 'evidence/built-runtime.json')).read_text()),
          'configuration_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
              for p in [ROOT/'scripts/benchmark-p256-native.py',ROOT/'scripts/collect-gpu-memory.ps1',ROOT/'config/cosmos2.cfg',ROOT/'scripts/start-cosmos2.ps1',runtime_path/'openspace.cfg',
                        ROOT/'user/data/profiles/cosmos2.profile',ROOT/'config/window-1080.json',
                        *sorted((ROOT/'user/data/assets/cosmos2').glob('*.asset'))]}}
report['configuration_sha256'].update({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*sorted((ROOT/'app').glob('*.py')),*sorted((ROOT/'app/ui').glob('*.js')),ROOT/'app/ui/index.html',ROOT/'app/ui/style.css']})
if massive_profile:
    report['profile']='C2-11 history,128 massive bodies,16 probes recorded at0.25s, IAS15 epsilon1e-9' if args.profile=='history' else 'C2-11 fields,128 massive bodies,569 frozen field samples, IAS15 epsilon1e-9' if args.profile=='fields' else 'C2-11 P256,256 massive bodies, IAS15 epsilon1e-9'
    report['scope']='Three warm visible256 routes with live native CEF. All256 masses gravitate. Field profile uses a frozen confirmed map while physical time evolves; resampling cost is recorded separately. WDDM sums can count shared allocations; engine DXGI budget is distinct. Does not replace frozen C2-06/G0 evidence or prove10k test-particle performance.'
    from cef_page import Page
    with Page() as page:
        page.goto('http://127.0.0.1:4700/');page.wait_for_function('appState!==null');page.locator('#ui-scale').select_option('1')
def persist():
    if report.get('completed') and 'frozen_source_archive' not in report:
        archive=ROOT/f'evidence/native-benchmark-{args.label}-source.tar.gz'
        if archive.exists():raise RuntimeError('Preserve existing source archive')
        files={path.replace('\\','/'):digest for path,digest in report['configuration_sha256'].items()}
        files.update({'patches/'+name:digest for name,digest in report['runtime_receipt']['source_patches'].items()})
        for p in report.get('scenario_initial_state',{}).values():
            generation=p['scientific_generation'];files.update(generation['code_sha256']);files.update(generation['data_sha256'])
        contents=[]
        for path,digest in sorted(files.items()):
            data=(ROOT/path).read_bytes()
            if hashlib.sha256(data).hexdigest()!=digest:raise RuntimeError('Source changed during measurement: '+path)
            contents.append((path,data))
        with tarfile.open(archive,'w:gz') as tar:
            for path,data in contents:
                member=tarfile.TarInfo(path);member.size=len(data);tar.addfile(member,io.BytesIO(data))
        report['frozen_source_archive']={'path':str(archive.relative_to(ROOT)),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
    tmp = destination.with_suffix('.tmp')
    tmp.write_text(json.dumps(report, indent=2)+'\n',encoding='utf-8')
    tmp.replace(destination)

gpu_job=None
def start_gpu_collector(scenario,run):
    label=f'{args.label}-{scenario}-{run}'
    ready=ROOT/f'output/gpu-memory-ready-{label}.json'
    gpu_path=ROOT/f'evidence/gpu-memory-{label}.json'
    if gpu_path.exists():
        raise RuntimeError('RelatórioGPU existente; use outro identificador.')
    ready.unlink(missing_ok=True)
    job=subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',
        '-File',str(ROOT/'scripts/collect-gpu-memory.ps1'),'-Label',label,
        '-Samples',str(int(args.seconds)+6),'-ExpectedMode','atlas' if scenario=='atlas' else 'experiment',
        '-ExpectedWorker','any' if scenario=='atlas' else 'running','-SignalReady'],
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
    deadline=time.monotonic()+15
    try:
        while time.monotonic()<deadline:
            if job.poll() is not None:
                raise RuntimeError('ColetorGPU terminou antes da captura: '+job.communicate()[0])
            if ready.exists():
                try:
                    value=json.loads(ready.read_text(encoding='utf-8-sig'))
                    if value['engine_pid']!=session['app'] or value['label']!=label:
                        raise RuntimeError('ReciboGPU de outra sessão.')
                    return job,gpu_path
                except (PermissionError,FileNotFoundError,ValueError,KeyError):
                    pass
            time.sleep(.05)
        raise TimeoutError('Primeira amostraGPU não chegou em15s.')
    except BaseException:
        job.terminate();job.communicate(timeout=5)
        raise

try:
    for scenario in (('history128',) if args.profile=='history' else ('fields128',) if args.profile=='fields' else ('p256',) if massive_profile else ('atlas','atlas_p32','p32')):
        command('atlas' if scenario=='atlas' else 'enter')
        if scenario!='atlas':
            command('reset',count=256 if massive_profile else 32)
            command('rate',value=1)
            initial=physics();report.setdefault('scenario_initial_state',{})[scenario]=initial
            if massive_profile:report['fixture_initial_state']=initial
            if args.profile=='history':
                guard={k:initial[k] for k in ('system_id','edit_token','revision')}
                guard.update(expected_time=initial['time'],frame=initial['contract']['frame'])
                for i in range(16):
                    p=physics();guard['instruments_revision']=p['instruments']['revision']
                    command('configure_instruments',**guard,operation='create',definition={
                        'mode':'fixed','name':'Perfil '+str(i+1),'position_m':[1.7e10+i*1e8,-9e9,3e9]})
                p=physics();guard.update(instruments_revision=p['instruments']['revision'],history_revision=p['instrument_history']['revision'])
                command('sample_instruments',**guard)
                command('configure_history',**guard,recording=True,cadence_wall_s=.25)
                with Page() as page:
                    page.evaluate('updateState()');page.wait_for_function('appState.physics.instrument_history.recording')
                    page.evaluate('document.getElementById("instrument-history").open=true;document.getElementById("history-chart").scrollIntoView({block:"center"})')
                report['scope']='Native128-mass evolution with16 simultaneous probes recorded at0.25s wall cadence, bounded128-record window and live2-probe graph fetched at most1Hz. Probe marks are frozen while readings evolve. WDDM/RAM sums may duplicate shared allocations. Separate from C2-06/G0/fields3; no256/10k acceptance.'
            if args.profile=='fields':
                cfg=initial['field_layers']['settings']
                cfg.update(center_mode='follow',body_id=initial['bodies'][0]['id'],shell_count=128,cut_resolution=21,
                    cut_orientation_deg=[30.,-20.,15.],cut_offset_m=3e9)
                guard={k:initial[k] for k in ('system_id','edit_token','revision')}
                guard.update(expected_time=initial['time'],frame=initial['contract']['frame'],fields_revision=initial['field_layers']['revision'])
                command('configure_fields',**guard,settings=cfg)
                report['field_resampling_latency_ms']=[]
                for _ in range(5):
                    p=physics();guard.update(fields_revision=p['field_layers']['revision']);began=time.perf_counter()
                    ack=command('sample_fields',**guard)['ack'];elapsed=(time.perf_counter()-began)*1000
                    assert ack['result']['sample_count']==569 and elapsed<2000
                    report['field_resampling_latency_ms'].append({'wall_ms':elapsed,'evaluation_ms':ack['result']['evaluation_ms'],
                        'worker_elapsed_ms':ack['elapsed_ms']})
                preview=ack['result'];report['field_map']=preview
                d=preview['render']['view_distance_m'];anchor=preview['render']['frame_node']
                routes[scenario]=[(anchor,[0,-d,.6*d]),(anchor,[d,0,.6*d]),(anchor,[0,-.7*d,.35*d])]
                with Page() as page:
                    page.evaluate('updateState()');page.wait_for_function('appState.fields_preview!==null')
                    page.evaluate('document.getElementById("gravity-fields").open=true;document.getElementById("fields-status").scrollIntoView({block:"start"})')
            command('resume')
        navigate(*routes[scenario][0])
        print(json.dumps({'phase':'warmup','scenario':scenario,'seconds':args.warmup}),flush=True)
        time.sleep(args.warmup)
        for run in range(1,args.runs+1):
            navigate(*routes[scenario][0])
            gpu_path=None
            if args.product_gpu:
                gpu_job,gpu_path=start_gpu_collector(scenario,run)
            lua('openspace.cosmos2BeginFrameCapture(12000);return {started=true}')
            began = time.perf_counter()
            initial_physics=physics() if massive_profile else None
            capture_start_utc=datetime.now(timezone.utc)
            memory = []
            for part, view in enumerate(routes[scenario]):
                if part: navigate(*view)
                metrics = lua('local m=openspace.cosmos2MemoryMetrics();if openspace.cosmos2ScriptLogStatus then m.script_log=openspace.cosmos2ScriptLogStatus() end;return m')
                memory.append({'offset_s':time.perf_counter()-began,'ram':product_memory(),
                               'engine_gpu':metrics,'route_anchor':view[0],
                               'first_frame_index':max(0,int(metrics['capture_samples'])-1) if part else 0,
                               **({'physics':physics()} if massive_profile else {})})
                remaining = began+(part+1)*args.seconds/3-time.perf_counter()
                if remaining>0: time.sleep(remaining)
            captured = lua('return openspace.cosmos2EndFrameCapture()')
            capture_end_utc=datetime.now(timezone.utc)
            capture_wall_interval=time.perf_counter()-began
            final_physics=physics() if massive_profile else None
            gpu_summary=None
            if gpu_job is not None:
                report['pending_collection']={'scenario':scenario,'run':run,
                    'capture':captured,'capture_wall_interval_s':capture_wall_interval,
                    'capture_start_utc':capture_start_utc.isoformat(),
                    'capture_end_utc':capture_end_utc.isoformat(),
                    'reason':'Frame capture complete; waiting for all GPU samples. Preserved on collector error/timeout.'}
                output=gpu_job.communicate(timeout=15)[0]
                if gpu_job.returncode!=0:
                    report['collection_failure']={'scenario':scenario,'run':run,
                        'capture':captured,'capture_wall_interval_s':capture_wall_interval,
                        'capture_start_utc':capture_start_utc.isoformat(),
                        'capture_end_utc':capture_end_utc.isoformat(),'collector_output':output}
                    raise RuntimeError('ColetaGPU recusada: '+output)
                gpu_job=None
                gpu=json.loads(gpu_path.read_text(encoding='utf-8-sig'))
                stamps=[datetime.fromisoformat(s['utc'].replace('Z','+00:00')) for s in gpu['samples']]
                if stamps[0]>capture_start_utc or stamps[-1]<capture_end_utc:
                    raise RuntimeError('AmostragemGPU não cobre a janela completa de frames.')
                gpu_summary={'report':str(gpu_path.relative_to(ROOT)),
                    'sha256':hashlib.sha256(gpu_path.read_bytes()).hexdigest(),
                    'samples':len(stamps),'covers_frame_window':True,
                    'product_dedicated_sum_max_bytes':max(s['product_dedicated_sum_bytes'] for s in gpu['samples']),
                    'scope':gpu['scope']}
                report.pop('pending_collection',None)
            raw = captured.pop('samples_s')
            values = np.array(raw if isinstance(raw,list) else [raw[str(i)] for i in range(1,len(raw)+1)])
            if len(values)<2: raise RuntimeError('Captura de frames vazia.')
            values = values[1:]  # first interval precedes the capture command
            if [captured['width'],captured['height']] != [1920,1080] or captured['capacity_reached']:
                raise RuntimeError('Resolução/capacidade invalida a medição.')
            if abs(float(values.sum())-args.seconds)>.5:
                raise RuntimeError('A duração medida difere da janela solicitada.')
            part_statistics = []
            for index, mark in enumerate(memory):
                end = memory[index+1]['first_frame_index'] if index+1<len(memory) else len(values)
                segment = values[mark['first_frame_index']:end]
                if not len(segment): raise RuntimeError('Trecho sem frames medidos.')
                part_statistics.append({'anchor':mark['route_anchor'],'first_frame':mark['first_frame_index'],
                                        'end_frame':end,'median_ms':float(np.median(segment)*1000),
                                        'p95_ms':float(np.quantile(segment,.95)*1000),'p99_ms':float(np.quantile(segment,.99)*1000),
                                        'over_100ms':int(np.sum(segment>.1)),'median_fps':float(1/np.median(segment))})
            data = {'scenario':scenario,'run':run,'frame_times_s':values.tolist(),'route_parts':part_statistics,
                    'statistics':{'frames':len(values),'measured_interval_s':float(values.sum()),
                                  'median_ms':float(np.median(values)*1000),'p95_ms':float(np.quantile(values,.95)*1000),
                                  'p99_ms':float(np.quantile(values,.99)*1000),'over_100ms':int(np.sum(values>.1)),
                                  'median_fps':float(1/np.median(values))},
                    'capture':captured,'memory':memory,'wall_interval_s':capture_wall_interval,
                    'capture_start_utc':capture_start_utc.isoformat(),
                    'capture_end_utc':capture_end_utc.isoformat(),'product_gpu':gpu_summary}
            if massive_profile:
                data['physics']={'initial':initial_physics,'final':final_physics,'measured_model_units_per_wall_s':(final_physics['time']-initial_physics['time'])/capture_wall_interval}
                assert len(final_physics['bodies'])==256 and all(b['mass']>0 for b in final_physics['bodies']) and final_physics['population_contract']['active_mass_count']==256 and final_physics['population_contract']['all_active_masses_gravitate'] and not final_physics['paused']
                assert final_physics['energy_error']<1e-8 and final_physics['conservation']['momentum_error_normalized']<1e-8 and final_physics['conservation']['angular_momentum_error_normalized']<1e-8
                assert data['physics']['measured_model_units_per_wall_s']>=.9
                if args.profile=='history':
                    assert final_physics['instrument_history']['recording'] and final_physics['instrument_history']['sample_count']==128
                    assert final_physics['instrument_history']['next_sequence']>initial_physics['instrument_history']['next_sequence']
                    data['history_sample_cost_ms_at_route_snapshots']=[m['physics']['history_evaluation_ms'] for m in memory]
            report['runs'].append(data);persist()
            print(json.dumps({'scenario':scenario,'run':run,**data['statistics']}),flush=True)
    if massive_profile:
        command('pause');command('rate',value=10);report['pause_latency_samples']=[]
        for _ in range(20):
            command('resume');time.sleep(.12);before=physics();began=time.perf_counter();response=command('pause');elapsed=(time.perf_counter()-began)*1000;after=physics()
            assert after['paused'] and elapsed<=250,(elapsed,after['time'])
            report['pause_latency_samples'].append({'wall_ms':elapsed,'worker_elapsed_ms':response['ack']['elapsed_ms'],'before_time':before['time'],'after_time':after['time']})
        report['all256_active_confirmed']=True
    report['completed'] = True
finally:
    if gpu_job is not None:
        if gpu_job.poll() is None: gpu_job.terminate()
        gpu_job.communicate(timeout=5)
    try:
        persist()
    finally:
        try:
            command('atlas')
        finally:
            socket.close()
print(json.dumps({'report':str(destination),'completed':report.get('completed',False)}),flush=True)
