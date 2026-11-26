"""Check the original-entry hotfix backend on a separate port; no user-flow acceptance."""
from pathlib import Path
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import traceback
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/original-forces-hotfix-staging'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out=ROOT/'evidence/original-forces-hotfix-http-20261114a.json'
    folder=ROOT/'output/original-forces-hotfix-http-20261114a'
    assert not out.exists() and not folder.exists()
    folder.mkdir()
    files=[p for tree in ['app','data'] for p in (STAGE/tree).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in files+[Path(__file__)]}
    proof=dict(accepted=False,completed=False,native_user_flow_accepted=False,source_sha256=sources,checks=[])
    (folder/'recipe-before-execution.json').write_text(json.dumps(proof,indent=2)+'\n')
    with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    env=os.environ.copy();env['COSMOS2_STORAGE']=str(folder/'gravity-sessions')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def get(path):
        with opener.open(f'http://127.0.0.1:{port}'+path,timeout=15) as response:return json.load(response)
    def post(path,value):
        request=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=json.dumps(value).encode(),headers={'Content-Type':'application/json'})
        with opener.open(request,timeout=30) as response:return json.load(response)
    child=None
    try:
        with (folder/'server.log').open('xb') as stream:
            child=subprocess.Popen([sys.executable,'-u','-Xutf8',str(STAGE/'app/server.py'),'--port',str(port)],cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+90
        while True:
            assert child.poll() is None,'Hotfix backend exited'
            try:
                if get('/health')['application']=='cosmos2':break
            except OSError:pass
            assert time.monotonic()<deadline
            time.sleep(.1)
        catalog=get('/api/forces/catalog');assert len(catalog['scenarios'])>=12
        proof['checks'].append(dict(name='local_catalog',scenarios=sorted(catalog['scenarios'])))
        for scenario in ['gravity','strong','weak','relativity']:
            value=post('/api/forces/evaluate',dict(scenario=scenario,controls={},parameters={}))
            assert value['ok'] and value['configuration']['scenario']==scenario and value['result']['time_s']
            (folder/(scenario+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
            proof['checks'].append(dict(name='bounded_backend_smoke',scenario=scenario,states=len(value['result']['time_s']),physics_sha256=value['physics_sha256']))
        assert all(sha(ROOT/name)==seal for name,seal in sources.items())
        proof.update(accepted=True,completed=True,port=port,scope='Separate HTTP backend catalog and four existing model smoke cases only; no native button/recovery/visual acceptance and no installation')
    except Exception:
        proof['failure']=traceback.format_exc()
    finally:
        if child is not None:
            try:
                post('/api/shutdown',{});child.wait(timeout=15)
            except Exception:
                if child.poll() is None:child.terminate();child.wait(timeout=15)
            proof['server_exit']=child.returncode
            if child.returncode!=0:proof['accepted']=False
        out.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:proof.get(k) for k in ['accepted','completed','native_user_flow_accepted','server_exit','failure']},ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
