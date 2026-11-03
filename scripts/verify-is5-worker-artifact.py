"""Real subprocess, recomputed reload, view branches, guards and Windows atomic locks."""
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

ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/is5-solar-core-staging';APP=ROOT/'output/is4-solar-wind-product0.9.1/app'
sys.path[:0]=[str(STAGE),str(APP)]
from is5_client import Client
from is5_artifact import Store,Run,DEFAULT_VIEW
from is5_core import DEFAULT_PARAMETERS,CHANNELS
from is5_solar_source import digest
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/('output/is5-worker-artifact-'+args.label);path=ROOT/('evidence/is5-worker-artifact-'+args.label+'.json')
    if folder.exists() or path.exists():raise FileExistsError('Preserve artifact evidence')
    folder.mkdir();storage=folder/'checkpoints';fixture=ROOT/'output/is4-body-snapshot-20261025b/IGRF14-13.json';phase=json.loads(fixture.read_text())['phase']
    files=[*STAGE.glob('*.py'),STAGE/'reference-manifest.json',Path(__file__),fixture,ROOT/'IS-5-ARTEFATO-WORKER-CONTRATO.md'];hashes={f.relative_to(ROOT).as_posix():sha(f) for f in files}
    with zipfile.ZipFile(folder/'executed-sources-and-fixture.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(schema=1,accepted=False,completed=False,source_sha256=hashes,checks=[],refusals=0);client=None
    def persist():path.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    persist()
    try:
        config=dict(parameters=copy.deepcopy(DEFAULT_PARAMETERS),acting={k:True for k in ['strong','weak','electromagnetic']},channel_switches={k:True for k in CHANNELS},decay_basis='nubase2020')
        before=copy.deepcopy(phase);client=Client(storage);worker=client.snapshot()['worker_id'];client.call('create',dict(source_phase=phase,configuration=config))
        first=client.call('get_result')['result'];assert first['actual']==first['reference'] and phase==before
        artifact=client.snapshot()['artifact_id'];token=client.snapshot()['edit_token'];oldguard=Client.guard(client.snapshot())
        preferences=copy.deepcopy(DEFAULT_VIEW);preferences['selected_index']=120;preferences['visible']['composition']=False
        client.call('set_view',{'view':preferences});assert client.snapshot()['artifact_id']==artifact and client.snapshot()['artifact_sha256']==digest(first)
        client.call('save');saved=(storage/'saved.json').read_bytes()
        a=client.call('branch_create',dict(name='Cenário A',parent=None))['result']['branch']['id']
        altered=copy.deepcopy(config);altered['acting']['weak']=False;client.call('configure',{'configuration':altered})
        assert client.snapshot()['artifact_id']!=artifact and not client.snapshot()['configuration']['acting']['weak']
        assert client.snapshot()['configuration']['parameters']==config['parameters'] and client.snapshot()['source']==first['source']
        for guard in [oldguard,{**Client.guard(client.snapshot()),'revision':True}]:
            prior=client.snapshot()['artifact_id']
            try:client.call('sample',{'index':1},guard=guard)
            except ValueError:r['refusals']+=1
            else:raise AssertionError('Stale/type guard accepted')
            assert client.snapshot()['artifact_id']==prior
        b=client.call('branch_create',dict(name='Cenário B',parent=a))['result']['branch']['id']
        client.call('branch_load',{'branch_id':a});assert client.snapshot()['artifact_id']==artifact and client.snapshot()['view']==preferences
        client.call('load');assert client.snapshot()['edit_token']!=token and client.call('get_result')['result']==first
        client.call('sample',{'index':240});assert client.snapshot()['sample']['actual']['time_s']==config['parameters']['duration_s']
        export=client.call('export')['result'];data=json.loads(Path(export['path']).read_text());assert data['run']==first and data['record_sha256']==export['record_sha256']==digest({k:v for k,v in data.items() if k!='record_sha256'})
        client.close();client=None
        client=Client(storage);client.call('load');assert client.snapshot()['worker_id']!=worker and client.snapshot()['view']==preferences and client.call('get_result')['result']==first
        prior=copy.deepcopy(client.snapshot());raw=json.loads(saved)
        for change in ['seal','source_epoch','parameters','energy','generation','old_schema','view_bool','duplicate']:
            bad=copy.deepcopy(raw)
            if change=='seal':bad['record_sha256']='0'*64
            elif change=='source_epoch':bad['run']['source']['epoch']['et_tdb_s']+=1
            elif change=='parameters':bad['run']['configuration']['parameters']['temperature_K']=True
            elif change=='energy':bad['run']['actual']['energy_available_J_m3'][-1]*=2
            elif change=='generation':bad['run']['scientific_generation']['schema']=99
            elif change=='old_schema':bad['kind']='is4_product_checkpoint'
            elif change=='view_bool':bad['view']['selected_index']=True
            if change!='seal':bad['record_sha256']=digest({k:v for k,v in bad.items() if k!='record_sha256'})
            text=json.dumps(bad)
            if change=='duplicate':text=text.replace('"schema": 1','"schema": 1,"schema": 1',1)
            (storage/'saved.json').write_text(text)
            try:client.call('load')
            except ValueError:r['refusals']+=1
            else:raise AssertionError(change)
            assert client.snapshot()['artifact_id']==prior['artifact_id'] and client.snapshot()['edit_token']==prior['edit_token'] and client.snapshot()['view']==prior['view']
            (storage/'saved.json').write_bytes(saved)
        client.call('restart');assert client.snapshot()['artifact_id']!=artifact and client.snapshot()['view']['selected_index']==0 and client.snapshot()['source']==first['source']
        client.close();client=None
        store=Store(storage);run=Run.restore(first)
        kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p];kernel.CreateFileW.restype=ctypes.c_void_p;kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        def lock():
            handle=kernel.CreateFileW(str(store.path),0x80000000,3,None,3,128,None)
            if handle==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
            return handle
        handle=lock();timer=threading.Timer(.1,lambda:kernel.CloseHandle(handle));timer.start();store.save(run,preferences);timer.join()
        original=store.path.read_bytes();handle=lock()
        try:
            try:store.save(run,DEFAULT_VIEW)
            except PermissionError:r['refusals']+=1
            else:raise AssertionError('Permanently locked file replaced')
            assert store.path.read_bytes()==original and not list(storage.glob('*.tmp'))
        finally:kernel.CloseHandle(handle)
        for i in range(30):store.save(run,preferences,name='Ramo '+str(i),parent=a)
        try:store.save(run,preferences,name='Excesso')
        except ValueError:r['refusals']+=1
        else:raise AssertionError('Branch cap exceeded')
        assert len(store.catalog())==32 and all(b['valid'] for b in store.catalog())
        began=time.perf_counter();client=Client(storage);r['startup_with32sealed_branches_wall_s']=time.perf_counter()-began
        assert len(client.snapshot()['branches'])==32;client.call('load');assert client.call('get_result')['result']==first;client.close();client=None
        assert phase==before and all(sha(ROOT/n)==v for n,v in hashes.items())
        r.update(accepted=True,completed=True,artifact_sha256=digest(first),saved_bytes=len(saved),checks=['Actual subprocess with bounded summary and explicit full result','Configuration recomputation, source preserved, restart','Sealed source+configuration+curves+view, exact recomputation and new process restore','Immutable branches with explicit parent and32budget','Stale/corrupt/type/old-schema refusals preserve last accepted artifact','Real Windows transient lock recovers; permanent lock preserves entire checkpoint'])
    except Exception:r['failure']=traceback.format_exc()
    finally:
        if client:client.close()
        persist()
    print(json.dumps(dict(accepted=r['accepted'],refusals=r['refusals'],failure=r.get('failure'))),flush=True);return 0 if r['accepted'] else 1

if __name__=='__main__':raise SystemExit(main())
