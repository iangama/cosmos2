"""Request normal shutdown with the original heavy node's CPU initialization pending."""
from pathlib import Path
import hashlib
import json
import shutil
import time
import traceback
import psutil
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    receipt=ROOT/'evidence/node-lifecycle-v2-shutdown-20261024a.json'
    folder=ROOT/'output/node-lifecycle-v2-shutdown-20261024a'
    if receipt.exists() or folder.exists():raise FileExistsError('Preserve shutdown evidence.')
    folder.mkdir()
    launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert launch.get('nodeLifecycleV2Candidate')
    build=json.loads((ROOT/'evidence/built-runtime-node-lifecycle-v2.json').read_text(encoding='utf-8'))
    runtime=Path(launch['runtime']);engine=runtime/'bin/OpenSpace.exe'
    assert sha(engine)==build['engine_sha256']
    process=psutil.Process(launch['app']);started=process.create_time()
    assert Path(process.exe()).resolve()==engine.resolve()
    dumps=lambda:{str(p):sha(p) for p in [*runtime.glob('*.dmp'),*ROOT.glob('*.dmp')]}
    before=dumps();report={'schema':1,'completed':False,'accepted':False,'session':launch,
        'script_sha256':sha(Path(__file__)),'engine_sha256':sha(engine),'dumps_before':before}
    try:
        source=ROOT/'output/body-field-previews/1c663122b9804ae4a35fe1cb3b687001'
        parent='NodeLifetimeShutdownProbe';child=parent+'_child'
        code='openspace.addSceneGraphNode({Identifier='+json.dumps(parent)+',Parent="Root"});'
        code+='openspace.addSceneGraphNode({Identifier='+json.dumps(child)+',Parent='+json.dumps(parent)+',Renderable={Type="RenderableConstellationLines",File='+json.dumps((source/'field_map_bin_0.speck').as_posix())+',NamesFile='+json.dumps((source/'field_map_bin_0.names').as_posix())+',Unit="m",Enabled=false}});'
        code+='local s=openspace.cosmos2SceneInitialization(); openspace.toggleShutdown();return {pending_at_shutdown_request=s.cpu_initializing,requested=true}'
        began=time.perf_counter()
        with connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.2,ping_interval=None) as ws:
            ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
            ws.send(json.dumps({'topic':1,'type':'luascript','payload':{'script':code,'return':True}}))
            reply=json.loads(ws.recv(timeout=180));answer=reply['payload']['1']
            assert answer['pending_at_shutdown_request'] and answer['requested'],reply
            report['request']=answer
            receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        code=process.wait(timeout=240)
        report.update(engine_exit_code=code,seconds=time.perf_counter()-began)
        assert code==0,code
        deadline=time.monotonic()+15
        while psutil.pid_exists(launch['server']):
            if time.monotonic()>deadline:raise TimeoutError('Launcher did not close candidate server.')
            time.sleep(.1)
        after=dumps();assert after==before
        for name in ['engine.log','engine-errors.log','server.log','server-errors.log','bootstrap-ui.log','session.json']:
            path=ROOT/'output'/name
            if path.exists():shutil.copy2(path,folder/name)
        assert all(sha(ROOT/name)==value for name,value in build['preserved_sha256'].items())
        report.update(completed=True,accepted=True,dumps_after=after,
            logs_sha256={p.name:sha(p) for p in folder.iterdir() if p.is_file()},
            scope='Normal shutdown requested with real heavy child CPU work pending; engine exit0, launcher/server cleanup and no new dump. Does not establish CPU still pending at destructor entry; dedicated map visual/performance acceptance separate.')
    except Exception:report['failure']=traceback.format_exc()
    receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'accepted':report['accepted'],'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
