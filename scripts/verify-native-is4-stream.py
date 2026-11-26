"""Real worker to own normalized native trajectory receiver; live upload/draw/guards."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import subprocess
import sys
import time
import traceback
import zipfile
from importlib.machinery import SourceFileLoader
import numpy as np
from PIL import Image
from websockets.sync.client import connect
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/is4-body-particle-staging';APP=ROOT/'output/is3-body-points-product/app'
sys.path[:0]=[str(STAGE),str(APP)]
from is4_stream_scene import Stream,lua
import is4_trajectory_transport as wire
from cloud_transport import publish as atomic_publish
helpers=SourceFileLoader('is4_stream_worker_helpers',str(ROOT/'scripts/verify-is4-worker.py')).load_module()
h=SourceFileLoader('is4_stream_solar_helpers',str(ROOT/'scripts/verify-native-solar-tide.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
phase=lambda p:{k:copy.deepcopy(p[k]) for k in ['system_id','time','revision','bodies','interventions','atlas_initial']}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/('output/is4-native-stream-'+args.label);receipt=ROOT/('evidence/is4-native-stream-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve native stream evidence')
    launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'));assert launch.get('is4StreamHostCandidate')
    build=json.loads((ROOT/'evidence/built-runtime-is4-stream.json').read_text(encoding='utf-8'));assert sha(Path(launch['runtime'])/'bin/OpenSpace.exe')==build['engine_sha256']
    folder.mkdir();files=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]+[*STAGE.glob('*.py'),STAGE/'constants.json',Path(__file__),ROOT/'scripts/cef_page.py',ROOT/'IS-4-TRANSPORTE-NATIVO-CONTRATO.md']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files};owner=sha(ROOT/'user/sessions/latest.json')
    storage=ROOT/'output/is3-body-points-product/gravity-sessions';saved={str(p):sha(p) for p in storage.rglob('*') if p.is_file()}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    report={'schema':1,'accepted':False,'completed':False,'session':launch,'source_sha256':hashes,'cases':[],'captures':[]}
    def persist():receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    persist();client=None;stream=None;hidden={};original_camera=None;topic=0
    try:
        with connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.2,ping_interval=None,max_size=8*1024*1024) as ws:
            ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
            def native(code):
                nonlocal topic
                topic+=1;ws.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True}}))
                reply=json.loads(ws.recv(timeout=30));assert reply.get('topic')==topic and '1' in reply.get('payload',{}),reply
                return reply['payload']['1']
            def ready():
                deadline=time.monotonic()+30
                while native('return openspace.cosmos2SceneInitialization()')['cpu_initializing']:
                    if time.monotonic()>deadline:raise TimeoutError('CPU initialization')
                    time.sleep(.02)
                native('openspace.cosmos2BeginFrameCapture(240);return {ok=true}')
                while native('return openspace.cosmos2MemoryMetrics()')['capture_samples']<10:
                    if time.monotonic()>deadline:raise TimeoutError('No later rendered frames')
                    time.sleep(.02)
                value=native('return openspace.cosmos2EndFrameCapture()');assert value['invalid_samples']==0
            def settled(state):
                deadline=time.monotonic()+10
                while True:
                    stream.update(state);status=stream.poll()
                    confirmed=stream.confirmed
                    if confirmed and stream.pending is None and confirmed['scientific_state']['experiment']['phase']==state['experiment']['phase'] and confirmed['metadata']['revision']==state['experiment']['revision']:
                        ready();status=stream.poll()
                        assert status['draw_submitted_sequence']==confirmed['metadata']['sequence'],status
                        return status
                    if time.monotonic()>deadline:raise TimeoutError('Trajectory did not confirm latest paused phase')
                    time.sleep(.02)
            with Page() as page:
                page.goto('http://127.0.0.1:4700/');page.wait_for_function('appState!==null&&!pending')
                if page.evaluate('appState.mode==="experiment"'):h.click(page,'#atlas')
                page.wait_for_function('appState?.mode==="atlas"&&!pending')
                atlas=h.get('/api/atlas/state');h.click(page,'#copy-solar');page.wait_for_function('appState?.physics?.bodies.length===4&&!pending',timeout=70000)
                frozen=phase(h.get('/api/state')['physics']);constants=json.loads((STAGE/'constants.json').read_text(encoding='utf-8'))
                for target,kind in [('399','proton'),('599','electron')]:
                    p=h.get('/api/state')['physics'];assert p['paused'];body=next(b for b in p['bodies'] if b['reference_id']=='sol:naif:'+target)
                    request={k:p[k] for k in ['system_id','edit_token','revision']}|{'frame':p['contract']['frame'],'expected_time':p['time'],'body_id':body['id'],'command':'show_body_field','representation':'vector','model':'IGRF14' if target=='399' else 'JRM33'}
                    request|=({'latitude_deg':-23.55,'longitude_deg':-46.63,'altitude_m':1000.} if target=='399' else {'radius_m':1.5*71492000.,'latitude_deg':30.,'east_longitude_deg':90.,'degree':13})
                    h.post('/api/command',request);state=h.get('/api/state');p=state['physics'];layer=state['body_field_preview'];r=layer['reading']
                    ready();original_camera=native('return {navigation=openspace.navigation.getNavigationState("Root")}')['navigation']
                    names=['LabGrid','LabBarycenter','LabProbe']+[b[key] for b in p['bodies'] for key in ['scene_node','label_node','spin_node','shape_node']]+[m['node'] for m in layer['render']['meshes']]+[layer['render']['label_node']]
                    hidden=native('local f={};for _,n in ipairs('+lua(names)+') do local ok,v=pcall(openspace.propertyValue,"Scene."..n..".Renderable.Enabled");if ok and type(v)=="boolean" then f[n]=v;openspace.setPropertyValueSingle("Scene."..n..".Renderable.Enabled",false) end end;return {flags=f}')['flags']
                    field=np.array(r['field_ITRF93_T' if target=='399' else 'field_SystemIII_T']);direction=field/np.linalg.norm(field)
                    axis=np.eye(3)[int(np.argmin(abs(direction)))];side=np.cross(direction,axis);side/=np.linalg.norm(side)
                    speed=1e5 if kind=='proton' else 1e6;velocity=speed*(math.sin(math.pi/3)*side+math.cos(math.pi/3)*direction)
                    mass=constants['proton_mass_kg' if kind=='proton' else 'electron_mass_kg']['value'];q=constants['elementary_charge_C']['value']*(1 if kind=='proton' else -1)
                    period=2*math.pi/(abs(q/mass)*np.linalg.norm(field));unit=float(speed*math.sin(math.pi/3)/(abs(q/mass)*np.linalg.norm(field)))
                    params={'charge_C':float(q),'mass_kg':mass,'dt_s':float(period/800),'initial_position_m':r['point_ITRF93_m' if target=='399' else 'point_SystemIII_m'],'initial_velocity_m_s':velocity.tolist()}
                    (folder/(target+'-input.json')).write_text(json.dumps({'phase':p,'reading':r,'parameters':params},indent=2)+'\n',encoding='utf-8')
                    client=helpers.Client(folder/(target+'-storage'),folder,'worker-'+target)
                    client.call('create',{'source_phase':p,'source_reading':r,'parameters':params,'controls':{'electric':True,'magnetic':True,'gravity':True}})
                    stream=Stream(native,folder/(target+'-view'),unit,field.tolist());stream.attach(client.last);ready();stream.poll();stream.frame_camera();settled(client.last)
                    assert stream.confirmed['metadata']['count']==1
                    client.advance(1000);settled(client.last);stream.frame_camera();ready()
                    assert stream.confirmed['metadata']['count']==129
                    client.call('set_rate',{'value':params['dt_s']*200});client.call('resume')
                    samples=[];deadline=time.monotonic()+1.2
                    while time.monotonic()<deadline:
                        client.receive(lambda value:value.get('type')=='snapshot',1.)
                        stream.update(client.last);status=stream.poll()
                        samples.append({'worker_sequence':client.last['sequence'],'step':client.last['experiment']['step_index'],'native':copy.deepcopy(status)})
                    client.call('pause');settled(client.last)
                    assert client.last['experiment']['step_index']>1100 and len({s['native'].get('metadata',{}).get('sequence') for s in samples if s['native'].get('state')=='accepted'})>=5
                    baseline=copy.deepcopy(client.last['experiment']['phase']);stream.set_visible(False);client.advance(25)
                    assert client.last['experiment']['phase']!=baseline
                    stream.set_visible(True);settled(client.last)
                    physical=copy.deepcopy(client.last['experiment']['phase']);client.call('set_controls',{'controls':{'electric':True,'magnetic':True,'gravity':False}})
                    settled(client.last);assert physical==client.last['experiment']['phase']
                    good,record=wire.encode(client.last,unit,field.tolist());m=record['metadata'];count=0
                    native_before=stream.latest_native['metadata']['sequence']
                    for bad in [good[:-1]+bytes([good[-1]^1]),b'X'+good[1:],good]:
                        atomic_publish(stream.path,bad);ready();status=native('return {status=openspace.propertyValue("Scene.'+stream.trail+'.Renderable.ConfirmedTrajectoryStatus")}')
                        status=json.loads(status['status'])
                        assert status['state']=='rejected' and status['last_accepted_sequence']==native_before and status['previous_buffer_preserved'],status
                        count+=1
                    # Advance publication identity (same valid particle phase) after negative probes.
                    client.call('state');recovery,rr=wire.encode(client.last,unit,field.tolist());atomic_publish(stream.path,recovery)
                    stream.pending=rr;stream.last_phase=(copy.deepcopy(client.last['experiment']['phase']),client.last['experiment']['revision']);settled(client.last)
                    client.call('save');saved_phase=copy.deepcopy(client.last['experiment']['phase']);client.advance(77);future=copy.deepcopy(client.last['experiment']['phase']);settled(client.last)
                    client.call('load');assert client.last['experiment']['phase']==saved_phase
                    try:stream.update(client.last)
                    except ValueError:count+=1
                    else:raise AssertionError('Load accepted old render binding')
                    stream.close();stream=Stream(native,folder/(target+'-rebound-view'),unit,field.tolist());stream.attach(client.last);ready();stream.poll();stream.frame_camera();settled(client.last)
                    client.advance(77);settled(client.last);assert client.last['experiment']['phase']==future
                    caption={'target':target,'kind':kind,'time_s':future['time_s'],'unit_m':unit,'sequence':stream.confirmed['metadata']['sequence'],'count':stream.confirmed['metadata']['count']}
                    page.evaluate('(() => {let s=document.createElement("style");s.id="is4-proof-style";s.textContent="#lab-panel,#lab-details{display:none!important}#is4-proof{position:fixed;left:28px;top:116px;width:300px;padding:20px;z-index:900;background:rgba(7,20,31,.94);border:1px solid #31556b;border-radius:16px;color:#cbe7ed;font:14px/1.55 sans-serif}#is4-proof h2{font-size:21px;margin:0 0 12px}";document.head.append(s);let p=document.createElement("section");p.id="is4-proof";document.body.append(p);})()')
                    page.evaluate('(() => {const v='+json.dumps(caption)+';const p=document.getElementById("is4-proof");for(const text of ["Trajetória ampliada · "+(v.target==="399"?"Terra / próton":"Júpiter / elétron"),"Worker ao vivo validado; captura pausada", "Tempo próprio: "+v.time_s.toExponential(6)+" s","1 unidade local = "+v.unit_m.toPrecision(6)+" m",v.count+" amostras reais; linha e marcador no mesmo buffer","Upload GPU e desenho submetido: sequência "+v.sequence,"E=0 prescrito; B ativo; gravidade desligada nesta captura","Época, eixos e quatro centros congelados. Relógio orbital não avança."]){let e=document.createElement("p");e.textContent=text;p.append(e);}})()')
                    for scale in ['1','1.5']:
                        page.locator('#ui-scale').select_option(scale);ready();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                        name='cosmos2-is4-stream-'+args.label+'-'+target+'-'+str(int(float(scale)*100))+'.png'
                        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',name],check=True,capture_output=True)
                        pixels=np.array(Image.open(ROOT/'evidence'/name).convert('RGB')).astype(int)
                        region=pixels[200:950,600:];cyan=(region[:,:,0]<140)&(region[:,:,1]>170)&(region[:,:,2]>190)&(region[:,:,2]-region[:,:,0]>70)
                        assert cyan.sum()>200
                        report['captures'].append({'path':'evidence/'+name,'sha256':sha(ROOT/'evidence'/name),'scene_cyan_pixels':int(cyan.sum())})
                    page.locator('#ui-scale').select_option('1');page.evaluate('document.getElementById("is4-proof")?.remove();document.getElementById("is4-proof-style")?.remove()')
                    report['cases'].append({'target':target,'kind':kind,'live_samples':samples,'native_refusals_and_rebind_guard':count,'saved_future_exact_after_rebind':True,'one_and_129_samples':True,'final_native':stream.latest_native})
                    stream.close();stream=None;client.close();client=None
                    native('openspace.navigation.setNavigationState('+lua(original_camera)+');return {ok=true}');original_camera=None
                    native('local f='+lua(hidden)+';for n,v in pairs(f) do openspace.setPropertyValueSingle("Scene."..n..".Renderable.Enabled",v) end;return {ok=true}');hidden={}
                    assert phase(h.get('/api/state')['physics'])==frozen;persist()
                h.click(page,'#atlas');after=h.get('/api/atlas/state');assert after['epoch']==atlas['epoch'] and after['bodies']==atlas['bodies']
        assert all(sha(ROOT/n)==v for n,v in hashes.items()) and sha(ROOT/'user/sessions/latest.json')==owner
        assert all(sha(Path(n))==v for n,v in saved.items())
        report.update(accepted=True,completed=True,scope='Real live worker/normalized own-protocol native line and endpoint sharing VBO, upload and draw-submission receipts, corrupted/stale refusal with prior buffer, visibility/physical controls, exact saved future after rebind and captures100/150. Image review/product UI/profile remain separate.')
    except Exception:report['failure']=traceback.format_exc()
    finally:
        if client is not None:client.close()
        if stream or hidden or original_camera:
            try:
                with connect('ws://127.0.0.1:4682',open_timeout=3,close_timeout=.2,ping_interval=None) as cleanup:
                    cleanup.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
                    serial=0
                    def clean(code):
                        nonlocal serial
                        serial+=1;cleanup.send(json.dumps({'topic':serial,'type':'luascript','payload':{'script':code,'return':True}}));return json.loads(cleanup.recv(timeout=30))['payload']['1']
                    if stream:stream.native=clean;stream.close()
                    if original_camera:clean('openspace.navigation.setNavigationState('+lua(original_camera)+');return {ok=true}')
                    clean('local f='+lua(hidden)+';for n,v in pairs(f) do pcall(openspace.setPropertyValueSingle,"Scene."..n..".Renderable.Enabled",v) end;return {ok=true}')
            except Exception:report['cleanup_failure']=traceback.format_exc()
        try:
            with Page() as page:page.evaluate('document.getElementById("is4-proof")?.remove();document.getElementById("is4-proof-style")?.remove()')
        except Exception:pass
        persist()
    print(json.dumps({'accepted':report['accepted'],'cases':len(report['cases']),'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
