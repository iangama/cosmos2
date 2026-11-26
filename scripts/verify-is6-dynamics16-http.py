"""Exercise the real HTTP handler and numerical worker with the renderer substituted."""
import argparse
import copy
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
import traceback
import types
import urllib.error
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is6-dynamics16-product0.26.0/app'
sys.path[:0]=[str(APP),str(ROOT/'scripts')]
import system16_import as model
from http.server import ThreadingHTTPServer

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
UTC='2026-10-11T12:00:00Z'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);label=parser.parse_args().label
    assert label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label) and len(label)<=24
    folder=ROOT/f'output/is6-dynamics16-http-{label}';receipt=ROOT/f'evidence/is6-dynamics16-http-{label}.json'
    assert not folder.exists() and not receipt.exists(),'Preserve HTTP evidence'
    assert json.loads((ROOT/f'evidence/is6-dynamics16-service-{label}.json').read_text())['accepted']
    folder.mkdir();os.environ['COSMOS2_STORAGE']=str(folder/'sessions')
    sources=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    sources += [Path(__file__),ROOT/'scripts/verify-is6-dynamics16-service.py',APP.parent/'build-manifest.json',
                ROOT/'IS-6-DINAMICA16-INTERFACE-CONTRATO.md']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in sources}
    protected={n:sha(ROOT/n) for n in ['output/session.json','user/sessions/latest.json','Iniciar-Cosmos2.cmd']}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sources:z.write(p,p.relative_to(ROOT).as_posix())
    report=dict(completed=False,accepted=False,started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        source_sha256=hashes,source_archive_sha256=sha(folder/'executed-sources.zip'),protected_sha256=protected,
        refusals=[],successes=[],scope='Real HTTP handler and actual numerical worker, substituted Atlas/native rendering and inactive benches. Native transaction/camera acceptance remains pending.')
    def persist():receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    persist();worker=None;http=None;thread=None
    try:
        from importlib.machinery import SourceFileLoader
        helpers=SourceFileLoader('dynamics16_service_helpers',str(ROOT/'scripts/verify-is6-dynamics16-service.py')).load_module()
        worker=helpers.Worker(folder/'sessions')
        class WorkerLab:
            def __init__(self):self.mode='atlas';self.calls=[]
            def status(self):return dict(mode=self.mode,physics=worker.latest)
            def command(self,request):
                request=copy.deepcopy(request);name=request.pop('command');self.calls.append(name)
                if name=='atlas':worker.call('pause');self.mode='atlas';ack=dict(command=name)
                else:
                    ack=worker.call(name,**request)
                    if name=='import_atlas':self.mode='experiment'
                return dict(ok=True,ack=ack,**self.status())
        lab=WorkerLab()
        class ConfirmedAtlas:
            def __init__(self):self.utc=UTC;self.epoch_changes=0;self.native_calls=0
            def status(self):return dict(epoch=model.catalog.states(utc=self.utc)['epoch'])
            def apply_epoch(self,utc):self.utc=utc;self.epoch_changes+=1;return self.status()
        atlas=ConfirmedAtlas()
        class Bench:
            def __init__(self,*a,**k):self.flags=dict(active=False,busy=False,recovery_required=False)
            def status(self):return copy.deepcopy(self.flags)
        benches={}
        def stub(name,**entries):sys.modules[name]=types.SimpleNamespace(**entries)
        stub('laboratory',Laboratory=lambda:lab);stub('moon_atlas',Atlas=lambda:atlas)
        for module,classname in [('is4_laboratory','ParticleLaboratory'),('is5_laboratory','SolarLaboratory'),
                                 ('is6_spatial_import_laboratory','SpatialLaboratory'),('is6_layers_laboratory','LayerLaboratory')]:
            bench=Bench();benches[module]=bench;stub(module,**{classname:lambda *a,b=bench,**k:b})
        stub('moon_navigation',Navigation=lambda *a,**k:Bench())
        spec=importlib.util.spec_from_file_location('dynamics16_test_server',APP/'server.py')
        server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)
        http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler);http.daemon_threads=True
        thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        def call(path,value):
            request=urllib.request.Request(f'http://127.0.0.1:{http.server_port}'+path,data=json.dumps(value,allow_nan=False).encode(),headers={'Content-Type':'application/json'})
            try:
                with urllib.request.urlopen(request,timeout=40) as response:return response.status,json.load(response)
            except urllib.error.HTTPError as error:return error.code,json.load(error)
        def identity():
            p=worker.latest
            return dict(mode=lab.mode,physics={k:copy.deepcopy(p[k]) for k in ['time','bodies','system_id','edit_token','revision','atlas_initial'] if k in p},
                        atlas_epoch=atlas.utc,epoch_changes=atlas.epoch_changes,commands=list(lab.calls))
        def refuse(name,payload,path='/api/dynamics16/experiment'):
            before=identity();status,response=call(path,payload)
            assert status==400 and not response.get('ok',False),(name,status,response)
            assert identity()==before,(name,'state changed')
            report['refusals'].append(dict(name=name,status=status,error=response.get('error')));persist()
        for name,payload in [('missing UTC',{}),('non UTC type',dict(utc=123)),('null UTC',dict(utc=None)),
            ('outside early coverage',dict(utc='1900-01-01T00:00:00Z')),('outside late coverage',dict(utc='2100-01-01T00:00:00Z')),
            ('unknown field',dict(utc=UTC,unexpected=1)),('GM injection',dict(utc=UTC,GM=1)),
            ('body injection',dict(utc=UTC,bodies=[])),('model injection',dict(utc=UTC,kind=model.KIND)),
            ('stale confirmed epoch',dict(utc='2026-10-12T12:00:00Z'))]:refuse(name,payload)
        for name,bench in benches.items():
            for flag in list(bench.flags):
                bench.flags[flag]=True
                refuse(name+' '+flag,dict(utc=UTC));bench.flags[flag]=False
        status,response=call('/api/dynamics16/experiment',dict(utc=UTC))
        assert status==200 and response['ok'] and lab.mode=='experiment',response
        assert len(worker.latest['bodies'])==16 and worker.latest['paused'] and worker.latest['time']==0
        assert worker.latest['atlas_initial']['kind']==model.KIND and atlas.epoch_changes==0
        initial=copy.deepcopy(worker.latest)
        report['successes'].append(dict(name='dedicated UTC import',bodies=16,atlas_epoch_unchanged=True))
        refuse('second copy during experiment',dict(utc=UTC))
        refuse('generic import bypass',dict(command='import_atlas',initial_state={}),'/api/command')
        status,response=call('/api/command',dict(command='dynamics16_reading',**helpers.guard(initial),body_id=initial['bodies'][-1]['id']))
        assert status==200 and len(response['ack']['result']['sources'])==15
        report['successes'].append(dict(name='HTTP contribution dispatch',sources=15))
        for route,count,kind in [('/api/atlas/experiment',3,'atlas_sun_earth_moon'),('/api/solar/experiment',4,'solar_four_physical_centers')]:
            lab.command(dict(command='atlas'));status,response=call(route,dict(utc=UTC))
            assert status==200 and response['ok'] and len(worker.latest['bodies'])==count
            assert worker.latest['atlas_initial']['kind']==kind and worker.latest['dynamics16'] is None
            report['successes'].append(dict(name='legacy route '+route,bodies=count,kind=kind))
        assert all(sha(ROOT/n)==s for n,s in protected.items())
        assert all(sha(ROOT/n)==s for n,s in hashes.items())
        worker.close();worker=None
        report.update(completed=True,accepted=True,protected_unchanged=True,worker_exit=0,finished_utc=dt.datetime.now(dt.timezone.utc).isoformat())
        persist();print(json.dumps(dict(accepted=True,refusals=len(report['refusals']),successes=len(report['successes']))),flush=True)
    except BaseException as error:
        report.update(error=repr(error),traceback=traceback.format_exc());persist();raise
    finally:
        if http:http.shutdown();http.server_close()
        if thread:thread.join(timeout=3)
        if worker:
            try:worker.close()
            except BaseException:pass


if __name__=='__main__':main()
