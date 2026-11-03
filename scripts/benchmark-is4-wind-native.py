"""Four scoped particle windows; preserve raw evidence for a separate auditor."""
from pathlib import Path
import argparse
import copy
import datetime as dt
import json
import math
import subprocess
import time
import traceback
import zipfile
from importlib.machinery import SourceFileLoader
from native_product_memory import product_memory
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
h=SourceFileLoader('is4_profile_helpers',str(ROOT/'scripts/benchmark-body-points-native.py')).load_module()
get,post,native,sha=h.get,h.post,h.native,h.sha
APP=ROOT/'output/is4-solar-wind-product0.9.0/app'

def guard(s):
    w=s['worker'];e=w['experiment']
    return dict(worker_id=w['worker_id'],experiment_id=e['id'],edit_token=e['edit_token'],revision=e['revision'],expected_time_s=e['phase']['time_s'],frame=w['frame'])

def command(name,**extra):
    s=get('/api/particles/state')
    return post('/api/particles/command',dict(command=name,**extra,**({'guard':guard(s)} if name not in ['create','create_wind','leave','load_saved'] else {})))

def phase(s):
    return {k:copy.deepcopy(s[k]) for k in ['system_id','edit_token','revision','time','bodies','interventions','atlas_initial']}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or len(args.label)>16 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/('output/is4-wind-profile-'+args.label);receipt=ROOT/('evidence/is4-wind-profile-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve evidence')
    folder.mkdir();launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert '0.9.0' in launch['serverScript'] and launch['runtimeVariant']=='is4-stream'
    assert json.loads((ROOT/'evidence/is4-native-wind-product-20261025a.json').read_text())['accepted']
    files=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [Path(__file__),ROOT/'IS-4-VENTO-SOLAR-PERFIL-PREVIO.md',ROOT/'scripts/benchmark-body-points-native.py',ROOT/'scripts/verify-native-solar-integration.py',ROOT/'scripts/engine-command.py',ROOT/'scripts/native_product_memory.py',ROOT/'scripts/cef_page.py',ROOT/'scripts/collect-gpu-memory-diagnostic.ps1',ROOT/'scripts/collect-gpu-memory.ps1',ROOT/'scripts/launch-is4-particle-081-candidate.py',ROOT/'config/window-1080.json',ROOT/'config/cosmos2.cfg',ROOT/'evidence/built-runtime-is4-stream.json']
    preflight=['is4-wind-field-20261025c.json','is4-wind-potential-20261025a.json','is4-wind-trajectories-20261025b.json','is4-wind-trajectories-audit-20261025b.json','is4-wind-experiment-20261025b.json','is4-native-wind-product-20261025a.json','is4-wind-product-visual-review-20261025a.json']
    for name in preflight:
        file=ROOT/'evidence'/name;assert json.loads(file.read_text())['accepted'];files.append(file)
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    archive=folder/'executed-sources.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    report=dict(schema=1,accepted=False,completed=False,session=launch,source_sha256=hashes,archive_sha256=sha(archive),engine_sha256=sha(Path(launch['runtime'])/'bin/OpenSpace.exe'),owner_sha256=sha(ROOT/'user/sessions/latest.json'),limits_before_execution=h.LIMITS,CEF_input_guard='body.inert=true only during warmup/capture; CEF rendered, physics unchanged.',warmup_s=30,window_s=60,requested_steps_per_s=200,runs=[])
    def persist():receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    persist();gpu_job=None
    try:
        with Page() as page:
            page.goto(h.test.BASE+'/');page.wait_for_function('appState!==null&&particleState!==null&&!pending')
            if get('/api/particles/state')['active']:command('leave')
            if get('/api/state')['mode']=='experiment':h.test.click(page,'#atlas')
            h.test.click(page,'#copy-solar');page.wait_for_function('appState?.physics?.bodies.length===4&&!pending',timeout=70000)
            source=get('/api/state')['physics'];original=phase(source);page.locator('#ui-scale').select_option('1')
            for index,(target,visible) in enumerate([(t,v) for t in ['proton-north','electron-south'] for v in [True,False]],1):
                electron=target=='electron-south'
                sg={k:source[k] for k in ['system_id','edit_token','revision','time']}|{'frame':source['contract']['frame']}
                command('create_wind',source_guard=sg,species='electron' if electron else 'proton',relative_speed_m_s=1000000. if electron else 100000.,pitch_deg=90.,coordinates=dict(radius_m=(5. if electron else 1.)*149597870700.,latitude_deg=-60. if electron else 30.,east_longitude_deg=20.),wind_parameters=dict(wind_speed_m_s=400000.,radial_field_at_AU_T=3e-9,rotation_rate_rad_s=2*math.pi/(25.38*86400.),polarity=-1 if electron else 1))
                dt_s=get('/api/particles/state')['worker']['experiment']['parameters']['dt_s']
                command('set_rate',value=200*dt_s);command('visible',visible=visible);command('frame')
                page.evaluate('document.body.inert=true');command('resume')
                print(json.dumps(dict(stage='warmup',run=index,target=target,visible=visible)),flush=True);time.sleep(30)
                label='is4-w-'+args.label+'-'+str(index);ready=ROOT/('output/gpu-memory-ready-'+label+'.json');gpu_path=ROOT/('evidence/gpu-memory-'+label+'.json')
                if ready.exists() or gpu_path.exists():raise FileExistsError(label)
                gpu_job=subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/collect-gpu-memory-diagnostic.ps1'),'-Label',label,'-Samples','66','-ExpectedMode','experiment','-ExpectedWorker','paused','-SignalReady'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
                deadline=time.monotonic()+20
                while not ready.exists():
                    if gpu_job.poll() is not None:raise RuntimeError(gpu_job.communicate()[0])
                    if time.monotonic()>deadline:raise TimeoutError('GPU collector readiness')
                    time.sleep(.05)
                signal=json.loads(ready.read_text(encoding='utf-8-sig'));assert signal['engine_pid']==launch['app']
                initial=get('/api/particles/state');native('openspace.cosmos2BeginFrameCapture(12000);return {ready=true}')
                started=dt.datetime.now(dt.timezone.utc);began=time.perf_counter()
                row=dict(run=index,target=target,visible=visible,initial=initial,capture_start_utc=started.isoformat(),samples=[])
                report['pending_run']=row;persist();print(json.dumps(dict(stage='capture',run=index)),flush=True)
                for part in range(4):
                    remaining=began+20*part-time.perf_counter()
                    if remaining>0:time.sleep(remaining)
                    s=get('/api/particles/state');p=get('/api/state')['physics'];assert phase(p)==original
                    assert s['active'] and not s['error'] and not s['worker']['paused'] and not s['worker']['experiment']['termination']
                    assert s['view']['visible']==visible
                    node=s['view']['native_nodes']['trajectory']
                    flags=native('return {draw=openspace.propertyValue("Scene.'+node+'.Renderable.DrawElements"),enabled=openspace.propertyValue("Scene.'+node+'.Renderable.Enabled")}')
                    assert flags['draw']==visible and flags['enabled']
                    row['samples'].append(dict(offset_s=time.perf_counter()-began,particle=s,source=p,native_visibility=flags,ram=product_memory(launch),engine_gpu=native('return openspace.cosmos2MemoryMetrics()')))
                capture=native('return openspace.cosmos2EndFrameCapture()');ended=dt.datetime.now(dt.timezone.utc)
                row.update(capture=capture,capture_end_utc=ended.isoformat(),wall_interval_s=time.perf_counter()-began,final=get('/api/particles/state'));persist()
                output=gpu_job.communicate(timeout=20)[0];(folder/('gpu-'+str(index)+'.log')).write_text(output,encoding='utf-8')
                assert gpu_job.returncode==0,output
                gpu_job=None;gpu=json.loads(gpu_path.read_text(encoding='utf-8-sig'))
                stamps=[dt.datetime.fromisoformat(s['utc'].replace('Z','+00:00')) for s in gpu['samples']]
                assert len(stamps)==66 and stamps[0]<=started and stamps[-1]>=ended
                row.update(gpu_report=gpu_path.relative_to(ROOT).as_posix(),gpu_sha256=sha(gpu_path));report['runs'].append(row);report.pop('pending_run');persist()
                command('pause');command('leave');page.evaluate('document.body.inert=false')
            h.test.click(page,'#atlas')
        assert sha(ROOT/'user/sessions/latest.json')==report['owner_sha256'] and all(sha(ROOT/n)==v for n,v in hashes.items())
        report['completed']=True
    except Exception:report['failure']=traceback.format_exc()
    finally:
        if gpu_job:
            try:(folder/'interrupted-gpu.log').write_text(gpu_job.communicate(timeout=20)[0],encoding='utf-8')
            except subprocess.TimeoutExpired:gpu_job.terminate();gpu_job.communicate(timeout=5)
        try:
            if get('/api/particles/state')['active']:command('pause');command('leave')
            with Page() as page:page.evaluate('document.body.inert=false')
        except Exception:report['cleanup_failure']=traceback.format_exc()
        persist()
        if h._socket:h._socket.close()
    print(json.dumps(dict(completed=report['completed'],failure=report.get('failure'))),flush=True)
    return 0 if report['completed'] else 1

if __name__=='__main__':raise SystemExit(main())
