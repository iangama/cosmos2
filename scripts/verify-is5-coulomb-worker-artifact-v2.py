"""Real worker, bounded calculations, responsive state/quit, seals and Windows locks."""
from pathlib import Path
import argparse
import copy
import ctypes
import hashlib
import json
import sys
import threading
import time
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/is5-coulomb-worker-v2-staging'
sys.path.insert(0,str(STAGE))
from is5_coulomb_client import Client
from is5_coulomb_artifact import Store,Run,DEFAULT_VIEW,generation,core
from is5_solar_source import digest
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def asynchronous(function):
    result={}
    def body():
        try:result['value']=function()
        except Exception as error:result['error']=error
    thread=threading.Thread(target=body);thread.start()
    return thread,result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/f'output/is5-coulomb-worker-artifact-{args.label}'
    path=ROOT/f'evidence/is5-coulomb-worker-artifact-{args.label}.json'
    if folder.exists() or path.exists():raise FileExistsError('Preserve worker evidence')
    folder.mkdir();storage=folder/'checkpoints'
    fixture=ROOT/'output/is4-body-snapshot-20261025b/IGRF14-13.json'
    phase=json.loads(fixture.read_text(encoding='utf-8'))['phase']
    science=ROOT/'evidence/is5-coulomb-science-20261028a.json'
    accepted=json.loads(science.read_text(encoding='utf-8'));assert accepted['accepted']
    hashes={**accepted['source_sha256'],science.relative_to(ROOT).as_posix():sha(science)}
    for file in [*STAGE.glob('*.py'),STAGE/'base-manifest.json',ROOT/'IS-5-COULOMB-WORKER-CONTRATO.md',
                 ROOT/'scripts/prepare-is5-coulomb-worker.py',ROOT/'scripts/prepare-is5-coulomb-worker-v2.py',Path(__file__),fixture]:
        hashes[file.relative_to(ROOT).as_posix()]=sha(file)
    assert all(sha(ROOT/n)==h for n,h in hashes.items())
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=hashes,generation=generation(),groups=[],refusals=0,
           limits_before_execution=dict(state_during_calculation_s=2.,deadline_error_s=5.,quit_s=8.,orphan_exit_s=5.))
    client=secondary=None
    def persist():path.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def passed(name,**data):
        r['groups'].append(dict(name=name,**data));persist();print(json.dumps(dict(group=name,passed=True,**data)),flush=True)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32];kernel.OpenProcess.restype=ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint32];kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    def alive(pid):
        handle=kernel.OpenProcess(0x00100000,False,pid)
        if not handle:return False
        try:return kernel.WaitForSingleObject(handle,0)==258
        finally:kernel.CloseHandle(handle)
    def wait_dead(pid):
        until=time.monotonic()+5
        while alive(pid) and time.monotonic()<until:time.sleep(.05)
        assert not alive(pid),'Calculation child remained alive'
    def busy(c):
        until=time.monotonic()+5
        while time.monotonic()<until:
            began=time.perf_counter();state=c.call('state')['state'];elapsed=time.perf_counter()-began
            assert elapsed<=2.,elapsed
            if state['busy']:return state,elapsed
            time.sleep(.025)
        raise AssertionError('Calculation never reported busy')
    def preserved(before,after):
        for key in ['artifact_id','artifact_sha256','edit_token','revision','sample','view','configuration','source']:
            assert before[key]==after[key],key
    persist()
    try:
        config=dict(parameters=copy.deepcopy(core.base.DEFAULT_PARAMETERS),
                    acting={k:True for k in ['strong','weak','electromagnetic']},
                    channel_switches={k:True for k in core.CHANNELS},mode='isochoric',include_coulomb=True,include_screening=True)
        config['parameters']['catalyst_seed']='o16'
        original_phase=copy.deepcopy(phase);client=Client(storage)
        old_guard=Client.guard(client.snapshot())
        began=time.perf_counter();thread,result=asynchronous(lambda:client.call('create',dict(source_phase=phase,configuration=config)))
        state,response_s=busy(client);child=state['calculation']['process_id']
        assert alive(child)
        try:client.call('sample',{'index':1})
        except ValueError:r['refusals']+=1
        else:raise AssertionError('Mutation during calculation accepted')
        thread.join(290);assert not thread.is_alive() and 'error' not in result,result
        wait_dead(child)
        first=client.call('get_result')['result']
        assert first['actual']==first['reference'] and phase==original_phase
        assert first['configuration']==config
        assert len(first['actual']['species'])==16 and len(first['actual']['channels'])==18
        client.call('sample',{'index':240});probe=client.snapshot()['sample']['actual']
        assert len(probe['screening_factors'])==18 and probe['screening_factors']['pp']>1
        assert probe['screening_factors']['be7ec']==probe['screening_factors']['f17beta']==1.
        assert probe['Coulomb_internal_energy_J_m3']<0 and probe['temperature_K']==first['actual']['temperature_K'][-1]
        passed('responsive_creation_and_full_probes',state_response_s=response_s,create_wall_s=time.perf_counter()-began)
        for guard in [old_guard,{**Client.guard(client.snapshot()),'revision':True}]:
            prior=client.snapshot()
            try:client.call('sample',{'index':1},guard=guard)
            except ValueError:r['refusals']+=1
            else:raise AssertionError('Stale/bool guard accepted')
            preserved(prior,client.snapshot())
        preferences=copy.deepcopy(DEFAULT_VIEW);preferences['selected_index']=120;preferences['visible']['composition']=False
        client.call('set_view',{'view':preferences});client.call('save')
        saved=(storage/'saved.json').read_bytes();artifact=client.snapshot()['artifact_id'];worker_id=client.snapshot()['worker_id']
        a=client.call('branch_create',dict(name='Coulomb A',parent=None))['result']['branch']['id']
        before=client.snapshot();began=time.perf_counter()
        task,res=asynchronous(lambda:client.call('configure',dict(configuration=config,budget_s=.25)))
        state,_=busy(client);child=state['calculation']['process_id']
        task.join(6);assert not task.is_alive() and isinstance(res.get('error'),ValueError)
        assert 'budget exceeded' in str(res['error'])
        elapsed=time.perf_counter()-began;assert elapsed<=5.,elapsed
        wait_dead(child);preserved(before,client.call('state')['state'])
        time.sleep(.2);preserved(before,client.call('state')['state'])
        assert not list((storage/'_work').iterdir())
        passed('deadline_preserves_artifact_without_late_publication',deadline_error_s=elapsed)
        fixed=copy.deepcopy(config);fixed['mode']='prescribed';client.call('configure',{'configuration':fixed})
        assert client.snapshot()['sample']['actual']['internal_energy_J_m3'] is not None
        assert client.snapshot()['configuration']['mode']=='prescribed'
        client.call('load');assert client.call('get_result')['result']==first and client.snapshot()['view']==preferences
        ideal=copy.deepcopy(config);ideal['include_screening']=False;ideal['include_coulomb']=False
        client.call('configure',{'configuration':ideal});assert client.snapshot()['sample']['actual']['Coulomb_internal_energy_J_m3']==0
        assert set(client.snapshot()['sample']['actual']['screening_factors'].values())=={1.}
        reservoir=copy.deepcopy(config);reservoir['include_screening']=False
        client.call('configure',{'configuration':reservoir});assert client.snapshot()['sample']['actual']['Coulomb_internal_energy_J_m3']<0
        assert set(client.snapshot()['sample']['actual']['screening_factors'].values())=={1.}
        client.call('load');assert client.call('get_result')['result']==first
        passed('prescribed_and_two_independent_controls_recompute_and_restore')
        raw=json.loads(saved);prior=client.snapshot()
        for change in ['seal','source_epoch','parameters','energy','generation','old_schema','old_run','view_bool','duplicate']:
            bad=copy.deepcopy(raw)
            if change=='seal':bad['record_sha256']='0'*64
            elif change=='source_epoch':bad['run']['source']['epoch']['et_tdb_s']+=1
            elif change=='parameters':bad['run']['configuration']['parameters']['temperature_K']=True
            elif change=='energy':bad['run']['actual']['energy_available_J_m3'][-1]*=2
            elif change=='generation':bad['run']['scientific_generation']['schema']=99
            elif change=='old_schema':bad['kind']='is5_cno2_solar_checkpoint'
            elif change=='old_run':bad['run']['kind']='is5_cno2_calculated_solar_scenario'
            elif change=='view_bool':bad['view']['selected_index']=True
            if change!='seal':bad['record_sha256']=digest({k:v for k,v in bad.items() if k!='record_sha256'})
            text=json.dumps(bad)
            if change=='duplicate':text=text.replace('"schema": 1','"schema": 1,"schema": 1',1)
            (storage/'saved.json').write_text(text,encoding='utf-8')
            try:client.call('load')
            except ValueError:r['refusals']+=1
            else:raise AssertionError('Corrupt checkpoint accepted: '+change)
            preserved(prior,client.snapshot());(storage/'saved.json').write_bytes(saved)
        for modify in ['null_forces','screening_without_Coulomb','old_config']:
            invalid=copy.deepcopy(config)
            if modify=='null_forces':invalid['acting']=None
            elif modify=='screening_without_Coulomb':invalid['include_coulomb']=False
            else:invalid['decay_basis']='nubase2020'
            try:client.call('configure',{'configuration':invalid})
            except ValueError:r['refusals']+=1
            else:raise AssertionError('Malformed configuration accepted')
            preserved(prior,client.snapshot())
        passed('corrupt_old_type_and_configuration_refusals_preserve_state')
        altered=copy.deepcopy(config);altered['acting']['weak']=False
        client.call('configure',{'configuration':altered})
        assert client.snapshot()['artifact_id']!=artifact and client.snapshot()['source']==first['source']
        b=client.call('branch_create',dict(name='Coulomb B',parent=a))['result']['branch']['id']
        client.call('branch_load',{'branch_id':a})
        assert client.snapshot()['artifact_id']==artifact and client.snapshot()['view']==preferences
        exported=client.call('export')['result'];payload=json.loads(Path(exported['path']).read_text(encoding='utf-8'))
        assert payload['run']==first and payload['record_sha256']==exported['record_sha256']==digest({k:v for k,v in payload.items() if k!='record_sha256'})
        client.close();client=None
        client=Client(storage);client.call('load')
        assert client.snapshot()['worker_id']!=worker_id and client.call('get_result')['result']==first
        assert client.snapshot()['view']==preferences
        passed('branches_export_and_exact_new_process_restore')
        # Graceful quit must cancel the child and unblock the outstanding caller.
        task,res=asynchronous(lambda:client.call('restart'));state,_=busy(client);child=state['calculation']['process_id']
        began=time.perf_counter();client.close();client=None;elapsed=time.perf_counter()-began
        task.join(3);assert not task.is_alive() and 'error' in res
        wait_dead(child);assert elapsed<=8.
        passed('quit_during_calculation_cancels_child',quit_s=elapsed)
        # Killing only this test's protocol owner must not orphan its calculation.
        secondary=Client(folder/'abrupt-owner-check')
        task,res=asynchronous(lambda:secondary.call('create',dict(source_phase=phase,configuration=config)))
        state,_=busy(secondary);child=state['calculation']['process_id']
        secondary.process.terminate();secondary.process.wait(5)
        task.join(5);assert not task.is_alive() and 'error' in res
        wait_dead(child);secondary.close();secondary=None
        passed('child_exits_after_abrupt_owner_death')
        store=Store(storage);run=Run.restore(first)
        kernel.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p]
        kernel.CreateFileW.restype=ctypes.c_void_p
        def lock():
            handle=kernel.CreateFileW(str(store.path),0x80000000,3,None,3,128,None)
            if handle==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
            return handle
        handle=lock();timer=threading.Timer(.1,lambda:kernel.CloseHandle(handle));timer.start();store.save(run,preferences);timer.join()
        previous=store.path.read_bytes();handle=lock()
        try:
            try:store.save(run,DEFAULT_VIEW)
            except PermissionError:r['refusals']+=1
            else:raise AssertionError('Permanent Windows lock bypassed')
            assert store.path.read_bytes()==previous and not list(storage.glob('*.tmp'))
        finally:kernel.CloseHandle(handle)
        for i in range(30):store.save(run,preferences,name='Ramo '+str(i),parent=a)
        try:store.save(run,preferences,name='Excesso')
        except ValueError:r['refusals']+=1
        else:raise AssertionError('Branch cap exceeded')
        assert len(store.catalog())==32 and all(v['valid'] for v in store.catalog())
        began=time.perf_counter();client=Client(storage);startup=time.perf_counter()-began
        assert len(client.snapshot()['branches'])==32
        client.call('load');assert client.call('get_result')['result']==first
        client.close();client=None
        passed('Windows_locks_atomicity_and32branches',startup_with32branches_s=startup)
        assert phase==original_phase and all(sha(ROOT/n)==h for n,h in hashes.items())
        r.update(accepted=True,completed=True,artifact_sha256=digest(first),saved_bytes=len(saved))
    except Exception:r['failure']=traceback.format_exc()
    finally:
        if client:client.close()
        if secondary:secondary.close()
        persist()
    print(json.dumps(dict(accepted=r['accepted'],groups=len(r['groups']),refusals=r['refusals'],failure=r.get('failure'))),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
