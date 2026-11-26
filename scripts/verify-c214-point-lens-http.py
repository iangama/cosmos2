"""Exercise the new static lens through isolated HTTP and generation-aware private records."""
from pathlib import Path
import copy
import hashlib
import json
import math
import os
import socket
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
import zipfile

import mpmath as mp

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/c214-point-lens-service-staging'
PARENT=ROOT/'output/original-flow-hotfix-product0.28.4'
FOLDER=ROOT/'output/c214-point-lens-http-20261121a'
OUT=ROOT/'evidence/c214-point-lens-http-20261121a.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
OPENER=urllib.request.build_opener(urllib.request.ProxyHandler({}))


def main():
    assert not OUT.exists() and not FOLDER.exists();FOLDER.mkdir()
    prepared=json.loads((STAGE/'preparation.json').read_text());assert prepared['accepted']
    assert all(sha(STAGE/n)==s for n,s in prepared['files_sha256'].items())
    sources={(STAGE/n).relative_to(ROOT).as_posix():s for n,s in prepared['files_sha256'].items()}
    for p in [Path(__file__),STAGE/'preparation.json',ROOT/'C2-14-LENTE-PONTUAL-SERVICO-20261121.md']:
        sources[p.relative_to(ROOT).as_posix()]=sha(p)
    protected={p.relative_to(ROOT).as_posix():sha(p) for p in [ROOT/'output/session.json',ROOT/'config/local-working-product.json']}
    recipes=[dict(name='default',parameters={}),dict(name='observer-moved',parameters=dict(observer_x_au=1)),
      dict(name='lens-moved',parameters=dict(lens_x_au=1)),dict(name='source-moved',parameters=dict(source_x_au=9)),
      dict(name='aligned',parameters=dict(source_x_au=0))]
    (FOLDER/'recipe-before-execution.json').write_text(json.dumps(dict(source_sha256=sources,protected_sha256=protected,recipes=recipes),indent=2)+'\n')
    with zipfile.ZipFile(FOLDER/'executed-sources.zip','x',zipfile.ZIP_DEFLATED) as archive:
        for name in sources:archive.write(ROOT/name,name)
    proof=dict(accepted=False,completed=False,source_sha256=sources,protected_sha256=protected,checks=[],refusals=[],server_exits=[],
      scope='Two actual separate loopback server lifetimes. Unit conversion, moving observer/lens/source, effect/visibility semantics, alignment, export/save/restore and restart. No commands sent to live4700 or renderer; no native/performance/C2-14 promotion.')
    server=None;port=None
    def call(path,value=None):
        req=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=None if value is None else json.dumps(value).encode(),headers={'Content-Type':'application/json'})
        return json.load(OPENER.open(req,timeout=35))
    def start(label):
        nonlocal server,port
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
        env=os.environ.copy();env.update(COSMOS2_ROOT=str(ROOT),COSMOS2_STORAGE=str(FOLDER/'private-legacy-storage'))
        with (FOLDER/(label+'.log')).open('xb') as stream:
            server=subprocess.Popen([sys.executable,'-u','-Xutf8',str(STAGE/'app/server.py'),'--port',str(port)],cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+45
        while True:
            assert server.poll() is None,'Server failed before readiness'
            try:return call('/api/forces/catalog')
            except OSError:
                assert time.monotonic()<deadline;time.sleep(.05)
    def close(label):
        nonlocal server
        call('/api/shutdown',{});code=server.wait(timeout=20)
        proof['server_exits'].append(dict(label=label,code=code));assert code==0;server=None
    def evaluate(parameters=None,controls=None):return call('/api/forces/evaluate',dict(scenario='point-lens',parameters=parameters or {},controls=controls or {}))
    def refuse(name,request):
        try:call('/api/forces/evaluate',request)
        except urllib.error.HTTPError as e:
            value=json.load(e);assert e.code==400 and value['ok'] is False
            proof['refusals'].append(dict(name=name,error=value['error']))
        else:raise AssertionError('Invalid request admitted: '+name)
    try:
        catalog=start('first');assert 'point-lens' in catalog['scenarios'] and 'timelike-orbits' in catalog['scenarios']
        values={r['name']:evaluate(r['parameters']) for r in recipes}
        base=values['default'];p=base['result']['point_lens'];units=base['result']['units']
        mp.mp.dps=110
        expected_pc=mp.mpf(149597870700)*648000/mp.pi
        assert abs(mp.mpf(units['pc_m'])/expected_pc-1)<mp.mpf('3e-16')
        assert p['configuration']['lens_m'][2]==4*units['kpc_m'] and p['configuration']['source_m'][0]==8*units['au_m']
        assert p['configuration']['GM_m3_s2']==units['nominal_solar_GM_m3_s2']
        assert len(p['actual']['images'])==2 and base['scientific_contract']['sampling']['time_evolution']=='none'
        proof['checks'].append(dict(name='real-catalog-unit-conversion-and-static-scientific-contract'))
        for name in ['observer-moved','lens-moved','source-moved']:
            assert values[name]['result']['point_lens']['geometry']['u']!=p['geometry']['u']
            assert values[name]['physics_sha256']!=base['physics_sha256']
        proof['checks'].append(dict(name='each-of-the-three-object-positions-changes-the-actual-geometry'))
        hidden=evaluate(controls=dict(gravity=dict(visible=False)))
        assert hidden['physics_sha256']==base['physics_sha256'] and hidden['result']==base['result']
        off=evaluate(controls=dict(gravity=dict(acting=False)))
        effect_off=evaluate(controls=dict(gravity=dict(effects=dict(ray_bending=False))))
        assert off['result']==effect_off['result'] and off['physics_sha256']==effect_off['physics_sha256']
        assert off['result']['point_lens']['actual']['magnification_total']==1 and off['result']['point_lens']['reference']==p['reference']
        proof['checks'].append(dict(name='visibility-does-not-change-science-and-actuation-retains-the-full-reference'))
        aligned=values['aligned'];assert aligned['result']['point_lens']['actual']['magnification_total'] is None
        assert aligned['result']['point_lens_message'] and aligned['result']['point_lens']['actual']['images']==[]
        direct=evaluate(dict(source_x_au=0),dict(gravity=dict(acting=False)))
        assert direct['result']['point_lens']['actual']['magnification_total']==1 and direct['result']['point_lens']['reference']['magnification_total'] is None
        proof['checks'].append(dict(name='aligned-ring-and-direct-intervention-serialize-with-explicit-limit-status'))
        saved=call('/api/forces/save',aligned['configuration']);assert saved['ok']
        loaded=call('/api/forces/load',{});assert loaded['configuration']==aligned['configuration'] and loaded['restoration']['status']=='same_generation'
        export=call('/api/forces/export',aligned['configuration']);export_path=Path(export['export_file'])
        assert export_path.is_relative_to(STAGE) and json.loads(export_path.read_text())['result']['point_lens']['actual']['magnification_total'] is None
        saved_path=STAGE/'user/forces/latest.json';protected_saved=sha(saved_path)
        for name,params in [('source-in-front',dict(source_z_kpc=2)),('coincident-lens',dict(lens_z_kpc=0)),
                            ('near-nonzero-caustic',dict(source_x_au=1e-8)),('outside-secondary-impact',dict(source_x_au=1e5))]:
            refuse(name,dict(scenario='point-lens',parameters=params))
        for name,request in [('unknown-parameter',dict(scenario='point-lens',parameters=dict(unknown=1))),
                             ('nonboolean',dict(scenario='point-lens',controls=dict(gravity=dict(acting='false')))),
                             ('invalid-numeric-type',dict(scenario='point-lens',parameters=dict(source_x_au=True))),
                             ('nonfinite',dict(scenario='point-lens',parameters=dict(source_x_au=float('nan'))))]:refuse(name,request)
        assert sha(saved_path)==protected_saved
        proof['checks'].append(dict(name='bad-geometry-types-and-controls-refused-with-existing-private-save-preserved',refusals=len(proof['refusals'])))
        legacy_names=['gravity','electromagnetic','strong','weak','relativity','timelike-orbits']
        code="import sys,json;sys.path.insert(0,sys.argv[1]);import forces;print(json.dumps({k:forces.evaluate({'scenario':k})['result'] for k in json.loads(sys.argv[2])},allow_nan=False))"
        old=subprocess.run([sys.executable,'-Xutf8','-c',code,str(PARENT/'app'),json.dumps(legacy_names)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
        reference=json.loads(old.stdout)
        for name in legacy_names:
            value=call('/api/forces/evaluate',dict(scenario=name));assert value['result']==reference[name],name
        proof['checks'].append(dict(name='six-existing-force-scenarios-retain-identical-scientific-results',scenarios=legacy_names))
        close('first');start('restart')
        loaded=call('/api/forces/load',{});assert loaded['configuration']==aligned['configuration'] and loaded['restoration']['status']=='same_generation'
        restored=call('/api/forces/evaluate',loaded['configuration']);assert restored['physics_sha256']==aligned['physics_sha256']
        close('restart');proof['checks'].append(dict(name='restart-restores-private-conditions-and-the-same-scientific-generation'))
        assert all(sha(ROOT/n)==s for n,s in sources.items())
        assert all(sha(ROOT/n)==s for n,s in protected.items())
        proof['export_sha256']=sha(export_path);proof.update(accepted=True,completed=True)
        for name,value in values.items():(FOLDER/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    except Exception:proof['failure']=traceback.format_exc()
    finally:
        if server and server.poll() is None:
            try:close('cleanup')
            except Exception:server.terminate();server.wait(timeout=10)
        OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:proof.get(k) for k in ['accepted','completed','checks','refusals','server_exits','failure']},ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
