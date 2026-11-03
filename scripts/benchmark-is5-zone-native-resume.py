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
import zipfile
from native_product_memory import product_memory
from cef_page import Page

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is5-solar-zone-product0.10.3/app'
h = SourceFileLoader('is5_profile_helpers', str(ROOT / 'scripts/benchmark-body-points-native.py')).load_module()
get, post, native, sha = h.get, h.post, h.native, h.sha


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
    parser.add_argument('--acceptance-label', default='20261026a')
    parser.add_argument('--resume-label', required=True)
    args = parser.parse_args()
    for label in (args.label, args.acceptance_label, args.resume_label):
        if not label or len(label) > 20 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
            parser.error('Invalid label')
    folder = ROOT / ('output/is5-zone-profile-' + args.label)
    receipt = ROOT / ('evidence/is5-zone-profile-' + args.label + '.json')
    if folder.exists() or receipt.exists():
        raise FileExistsError('Preserve profile evidence')
    folder.mkdir()
    launch = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
    assert '0.10.3' in launch['serverScript'] and launch['runtimeVariant'] == 'is4-stream'
    preflight = [ROOT / ('evidence/is5-native-zone103-' + args.acceptance_label + '.json'),
                 ROOT / ('evidence/is5-zone103-visual-review-' + args.acceptance_label + '.json')]
    for p in preflight:
        assert json.loads(p.read_text())['accepted'], p
    previous_path=ROOT/('evidence/is5-zone-profile-'+args.resume_label+'.json')
    previous=json.loads(previous_path.read_text())
    assert not previous['completed'] and len(previous['runs'])==2
    assert 'subprocess.TimeoutExpired' in previous.get('failure','') and not previous.get('cleanup_failure')
    assert previous['session']['app']==launch['app'] and previous['session']['server']==launch['server']
    assert all(sha(ROOT/n)==v for n,v in previous['source_sha256'].items())
    files = [p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += preflight + [Path(__file__), ROOT/'IS-5-PERFIL-PREVIO.md', ROOT/'scripts/audit-is5-zone-profile-v2.py',
              ROOT/'scripts/benchmark-body-points-native.py', ROOT/'scripts/verify-native-solar-integration.py',
              ROOT/'scripts/engine-command.py', ROOT/'scripts/cef_page.py', ROOT/'scripts/native_product_memory.py',
              ROOT/'scripts/collect-gpu-memory-diagnostic.ps1', ROOT/'scripts/collect-gpu-memory.ps1',
              ROOT/'config/window-1080.json', ROOT/'config/cosmos2.cfg', ROOT/'evidence/built-runtime-is4-stream.json']
    files += [previous_path,ROOT/'scripts/benchmark-is5-zone-native.py',ROOT/'scripts/audit-is5-zone-profile.py']
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in files}
    archive = folder / 'executed-sources.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.relative_to(ROOT).as_posix())
    report = dict(schema=1, completed=False, accepted=False, session=launch, source_sha256=hashes,
                  archive_sha256=sha(archive), engine_sha256=sha(Path(launch['runtime'])/'bin/OpenSpace.exe'),
                  owner_sha256=sha(ROOT/'user/sessions/latest.json'), limits_before_execution=h.LIMITS,
                  warmup_s=30, window_s=60, requested_knots_per_s=2,
                  scope='Playback of calculated nuclear knots; not Radau integration throughput.', runs=[])
    report['runs']=copy.deepcopy(previous['runs'])
    report['resumed_from']=dict(path=previous_path.relative_to(ROOT).as_posix(),sha256=sha(previous_path),reused_runs=[1,2],reason='GPU collector deadline in third window; first two complete raw windows preserved.')
    def persist():
        receipt.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')
    persist()
    gpu_job = None
    try:
        with Page() as page:
            page.goto(h.test.BASE+'/')
            page.wait_for_function('appState!==null&&solarZoneState!==null&&!pending')
            if get('/api/solar-zone/state')['active']:
                command('leave')
            assert get('/api/state')['mode']=='experiment'
            source=get('/api/state')['physics']
            original=phase(source)
            assert original==phase(previous['runs'][0]['samples'][0]['source'])
            page.locator('#ui-scale').select_option('1')
            for index, (weak, visible) in enumerate([(w,v) for w in (True,False) for v in (True,False)], 1):
                if index<=2:
                    continue
                sg = {k:source[k] for k in ('system_id','edit_token','revision','time')} | {'frame':source['contract']['frame']}
                config = dict(parameters=dict(temperature_K=15e6, density_kg_m3=1.5e5, hydrogen_fraction=.34,
                            catalyst_fraction=.01, catalyst_seed='n14', duration_s=31557600000000., volume_m3=1.),
                            acting=dict(strong=True,weak=weak,electromagnetic=True),
                            channel_switches={k:True for k in ('pp','dp','he3he3','c12pg','n13beta','c13pg','n14pg','o15beta','n15pa')}, decay_basis='nubase2020')
                command('create', source_guard=sg, configuration=config)
                command('set_view', view=dict(selected_index=0,visible={k:visible for k in ('composition','energy','neutrinos','reference')}))
                command('set_rate', value=2)
                page.wait_for_function('solarZoneState?.active&&solarZoneCurveId===solarZoneState.worker.artifact_id', timeout=70000)
                page.evaluate('document.body.inert=true')
                command('play')
                print(json.dumps(dict(stage='warmup', run=index, weak=weak, charts=visible)), flush=True)
                time.sleep(30)
                label = 'is5-z-' + args.label + '-' + str(index)
                ready = ROOT / ('output/gpu-memory-ready-'+label+'.json')
                gpu_path = ROOT / ('evidence/gpu-memory-'+label+'.json')
                if ready.exists() or gpu_path.exists():
                    raise FileExistsError(label)
                gpu_job = subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                    str(ROOT/'scripts/collect-gpu-memory-diagnostic.ps1'),'-Label',label,'-Samples','66',
                    '-ExpectedMode','experiment','-ExpectedWorker','paused','-SignalReady'],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
                deadline = time.monotonic()+20
                while not ready.exists():
                    if gpu_job.poll() is not None:
                        raise RuntimeError(gpu_job.communicate()[0])
                    if time.monotonic()>deadline:
                        raise TimeoutError('GPU collector readiness')
                    time.sleep(.05)
                assert json.loads(ready.read_text(encoding='utf-8-sig'))['engine_pid']==launch['app']
                initial = get('/api/solar-zone/state')
                native('openspace.cosmos2BeginFrameCapture(12000);return {ready=true}')
                started = dt.datetime.now(dt.timezone.utc)
                began = time.perf_counter()
                row = dict(run=index, weak=weak, charts_visible=visible, initial=initial,
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
                    assert phase(p)==original and s['active'] and s['playing'] and not s['error']
                    n=s['scene']['node'];l=s['scene']['label_node']
                    flags=native('return {marker=openspace.propertyValue("Scene.'+n+'.Renderable.Enabled"),label=openspace.propertyValue("Scene.'+l+'.Renderable.Enabled"),text=openspace.propertyValue("Scene.'+l+'.Renderable.Text"),position=openspace.propertyValue("Scene.'+n+'.Translation.Position")}')
                    row['samples'].append(dict(offset_s=time.perf_counter()-began, zone=s, source=p,
                        native_source=flags, ram=product_memory(launch), engine_gpu=native('return openspace.cosmos2MemoryMetrics()')))
                capture=native('return openspace.cosmos2EndFrameCapture()')
                ended=dt.datetime.now(dt.timezone.utc)
                row.update(capture=capture, capture_end_utc=ended.isoformat(),wall_interval_s=time.perf_counter()-began,
                           final=get('/api/solar-zone/state'))
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
                command('pause');command('leave')
                page.evaluate('document.body.inert=false')
            post('/api/command',dict(command='atlas'))
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
            if get('/api/solar-zone/state')['active']:
                command('pause');command('leave')
            with Page() as page:
                page.evaluate('document.body.inert=false')
        except Exception:
            report['cleanup_failure']=traceback.format_exc()
        persist()
        if h._socket:
            h._socket.close()
    print(json.dumps(dict(completed=report['completed'],failure=report.get('failure'))),flush=True)
    return 0 if report['completed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
