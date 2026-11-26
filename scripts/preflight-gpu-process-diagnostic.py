"""Exercise the unchanged GPU predicates and preserve a real late-child failure."""
from pathlib import Path
import hashlib
import json
import subprocess
import time
import traceback
import zipfile
from importlib.machinery import SourceFileLoader
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
h=SourceFileLoader('gpu_process_preflight_helpers',str(ROOT/'scripts/verify-native-solar-tide.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    folder=ROOT/'output/is3-gpu-process-preflight-20261024a'
    receipt=ROOT/'evidence/is3-gpu-process-preflight-20261024a.json'
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve GPU preflight evidence.')
    launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert launch.get('bodyViewTopologyCandidate')
    original=ROOT/'scripts/collect-gpu-memory.ps1';diagnostic=ROOT/'scripts/collect-gpu-memory-diagnostic.ps1'
    marker='$before=Read-Scenario'
    body=marker+original.read_text(encoding='utf-8').split(marker,1)[1]
    wrapped=diagnostic.read_text(encoding='utf-8').split('try {\n',1)[1].split('\n} catch {',1)[0]
    assert body==wrapped
    paths=[original,diagnostic,Path(__file__).resolve(),ROOT/'scripts/cef_page.py']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths};owner=sha(ROOT/'user/sessions/latest.json')
    folder.mkdir()
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for p in paths:archive.write(p,p.relative_to(ROOT).as_posix())
    report={'schema':1,'accepted':False,'completed':False,'source_sha256':hashes,'original_predicates_body_verbatim':True,'checks':{}}
    job=None
    def collector(label,samples):
        assert not (ROOT/('evidence/gpu-memory-'+label+'.json')).exists()
        assert not (ROOT/('evidence/gpu-memory-diagnostic-failure-'+label+'.json')).exists()
        return subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(diagnostic),
            '-Label',label,'-Samples',str(samples),'-ExpectedMode','experiment','-ExpectedWorker','paused','-SignalReady'],
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
    try:
        with Page() as page:
            page.goto('http://127.0.0.1:4700/');page.wait_for_function('appState?.mode==="atlas"&&!pending')
            h.click(page,'#experiment')
            h.post('/api/command',{'command':'reset','count':32});h.post('/api/command',{'command':'rate','value':1.})
            first=h.get('/api/state')['physics'];assert first['fixture_count']==32 and first['paused'] and first['revision']==0
            good_label='viewgpudiag20261024a-ok';job=collector(good_label,3)
            output=job.communicate(timeout=25)[0];(folder/'valid-collector.log').write_text(output,encoding='utf-8')
            assert job.returncode==0,output;job=None
            good_path=ROOT/('evidence/gpu-memory-'+good_label+'.json');good=json.loads(good_path.read_text(encoding='utf-8-sig'))
            assert len(good['samples'])==3 and not good['counter_errors']
            assert all(not s['invalid_samples'] for s in good['samples'])
            assert good['collector_sha256']==sha(diagnostic)
            report['checks']['valid_three_WDDM_samples']={'path':good_path.relative_to(ROOT).as_posix(),'sha256':sha(good_path)}
            bad_label='viewgpudiag20261024a-child';job=collector(bad_label,5)
            ready=ROOT/('output/gpu-memory-ready-'+bad_label+'.json');deadline=time.monotonic()+20
            while not ready.exists():
                if job.poll() is not None:raise RuntimeError(job.communicate()[0])
                if time.monotonic()>deadline:raise TimeoutError('Collector readiness missing.')
                time.sleep(.05)
            # Disposable32-body fixture, paused atzero, never saved. Terminate
            # only this candidate's worker processes, then use the normal enter
            # command to create a replacement under the same owning server.
            script='''$ErrorActionPreference='Stop';
$workers=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'is3-body-view-topology-product.*worker.py' });
if($workers.Count -lt 1){throw 'No owned disposable worker found.'};
$workers | Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Depth 3;
foreach($w in $workers){Stop-Process -Id $w.ProcessId -ErrorAction SilentlyContinue};
'''
            stopped=subprocess.run(['powershell.exe','-NoProfile','-Command',script],check=True,capture_output=True,text=True,encoding='utf-8',errors='replace')
            (folder/'replaced-disposable-worker.json').write_text(stopped.stdout,encoding='utf-8')
            h.post('/api/command',{'command':'enter'})
            after=h.get('/api/state')['physics'];assert after['fixture_count']==32 and after['paused'] and after['revision']==0 and after['time']==0
            assert after['system_id']!=first['system_id']
            output=job.communicate(timeout=25)[0];code=job.returncode;job=None
            (folder/'late-child-collector.log').write_text(output,encoding='utf-8');assert code!=0
            failure_path=ROOT/('evidence/gpu-memory-diagnostic-failure-'+bad_label+'.json')
            failure=json.loads(failure_path.read_text(encoding='utf-8-sig'))
            assert failure['accepted'] is False and failure['completed'] is False
            assert 'Novo processo filho durante a coleta' in failure['failed_predicate_message']
            assert len(failure['samples'])==5 and failure['new_direct_children_at_failure']
            assert failure['initial_inventory'] and failure['end_inventory_at_guard'] and failure['inventory_at_failure']
            assert not failure['counter_errors'] and all(not s['invalid_samples'] for s in failure['samples'])
            assert failure['original_collector_sha256']==sha(original) and failure['diagnostic_collector_sha256']==sha(diagnostic)
            assert not (ROOT/('evidence/gpu-memory-'+bad_label+'.json')).exists()
            report['checks']['real_late_child_refusal_preserves_five_samples_and_inventories']={
                'path':failure_path.relative_to(ROOT).as_posix(),'sha256':sha(failure_path),
                'new_children':failure['new_direct_children_at_failure']}
            h.click(page,'#atlas')
        assert all(sha(ROOT/name)==value for name,value in hashes.items()) and sha(ROOT/'user/sessions/latest.json')==owner
        report.update(accepted=True,completed=True,scope='Three real WDDM samples and exact original late-child guard exercised on a disposable paused32-body fixture; preserves failure-time evidence. No formal performance or retrospective attribution of0.6A.')
    except Exception:report['failure']=traceback.format_exc()
    finally:
        if job is not None:
            try:job.communicate(timeout=20)
            except subprocess.TimeoutExpired:job.terminate();job.communicate(timeout=5)
        receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'accepted':report['accepted'],'checks':list(report['checks']),'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
