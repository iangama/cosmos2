"""Four native solar-instrument playback windows, with raw frame/process/GPU evidence."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import argparse
import copy
import datetime as dt
import json
import subprocess
import time
import traceback
import sys
import zipfile
import urllib.request
import urllib.error
from native_product_memory import product_memory
from cef_page import Page

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is5-reference-product0.16.0/app'
h = SourceFileLoader('is5_profile_helpers', str(ROOT / 'scripts/benchmark-body-points-native.py')).load_module()
get, native, sha = h.get, h.native, h.sha


def post(route, payload):
    request=urllib.request.Request(h.test.BASE+route, data=json.dumps(payload).encode(),
        headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=390) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'HTTP{error.code} {route}: {error.read().decode("utf-8")}') from error


def command(action, **extra):
    request = dict(command=action, **extra)
    if action not in ('create', 'load_saved'):
        w = get('/api/solar-zone/state')['worker']
        request['guard'] = {k: w[k] for k in ('worker_id', 'artifact_id', 'edit_token', 'revision')}
    return post('/api/solar-zone/command', request)


def phase(p):
    return {k: copy.deepcopy(p[k]) for k in ('system_id','edit_token','revision','time','bodies','interventions','atlas_initial')}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    parser.add_argument('--acceptance-label', default='20261029b')
    args = parser.parse_args()
    for label in (args.label, args.acceptance_label):
        if not label or len(label) > 20 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
            parser.error('Invalid label')
    folder = ROOT / ('output/is5-reference-profile-' + args.label)
    receipt = ROOT / ('evidence/is5-reference-profile-' + args.label + '.json')
    if folder.exists() or receipt.exists():
        raise FileExistsError('Preserve profile evidence')
    folder.mkdir()
    launch = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
    assert Path(launch['serverScript']).resolve()==(APP/'server.py').resolve()
    assert launch.get('is5ReferenceCandidate') is True and launch['runtimeVariant']=='is4-stream'
    preflight = [ROOT / ('evidence/is5-native-reference-' + args.acceptance_label + '.json'),
                 ROOT / ('evidence/is5-reference-visual-review-' + args.acceptance_label + '.json')]
    accepted_sources={}
    for p in preflight:
        evidence=json.loads(p.read_text(encoding='utf-8'))
        assert evidence['accepted'],p
        for name,value in evidence['source_sha256'].items():
            assert sha(ROOT/name)==value,(p,name)
            assert name not in accepted_sources or accepted_sources[name]==value,name
            accepted_sources[name]=value
    files=[ROOT/name for name in accepted_sources]
    files += [p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += preflight + [Path(__file__), ROOT/'IS-5-REFERENCIAS-SOLARES-PERFIL-PREVIO.md', ROOT/'scripts/audit-is5-reference-profile.py',
              ROOT/'scripts/benchmark-body-points-native.py', ROOT/'scripts/verify-native-solar-integration.py',
              ROOT/'scripts/engine-command.py', ROOT/'scripts/cef_page.py', ROOT/'scripts/native_product_memory.py',
              ROOT/'scripts/collect-gpu-memory-diagnostic.ps1', ROOT/'scripts/collect-gpu-memory.ps1',
              ROOT/'config/window-1080.json', ROOT/'config/cosmos2.cfg', ROOT/'evidence/built-runtime-is4-stream.json']
    files=list(dict.fromkeys(files))
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in files}
    archive = folder / 'executed-sources.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.relative_to(ROOT).as_posix())
    report = dict(schema=1, completed=False, accepted=False, session=launch, source_sha256=hashes,
                  archive_sha256=sha(archive), engine_sha256=sha(Path(launch['runtime'])/'bin/OpenSpace.exe'),
                  owner_sha256=sha(ROOT/'user/sessions/latest.json'), limits_before_execution=h.LIMITS,
                  warmup_s=30, window_s=60, requested_radial_queries_per_s=2,
                  scope='Read-only B23 radial queries/UI with absent or paused Coulomb zone; no ODE throughput or solar evolution.', runs=[])
    def persist():
        receipt.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')
    persist()
    gpu_job = None
    try:
        with Page() as page:
            report['page_errors']=[]
            page.on('pageerror',lambda error:report['page_errors'].append(error))
            page.goto(h.test.BASE+'/')
            page.wait_for_function('appState!==null&&solarZoneState!==null&&!pending')
            if get('/api/solar-zone/state')['active']:
                command('leave')
            if get('/api/state')['mode'] == 'experiment':
                post('/api/command', dict(command='atlas'))
                page.wait_for_function('appState?.mode==="atlas"')
            h.test.click(page, '#copy-solar')
            page.wait_for_function('appState?.physics?.bodies.length===4&&!pending', timeout=70000)
            source = get('/api/state')['physics']
            original = phase(source)
            page.locator('#ui-scale').select_option('1')
            h.test.click(page,'#open-stellar-reference')
            page.wait_for_function('stellarReferenceState.sample?.model==="GS98"')
            page.locator('#stellar-reference-close').click()
            def reference():
                return page.evaluate('(()=>{const s=stellarReferenceState;return {open:!document.getElementById("stellar-reference-panel").hidden,scale:document.getElementById("ui-scale").value,index:s.index,sample:s.sample,requested:s.requestedSamples,completed:s.completedSamples,applied:s.appliedSamples,errors:s.sampleErrors}})()')
            for index, (zone_active, visible) in enumerate([(z,v) for z in (False,True) for v in (True,False)], 1):
                if zone_active:
                    sg={k:source[k] for k in ('system_id','edit_token','revision','time')}|{'frame':source['contract']['frame']}
                    command('create',source_guard=sg,configuration=page.evaluate('zoneConfiguration()'))
                    page.wait_for_function('solarZoneState?.active&&!solarZoneCurvePending&&!solarZonePending&&solarZoneCurveId===solarZoneState.worker.artifact_id',timeout=380000)
                else:
                    assert not get('/api/solar-zone/state')['active']
                if visible:
                    h.test.click(page,'#open-stellar-reference')
                    page.wait_for_function('!document.getElementById("stellar-reference-panel").hidden')
                    page.wait_for_function('stellarReferenceState.sample?.model==="GS98"')
                else:page.evaluate('document.getElementById("stellar-reference-panel").hidden=true')
                page.evaluate('document.getElementById("stellar-reference-panel").scrollTop=0')
                assert page.evaluate('document.getElementById("ui-scale").value')=='1'
                page.evaluate('document.body.inert=true')
                if visible:
                    page.evaluate('window.referenceProfileTimer=setInterval(()=>{const e=document.getElementById("stellar-reference-index");e.value=(Number(e.value)+17)%2001;e.dispatchEvent(new Event("input"));},500)')
                print(json.dumps(dict(stage='warmup',run=index,zone_active=zone_active,reference_open=visible)),flush=True)
                time.sleep(30)
                label = 'is5-reference-' + args.label + '-' + str(index)
                ready = ROOT / ('output/gpu-memory-ready-'+label+'.json')
                gpu_path = ROOT / ('evidence/gpu-memory-'+label+'.json')
                if ready.exists() or gpu_path.exists():
                    raise FileExistsError(label)
                gpu_job = subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                    str(ROOT/'scripts/collect-gpu-memory-diagnostic.ps1'),'-Label',label,'-Samples','66',
                    '-ExpectedMode','experiment','-ExpectedWorker','paused','-SignalReady'],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
                deadline = time.monotonic()+20
                while True:
                    if gpu_job.poll() is not None:
                        raise RuntimeError(gpu_job.communicate()[0])
                    if time.monotonic()>deadline:
                        raise TimeoutError('GPU collector readiness')
                    if ready.exists():
                        try:
                            signal=json.loads(ready.read_text(encoding='utf-8-sig'))
                        except (PermissionError,json.JSONDecodeError):
                            time.sleep(.05)
                            continue
                        assert signal['engine_pid']==launch['app']
                        break
                    time.sleep(.05)
                initial = dict(zone=get('/api/solar-zone/state'),reference=reference())
                native('openspace.cosmos2BeginFrameCapture(12000);return {ready=true}')
                started = dt.datetime.now(dt.timezone.utc)
                began = time.perf_counter()
                row = dict(run=index,zone_active=zone_active,reference_open=visible,initial=initial,
                           capture_start_utc=started.isoformat(), samples=[])
                report['pending_run']=row
                persist()
                print(json.dumps(dict(stage='capture',run=index)),flush=True)
                for part in range(4):
                    remaining=began+20*part-time.perf_counter()
                    if remaining>0:
                        time.sleep(remaining)
                    s=get('/api/solar-zone/state')
                    p=get('/api/state')['physics']
                    assert phase(p)==original and s['active']==zone_active and not s['playing'] and not s['busy'] and not s['error']
                    row['samples'].append(dict(offset_s=time.perf_counter()-began,zone=s,source=p,reference=reference(),
                        ram=product_memory(launch),engine_gpu=native('return openspace.cosmos2MemoryMetrics()')))
                capture=native('return openspace.cosmos2EndFrameCapture()')
                ended=dt.datetime.now(dt.timezone.utc)
                row.update(capture=capture, capture_end_utc=ended.isoformat(),wall_interval_s=time.perf_counter()-began,
                           final=dict(zone=get('/api/solar-zone/state'),reference=reference()))
                persist()
                output=gpu_job.communicate(timeout=60)[0]
                (folder/('gpu-'+str(index)+'.log')).write_text(output,encoding='utf-8')
                assert gpu_job.returncode==0,output
                gpu_job=None
                gpu=json.loads(gpu_path.read_text(encoding='utf-8-sig'))
                stamps=[dt.datetime.fromisoformat(s['utc'].replace('Z','+00:00')) for s in gpu['samples']]
                assert len(stamps)==66 and stamps[0]<=started and stamps[-1]>=ended
                row.update(gpu_report=gpu_path.relative_to(ROOT).as_posix(),gpu_sha256=sha(gpu_path))
                report['runs'].append(row)
                report.pop('pending_run')
                persist()
                page.evaluate('clearInterval(window.referenceProfileTimer)')
                if zone_active:command('leave')
                page.evaluate('document.getElementById("stellar-reference-panel").hidden=true')
                page.evaluate('document.body.inert=false')
            post('/api/command',dict(command='atlas'))
        assert not report['page_errors'],report['page_errors']
        assert sha(ROOT/'user/sessions/latest.json')==report['owner_sha256']
        assert all(sha(ROOT/n)==v for n,v in hashes.items())
        report['completed']=True
    except Exception:
        report['failure']=traceback.format_exc()
    finally:
        if gpu_job:
            try:
                (folder/'interrupted-gpu.log').write_text(gpu_job.communicate(timeout=60)[0],encoding='utf-8')
            except subprocess.TimeoutExpired:
                gpu_job.terminate();gpu_job.communicate(timeout=5)
        try:
            with Page() as page:
                page.evaluate('clearInterval(window.referenceProfileTimer);document.body.inert=false;document.getElementById("stellar-reference-panel").hidden=true')
            if get('/api/solar-zone/state')['active']:
                command('pause');command('leave')
            if get('/api/state')['mode']=='experiment':post('/api/command',dict(command='atlas'))
            native('openspace.toggleShutdown();return {closing=true}')
        except Exception:
            report['cleanup_failure']=traceback.format_exc()
        persist()
        if h._socket:
            h._socket.close()
    print(json.dumps(dict(completed=report['completed'],failure=report.get('failure'))),flush=True)
    return 0 if report['completed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
