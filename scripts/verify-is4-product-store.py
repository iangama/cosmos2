"""Atomic phase+view envelope and branches, actual Windows locks and independent reload."""
from pathlib import Path
import argparse
import copy
import ctypes
import hashlib
import json
import subprocess
import sys
import threading
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1];APP=ROOT/'output/is4-body-particle-product0.8.1/app'
sys.path.insert(0,str(APP))
from is4_product_store import Store
from is4_body_snapshot import digest
from is4_experiment import Experiment
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/('output/is4-product-store-'+args.label);receipt=ROOT/('evidence/is4-product-store-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve store evidence')
    folder.mkdir();fixture=ROOT/'output/is4-body-particle-product0.8.0/particle-sessions/latest.json'
    files=[*APP.glob('is4*.py'),fixture,Path(__file__)];hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    report={'schema':1,'accepted':False,'completed':False,'source_sha256':hashes,'checks':[]}
    try:
        particle=json.loads(fixture.read_text(encoding='utf-8'));store=Store(folder/'store');view={'physical_unit_m':.125,'visible':False}
        store.save(particle,view);r,c=store.load();assert r['particle']==particle and r['view']==view
        checkpoint_before=store.path.read_bytes();target=folder/'restored';v,restored=store.restore_to(target);assert v==view
        expected=Experiment.load(target);expected.advance_steps(77);future=expected.payload();future.pop('edit_token')
        code='import sys,json;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from is4_product_store import Store;from is4_experiment import Experiment;s=Store(sys.argv[2]);v,e=s.restore_to(sys.argv[3]);e=Experiment.load(sys.argv[3]);e.advance_steps(77);p=e.payload();p.pop("edit_token");Path(sys.argv[4]).write_text(json.dumps({"view":v,"future":p}),encoding="utf-8")'
        out=folder/'new-process.json';subprocess.run([sys.executable,'-Xutf8','-c',code,str(APP),str(store.folder),str(folder/'new-process-worker'),str(out)],check=True)
        actual=json.loads(out.read_text(encoding='utf-8'));assert actual['view']==view and actual['future']==json.loads(json.dumps(future))
        a=store.save(particle,view,name='Primeiro ramo');b=store.save(particle,{**view,'visible':True},name='Segundo ramo',parent=a['branch']['id'])
        rb,_=store.load(b['branch']['id']);assert rb['branch']['parent']==a['branch']['id'] and rb['view']['visible']
        assert len(store.catalog())==2 and all(x['valid'] for x in store.catalog())
        refusals=0
        for edit in ['unit_bool','unit_zero','visible_int','schema_bool','particle_offset','seal','extra']:
            bad=copy.deepcopy(r)
            if edit=='unit_bool':bad['view']['physical_unit_m']=True
            if edit=='unit_zero':bad['view']['physical_unit_m']=0.
            if edit=='visible_int':bad['view']['visible']=0
            if edit=='schema_bool':bad['schema']=True
            if edit=='particle_offset':bad['particle']['phase']['position_offset_m'][0]+=1.
            if edit=='extra':bad['extra']=True
            if edit!='seal':bad['record_sha256']=digest({k:v for k,v in bad.items() if k!='record_sha256'})
            else:bad['record_sha256']='0'*64
            store.path.write_text(json.dumps(bad),encoding='utf-8');previous=(target/'latest.json').read_bytes()
            try:store.restore_to(target)
            except (ValueError,TypeError):refusals+=1
            else:raise AssertionError(edit)
            assert (target/'latest.json').read_bytes()==previous
            store.path.write_bytes(checkpoint_before)
        kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p];kernel.CreateFileW.restype=ctypes.c_void_p;kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        def lock():
            handle=kernel.CreateFileW(str(store.path),0x80000000,3,None,3,128,None)
            if handle==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
            return handle
        handle=lock();timer=threading.Timer(.1,lambda:kernel.CloseHandle(handle));timer.start();store.save(particle,view);timer.join()
        previous=store.path.read_bytes();handle=lock()
        try:
            try:store.save(particle,{**view,'visible':True})
            except PermissionError:refusals+=1
            else:raise AssertionError('Locked envelope replaced')
            assert store.path.read_bytes()==previous and not list(store.folder.glob('*.tmp'))
        finally:kernel.CloseHandle(handle)
        for _ in range(30):store.save(particle,view,name='Ramo limitado')
        try:store.save(particle,view,name='Excesso')
        except ValueError:refusals+=1
        else:raise AssertionError('Branch budget exceeded')
        assert len(list(store.branches.glob('*.json')))==32 and all(sha(ROOT/n)==v for n,v in hashes.items())
        report.update(accepted=True,completed=True,refusals=refusals,checks=['Atomic scientific+view record','New process exact future77 steps with paired positions','Branch parent/visibility independent and budget32','Corruption refuses before replacing worker manifest','Real Windows short lock recovers; permanent lock preserves old whole envelope'])
    except Exception:report['failure']=traceback.format_exc()
    receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'accepted':report['accepted'],'refusals':report.get('refusals'),'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
