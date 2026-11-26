"""Two native frozen magnetic layers with actual CEF and four-center dynamics."""
from pathlib import Path
import argparse
import datetime as dt
import json
import subprocess
import time
import traceback
import zipfile
import numpy as np
from importlib.machinery import SourceFileLoader
from native_product_memory import product_memory
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
test = SourceFileLoader('solar_native_test', str(ROOT / 'scripts/verify-native-solar-integration.py')).load_module()
get, post, native, sha, Page = test.get, test.post, test.native, test.sha, test.Page
# One persistent CDP-independent Lua transport: opening/closing a topic socket
# inside a frame window can itself stall this engine near the close timeout.
_socket = None
_topic = 0

def native(code):
    global _socket, _topic
    if _socket is None:
        _socket=connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.2,ping_interval=None,max_size=4*1024*1024)
        _socket.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
    _topic+=1
    _socket.send(json.dumps({'topic':_topic,'type':'luascript','payload':{'script':code,'return':True}}))
    reply=json.loads(_socket.recv(timeout=15))
    assert reply.get('topic')==_topic and '1' in reply.get('payload',{}),reply
    return reply['payload']['1']

LIMITS = {'median_ms' : 16.7, 'p95_ms': 25., 'p99_ms': 50., 'over_100ms': 0,
          'measured_rate_min': .9, 'RAM_bytes': 8*2**30, 'GPU_bytes': 5.5*2**30}


def statistics(values):
    return {'frames': len(values), 'median_ms': float(np.median(values)*1000),
            'p95_ms': float(np.quantile(values, .95)*1000), 'p99_ms': float(np.quantile(values, .99)*1000),
            'over_100ms': int(sum(values>.1))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or len(args.label)>20 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label.')
    folder = ROOT / ('output/is3-view-topology-profile-'+args.label)
    receipt = ROOT / ('evidence/is3-view-topology-profile-'+args.label+'.json')
    if folder.exists() or receipt.exists():
        raise FileExistsError('Preserve existing profile.')
    for preflight in ['is3-gpu-process-preflight-20261024a.json','is3-native-view-topology-20261024a.json']:
        assert json.loads((ROOT/'evidence'/preflight).read_text(encoding='utf-8'))['accepted']
    folder.mkdir()
    launch = json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert launch.get('bodyViewTopologyCandidate') and launch['runtimeVariant']=='cloud'
    engine = Path(launch['runtime'])/'bin/OpenSpace.exe'
    owner = ROOT/'user/sessions/latest.json'
    files = sorted(p for p in (ROOT/'output/is3-body-view-topology-product/app').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    files += [Path(__file__).resolve(), ROOT/'IS-3-VISUAL-PERFIL-DIAGNOSTICO-PREVIO.md',
              ROOT/'scripts/verify-native-solar-integration.py', ROOT/'scripts/cef_page.py',
              ROOT/'scripts/native_product_memory.py', ROOT/'scripts/collect-gpu-memory-diagnostic.ps1',
              ROOT/'config/window-1080.json', ROOT/'config/cosmos2.cfg', ROOT/'scripts/audit-body-view-topology-native-profile.py', ROOT/'scripts/start-is3-body-view-topology-candidate.ps1']
    files += [ROOT/'scripts/collect-gpu-memory.ps1',
              ROOT/'evidence/is3-gpu-process-preflight-20261024a.json',
              ROOT/'evidence/is3-native-view-topology-20261024a.json']
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in files}
    archive = folder/'executed-sources-and-recipe.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    report = {'schema': 1, 'session': launch, 'engine_sha256': sha(engine), 'source_sha256': hashes,
              'source_archive': archive.relative_to(ROOT).as_posix(), 'source_archive_sha256': sha(archive),
              'owner_pointer_sha256': sha(owner), 'limits_before_execution': LIMITS,
              'warmup_s': 30, 'window_s': 60, 'routes': ['point','side','polar'], 'requested_rate': .1,
              'runs': [], 'completed': False, 'accepted': False,
              'scope': 'Four visible/hidden frozen internal magnetic line bundles, IGRF14/JRM33, with four neutral Newtonian centers at canonical rate.1; no live field resampling, Lorentz, live resampling, multiple simultaneous layers or arbitrary-workload acceptance; paired visibility states include current marker policy. Resource sums may overcount shared allocations.'}

    def persist():
        receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')

    persist()
    gpu_job = None
    try:
        with Page() as page:
            page.goto(test.BASE+'/')
            page.wait_for_function('appState?.mode==="atlas"&&atlasState&&!pending')
            original_atlas=get('/api/atlas/state')
            page.locator('#ui-scale').select_option('1')
            for run,target in enumerate(['399','399','599','599'],1):
                test.click(page,'#copy-solar')
                page.wait_for_function('appState?.physics?.bodies.length===4&&!pending',timeout=70000)
                state=get('/api/state')['physics'];body=next(b for b in state['bodies'] if b['reference_id']=='sol:naif:'+target)
                parameters={'latitude_deg':-23.55,'longitude_deg':-46.63,'altitude_m':1000.} if target=='399' else {'radius_m':1.5*71492000.,'latitude_deg':0.,'east_longitude_deg':0.,'degree':13}
                model='IGRF14' if target=='399' else 'JRM33'
                request={'command':'show_body_field','representation':'lines','model':model,'system_id':state['system_id'],'edit_token':state['edit_token'],'revision':state['revision'],'expected_time':state['time'],'frame':state['contract']['frame'],'body_id':body['id'],**parameters}
                post('/api/command',request)
                frozen=get('/api/state')['body_field_preview']
                visible=run%2==1
                if not visible:post('/api/command',{'command':'set_body_field_visible','layer_id':frozen['render']['id'],'visible':False})
                frozen=get('/api/state')['body_field_preview'];render=frozen['render'];reading=frozen['reading']
                matrix=np.array(reading['J2000_to_render'])@np.array(reading['ITRF93_to_J2000'] if target=='399' else reading['SystemIII_to_J2000'])
                distance=render['view']['distance_m']
                views=[(render['view']['position_render_relative_m'],render['view']['up_render']),
                    ((matrix@np.array([0.,-distance,.3*distance])).tolist(),(matrix@np.array([0.,0.,1.])).tolist()),
                    ((matrix@np.array([0.,0.,distance])).tolist(),(matrix@np.array([0.,1.,0.])).tolist())]
                def navigate(index):
                    position,up=views[index]
                    vector=lambda v:'{'+','.join(format(float(x),'.17g') for x in v)+'}'
                    native('openspace.navigation.setNavigationState({Anchor='+json.dumps(render['frame_node'])+',ReferenceFrame="LabRoot",Position='+vector(position)+',Up='+vector(up)+'});return {queued=true}')
                post('/api/command',{'command':'rate','value':.1})
                post('/api/command',{'command':'resume'});navigate(0)
                print(json.dumps({'phase':'warmup','run':run,'model':model,'seconds':30}),flush=True)
                time.sleep(30)
                label = 'is3-view-topology-'+args.label+'-'+str(run)
                ready = ROOT/('output/gpu-memory-ready-'+label+'.json')
                gpu_path = ROOT/('evidence/gpu-memory-'+label+'.json')
                if ready.exists() or gpu_path.exists():raise FileExistsError(label)
                gpu_job = subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                    str(ROOT/'scripts/collect-gpu-memory-diagnostic.ps1'),'-Label',label,'-Samples','66',
                    '-ExpectedMode','experiment','-ExpectedWorker','running','-SignalReady'],
                    stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
                until = time.monotonic()+20
                while True:
                    if gpu_job.poll() is not None:raise RuntimeError('GPU readiness failed: '+gpu_job.communicate()[0])
                    if time.monotonic()>until:raise TimeoutError('GPU readiness did not arrive.')
                    if ready.exists():
                        try:signal=json.loads(ready.read_text(encoding='utf-8-sig'))
                        except (PermissionError,json.JSONDecodeError):time.sleep(.05);continue
                        assert signal['engine_pid']==launch['app'];break
                    time.sleep(.05)
                initial = get('/api/state')['physics']
                native('openspace.cosmos2BeginFrameCapture(12000);return {ready=true}')
                started = dt.datetime.now(dt.timezone.utc)
                began = time.perf_counter()
                row = {'run':run,'model':model,'visible':visible,'frozen_layer':frozen,'capture_start_utc':started.isoformat(),'initial':initial,'memory':[]}
                report['pending_run'] = row;persist()
                for part, route in enumerate(report['routes']):
                    navigate(part)
                    current=get('/api/state')['body_field_preview']
                    assert current['render']['id']==render['id'] and current['reading']==reading
                    visibility=native('local f={};for _,n in ipairs({'+','.join(json.dumps(mesh['node']) for mesh in render['meshes'])+'}) do f[n]=openspace.propertyValue("Scene."..n..".Renderable.Enabled") end;return {flags=f,marker=openspace.propertyValue("Scene.'+body['scene_node']+'.Renderable.Enabled"),anchor=openspace.navigation.getNavigationState().Anchor}')
                    assert all(v==visible for v in visibility['flags'].values()) and visibility['marker'] is not visible and visibility['anchor']==render['frame_node']
                    metrics = native('return openspace.cosmos2MemoryMetrics()')
                    row['memory'].append({'route':route,'offset_s':time.perf_counter()-began,
                        'first_frame_index':max(0,int(metrics['capture_samples'])-1) if part else 0,
                        'ram':product_memory(launch),'engine_gpu':metrics,'physics':get('/api/state')['physics'],'layer_id':current['render']['id'],'native_visibility':visibility})
                    remaining = began+(part+1)*20-time.perf_counter()
                    if remaining>0:time.sleep(remaining)
                capture = native('return openspace.cosmos2EndFrameCapture()')
                ended = dt.datetime.now(dt.timezone.utc)
                row.update(capture_end_utc=ended.isoformat(),wall_interval_s=time.perf_counter()-began,
                           final=get('/api/state')['physics'],capture=capture)
                persist()  # Raw frames survive even if the GPU collector rejects later.
                output = gpu_job.communicate(timeout=20)[0]
                (folder/('gpu-collector-'+str(run)+'.log')).write_text(output,encoding='utf-8')
                assert gpu_job.returncode==0,output
                gpu_job=None
                gpu = json.loads(gpu_path.read_text(encoding='utf-8-sig'))
                stamps=[dt.datetime.fromisoformat(s['utc'].replace('Z','+00:00')) for s in gpu['samples']]
                assert len(stamps)==66 and stamps[0]<=started and stamps[-1]>=ended
                raw = capture.pop('samples_s')
                values = np.array(raw if isinstance(raw,list) else [raw[str(i)] for i in range(1,len(raw)+1)])[1:]
                row.update(frame_times_s=values.tolist(),statistics=statistics(values),
                           gpu_report=gpu_path.relative_to(ROOT).as_posix(),gpu_sha256=sha(gpu_path))
                row['measured_rate']=(row['final']['time']-initial['time'])/row['wall_interval_s']/.1
                row['route_parts']=[]
                boundaries=[m['first_frame_index'] for m in row['memory']]+[len(values)]
                for i,route in enumerate(report['routes']):
                    row['route_parts'].append({'route':route,'first_frame':boundaries[i],'end_frame':boundaries[i+1],
                                               **statistics(values[boundaries[i]:boundaries[i+1]])})
                report['runs'].append(row);report.pop('pending_run',None);persist()
                print(json.dumps({'run':run,'statistics':row['statistics'],'measured_rate':row['measured_rate']}),flush=True)
                post('/api/command',{'command':'pause'})
                post('/api/command',{'command':'clear_body_field','layer_id':render['id']})
                test.click(page,'#atlas')
            final_atlas=get('/api/atlas/state')
            assert final_atlas['epoch']==original_atlas['epoch'] and final_atlas['bodies']==original_atlas['bodies']
        assert sha(owner)==report['owner_pointer_sha256']
        assert all(sha(ROOT/p)==value for p,value in hashes.items())
        report['completed']=True  # Separate auditor decides acceptance.
    except Exception:
        report['failure']=traceback.format_exc()
    finally:
        if gpu_job is not None:
            try:
                output=gpu_job.communicate(timeout=20)[0]
                (folder/'interrupted-collector.log').write_text(output,encoding='utf-8')
            except subprocess.TimeoutExpired:
                gpu_job.terminate();gpu_job.communicate(timeout=5)
        try:post('/api/command',{'command':'pause'})
        except Exception:pass
        persist()
        if _socket is not None:_socket.close()
    print(json.dumps({'receipt':receipt.relative_to(ROOT).as_posix(),'completed':report['completed'],'failure':report.get('failure')}))
    return 0 if report['completed'] else 1


if __name__=='__main__':raise SystemExit(main())
