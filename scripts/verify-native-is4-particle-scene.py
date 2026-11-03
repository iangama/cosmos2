"""Paused magnified particle scenes on an unchanged0.7.1 host, with local/world readback."""
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
from websockets.sync.client import connect
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/is4-body-particle-staging';APP=ROOT/'output/is3-body-points-product/app'
sys.path[:0]=[str(STAGE),str(APP)]
from is4_particle_scene import prepare
helpers=SourceFileLoader('is4_native_worker_helpers',str(ROOT/'scripts/verify-is4-worker.py')).load_module()
h=SourceFileLoader('is4_native_solar_helpers',str(ROOT/'scripts/verify-native-solar-tide.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
phase=lambda p:{k:copy.deepcopy(p[k]) for k in ['system_id','time','revision','bodies','interventions','atlas_initial']}

def lua(value):
    if value is None:return 'nil'
    if type(value) is bool:return 'true' if value else 'false'
    if type(value) in (int,float):
        if not math.isfinite(value):raise ValueError('Finite Lua number required')
        return format(value,'.17g')
    if isinstance(value,str):return json.dumps(value,ensure_ascii=True)
    if isinstance(value,list):return '{'+','.join(lua(v) for v in value)+'}'
    if isinstance(value,dict):return '{'+','.join('['+lua(k)+']='+lua(v) for k,v in value.items())+'}'
    raise ValueError('Unsupported Lua value')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    folder=ROOT/('output/is4-native-particle-scene-'+args.label);receipt=ROOT/('evidence/is4-native-particle-scene-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve native geometry evidence.')
    launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'));assert launch.get('is4GeometryHostCandidate')
    assert json.loads((ROOT/'evidence/is4-particle-scene-20261025a.json').read_text(encoding='utf-8'))['accepted']
    build=json.loads((ROOT/'evidence/built-runtime-node-lifecycle-v2.json').read_text(encoding='utf-8'));assert sha(Path(launch['runtime'])/'bin/OpenSpace.exe')==build['engine_sha256']
    folder.mkdir();files=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]+[*STAGE.glob('*.py'),STAGE/'constants.json',Path(__file__),ROOT/'scripts/cef_page.py',ROOT/'IS-4-VISTA-AMPLIADA-CONTRATO.md']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files};owner=sha(ROOT/'user/sessions/latest.json')
    prior_storage=ROOT/'output/is3-body-points-product/gravity-sessions';saved={str(p):sha(p) for p in prior_storage.rglob('*') if p.is_file()}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    report={'schema':1,'accepted':False,'completed':False,'session':launch,'source_sha256':hashes,'cases':[],'captures':[]}
    def persist():receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    persist();client=None;active_frame=None;hidden={};original_camera=None;topic=0
    try:
        with connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.2,ping_interval=None,max_size=8*1024*1024) as ws:
            ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
            def native(code):
                nonlocal topic
                topic+=1;ws.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True}}))
                reply=json.loads(ws.recv(timeout=30));assert reply.get('topic')==topic and '1' in reply.get('payload',{}),reply;return reply['payload']['1']
            def ready():
                deadline=time.monotonic()+30
                while native('return openspace.cosmos2SceneInitialization()')['cpu_initializing']:
                    if time.monotonic()>deadline:raise TimeoutError('Scene CPU initialization did not drain')
                    time.sleep(.05)
                native('openspace.cosmos2BeginFrameCapture(240);return {ok=true}')
                while native('return openspace.cosmos2MemoryMetrics()')['capture_samples']<10:
                    if time.monotonic()>deadline:raise TimeoutError('No rendered frames after CPU idle')
                    time.sleep(.05)
                capture=native('return openspace.cosmos2EndFrameCapture()');assert capture['invalid_samples']==0
            with Page() as page:
                page.goto('http://127.0.0.1:4700/');page.wait_for_function('appState?.mode==="atlas"&&!pending')
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
                    period=2*math.pi/(abs(q/mass)*np.linalg.norm(field));unit=speed*math.sin(math.pi/3)/(abs(q/mass)*np.linalg.norm(field))
                    params={'charge_C':float(q),'mass_kg':mass,'dt_s':float(period/800),'initial_position_m':r['point_ITRF93_m' if target=='399' else 'point_SystemIII_m'],'initial_velocity_m_s':velocity.tolist()}
                    input_path=folder/(target+'-input.json');input_path.write_text(json.dumps({'phase':p,'reading':r,'parameters':params},indent=2)+'\n',encoding='utf-8')
                    client=helpers.Client(folder/(target+'-worker-storage'),folder,'worker-'+target)
                    client.call('create',{'source_phase':p,'source_reading':r,'parameters':params,'controls':{'electric':True,'magnetic':True,'gravity':True}});client.advance(1000)
                    packet=copy.deepcopy(client.last);code,built=prepare(packet,float(unit),field.tolist());g=built['geometry'];render=built['render'];active_frame=render['frame_node']
                    confirmed=native(code);assert confirmed['ready'] and confirmed['sequence']==packet['sequence']
                    basis=[]
                    for index in range(3):
                        name=active_frame+'_basis_'+str(index);vector=[0.,0.,0.];vector[index]=1.;basis.append(name)
                        native('openspace.addSceneGraphNode({Identifier='+json.dumps(name)+',Parent='+json.dumps(active_frame)+',Transform={Translation={Type="StaticTranslation",Position={'+','.join(str(v) for v in vector)+'}}}});return {ok=true}')
                    ready()
                    answer=native('return {marker=openspace.worldPosition('+json.dumps(render['marker_node'])+'),frame=openspace.worldPosition('+json.dumps(active_frame)+'),basis={'+','.join('openspace.worldPosition('+json.dumps(name)+')' for name in basis)+'},local_marker=openspace.propertyValue("Scene.'+render['marker_node']+'.Translation.Position")}')
                    matrix=np.array(g['model_to_render']);frame=np.array(answer['frame']);world=np.array(answer['marker'])
                    reconstructed=matrix.T@(world-frame)/g['graphic_unit_m']*unit
                    world_error=float(np.linalg.norm(reconstructed-packet['experiment']['phase']['position_offset_m']))
                    assert world_error<=g['adopted_total_error_bound_m'],('world_marker',world_error,g['adopted_total_error_bound_m'])
                    answer_path=folder/(target+'-native-readback.json');answer_path.write_text(json.dumps(answer,indent=2)+'\n',encoding='utf-8')
                    bases=answer['basis']
                    if isinstance(bases,dict):
                        assert set(bases)=={'1','2','3'},bases
                        bases=[bases[str(i)] for i in range(1,4)]
                    native_basis=(np.array(bases)-frame).T/g['graphic_unit_m']
                    assert np.max(abs(native_basis-matrix))*unit<=g['adopted_total_error_bound_m']
                    assert np.max(abs(np.array(answer['local_marker'])-g['marker_normalized']))<=2e-12*max(1.,float(np.linalg.norm(g['marker_normalized'])))
                    caption={'title':'Carga de teste no campo da '+('Terra' if target=='399' else 'Júpiter'),'model':g['model'],'degree':g['degree'],
                        'epoch':g['source_epoch']['utc'],'time':packet['experiment']['phase']['time_s'],'unit':float(unit),
                        'offset':packet['experiment']['phase']['position_offset_m'],'samples':len(g['vertices_normalized'])}
                    page.evaluate('(() => {let s=document.createElement("style");s.id="is4-proof-style";s.textContent="#lab-panel,#lab-details{display:none!important} #is4-proof{position:fixed;left:28px;top:116px;width:300px;padding:20px;z-index:900;background:rgba(7,20,31,.94);border:1px solid #31556b;border-radius:16px;color:#cbe7ed;font:14px/1.55 sans-serif}#is4-proof h2{font-size:21px;color:#f1f7fb;margin:0 0 12px}";document.head.append(s);let p=document.createElement("section");p.id="is4-proof";document.body.append(p);})()')
                    page.evaluate('(() => {const v='+json.dumps(caption,ensure_ascii=True)+';let p=document.getElementById("is4-proof");const h=document.createElement("h2");h.textContent=v.title;p.append(h);for(const text of ["Trajetória pausada • vista ampliada",v.model+" · grau "+v.degree,"Época do campo: "+v.epoch,"Tempo da partícula: "+(v.time*1e6).toPrecision(6)+" µs","1 unidade local = "+v.unit.toPrecision(6)+" m", "Deslocamento em m: "+v.offset.map(x=>x.toExponential(4)).join(" / "),v.samples+" amostras reais da trajetória recente","E = 0 prescrito • B e gravidade ativos","Origem no lançamento; eixos do modelo congelados. A esfera é um marcador gráfico."]){const e=document.createElement("p");e.textContent=text;p.append(e);}})()')
                    for scale in ['1','1.5']:
                        page.locator('#ui-scale').select_option(scale);ready();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                        view=native('return {camera=openspace.navigation.getNavigationState("Root"),marker=openspace.worldPosition('+json.dumps(render['marker_node'])+'),enabled=openspace.propertyValue("Scene.'+render['trajectory_node']+'.Renderable.Enabled")}')
                        name='cosmos2-is4-paused-'+args.label+'-'+target+'-'+str(int(float(scale)*100))+'.png'
                        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',name],check=True,capture_output=True)
                        from PIL import Image
                        pixels=np.array(Image.open(ROOT/'evidence'/name).convert('RGB')).astype(int)
                        cyan=(pixels[:,:,0]<170)&(pixels[:,:,1]>150)&(pixels[:,:,2]>170)&(pixels[:,:,2]-pixels[:,:,0]>70)
                        cyan[:,:int(pixels.shape[1]*.3)]=False
                        report['captures'].append({'path':'evidence/'+name,'sha256':sha(ROOT/'evidence'/name),'native_view':view,'scene_cyan_pixels':int(cyan.sum())})
                        persist()
                        assert cyan.sum()>100,('Trajectory absent from capture',scale,int(cyan.sum()))
                    page.locator('#ui-scale').select_option('1');page.evaluate('document.getElementById("is4-proof")?.remove();document.getElementById("is4-proof-style")?.remove()')
                    native('openspace.navigation.setNavigationState('+lua(original_camera)+');return {ok=true}');original_camera=None
                    native('openspace.removeSceneGraphNode('+json.dumps(active_frame)+');return {ok=true}');active_frame=None
                    native('local f='+lua(hidden)+';for n,v in pairs(f) do openspace.setPropertyValueSingle("Scene."..n..".Renderable.Enabled",v) end;return {ok=true}');hidden={}
                    assert phase(h.get('/api/state')['physics'])==frozen
                    report['cases'].append({'target':target,'kind':kind,'time_s':caption['time'],'physical_unit_m':float(unit),'packet_sequence':packet['sequence'],
                        'geometry_receipt':render['receipt'],'geometry_sha256':render['receipt_sha256'],'native_world_marker_error_m':world_error,
                        'adopted_geometry_bound_m':g['adopted_total_error_bound_m'],'local_marker_and_native_basis_confirmed':True,'CPU_idle_and_later_frames':True})
                    client.close();client=None;persist()
                h.click(page,'#atlas');after=h.get('/api/atlas/state');assert after['epoch']==atlas['epoch'] and after['bodies']==atlas['bodies']
        assert all(sha(ROOT/name)==value for name,value in hashes.items()) and sha(ROOT/'user/sessions/latest.json')==owner
        assert all(sha(Path(name))==value for name,value in saved.items())
        report.update(accepted=True,completed=True,scope='Paused native magnified particle/trail geometry, normalized marker and world-frame/basis readback, CPU-idle plus later rendered frames,100/150 captures and host phase/visibility/camera cleanup. Image review, live transport/GPU phase confirmation, product UI and performance remain separate.')
    except Exception:report['failure']=traceback.format_exc()
    finally:
        if client is not None:
            try:client.close()
            except Exception:
                if client.process.poll() is None:client.process.terminate();client.process.wait(timeout=5)
        if active_frame or hidden or original_camera:
            try:
                with connect('ws://127.0.0.1:4682',open_timeout=3,close_timeout=.2,ping_interval=None) as cleanup:
                    cleanup.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
                    code=('openspace.navigation.setNavigationState('+lua(original_camera)+');' if original_camera else '')
                    if active_frame:code+='if openspace.hasSceneGraphNode('+json.dumps(active_frame)+') then openspace.removeSceneGraphNode('+json.dumps(active_frame)+') end;'
                    code+='local f='+lua(hidden)+';for n,v in pairs(f) do pcall(openspace.setPropertyValueSingle,"Scene."..n..".Renderable.Enabled",v) end;return {ok=true}'
                    cleanup.send(json.dumps({'topic':1,'type':'luascript','payload':{'script':code,'return':True}}));cleanup.recv(timeout=30)
            except Exception:pass
        try:
            with Page() as cleanup_page:cleanup_page.evaluate('document.getElementById("is4-proof")?.remove();document.getElementById("is4-proof-style")?.remove()')
        except Exception:pass
        persist()
    print(json.dumps({'accepted':report['accepted'],'cases':len(report['cases']),'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
