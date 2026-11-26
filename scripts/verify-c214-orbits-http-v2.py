"""Real isolated backend HTTP, async cancellation, private export and generation-aware restoration."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/c214-orbits-staging-v2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
OPENER=urllib.request.build_opener(urllib.request.ProxyHandler({}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);args=parser.parse_args()
    assert args.label and len(args.label)<=20 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
    folder=ROOT/f'output/c214-orbits-http-{args.label}';out=ROOT/f'evidence/c214-orbits-http-{args.label}.json'
    assert not folder.exists() and not out.exists()
    gate_path=ROOT/'evidence/c214-orbits-service-20261114a.json';gate=json.loads(gate_path.read_text())
    assert gate['accepted'] and gate['completed']
    assert all(sha(ROOT/name)==seal for name,seal in gate['source_sha256'].items())
    parent=ROOT/'output/c214-orbits-staging'
    for p in (STAGE/'app').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.name != 'server.py':
            assert sha(p)==sha(parent/'app'/p.relative_to(STAGE/'app')),p
    saved_path=STAGE/'user/forces/latest.json';assert not saved_path.exists(),'Preserve previous private force save'
    sources=gate['source_sha256']|{gate_path.relative_to(ROOT).as_posix():sha(gate_path),Path(__file__).relative_to(ROOT).as_posix():sha(Path(__file__))}
    for base in [STAGE/'app',STAGE/'data']:
        sources.update({p.relative_to(ROOT).as_posix():sha(p) for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    folder.mkdir()
    request=dict(scenario='timelike-orbits',parameters=dict(radial_cycles=1,semi_latus_rectum_rs=10000.,eccentricity=.2))
    (folder/'recipe-before-execution.json').write_text(json.dumps(dict(configuration=request,source_sha256=sources),indent=2)+'\n',encoding='utf8')
    with zipfile.ZipFile(folder/'executed-sources.zip','x',zipfile.ZIP_DEFLATED) as archive:
        for name in sources:archive.write(ROOT/name,name)
    answer=dict(accepted=False,completed=False,source_sha256=sources,groups=[],refusals=[],
                scope='Actual isolated backend HTTP and private records only; no native UI/residency acceptance.')
    process=None
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
    base=f'http://127.0.0.1:{port}'

    def call(path,value=None,raw=None):
        body=raw if raw is not None else None if value is None else json.dumps(value).encode()
        req=urllib.request.Request(base+path,data=body,headers={'Content-Type':'application/json'})
        with OPENER.open(req,timeout=25) as response:return json.load(response)

    def refuse(name,path,value=None,raw=None):
        try:call(path,value,raw)
        except urllib.error.HTTPError as error:
            result=json.load(error);assert error.code==400 and result['ok'] is False
            answer['refusals'].append(dict(name=name,status=error.code,error=result['error']))
        else:raise AssertionError('Malformed HTTP accepted: '+name)

    def idle():
        deadline=time.monotonic()+25
        while True:
            state=call('/api/timelike/state')
            if not state['busy']:return state
            assert time.monotonic()<deadline
            time.sleep(.02)

    try:
        env=os.environ.copy();env.update(COSMOS2_ROOT=str(ROOT),COSMOS2_STORAGE=str(folder/'private-legacy-storage'))
        with (folder/'server.log').open('xb') as log,(folder/'server-errors.log').open('xb') as errors:
            process=subprocess.Popen([sys.executable,'-u','-Xutf8',str(STAGE/'app/server.py'),'--port',str(port)],cwd=ROOT,
                                     env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=errors)
        deadline=time.monotonic()+45
        while True:
            assert process.poll() is None,'Backend exited before readiness'
            try:state=call('/api/timelike/state');break
            except urllib.error.URLError:
                assert time.monotonic()<deadline
                time.sleep(.05)
        catalog=call('/api/forces/catalog');assert 'timelike-orbits' in catalog['scenarios'] and 'relativity' in catalog['scenarios']
        starting=call('/api/timelike/command',dict(command='compute',configuration=request,edit_token=state['edit_token'],revision=state['revision']))
        ready=idle();assert ready['phase']=='complete' and ready['published_job_id']==starting['job_id']
        response=ready['result'];assert response['ok'] and response['scientific_contract']['model_id']=='cosmos2:schwarzschild-exterior-timelike-bound'
        (folder/'completed-result.json').write_text(json.dumps(response,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
        answer['groups'].append('real-http-job-and-provenance')
        long_request=dict(scenario='timelike-orbits',parameters=dict(radial_cycles=16,semi_latus_rectum_rs=1e6,eccentricity=.8))
        busy=call('/api/timelike/command',dict(command='compute',configuration=long_request,edit_token=ready['edit_token'],revision=ready['revision']))
        call('/api/timelike/command',dict(command='cancel',job_id=busy['job_id'],edit_token=busy['edit_token'],revision=busy['revision']))
        stopped=idle();assert stopped['phase']=='cancelled' and stopped['result']==response and stopped['published_job_id']==ready['published_job_id']
        answer['groups'].append('real-http-cancellation-preserves-completed-result')
        refuse('stale-token','/api/timelike/command',dict(command='compute',configuration=request,edit_token=state['edit_token'],revision=state['revision']))
        refuse('fractional-cycles','/api/timelike/command',dict(command='compute',configuration=dict(request,parameters=dict(radial_cycles=1.5)),edit_token=stopped['edit_token'],revision=stopped['revision']))
        refuse('invalid-json','/api/forces/evaluate',raw=b'{')
        refuse('non-object','/api/timelike/command',raw=b'[]')
        refuse('unknown-effect','/api/forces/evaluate',dict(request,controls=dict(gravity=dict(effects=dict(unknown=True)))))
        stored=call('/api/forces/save',request)['saved'];original=saved_path.read_bytes()
        restored=call('/api/forces/load',{});assert restored['restoration']['status']=='same_generation'
        old=copy.deepcopy(stored);old['scientific_generation']['runtime']['numpy']='fixture-previous-runtime'
        old['generation_sha256']=digest(old['scientific_generation'])
        old['manifest_sha256']=digest({key:value for key,value in old.items() if key!='manifest_sha256'})
        saved_path.write_text(json.dumps(old)+'\n',encoding='utf8')
        changed=call('/api/forces/load',{});assert changed['restoration']['status']=='changed_generation'
        assert any(d['kind']=='runtime' and d['name']=='numpy' for d in changed['restoration']['differences'])
        broken=copy.deepcopy(stored);broken['configuration']['parameters']['mass_solar']*=2
        saved_path.write_text(json.dumps(broken)+'\n',encoding='utf8');refuse('corrupt-private-save','/api/forces/load',{})
        legacy=dict(schema=1,configuration=stored['configuration'],sha256=stored['sha256'])
        saved_path.write_text(json.dumps(legacy)+'\n',encoding='utf8')
        assert call('/api/forces/load',{})['restoration']['status']=='unknown_generation'
        saved_path.write_bytes(original)
        answer['groups'].append('private-save-current-changed-unknown-and-corrupt-generation')
        exported=call('/api/forces/export',request)
        artifact=Path(exported['export_file']).resolve();assert artifact.is_relative_to((STAGE/'user/exports').resolve())
        assert exported['result']==response['result'] and json.loads(artifact.read_text())==exported
        answer['groups'].append('private-complete-export-with-matching-physics')
        call('/api/shutdown',{})
        assert process.wait(timeout=25)==0
        answer.update(accepted=True,completed=True,server_exit=0,port=port,export_sha256=sha(artifact))
        assert all(sha(ROOT/name)==seal for name,seal in (sources|gate['protected_sha256']).items())
    except Exception:
        answer['failure']=traceback.format_exc()
    finally:
        if process is not None and process.poll() is None:
            try:call('/api/shutdown',{});answer['cleanup_exit']=process.wait(timeout=25)
            except Exception:answer['cleanup_failure']=traceback.format_exc()
        if saved_path.exists() and 'original' in locals():saved_path.write_bytes(original)
    out.write_text(json.dumps(answer,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({key:value for key,value in answer.items() if key!='source_sha256'},ensure_ascii=False),flush=True)
    return 0 if answer['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
