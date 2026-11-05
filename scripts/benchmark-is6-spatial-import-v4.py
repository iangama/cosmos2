"""Owned0.22.1 frozen imported mesh profile with raw frames and native PDH."""
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
from cef_page_v2 import Page
from native_product_memory_v2 import product_memory
from is6_owned_profile_host import Host
import gpu_pdh_audit_v3 as gpu_audit
import windows_gpu_pdh_v2 as pdh
import collect_gpu_pdh_v3 as gpu_collector
from owned_process_preparation import stabilize

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT/'output/is6-spatial-import-product0.22.1/app'
sys.path.insert(0,str(APP))
import is6_spatial_import_store as storage
from is6_product_scene import lua
h = SourceFileLoader('spatial_import_frame_helpers',str(ROOT/'scripts/benchmark-body-points-native.py')).load_module()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
PHASE = ['system_id','edit_token','revision','time','bodies','atlas_initial','interventions']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label',required=True)
    parser.add_argument('--plan-label',default='20261105p1')
    args = parser.parse_args()
    for label in [args.label,args.plan_label]:
        if not label or len(label)>25 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
            parser.error('Invalid label')
    folder = ROOT/('output/is6-spatial-import-profile-'+args.label)
    out = ROOT/('evidence/is6-spatial-import-profile-'+args.label+'.json')
    if folder.exists() or out.exists():
        raise FileExistsError('Preserve spatial import profile')
    plan_path = ROOT/('evidence/is6-spatial-import-profile-plan-'+args.plan_label+'.json')
    plan = json.loads(plan_path.read_text())
    assert plan['accepted'] and plan['candidate']=='0.22.1' and len(plan['windows'])==4
    sources = dict(plan['source_sha256'])
    for path in [Path(__file__),plan_path,ROOT/'scripts/audit-is6-spatial-import-profile-v3.py',
        ROOT/'scripts/native_product_memory_v2.py',ROOT/'scripts/benchmark-body-points-native.py',
        ROOT/'scripts/owned_process_preparation.py',ROOT/'IS-6-IMPORTACAO-ESPACIAL-PREPARACAO-V4.md',
        ROOT/'scripts/verify-native-solar-integration.py',ROOT/'scripts/cef_page_v2.py',
        ROOT/'scripts/launch-is6-spatial-import-candidate-v2.py',ROOT/'scripts/bootstrap-native-ui-v2.py',
        ROOT/'scripts/native_ui_readiness.py',ROOT/'config/window-1080.json',ROOT/'config/cosmos2.cfg']:
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
    assert all(sha(ROOT/name)==seal for name,seal in sources.items())
    folder.mkdir()
    archive = folder/'executed-sources-inputs.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as package:
        for name in sources:
            package.write(ROOT/name,name)
    result = dict(completed=False,accepted=False,candidate='0.22.1',source_sha256=sources,
        archive_sha256=sha(archive),limits_before_execution=plan['limits_before_execution'],
        warmup_s=30,window_s=60,owner_sha256=sha(ROOT/'user/sessions/latest.json'),runs=[],
        inputs_before_execution=[],page_errors=[],
        scope='Imported solar1–8Rref65x96 mesh/API-view windows only. No import/save/startup throughput,257-ring derivation, coupled orbital GR, promotion or full IS6/v1 acceptance.')
    host = Host(folder,h)
    gpu_job=producer=None
    stop = threading.Event()
    store = storage.Store(APP.parent/'is6-spatial-import-service-records')
    def persist():
        out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    def state():
        return h.get('/api/spatial/state')
    def command(operation,**fields):
        return h.post('/api/spatial/command',dict(command=operation,guard=state()['guard'],**fields))
    def archive_paths(paths):
        rows = {path.relative_to(ROOT).as_posix():sha(path) for path in paths}
        with zipfile.ZipFile(archive,'a',zipfile.ZIP_DEFLATED) as package:
            for path in paths:
                package.write(path,path.relative_to(ROOT).as_posix())
        result['archive_sha256'] = sha(archive)
        return rows
    def records():
        return {path.relative_to(ROOT).as_posix():sha(path) for path in [store.path,*store.branches.glob('*.json'),*store.exports.glob('*.json')] if path.is_file()}
    def context(phase):
        names=['LabGrid','LabBarycenter','LabProbe']
        for body in phase['bodies']:
            names.extend(body[k] for k in ['scene_node','label_node','shape_node','spin_node'] if body.get(k))
        return h.native('local f={};for _,n in ipairs('+lua(names)+') do if openspace.hasSceneGraphNode(n) then local ok,v=pcall(openspace.propertyValue,"Scene."..n..".Renderable.Enabled");if ok and type(v)=="boolean" then f[n]=v end end end;return {camera=openspace.navigation.getNavigationState("Root"),flags=f}')
    persist()
    try:
        session=host.start()
        result.update(session=session,readiness=host.readiness,
                      engine_sha256=sha(Path(session['runtime'])/'bin/OpenSpace.exe'))
        result['records_before']=records()
        archived=[]
        for name,seal in result['records_before'].items():
            path=ROOT/name
            target=folder/'persisted-before'/path.relative_to(store.folder)
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(path.read_bytes())
            assert sha(target)==seal
            archived.append(target)
        result['persisted_archives']=archive_paths(archived)
        with Page() as page:
            page.on('pageerror',lambda error:result['page_errors'].append(error))
            page.wait_for_function('typeof spatialInstrument!=="undefined"&&spatialInstrument.snapshot&&typeof appState!=="undefined"&&appState&&!pending',timeout=70000)
            assert page.evaluate('location.href')=='http://127.0.0.1:4700/' and h.get('/api/state')['mode']=='atlas'
            page.locator('#open-spatial').click()
            page.locator('#spatial-copy').click()
            page.wait_for_function('appState.physics?.bodies.length===4&&!pending',timeout=70000)
            phase=h.get('/api/state')['physics']
            held={key:copy.deepcopy(phase[key]) for key in PHASE}
            assert phase['paused'] is True
            result['source_phase']=held
            result['base_context']=context(phase)
            page.locator('#ui-scale').select_option('1')
            # Preparation only: a just-replaced physics/CEF descendant may
            # leave while the first inventory is being enumerated. No GPU
            # sample has started; require five equal one-second snapshots.
            preparation=dict(observations=[],consecutive_stable=0)
            result['process_tree_preparation']=preparation
            def observe_preparation(row):
                preparation['observations'].append(row)
                preparation['consecutive_stable']=row['consecutive_stable']
                persist()
            preparation.update(stabilize(lambda:gpu_collector.inventory(session),observe_preparation))
            persist()
            prelabel='is6p-'+args.label+'-pre'
            preflight=ROOT/('evidence/gpu-pdh-'+prelabel+'.json')
            validator=ROOT/('evidence/gpu-pdh-preflight-'+prelabel+'.json')
            assert not preflight.exists() and not validator.exists()
            work=subprocess.run([sys.executable,'-Xutf8',str(ROOT/'scripts/collect_gpu_pdh_v3.py'),
                '--label',prelabel,'--samples','3','--expected-mode','experiment','--expected-worker','paused'],
                capture_output=True,text=True,encoding='utf8',timeout=40)
            assert work.returncode==0,work.stdout+work.stderr
            checked=subprocess.run([sys.executable,'-Xutf8',str(ROOT/'scripts/verify-gpu-pdh-report-v3.py'),
                '--label',prelabel,'--input',str(preflight)],capture_output=True,text=True,encoding='utf8',timeout=90)
            assert checked.returncode==0,checked.stdout+checked.stderr
            assert json.loads(validator.read_text())['accepted']
            result['paused_GPU_preflight']=dict(path=preflight.relative_to(ROOT).as_posix(),sha256=sha(preflight),
                validation=validator.relative_to(ROOT).as_posix(),validation_sha256=sha(validator))
            archive_paths([preflight,validator])
            for item in plan['windows']:
                data=json.loads((ROOT/item['path']).read_text())
                assert sha(ROOT/item['path'])==item['sha256']
                command('branch_load',branch_id=plan['branch_id'],source_guard=storage.artifact.body.guard(phase))
                command('set_view',view=data['initial_view'])
                initial=state()
                assert initial['artifact']['sha256']==plan['artifact_sha256']
                assert initial['artifact']['origin']['source_sha256']==plan['source_sha256_original']
                scene=initial['scene']
                native_file=Path(h.native('return {file=openspace.propertyValue("Scene.'+scene['wire']+'.Renderable.File")}')['file'])
                scene_paths=[native_file,native_file.with_suffix('.names'),native_file.parent/'binding.json']
                files=archive_paths(scene_paths)
                entry=dict(run=data['run'],recipe=item,scene_files=files)
                result['inputs_before_execution'].append(entry)
                row=dict(run=data['run'],kind=data['kind'],input=entry,initial=initial,context=context(phase),
                    samples=[],commands=[],producer_errors=[])
                result['pending_run']=row
                page.wait_for_function('spatialInstrument.snapshot.artifact?.id==='+json.dumps(initial['artifact']['id']))
                page.evaluate('document.getElementById("spatial-reading").scrollIntoView({block:"start"});document.body.inert=true')
                persist()
                print(json.dumps(dict(stage='warmup',run=data['run'],kind=data['kind'],seconds=30)),flush=True)
                time.sleep(30)
                label='is6p-'+args.label+'-'+str(data['run'])
                ready=ROOT/('output/gpu-memory-ready-'+label+'.json')
                gpu_path=ROOT/('evidence/gpu-pdh-'+label+'.json')
                assert not ready.exists() and not gpu_path.exists()
                gpu_job=subprocess.Popen([sys.executable,'-u','-Xutf8',str(ROOT/'scripts/collect_gpu_pdh_v3.py'),
                    '--label',label,'--samples','66','--expected-mode','experiment','--expected-worker','paused',
                    '--signal-ready'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8')
                deadline=time.monotonic()+20
                while not ready.exists():
                    if gpu_job.poll() is not None:
                        raise RuntimeError(gpu_job.communicate()[0])
                    if time.monotonic()>deadline:
                        raise TimeoutError('Native PDH collector did not signal readiness')
                    time.sleep(.025)
                signal=json.loads(ready.read_text())
                assert signal['schema']==4 and signal['engine_pid']==session['app']
                h.native('openspace.cosmos2BeginFrameCapture(12000);return {ready=true}')
                began=time.perf_counter()
                row['capture_start_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
                recipe=data['recipe']
                def produce():
                    try:
                        for scheduled in recipe:
                            if stop.wait(max(0,began+scheduled['offset_s']-time.perf_counter())):
                                return
                            entered=time.perf_counter()
                            response=command('set_view',view=scheduled['view'])['spatial']
                            finished=time.perf_counter()
                            assert response['artifact']['sample']==scheduled['sample'] and response['artifact']['view']==scheduled['view']
                            row['commands'].append(dict(tick=scheduled['tick'],started_offset_s=entered-began,
                                finished_offset_s=finished-began,elapsed_s=finished-entered,guard=response['guard'],
                                artifact_sha256=response['artifact']['sha256'],view=response['artifact']['view'],sample=response['artifact']['sample']))
                    except Exception:
                        row['producer_errors'].append(traceback.format_exc())
                producer=threading.Thread(target=produce,daemon=True)
                producer.start()
                print(json.dumps(dict(stage='capture',run=data['run'],kind=data['kind'])),flush=True)
                for part in range(4):
                    delay=began+20*part-time.perf_counter()
                    if delay>0:
                        time.sleep(delay)
                    deadline=time.monotonic()+1
                    while True:
                        before=state()
                        native=h.native('return {draw=openspace.propertyValue("Scene.'+scene['wire']+'.Renderable.DrawElements")}')
                        after=state()
                        if not before['busy'] and not after['busy'] and before['guard']==after['guard']:
                            break
                        if time.monotonic()>deadline:
                            raise TimeoutError('No stable native visibility readback')
                        time.sleep(.01)
                    physics=h.get('/api/state')['physics']
                    assert {key:physics[key] for key in PHASE}==held and physics['paused'] is True
                    ui=page.evaluate('({url:location.href,scale:document.getElementById("ui-scale").value,active:spatialInstrument.snapshot.active,error:spatialInstrument.error,guard:spatialInstrument.snapshot.guard})')
                    row['samples'].append(dict(offset_s=time.perf_counter()-began,spatial=before,following_spatial=after,
                        native=native,source_phase={key:physics[key] for key in PHASE},paused=physics['paused'],
                        context=context(phase),ui=ui,ram=product_memory(session),
                        engine_gpu=h.native('return openspace.cosmos2MemoryMetrics()')))
                row.update(capture=h.native('return openspace.cosmos2EndFrameCapture()'),
                    capture_end_utc=dt.datetime.now(dt.timezone.utc).isoformat(),wall_interval_s=time.perf_counter()-began,final=state())
                producer.join(timeout=2)
                assert not producer.is_alive()
                producer=None
                output=gpu_job.communicate(timeout=30)[0]
                (folder/('gpu-'+str(data['run'])+'.log')).write_text(output,encoding='utf8')
                assert gpu_job.returncode==0,output
                gpu_job=None
                row.update(gpu_report=gpu_path.relative_to(ROOT).as_posix(),gpu_sha256=sha(gpu_path))
                gpu=json.loads(gpu_path.read_text())
                gpu_audit.audit(gpu,expected_samples=66,expected_session=session,engine_sha256=result['engine_sha256'],
                    generation=pdh.generation(),coverage=[row['capture_start_utc'],row['capture_end_utc']])
                result['runs'].append(row)
                result.pop('pending_run')
                persist()
                page.evaluate('document.body.inert=false')
                command('leave')
            result['records_after']=records()
            assert result['records_after']==result['records_before'] and not result['page_errors']
        assert all(sha(ROOT/name)==seal for name,seal in sources.items())
        result['completed']=True
    except Exception:
        result['failure']=traceback.format_exc()
    finally:
        stop.set()
        if producer:
            producer.join(timeout=5)
        if gpu_job:
            try:
                output=gpu_job.communicate(timeout=30)[0]
            except subprocess.TimeoutExpired:
                gpu_job.terminate()
                output=gpu_job.communicate(timeout=5)[0]
            (folder/'interrupted-gpu.log').write_text(output,encoding='utf8')
        try:
            with Page() as page:
                page.evaluate('document.body.inert=false')
            result['processes']=host.close()
            assert sha(ROOT/'user/sessions/latest.json')==result['owner_sha256']
        except Exception:
            result['cleanup_failure']=traceback.format_exc()
        persist()
    print(json.dumps(dict(completed=result['completed'],runs=len(result['runs']),failure=result.get('failure'),
                         cleanup_failure=result.get('cleanup_failure'))),flush=True)
    return 0 if result['completed'] and not result.get('cleanup_failure') else 1


if __name__=='__main__':
    raise SystemExit(main())
