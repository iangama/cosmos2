"""Four native spatial rendering/probe windows, raw frames and Windows resources."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import argparse
import copy
import datetime as dt
import hashlib
import json
import subprocess
import sys
import threading
import time
import traceback
import zipfile
from cef_page import Page
from native_product_memory import product_memory

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is6-spatial-product0.18.2/app'
sys.path.insert(0,str(APP))
from is6_product_scene import artifact
h=SourceFileLoader('is6_frame_helpers',str(ROOT/'scripts/benchmark-body-points-native.py')).load_module()
get,native,post=h.get,h.native,h.post
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
LIMITS=dict(median_ms=16.7,p95_ms=25.,p99_ms=50.,over_100ms=0,RAM_bytes=8*2**30,GPU_bytes=5.5*2**30,
            command_rate_min=.9,command_p95_s=.5,command_max_s=1.)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);parser.add_argument('--acceptance-label',default='20261102f');args=parser.parse_args()
    for label in [args.label,args.acceptance_label]:
        if not label or len(label)>20 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):parser.error('Invalid label')
    folder=ROOT/('output/is6-spatial-profile-'+args.label);receipt=ROOT/('evidence/is6-spatial-profile-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve profile evidence')
    launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert Path(launch['serverScript']).resolve()==(APP/'server.py').resolve() and launch['is6SpatialCandidate']
    anchors=[ROOT/('evidence/is6-product-native-'+args.acceptance_label+'.json'),ROOT/('evidence/is6-product-visual-review-'+args.acceptance_label+'.json'),
             ROOT/'evidence/is6-persistence-native-20261102b.json',ROOT/'evidence/is6-catalog-cache-20261102a.json']
    sources={}
    for p in anchors:
        r=json.loads(p.read_text());assert r['accepted'],p;sources.update(r['source_sha256'])
    for p in [Path(__file__),ROOT/'scripts/audit-is6-spatial-profile.py',ROOT/'IS-6-PERFIL-PREVIO.md',
              ROOT/'scripts/benchmark-body-points-native.py',ROOT/'scripts/native_product_memory.py',ROOT/'scripts/collect-gpu-memory-diagnostic.ps1',ROOT/'scripts/collect-gpu-memory.ps1',*anchors]:
        sources[p.relative_to(ROOT).as_posix()]=sha(p)
    assert all(sha(ROOT/n)==v for n,v in sources.items())
    folder.mkdir();archive=folder/'executed-sources.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in sources:z.write(ROOT/n,n)
    r=dict(completed=False,accepted=False,session=launch,source_sha256=sources,archive_sha256=sha(archive),
           engine_sha256=sha(Path(launch['runtime'])/'bin/OpenSpace.exe'),owner_sha256=sha(ROOT/'user/sessions/latest.json'),
           limits_before_execution=LIMITS,warmup_s=30,window_s=60,runs=[],page_errors=[],
           scope='Static spatial mesh and exact-probe/visibility2Hz product journeys; not GR integration throughput, arbitrary workloads, multiple simultaneous layers or promotion.')
    def persist():receipt.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def state():return get('/api/spatial/state')
    def command(operation,**extra):return post('/api/spatial/command',dict(command=operation,guard=state()['guard'],**extra))
    gpu_job=producer=None;stop=threading.Event()
    persist()
    try:
        with Page() as page:
            page.on('pageerror',lambda error:r['page_errors'].append(error));page.goto(h.test.BASE+'/')
            page.wait_for_function('appState&&atlasState&&spatialInstrument.snapshot&&!pending')
            if state()['active']:command('leave')
            if get('/api/state')['mode']=='experiment':post('/api/command',dict(command='atlas'))
            page.wait_for_function('appState?.mode==="atlas"&&!pending')
            h.test.click(page,'#copy-solar');page.wait_for_function('appState?.physics?.bodies.length===4&&!pending',timeout=70000)
            phase=get('/api/state')['physics'];held=h.test.phase(copy.deepcopy(phase));r['source_phase']=held
            page.locator('#ui-scale').select_option('1');page.locator('#open-spatial').click()
            for index,(kind,count) in enumerate([('static-default',65),('static-maximum',257),('probe-maximum',257),('visibility-maximum',257)],1):
                config={**artifact.DEFAULT_CONFIGURATION,'radial_count':count}
                command('create',source_guard=artifact.body.guard(phase),body_id=phase['bodies'][0]['id'],configuration=config)
                s=state();payload=command('get_artifact')['result'];run=artifact.Run.restore(payload)
                payload_path=folder/('artifact-'+str(index)+'.json');payload_path.write_text(json.dumps(payload,ensure_ascii=False)+'\n',encoding='utf-8')
                assert s['artifact']['configuration']==config
                recipe=[]
                if kind in ['probe-maximum','visibility-maximum']:
                    for tick in range(120):
                        view=run.default_view()
                        if kind=='probe-maximum':view.update(selected_radial_index=(tick*17)%count,selected_azimuth_index=(tick*11)%96,reference_radial_index=(tick*19)%count)
                        else:view['visible']=tick%2==1
                        recipe.append(dict(tick=tick,offset_s=tick*.5,view=view,sample=run.sample(view)))
                recipe_path=folder/('recipe-'+str(index)+'.json');recipe_path.write_text(json.dumps(recipe,ensure_ascii=False)+'\n',encoding='utf-8')
                with zipfile.ZipFile(archive,'a',zipfile.ZIP_DEFLATED) as z:
                    for p in [payload_path,recipe_path]:z.write(p,p.relative_to(ROOT).as_posix())
                r['archive_sha256']=sha(archive)
                r.setdefault('inputs_before_execution',[]).append(dict(run=index,artifact=payload_path.relative_to(ROOT).as_posix(),artifact_sha256=sha(payload_path),recipe=recipe_path.relative_to(ROOT).as_posix(),recipe_sha256=sha(recipe_path)))
                persist()
                page.wait_for_function('spatialInstrument.snapshot.artifact?.id==='+json.dumps(run.id))
                page.evaluate('document.getElementById("spatial-reading").scrollIntoView({block:"start"});document.body.inert=true')
                print(json.dumps(dict(stage='warmup',run=index,kind=kind,seconds=30)),flush=True);time.sleep(30)
                label='is6-'+args.label+'-'+str(index);ready=ROOT/('output/gpu-memory-ready-'+label+'.json');gpu_path=ROOT/('evidence/gpu-memory-'+label+'.json')
                if ready.exists() or gpu_path.exists():raise FileExistsError(label)
                gpu_job=subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/collect-gpu-memory-diagnostic.ps1'),'-Label',label,'-Samples','66','-ExpectedMode','experiment','-ExpectedWorker','paused','-SignalReady'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
                until=time.monotonic()+20
                while True:
                    if gpu_job.poll() is not None:raise RuntimeError(gpu_job.communicate()[0])
                    if time.monotonic()>until:raise TimeoutError('GPU readiness')
                    if ready.exists():
                        try:signal=json.loads(ready.read_text(encoding='utf-8-sig'))
                        except (ValueError,PermissionError):time.sleep(.05);continue
                        assert signal['engine_pid']==launch['app'];break
                    time.sleep(.05)
                row=dict(run=index,kind=kind,radial_count=count,artifact=payload_path.relative_to(ROOT).as_posix(),artifact_sha256=sha(payload_path),
                         recipe=recipe_path.relative_to(ROOT).as_posix(),recipe_sha256=sha(recipe_path),initial=state(),samples=[],commands=[],producer_errors=[])
                r['pending_run']=row;persist()
                native('openspace.cosmos2BeginFrameCapture(12000);return {ready=true}')
                started=dt.datetime.now(dt.timezone.utc);began=time.perf_counter();row['capture_start_utc']=started.isoformat()
                def produce():
                    try:
                        for item in recipe:
                            if stop.wait(max(0,began+item['offset_s']-time.perf_counter())):return
                            entered=time.perf_counter();response=command('set_view',view=item['view']);finished=time.perf_counter()
                            confirmed=response['spatial']
                            assert confirmed['artifact']['sha256']==s['artifact']['sha256'] and confirmed['artifact']['sample']==item['sample'] and confirmed['artifact']['view']==item['view']
                            row['commands'].append(dict(tick=item['tick'],started_offset_s=entered-began,finished_offset_s=finished-began,elapsed_s=finished-entered,guard=confirmed['guard'],artifact_sha256=confirmed['artifact']['sha256'],view=confirmed['artifact']['view'],sample=confirmed['artifact']['sample']))
                    except Exception:row['producer_errors'].append(traceback.format_exc())
                producer=threading.Thread(target=produce,daemon=True);producer.start()
                print(json.dumps(dict(stage='capture',run=index,kind=kind)),flush=True)
                for part in range(4):
                    remaining=began+20*part-time.perf_counter()
                    if remaining>0:time.sleep(remaining)
                    stable_until=time.monotonic()+1
                    while True:
                        sample=state()
                        flags=native('return {draw=openspace.propertyValue("Scene.'+sample['scene']['wire']+'.Renderable.DrawElements")}')
                        following=state()
                        if not sample['busy'] and not following['busy'] and sample['guard']==following['guard']:
                            break
                        if time.monotonic()>stable_until:raise TimeoutError('Stable visibility readback')
                        time.sleep(.01)
                    p=get('/api/state')['physics'];assert h.test.phase(p)==held
                    row['samples'].append(dict(offset_s=time.perf_counter()-began,spatial=sample,following_spatial=following,source=p,native=flags,ram=product_memory(launch),engine_gpu=native('return openspace.cosmos2MemoryMetrics()')))
                row.update(capture=native('return openspace.cosmos2EndFrameCapture()'),capture_end_utc=dt.datetime.now(dt.timezone.utc).isoformat(),wall_interval_s=time.perf_counter()-began,final=state())
                producer.join(timeout=2)
                if producer.is_alive():raise TimeoutError('Probe producer did not finish')
                producer=None;persist()
                output=gpu_job.communicate(timeout=60)[0];(folder/('gpu-'+str(index)+'.log')).write_text(output,encoding='utf-8')
                assert gpu_job.returncode==0,output;gpu_job=None
                row.update(gpu_report=gpu_path.relative_to(ROOT).as_posix(),gpu_sha256=sha(gpu_path))
                r['runs'].append(row);r.pop('pending_run');persist()
                page.evaluate('document.body.inert=false');command('leave')
            post('/api/command',dict(command='atlas'))
        assert not r['page_errors'] and sha(ROOT/'user/sessions/latest.json')==r['owner_sha256']
        assert all(sha(ROOT/n)==v for n,v in sources.items())
        r['completed']=True
    except Exception:r['failure']=traceback.format_exc()
    finally:
        stop.set()
        if producer:producer.join(timeout=5)
        if gpu_job:
            try:(folder/'interrupted-gpu.log').write_text(gpu_job.communicate(timeout=60)[0],encoding='utf-8')
            except subprocess.TimeoutExpired:gpu_job.terminate();gpu_job.communicate(timeout=5)
        try:
            if state()['active']:command('leave')
            with Page() as page:page.evaluate('document.body.inert=false')
            if get('/api/state')['mode']=='experiment':post('/api/command',dict(command='atlas'))
            native('openspace.toggleShutdown();return {closing=true}')
        except Exception:r['cleanup_failure']=traceback.format_exc()
        persist()
        if h._socket:h._socket.close()
    print(json.dumps(dict(completed=r['completed'],runs=len(r['runs']),failure=r.get('failure'),cleanup_failure=r.get('cleanup_failure'))),flush=True)
    return 0 if r['completed'] else 1


if __name__=='__main__':raise SystemExit(main())
