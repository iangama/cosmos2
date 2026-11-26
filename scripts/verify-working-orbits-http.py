"""Check the combined local candidate over isolated HTTP; no live owner commands."""
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
PRODUCT=ROOT/'output/original-flow-hotfix-product0.28.3'
OUT=ROOT/'evidence/working-orbits-http-20261121a.json'
FOLDER=ROOT/'output/working-orbits-http-20261121a'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
OPENER=urllib.request.build_opener(urllib.request.ProxyHandler({}))


def main():
    assert not OUT.exists() and not FOLDER.exists();FOLDER.mkdir()
    manifest=json.loads((PRODUCT/'build-manifest.json').read_text())
    assert all(sha(PRODUCT/n)==seal for n,seal in manifest['files_sha256'].items())
    profile=json.loads((ROOT/'evidence/c214-orbits-profile-20261121b.json').read_text())
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
    base=f'http://127.0.0.1:{port}'
    proof=dict(accepted=False,completed=False,checks=[],source_sha256={Path(__file__).relative_to(ROOT).as_posix():sha(Path(__file__)),
      (PRODUCT/'build-manifest.json').relative_to(ROOT).as_posix():sha(PRODUCT/'build-manifest.json')},
      scope='Separate loopback server and private candidate storage. Combined HTTP wiring, unchanged accepted timelike physics fingerprints, current spatial preview, save/export/restore. No native usability or transferred performance acceptance.')
    def call(path,value=None):
        request=urllib.request.Request(base+path,data=None if value is None else json.dumps(value).encode(),headers={'Content-Type':'application/json'})
        return json.load(OPENER.open(request,timeout=30))
    server=None
    try:
        env=os.environ.copy();env.update(COSMOS2_ROOT=str(ROOT),COSMOS2_STORAGE=str(FOLDER/'private-legacy-storage'))
        with (FOLDER/'server.log').open('xb') as stream:
            server=subprocess.Popen([sys.executable,'-u','-Xutf8',str(PRODUCT/'app/server.py'),'--port',str(port)],cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+45
        while True:
            assert server.poll() is None,'Server failed before readiness'
            try:state=call('/api/timelike/state');break
            except OSError:
                assert time.monotonic()<deadline;time.sleep(.05)
        assert 'timelike-orbits' in call('/api/forces/catalog')['scenarios']
        for run in profile['runs']:
            cfg=run['stable_control']['expected_scenario']['configuration']
            call('/api/timelike/command',dict(command='compute',configuration=cfg,edit_token=state['edit_token'],revision=state['revision']))
            deadline=time.monotonic()+25
            while True:
                state=call('/api/timelike/state')
                if not state['busy']:break
                assert time.monotonic()<deadline;time.sleep(.025)
            assert state['phase']=='complete' and state['published_job_id']==state['job_id'],state['error']
            assert state['result']['physics_sha256']==run['stable_control']['expected_scenario']['physics_sha256']
            assert state['result']['configuration']==cfg and len(state['result']['result']['time_s'])==1025
            proof['checks'].append(dict(name='combined-backend-matches-accepted-physics-'+run['recipe']['name'],physics_sha256=state['result']['physics_sha256']))
        cfg=state['configuration'];saved=call('/api/forces/save',cfg);assert saved['ok']
        loaded=call('/api/forces/load',{});assert loaded['configuration']==cfg
        exported=call('/api/forces/export',cfg);assert exported['physics_sha256']==state['result']['physics_sha256']
        assert Path(exported['export_file']).is_relative_to(PRODUCT)
        proof['checks'].append(dict(name='new-orbit-conditions-save-load-and-export-retain-physics'))
        source=ROOT/'output/original-flow-hotfix-product0.27.6/is6-spatial-import-service-records/exports/f6dee22dbd064d8686fe05629cc07092.json'
        spatial=call('/api/spatial/state')
        preview=call('/api/spatial/import-preview',dict(guard=spatial['guard'],source_text=source.read_text(encoding='utf8')))
        assert preview['spatial']['import_preview']['source_sha256']==sha(source)
        proof['checks'].append(dict(name='new-spatial-format-remains-admitted-in-combined-server'))
        assert all(sha(PRODUCT/n)==seal for n,seal in manifest['files_sha256'].items())
        proof.update(accepted=True,completed=True)
    except Exception:proof['failure']=traceback.format_exc()
    finally:
        if server and server.poll() is None:
            try:call('/api/shutdown',{});proof['server_exit']=server.wait(timeout=20)
            except Exception:server.terminate();proof['server_exit']=server.wait(timeout=10)
        if proof.get('server_exit')!=0:proof.update(accepted=False,completed=False)
        OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:proof.get(k) for k in ['accepted','completed','checks','server_exit','failure']}))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
