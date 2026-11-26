"""Isolated real HTTP import admission, exact-content guard and restart persistence."""
from pathlib import Path
import contextlib
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/spatial-roundtrip-http-staging-v1'
FOLDER=ROOT/'output/spatial-roundtrip-http-20261121a'
OUT=ROOT/'evidence/spatial-roundtrip-http-20261121a.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert STAGE.is_dir() and not FOLDER.exists() and not OUT.exists();FOLDER.mkdir()
    prep=json.loads((STAGE/'preparation.json').read_text(encoding='utf8'))
    assert prep['accepted'] and prep['completed'] and prep['scientific_python_unchanged']==137
    assert all(sha(STAGE/name)==digest for name,digest in prep['files_sha256'].items())
    source=ROOT/'output/original-flow-hotfix-product0.27.6/is6-spatial-import-service-records/exports/f6dee22dbd064d8686fe05629cc07092.json'
    raw=source.read_bytes();text=raw.decode('utf8');document=json.loads(raw)
    protected={name:sha(ROOT/name) for name in ['output/session.json','Iniciar-Cosmos2.cmd','Abrir-Planetas.cmd','Abrir-Planetas-e-Luas.cmd','config/local-working-product.json',source.relative_to(ROOT).as_posix()]}
    proof=dict(accepted=False,completed=False,native_user_flow_accepted=False,installed=False,checks=[],server_exits=[],
      source_sha256={name:sha(ROOT/name) for name in ['scripts/verify-spatial-roundtrip-http.py','output/spatial-roundtrip-http-staging-v1/preparation.json']},
      protected_sha256=protected,
      scope='Real loopback HTTP on separate ports and isolated staging storage; exact file exported by native0.27.6, legacy/BOM compatibility, byte-exact preview guard, import persistence after restart, malformed format/fields refusal. No renderer or live owner-session commands, no native/scientific promotion.')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    @contextlib.contextmanager
    def backend(label):
        with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        assert port not in {4700,4682,8088}
        env=os.environ.copy();env['COSMOS2_STORAGE']=str(STAGE/'gravity-sessions')
        log=(FOLDER/(label+'.log')).open('xb')
        process=subprocess.Popen([sys.executable,'-u','-Xutf8',str(STAGE/'app/server.py'),'--port',str(port)],cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        def request(route,payload=None):
            body=None if payload is None else json.dumps(payload,ensure_ascii=False).encode('utf8')
            req=urllib.request.Request('http://127.0.0.1:'+str(port)+route,data=body,headers={} if body is None else {'Content-Type':'application/json'})
            try:response=opener.open(req,timeout=180)
            except urllib.error.HTTPError as error:response=error
            with response:
                value=response.read();return response.status,json.loads(value) if 'application/json' in response.headers.get('Content-Type','') else value
        try:
            deadline=time.monotonic()+60
            while True:
                assert process.poll() is None,'The isolated server exited: '+label
                try:
                    code,value=request('/health')
                    if code==200 and value['application']=='cosmos2':break
                except OSError:pass
                assert time.monotonic()<deadline,'Isolated HTTP health timeout';time.sleep(.1)
            yield request
        finally:
            if process.poll() is None:
                try:request('/api/shutdown',{});process.wait(timeout=20)
                except Exception:process.terminate();process.wait(timeout=15)
            log.close();proof['server_exits'].append(dict(label=label,exit_code=process.returncode))
    def persist():OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    def check(name,**data):proof['checks'].append(dict(name=name,**data));persist()
    def preview(request,source_text):
        code,state=request('/api/spatial/state');assert code==200
        code,value=request('/api/spatial/import-preview',dict(guard=state['guard'],source_text=source_text))
        assert code==200 and value['ok'],value
        snapshot=value['spatial'];assert snapshot['import_preview']['valid']
        return snapshot
    def commit(request,snapshot,source_text,name):
        return request('/api/spatial/import-commit',dict(guard=snapshot['guard'],preview_id=snapshot['import_preview']['id'],source_text=source_text,name=name))
    try:
        imported=[]
        with backend('first') as request:
            code,state=request('/api/spatial/state');assert code==200 and not state['active'] and not state['branches']
            current=preview(request,text)
            assert current['import_preview']['source_format']=='spatial-checkpoint-with-origin-2'
            assert current['import_preview']['source_sha256']==sha(source)
            assert current['import_preview']['magnetic_sample_created'] is False
            code,value=commit(request,current,text,'HTTP origem atual');assert code==200 and value['ok'],value
            first=value['result']['record'];imported.append(first['branch']['id'])
            assert first['origin']['source_sha256']==sha(source)
            assert not value['spatial']['active'] and not value['spatial']['recovery_required']
            check('current-native-export-previews-and-imports-over-http',branch=first['branch']['id'],source_sha256=sha(source))
            current=preview(request,text)
            code,value=commit(request,current,text+' ','Origem alterada');assert code==400 and not value['ok'] and 'arquivo mudou' in value['error'].lower()
            code,state=request('/api/spatial/state');assert code==200 and len(state['branches'])==1
            check('semantic-json-equivalence-does-not-bypass-exact-source-text-guard')
            bom='\ufeff'+text;current=preview(request,bom)
            assert current['import_preview']['source_sha256']==hashlib.sha256(bom.encode('utf8')).hexdigest()
            code,value=commit(request,current,bom,'HTTP origem BOM');assert code==200 and value['ok'],value
            imported.append(value['result']['record']['branch']['id'])
            check('utf8-bom-is-preserved-in-source-hash-and-import')
            sys.path.insert(0,str(STAGE/'app'))
            import is6_spatial_import as legacy
            old={key:value for key,value in document.items() if key not in {'origin','record_sha256'}}
            old.update(schema=1,kind='is6_spatial_body_mesh_checkpoint');old['record_sha256']=legacy.digest(old)
            old_text=legacy.artifact.encoded(old).decode('utf8');current=preview(request,old_text)
            assert current['import_preview']['source_format']=='spatial-checkpoint-1'
            code,value=commit(request,current,old_text,'HTTP envelope legado isolado');assert code==200 and value['ok'],value
            imported.append(value['result']['record']['branch']['id'])
            check('legacy-schema1-remains-admitted-through-http',fixture='Legacy wrapper reconstructed from unchanged native artifact/view for isolated compatibility testing.')
            code,state=request('/api/spatial/state');guard=state['guard']
            code,value=request('/api/spatial/import-preview',dict(guard=guard,source_text='{"schema":99,"kind":"unknown"}'))
            assert code==400 and not value['ok'] and value['error']
            code,value=request('/api/spatial/import-preview',dict(guard=guard,source_text=text,extra=True));assert code==400 and not value['ok']
            code,state=request('/api/spatial/state');assert code==200 and len(state['branches'])==3
            check('unknown-format-and-extra-fields-refused-without-branch-creation')
        with backend('restart') as request:
            code,state=request('/api/spatial/state');assert code==200 and not state['active']
            assert {branch['id'] for branch in state['branches']}==set(imported)
            assert all(branch['valid'] for branch in state['branches']),state['branches']
            check('restart-retains-valid-current-bom-and-legacy-imports',branches=len(imported))
        assert len(proof['server_exits'])==2 and all(row['exit_code']==0 for row in proof['server_exits'])
        assert all(sha(ROOT/name)==digest for name,digest in protected.items())
        assert all(sha(STAGE/name)==digest for name,digest in prep['files_sha256'].items())
        proof.update(accepted=True,completed=True)
    except Exception:proof['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps({key:proof.get(key) for key in ['accepted','completed','checks','server_exits','failure']},ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
