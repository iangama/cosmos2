"""K5: own UI/API profile with existing, unchanged compound records."""
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

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is6-layers-product0.21.1/app'
sys.path.insert(0,str(APP))
from cef_page_v2 import Page
from native_product_memory import product_memory
from is6_product_scene import lua
import is6_layer_contract as contract
import is6_layers_import_store_v2 as storage
import is6_layers_profile_support as support
h=SourceFileLoader('k4_frame_helpers',str(ROOT/'scripts/benchmark-body-points-native.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def context(phase):
    names=['LabGrid','LabBarycenter','LabProbe']
    for body in phase['bodies']:
        names.extend(body[k] for k in ['scene_node','label_node','shape_node','spin_node'] if body.get(k))
    return h.native('local f={};for _,n in ipairs('+lua(names)+') do if openspace.hasSceneGraphNode(n) then local ok,v=pcall(openspace.propertyValue,"Scene."..n..".Renderable.Enabled");if ok and type(v)=="boolean" then f[n]=v end end end;return {camera=openspace.navigation.getNavigationState("Root"),flags=f}')


def click(page,selector):
    page.wait_for_function('!document.querySelector('+json.dumps(selector)+').disabled',timeout=30000)
    page.locator(selector).click()
    page.wait_for_function('!layerInstrument.pending&&!layerInstrument.snapshot?.busy',timeout=70000)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);parser.add_argument('--plan-label',default='20261104t');args=parser.parse_args()
    for label in [args.label,args.plan_label]:
        if not label or len(label)>20 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):parser.error('Invalid label')
    folder=ROOT/('output/is6-layers-import-profile-'+args.label);out=ROOT/('evidence/is6-layers-import-profile-'+args.label+'.json')
    if folder.exists() or out.exists():raise FileExistsError('Preserve profile evidence')
    plan_path=ROOT/('evidence/is6-layers-import-profile-plan-'+args.plan_label+'.json');plan=json.loads(plan_path.read_text())
    assert plan['accepted'] and plan['candidate']=='0.21.1' and plan['limits_before_execution']==support.LIMITS
    sources=dict(plan['source_sha256'])
    files=[Path(__file__),plan_path,ROOT/'scripts/audit-is6-layers-import-profile-v2.py',ROOT/'scripts/run-is6-layers-import-profile-background-v2.py',
           ROOT/'scripts/benchmark-body-points-native.py',ROOT/'scripts/native_product_memory.py',ROOT/'scripts/cef_page_v2.py',
           ROOT/'scripts/collect-is6-gpu-memory-scoped.ps1',ROOT/'config/window-1080.json',ROOT/'config/cosmos2.cfg']
    for path in files:sources[path.relative_to(ROOT).as_posix()]=sha(path)
    assert all(sha(ROOT/p)==seal for p,seal in sources.items())
    launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert launch['is6LayersCandidate'] and Path(launch['serverScript']).resolve()==APP/'server.py'
    folder.mkdir();archive=folder/'executed-sources-and-inputs.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name in sources:z.write(ROOT/name,name)
    r=dict(accepted=False,completed=False,source_sha256=sources,session=launch,archive_sha256=sha(archive),
           engine_sha256=sha(Path(launch['runtime'])/'bin/OpenSpace.exe'),owner_sha256=sha(ROOT/'user/sessions/latest.json'),
           limits_before_execution=support.LIMITS,warmup_s=30,window_s=60,runs=[],inputs_before_execution=[],scene_files_before_execution=[],page_errors=[],
           scope='K5 0.21.1 rendering/API visibility with existing compound catalog; records remain byte-identical. Not save throughput, human input throughput, automatic migration, promotion or full IS6/v1 acceptance.')
    gpu_job=producer=None;stop=threading.Event()
    def persist():out.write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    def state():return h.get('/api/layers/state')
    def command(name,**fields):return h.post('/api/layers/command',dict(command=name,guard=state()['guard'],**fields))
    def archive_paths(paths):
        seals={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
        with zipfile.ZipFile(archive,'a',zipfile.ZIP_DEFLATED) as z:
            for path in paths:z.write(path,path.relative_to(ROOT).as_posix())
        r['archive_sha256']=sha(archive)
        return seals
    def persisted_records():
        return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted((APP.parent/'layer-checkpoints').rglob('*.json'))}
    persist()
    try:
        r['persisted_before']=persisted_records()
        assert r['persisted_before'] and (APP.parent/'layer-checkpoints/latest.json').is_file()
        r['imported_records_before']=sum(storage.decode(json.loads((ROOT/name).read_text()))[2] is not None for name in r['persisted_before'])
        assert r['imported_records_before']>=1
        r['persisted_archives']={}
        archived=[]
        for name,seal in r['persisted_before'].items():
            original=ROOT/name;target=folder/'persisted-before'/original.relative_to(APP.parent/'layer-checkpoints')
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(original.read_bytes());assert sha(target)==seal
            r['persisted_archives'][name]=dict(path=target.relative_to(ROOT).as_posix(),sha256=seal);archived.append(target)
        archive_paths(archived);persist()
        with Page() as page:
            page.on('pageerror',lambda error:r['page_errors'].append(error));page.goto(h.test.BASE+'/')
            page.wait_for_function('appState&&atlasState&&layerInstrument.snapshot&&!pending')
            assert h.get('/api/state')['mode']=='atlas' and not state()['active']
            click(page,'#open-layers');click(page,'#layers-copy')
            page.wait_for_function('appState.physics?.bodies.length===4&&!pending',timeout=70000)
            phase=h.get('/api/state')['physics'];held=support.phase_fields(copy.deepcopy(phase));r['source_phase']=held;r['base_context']=context(phase)
            page.locator('#ui-scale').select_option('1')
            for index,(target,kind) in enumerate(support.WINDOWS,1):
                reference='sol:naif:'+target;settings=support.settings(phase,reference);planned=plan['windows'][index-1]
                assert planned['reference_id']==reference and planned['kind']==kind
                assert {k:v for k,v in settings.items() if k!='body_id'}==planned['settings'] and support.recipe(kind)==planned['recipe']
                page.locator('#layers-body').select_option(settings['body_id']);click(page,'#layers-create')
                initial=state();artifact=command('get_artifact')['result'];scientific=artifact['scientific']
                assert initial['checkpoint_available'] and len([b for b in initial['branches'] if b['valid']])>=3
                digest=support.verify_scientific(contract,scientific,phase,reference)
                support.confirm_response(initial,initial['artifact']['id'],digest,dict(spatial=True,magnetic=True))
                data=dict(body=target,kind=kind,scientific=scientific,recipe=planned['recipe'],settings=settings)
                input_path=folder/('input-'+str(index)+'.json');input_path.write_text(json.dumps(data,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
                entry=dict(run=index,path=input_path.relative_to(ROOT).as_posix(),sha256=sha(input_path));r['inputs_before_execution'].append(entry)
                archive_paths([input_path])
                scene=initial['scene'];paths=h.native('local m={};for _,n in ipairs('+lua(scene['magnetic_nodes'])+') do m[n]=openspace.propertyValue("Scene."..n..".Renderable.File") end;return {spatial=openspace.propertyValue("Scene.'+scene['spatial_wire']+'.Renderable.File"),magnetic=m}')
                mesh_paths=[Path(paths['spatial']),*[Path(p) for p in paths['magnetic'].values()]]
                scene_files=[*mesh_paths,*[p.with_suffix('.names') for p in mesh_paths],Path(paths['spatial']).parent/'binding.json',mesh_paths[1].parent/'receipt.json']
                r['scene_files_before_execution'].append(dict(run=index,sha256=archive_paths(scene_files)))
                row=dict(run=index,body=target,kind=kind,input=entry,initial=initial,scene_files=paths,context=context(phase),samples=[],commands=[],producer_errors=[])
                page.evaluate('document.getElementById("layers-panel").scrollTop=0;document.body.inert=true');persist()
                print(json.dumps(dict(stage='warmup',run=index,body=target,kind=kind,seconds=30)),flush=True);time.sleep(30)
                label='is6-k5-'+args.label+'-'+str(index);ready=ROOT/('output/gpu-memory-ready-'+label+'.json');gpu_path=ROOT/('evidence/gpu-memory-'+label+'.json')
                if ready.exists() or gpu_path.exists():raise FileExistsError('Preserve GPU evidence')
                gpu_job=subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/collect-is6-gpu-memory-scoped.ps1'),
                    '-Label',label,'-Samples','66','-ExpectedMode','experiment','-ExpectedWorker','paused','-SignalReady'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace')
                until=time.monotonic()+30
                while True:
                    if gpu_job.poll() is not None:raise RuntimeError(gpu_job.communicate()[0])
                    if time.monotonic()>until:raise TimeoutError('GPU readiness')
                    if ready.exists():
                        try:signal=json.loads(ready.read_text(encoding='utf-8-sig'))
                        except (ValueError,PermissionError):time.sleep(.05);continue
                        assert signal['engine_pid']==launch['app'];break
                    time.sleep(.05)
                r['pending_run']=row;persist();h.native('openspace.cosmos2BeginFrameCapture(12000);return {ready=true}')
                row['capture_start_utc']=dt.datetime.now(dt.timezone.utc).isoformat();began=time.perf_counter()
                def produce():
                    guard=initial['guard']
                    try:
                        for item in data['recipe']:
                            if stop.wait(max(0,began+item['offset_s']-time.perf_counter())):return
                            entered=time.perf_counter();answer=h.post('/api/layers/command',dict(command='set_visibility',guard=guard,visible=item['visible']));finished=time.perf_counter()
                            snapshot=answer['layers'];support.confirm_response(snapshot,initial['artifact']['id'],digest,item['visible'])
                            row['commands'].append(dict(tick=item['tick'],visible=item['visible'],guard_before=guard,response=snapshot,started_offset_s=entered-began,finished_offset_s=finished-began,elapsed_s=finished-entered))
                            guard=snapshot['guard']
                    except Exception:row['producer_errors'].append(traceback.format_exc())
                producer=threading.Thread(target=produce,daemon=True);producer.start();print(json.dumps(dict(stage='capture',run=index,body=target,kind=kind)),flush=True)
                for part in range(4):
                    remaining=began+part*20-time.perf_counter()
                    if remaining>0:time.sleep(remaining)
                    deadline=time.monotonic()+1
                    while True:
                        first=state();flags=h.native(support.flag_script(lua,scene));following=state()
                        if not first['busy'] and not following['busy'] and first['guard']==following['guard']:break
                        if time.monotonic()>deadline:raise TimeoutError('Stable K3 checkpoint')
                        time.sleep(.005)
                    support.verify_flags(flags,scene,first['artifact']['visible']);physics=h.get('/api/state')['physics'];assert support.phase_fields(physics)==held and physics['paused']
                    ui=page.evaluate('({url:location.href,scale:document.getElementById("ui-scale").value,panelHidden:document.getElementById("layers-panel").hidden,guard:layerInstrument.snapshot.guard,active:layerInstrument.snapshot.active,error:layerInstrument.error,reading:document.getElementById("layers-spatial-reading").textContent})')
                    row['samples'].append(dict(offset_s=time.perf_counter()-began,layers=first,following_layers=following,native=flags,source_phase=support.phase_fields(physics),paused=physics['paused'],context=context(phase),ui=ui,ram=product_memory(launch),engine_gpu=h.native('return openspace.cosmos2MemoryMetrics()')))
                row.update(capture=h.native('return openspace.cosmos2EndFrameCapture()'),capture_end_utc=dt.datetime.now(dt.timezone.utc).isoformat(),wall_interval_s=time.perf_counter()-began,final=state())
                producer.join(timeout=2);assert not producer.is_alive() and not row['producer_errors'];producer=None;persist()
                output=gpu_job.communicate(timeout=30)[0];(folder/('gpu-'+str(index)+'.log')).write_text(output,encoding='utf8');assert gpu_job.returncode==0,output;gpu_job=None
                row.update(gpu_report=gpu_path.relative_to(ROOT).as_posix(),gpu_sha256=sha(gpu_path));r['runs'].append(row);r.pop('pending_run')
                page.evaluate('document.body.inert=false');click(page,'#layers-leave');assert not state()['active'] and not state()['recovery_required']
                row['context_after_cleanup']=context(phase)
                nodes=[scene['spatial_frame'],scene['spatial_wire'],scene['spatial_frame'].replace('SpatialFrame_','SpatialFocus_'),scene['magnetic_frame'],*scene['magnetic_nodes'],*[scene['magnetic_frame']+s for s in ['_basis','_probe','_display_probe']]]
                row['nodes_after_cleanup']=h.native('local r={};for _,n in ipairs('+lua(nodes)+') do r[n]=openspace.hasSceneGraphNode(n) end;return r');assert not any(row['nodes_after_cleanup'].values());persist()
            h.post('/api/command',dict(command='atlas'));r['persisted_after']=persisted_records()
            assert r['persisted_after']==r['persisted_before'];r['completed']=True
    except Exception:r['failure']=traceback.format_exc()
    finally:
        stop.set()
        if producer:producer.join(timeout=5)
        if gpu_job:
            try:(folder/'interrupted-gpu.log').write_text(gpu_job.communicate(timeout=60)[0],encoding='utf8')
            except subprocess.TimeoutExpired:gpu_job.terminate();gpu_job.communicate(timeout=5)
        try:
            if state()['active'] or state()['recovery_required']:command('leave')
            with Page() as page:page.evaluate('document.body.inert=false')
            if h.get('/api/state')['mode']=='experiment':h.post('/api/command',dict(command='atlas'))
            h.native('openspace.toggleShutdown();return {closing=true}')
            assert sha(ROOT/'user/sessions/latest.json')==r['owner_sha256'] and all(sha(ROOT/p)==seal for p,seal in sources.items())
        except Exception:r['cleanup_failure']=traceback.format_exc();r['completed']=False
        persist()
        if h._socket:h._socket.close()
    print(json.dumps(dict(completed=r['completed'],runs=len(r['runs']),failure=r.get('failure','').splitlines()[-1:])),flush=True)
    return 0 if r['completed'] else 1


if __name__=='__main__':raise SystemExit(main())
