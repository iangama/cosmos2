"""Exercise real pending-node removal using the dataset involved in the preserved crash."""
from pathlib import Path
import hashlib
import json
import time
import traceback
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    receipt=ROOT/'evidence/node-lifecycle-native-20261024a.json'
    if receipt.exists():raise FileExistsError('Preserve lifecycle test evidence.')
    built=ROOT/'evidence/built-runtime-node-lifecycle.json';build=json.loads(built.read_text(encoding='utf-8'))
    launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'));assert launch.get('nodeLifecycleCandidate')
    engine=Path(launch['runtime'])/'bin/OpenSpace.exe';assert sha(engine)==build['engine_sha256']
    source=ROOT/'output/body-field-previews/1c663122b9804ae4a35fe1cb3b687001'
    speck,names=source/'field_map_bin_0.speck',source/'field_map_bin_0.names';assert speck.is_file() and names.is_file()
    report={'schema':1,'accepted':False,'completed':False,'engine_sha256':sha(engine),'session':launch,
            'script_sha256':sha(Path(__file__)),'dataset_sha256':{'speck':sha(speck),'names':sha(names)},'cases':[]}
    try:
        with connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.2,ping_interval=None,max_size=4*1024*1024) as ws:
            ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}));topic=0
            def native(code):
                nonlocal topic
                topic+=1;ws.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True}}))
                reply=json.loads(ws.recv(timeout=180));assert reply.get('topic')==topic and '1' in reply.get('payload',{}),reply
                return reply['payload']['1']
            def node(identifier,parent='Root'):
                return 'openspace.addSceneGraphNode({Identifier='+json.dumps(identifier)+',Parent='+json.dumps(parent)+',Renderable={Type="RenderableConstellationLines",File='+json.dumps(speck.as_posix())+',NamesFile='+json.dumps(names.as_posix())+',Unit="m",Enabled=false}});'
            for case in ['immediate_leaf','immediate_parent_child']:
                identifier='NodeLifetimeProbe_'+case
                if case=='immediate_leaf':code=node(identifier)+'openspace.removeSceneGraphNode('+json.dumps(identifier)+');'
                else:
                    code='openspace.addSceneGraphNode({Identifier='+json.dumps(identifier)+',Parent="Root"});'+node(identifier+'_child',identifier)+'openspace.removeSceneGraphNode('+json.dumps(identifier)+');'
                began=time.perf_counter();answer=native(code+'return {exists=openspace.hasSceneGraphNode('+json.dumps(identifier)+')}')
                assert not answer['exists'];status=native('return openspace.cosmos2SceneInitialization()')
                assert not status['cpu_initializing']
                report['cases'].append({'case':case,'seconds':time.perf_counter()-began,'removed':True,'CPU_initialization_drained':True})
            native('openspace.cosmos2BeginFrameCapture(240);return {ok=true}')
            deadline=time.monotonic()+15
            while native('return openspace.cosmos2MemoryMetrics()')['capture_samples']<5:
                if time.monotonic()>deadline:raise TimeoutError('Engine did not render after removal.')
                time.sleep(.05)
            capture=native('return openspace.cosmos2EndFrameCapture()');assert capture['invalid_samples']==0
            report.update(accepted=True,completed=True,rendered_after_pending_removal=True,
                scope='Actual immediate removal of the heavy crash dataset, leaf and parent/child, then rendered frames. Stress stalls are not performance acceptance; full0.7 map replay and new runtime resource/visual profile pending.')
        assert sha(engine)==build['engine_sha256'] and all(sha(ROOT/name)==value for name,value in build['preserved_sha256'].items())
    except Exception:report['failure']=traceback.format_exc()
    receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'accepted':report['accepted'],'cases':len(report['cases']),'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
