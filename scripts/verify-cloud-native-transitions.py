"""Exercise rapid field cleanup and 256/10000 transitions after the observed exit."""
from pathlib import Path
import hashlib
import json
import time
import urllib.error
import urllib.request
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parents[1]
launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert launch['cloudCandidate'] and launch['runtimeVariant']=='cloud'
owner=ROOT/'user/sessions/latest.json';owner_bytes=owner.read_bytes()
pointer=ROOT/'output/c211-cloud-candidate/sessions/latest.json'
saved=pointer.read_bytes() if pointer.exists() else None
report={'status':'running','field_cleanup_cycles':[],'population_transitions':[],
    'scope':'Functional stability exercise, not a frame/memory performance profile; no assertion about the root cause of the earlier native exit.'}
receipt=ROOT/'evidence/cloud-native-transitions-check.json'
def persist():receipt.write_text(json.dumps(report,indent=2)+'\n')
def state():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/state',timeout=10))
def command(command_name,**args):
    req=urllib.request.Request('http://127.0.0.1:4700/api/command',data=json.dumps({'command':command_name,**args}).encode(),headers={'Content-Type':'application/json'})
    try:return json.load(urllib.request.urlopen(req,timeout=70))
    except urllib.error.HTTPError as e:raise RuntimeError(e.read().decode()) from e
def guard(p):return {k:p[k] for k in ('system_id','edit_token','revision')}|{'expected_time':p['time'],'frame':p['contract']['frame']}
def wait(predicate,timeout=30):
    deadline=time.perf_counter()+timeout
    while time.perf_counter()<deadline:
        s=state()
        if s['error']:raise RuntimeError(s['error'])
        if predicate(s):return s
        time.sleep(.05)
    raise TimeoutError('Transition did not reach the requested confirmed state')
ws=connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=1,ping_interval=None)
ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}));topic=0
def lua(code):
    global topic
    topic+=1;ws.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True}}))
    result=json.loads(ws.recv(timeout=20));assert result['topic']==topic,result
    return result.get('payload',{}).get('1')
def confirmed(s):
    p=s.get('physics');n=(s.get('cloud_view') or {}).get('native')
    return bool(p and n and n['gpu_buffer_uploaded'] and n['metadata']['time_model']==p['time'] and n['metadata']['edit_token']==p['edit_token'])
try:
    persist();command('enter');command('pause');command('reset',count=32);command('save')
    for cycle in range(6):
        p=state()['physics'];command('new_system',**guard(p),name='Limpeza de campo',mass_kg=1e30,position_m=[0,0,0],velocity_m_s=[0,0,0])
        p=state()['physics'];cfg=dict(p['field_layers']['settings']);cfg.update(shell_radius_m=3e9,cut_half_width_m=4e9,shell_count=128,cut_enabled=True,shell_enabled=True)
        command('configure_fields',**guard(p),fields_revision=p['field_layers']['revision'],settings=cfg)
        p=state()['physics'];command('sample_fields',**guard(p),fields_revision=p['field_layers']['revision'])
        render=state()['fields_preview']['render'];nodes=render['nodes'];meshes=render['meshes']
        assert len(meshes)>=3
        for visible in (False,True):
            command('set_fields_visible',visible=visible)
            result=lua('return {enabled={'+','.join('openspace.propertyValue('+json.dumps('Scene.'+m['node']+'.Renderable.Enabled')+')' for m in meshes)+'}}')['enabled']
            values=list(result.values()) if isinstance(result,dict) else result
            assert all(v==visible for v in values)
        lua('openspace.navigation.setNavigationState({Anchor='+json.dumps(render['frame_node'])+',ReferenceFrame="LabRoot",Position={0,-1e10,6e9},Up={0,0,1}});return {ready=true}')
        command('load')
        s=state();assert len(s['physics']['bodies'])==32 and s['fields_preview'] is None
        remaining=lua('return {remaining={'+','.join('openspace.hasSceneGraphNode('+json.dumps(n)+')' for n in nodes)+'}}')['remaining']
        values=list(remaining.values()) if isinstance(remaining,dict) else remaining
        assert not any(values)
        report['field_cleanup_cycles'].append({'cycle':cycle+1,'map_meshes':len(meshes),'all_nodes_removed':True,'restored_32_bodies':True})
        persist();print('field cleanup '+str(cycle+1)+'/6',flush=True)
    for cycle in range(2):
        command('reset',count=256);p=state()['physics'];assert len(p['bodies'])==256
        command('rate',value=1);command('resume');wait(lambda s:s['physics']['time']>.3);command('pause')
        command('load_cloud_experiment',**guard(state()['physics']),parameters={'count':10000});wait(confirmed)
        command('resume');wait(lambda s:s['physics']['time']>.3);command('pause');s=wait(confirmed)
        assert s['physics']['test_particle_cloud']['test_particles']==10000
        assert lua('return {count=openspace.propertyValue("Scene.C2CloudStream.Renderable.NumberOfDataPoints")}')['count']==10000
        command('atlas');assert lua('return {cloud=openspace.hasSceneGraphNode("C2CloudStream")}')['cloud'] is False
        command('enter');wait(confirmed)
        command('reset',count=256);p=state()['physics'];assert len(p['bodies'])==256 and p['test_particle_cloud'] is None
        assert lua('return {cloud=openspace.hasSceneGraphNode("C2CloudStream")}')['cloud'] is False
        command('resume');start=p['time'];wait(lambda s:s['physics']['time']>start+.3);command('pause')
        report['population_transitions'].append({'cycle':cycle+1,'route':'256 evolving -> 10000 confirmed evolving -> Atlas -> 10000 reentered -> 256 evolving','passed':True})
        persist();print('population transition '+str(cycle+1)+'/2',flush=True)
    command('atlas')
    report.update(status='six_field_cleanup_and_two_population_transition_cycles_verified',owner_pointer_preserved=owner.read_bytes()==owner_bytes,
        owner_pointer_sha256=hashlib.sha256(owner_bytes).hexdigest(),native_alive_after_all_cycles=True)
except BaseException as error:
    report.update(status='failed',error=repr(error));raise
finally:
    ws.close()
    if saved is not None:pointer.write_bytes(saved)
    else:pointer.unlink(missing_ok=True)
    report['owner_pointer_preserved']=owner.read_bytes()==owner_bytes
    persist();assert report['owner_pointer_preserved']
print(json.dumps(report,indent=2),flush=True)
