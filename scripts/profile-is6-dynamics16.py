"""Sealed four-window native profile for paused and moving sixteen-center dynamics."""
import argparse
import copy
import datetime as dt
import hashlib
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
import zipfile

from cef_page_v2 import Page
from native_product_memory_v2 import product_memory
from owned_process_preparation import stabilize
import collect_gpu_pdh_dynamics16 as gpu

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is6-dynamics16-product0.26.2/app'
h=SourceFileLoader('dynamics16_profile_helpers',str(ROOT/'scripts/benchmark-body-points-native.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);parser.add_argument('--plan-label',required=True);args=parser.parse_args()
    for label in [args.label,args.plan_label]:assert label and len(label)<=20 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label)
    folder=ROOT/f'output/is6-dynamics16-profile-{args.label}';out=ROOT/f'evidence/is6-dynamics16-profile-{args.label}.json'
    assert not folder.exists() and not out.exists(),'Preserve own performance evidence'
    plan_path=ROOT/f'evidence/is6-dynamics16-profile-plan-{args.plan_label}.json';plan=json.loads(plan_path.read_text())
    assert plan['accepted'] and plan['candidate']=='0.26.2' and len(plan['windows'])==4
    sources={**plan['source_sha256'],plan_path.relative_to(ROOT).as_posix():sha(plan_path)}
    assert all(sha(ROOT/n)==s for n,s in sources.items())
    launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert Path(launch['serverScript']).resolve()==APP/'server.py'
    assert Path(launch['launcher_script']).name=='launch-is6-dynamics16-candidate-v5.py'
    ready=json.loads((ROOT/'output/local-ui-readiness.json').read_text())
    assert ready['ready'] and ready['checked_root_page'] and ready['http_ready_before_engine_start'] and ready['server_pid']==launch['server']
    folder.mkdir();startup=folder/'startup-readiness.json';startup.write_bytes((ROOT/'output/local-ui-readiness.json').read_bytes())
    sources[startup.relative_to(ROOT).as_posix()]=sha(startup)
    archive=folder/'executed-sources.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name in sources:z.write(ROOT/name,name)
    result=dict(accepted=False,completed=False,session=launch,source_sha256=sources,source_archive_sha256=sha(archive),
        engine_sha256=sha(Path(launch['runtime'])/'bin/OpenSpace.exe'),owner_sha256=sha(ROOT/'user/sessions/latest.json'),
        warmup_s=30,window_s=60,limits_before_execution=plan['limits_before_execution'],runs=[],page_errors=[],
        scope='Own four-window sixteen-center physics/render profile; raw moving-clock WDDM process audit. No promotion, K5A replacement or full IS6 acceptance.')
    def persist():out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    def command(name,**fields):return h.post('/api/command',dict(command=name,**fields))
    def physics():return h.get('/api/state')['physics']
    def click(page,selector):
        page.locator(selector).click();page.wait_for_function('!pending',timeout=70000)
    job=None;persist()
    try:
        assert h.get('/api/state')['mode']=='atlas'
        atlas=h.get('/api/atlas/state');result['atlas_epoch']=atlas['epoch']
        with Page() as page:
            page.on('pageerror',lambda error:result['page_errors'].append(error))
            page.wait_for_function('appState?.mode==="atlas"&&atlasState&&!pending')
            page.locator('#ui-scale').select_option('1')
            for index,recipe in enumerate(plan['windows'],1):
                click(page,'#copy-sixteen')
                page.wait_for_function('appState?.mode==="experiment"&&appState.physics.bodies.length===16&&!pending',timeout=70000)
                initial=copy.deepcopy(physics());assert initial['paused'] and initial['time']==0 and len(initial['bodies'])==16
                assert initial['atlas_initial']['source']['epoch']['et_tdb_s']==atlas['epoch']['et_tdb_s']
                command('rate',value=recipe['rate'])
                if recipe['reference_id']:
                    selected=next(b for b in initial['bodies'] if b['reference_id']==recipe['reference_id'])
                    page.evaluate('$("solar-panel").open=true')
                    page.locator('#solar-body').select_option(selected['id']);click(page,'#solar-view-body')
                    expected_anchor=selected['scene_node']
                else:click(page,'#lab-home');expected_anchor='LabFrame'
                if not recipe['paused']:
                    command('resume');time.sleep(1);command('pause')
                preparation=dict(observations=[])
                if index==1:
                    def observe(row):preparation['observations'].append(row);result['process_tree_preparation']=preparation;persist()
                    preparation.update(stabilize(lambda:gpu.inventory(launch),observe));result['process_tree_preparation']=preparation
                page.evaluate('$("lab-panel").scrollTop=0;document.body.inert=true')
                row=dict(run=index,recipe=recipe,initial=initial,prewarm_phase=physics(),expected_anchor=expected_anchor,samples=[])
                result['pending_run']=row;persist()
                print(json.dumps(dict(stage='warmup',run=index,recipe=recipe,seconds=30)),flush=True);time.sleep(30)
                if not recipe['paused']:command('resume')
                gpu_label=f'is6d16-{args.label}-{index}'
                gpu_path=ROOT/f'evidence/gpu-pdh-{gpu_label}.json';signal_path=ROOT/f'output/gpu-memory-ready-{gpu_label}.json'
                assert not gpu_path.exists() and not signal_path.exists()
                job=subprocess.Popen([sys.executable,'-Xutf8',str(ROOT/'scripts/collect_gpu_pdh_dynamics16.py'),
                    '--label',gpu_label,'--samples','66','--expected-mode','experiment','--expected-worker','paused' if recipe['paused'] else 'any','--signal-ready'],
                    stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace')
                deadline=time.monotonic()+30
                while True:
                    if job.poll() is not None:raise RuntimeError(job.communicate()[0])
                    if signal_path.exists():
                        try:signal=json.loads(signal_path.read_text())
                        except (ValueError,PermissionError):time.sleep(.05);continue
                        assert signal['engine_pid']==launch['app'];break
                    if time.monotonic()>deadline:raise TimeoutError('PDH first sample not confirmed')
                    time.sleep(.05)
                h.native('openspace.cosmos2BeginStageTrace();openspace.cosmos2BeginFrameCapture(12000);return {ready=true}')
                row['capture_start_utc']=dt.datetime.now(dt.timezone.utc).isoformat();began=time.perf_counter()
                row['phase_at_capture_start']=copy.deepcopy(physics())
                print(json.dumps(dict(stage='capture',run=index,paused=recipe['paused'],rate=recipe['rate'])),flush=True)
                for part in range(4):
                    remaining=began+part*20-time.perf_counter()
                    if remaining>0:time.sleep(remaining)
                    phase=copy.deepcopy(physics())
                    assert phase['paused'] is recipe['paused'] and phase['requested_rate']==recipe['rate']
                    assert phase['revision']==0 and len(phase['bodies'])==16 and phase['atlas_initial']==initial['atlas_initial']
                    native=h.native('return {camera=openspace.navigation.getNavigationState(),memory=openspace.cosmos2MemoryMetrics()}')
                    assert native['camera']['Anchor']==expected_anchor
                    row['samples'].append(dict(offset_s=time.perf_counter()-began,physics=phase,ram=product_memory(launch),native=native,
                        ui=page.evaluate('({scale:$("ui-scale").value,mode:appState.mode,hidden:$("lab-panel").hidden})')))
                row.update(h.native('return {trace=openspace.cosmos2EndStageTrace(),capture=openspace.cosmos2EndFrameCapture()}'))
                row.update(capture_end_utc=dt.datetime.now(dt.timezone.utc).isoformat(),wall_interval_s=time.perf_counter()-began,phase_at_capture_end=copy.deepcopy(physics()))
                output=job.communicate(timeout=30)[0];(folder/f'gpu-{index}.log').write_text(output,encoding='utf8')
                assert job.returncode==0,output;job=None
                row.update(gpu_report=gpu_path.relative_to(ROOT).as_posix(),gpu_sha256=sha(gpu_path))
                command('pause');row['final']=copy.deepcopy(physics())
                assert row['final']['time']*row['final']['physical_scale']['time_unit_s']<30*86400
                result['runs'].append(row);result.pop('pending_run');persist()
                page.evaluate('document.body.inert=false');command('atlas')
                page.wait_for_function('appState?.mode==="atlas"&&!pending')
            assert not result['page_errors']
            assert h.get('/api/atlas/state')['epoch']==result['atlas_epoch']
            result['completed']=True
    except Exception:result['failure']=traceback.format_exc()
    finally:
        if job:
            try:(folder/'interrupted-gpu.log').write_text(job.communicate(timeout=30)[0],encoding='utf8')
            except subprocess.TimeoutExpired:job.terminate();job.communicate(timeout=5)
        try:
            h.native('openspace.cosmos2EndStageTrace();openspace.cosmos2EndFrameCapture();return {stopped=true}')
            with Page() as page:page.evaluate('document.body.inert=false')
            if h.get('/api/state')['mode']=='experiment':command('pause');command('atlas')
            assert all(sha(ROOT/n)==s for n,s in sources.items()) and sha(ROOT/'user/sessions/latest.json')==result['owner_sha256']
        except Exception:result['cleanup_failure']=traceback.format_exc();result['completed']=False
        persist()
    print(json.dumps(dict(completed=result['completed'],runs=len(result['runs']),failure=result.get('failure','').splitlines()[-1:])),flush=True)
    return 0 if result['completed'] else 1


if __name__=='__main__':raise SystemExit(main())
