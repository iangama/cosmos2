"""Isolated particle actor, native connection and own checkpoints; source clock stays frozen."""
from pathlib import Path
from concurrent.futures import Future
import copy
import hashlib
import json
import math
import queue
import threading
import time
import uuid
import numpy as np
from websockets.sync.client import connect
from is4_client import Client
from is4_stream_scene import Stream,lua
from is4_values import scalar
from is4_experiment import Experiment
from is4_body_snapshot import digest
from is4_product_store import Store

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
HERE=Path(__file__).resolve().parent
STORAGE=HERE.parent/'particle-sessions'
CONSTANTS=json.loads((HERE/'constants.json').read_text(encoding='utf-8'))


class ParticleLaboratory:
    def __init__(self,lab):
        self.lab=lab;self.actions=queue.Queue(maxsize=16);self.lock=threading.Lock();self.public={'active':False,'busy':False,'error':None}
        self.client=None;self.stream=None;self.engine=None;self.topic=0;self.hidden={};self.camera=None;self.sample=None;self.error=None;self.closing=False;self.native_failure_since=None
        self.store=Store(HERE.parent/'particle-checkpoints');self.branches=self.store.catalog();self.branch_parent=None
        self.thread=threading.Thread(target=self._run,daemon=True);self.thread.start()

    def status(self):
        with self.lock:return copy.deepcopy(self.public)

    def command(self,request):
        if not isinstance(request,dict):raise ValueError('Comando de partícula deve ser um objeto.')
        future=Future()
        try:self.actions.put_nowait((copy.deepcopy(request),future))
        except queue.Full:raise ValueError('Aguarde os comandos de partícula em andamento.')
        return future.result(timeout=35)

    def _native(self,code):
        try:
            if self.engine is None:
                self.engine=connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.2,ping_interval=None,max_size=4*1024*1024)
                self.engine.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
            self.topic+=1;self.engine.send(json.dumps({'topic':self.topic,'type':'luascript','payload':{'script':code,'return':True}}))
            answer=json.loads(self.engine.recv(timeout=10))
            if answer.get('topic')!=self.topic or '1' not in answer.get('payload',{}):raise RuntimeError('Motor não confirmou a cena da partícula.')
            return answer['payload']['1']
        except Exception:
            if self.engine:self.engine.close();self.engine=None
            raise

    def _view(self,state,unit,field,visible=True):
        if self.stream:self.stream.close();self.stream=None
        folder=HERE.parent/'particle-previews'/uuid.uuid4().hex
        stream=Stream(self._native,folder,unit,field)
        stream.visible=visible
        try:
            stream.attach(state);deadline=time.monotonic()+15
            while True:
                initializing=self._native('return openspace.cosmos2SceneInitialization()')['cpu_initializing']
                if not initializing:
                    status=stream.poll()
                    if stream.confirmed:break
                if time.monotonic()>deadline:raise TimeoutError('Motor não confirmou a trajetória no prazo.')
                time.sleep(.02)
            stream.frame_camera();self.stream=stream
        except Exception:
            stream.close();raise

    def _hide(self):
        if self.camera is not None:return
        state=self.lab.status();p=state['physics'];layer=state['body_field_preview']
        self.camera=self._native('return {navigation=openspace.navigation.getNavigationState("Root")}')['navigation']
        names=['LabGrid','LabBarycenter','LabProbe']+[b[k] for b in p['bodies'] for k in ['scene_node','label_node']]
        if layer:names += [m['node'] for m in layer['render']['meshes']]+[layer['render']['label_node']]
        self.hidden=self._native('local f={};for _,n in ipairs('+lua(names)+') do if openspace.hasSceneGraphNode(n) then local ok,v=pcall(openspace.propertyValue,"Scene."..n..".Renderable.Enabled");if ok and type(v)=="boolean" then f[n]=v;openspace.setPropertyValueSingle("Scene."..n..".Renderable.Enabled",false) end end end;return {flags=f}')['flags']

    def _restore(self):
        if self.stream:self.stream.close();self.stream=None
        if self.camera is not None:self._native('openspace.navigation.setNavigationState('+lua(self.camera)+');return {ready=true}')
        if self.hidden:self._native('local f='+lua(self.hidden)+';for n,v in pairs(f) do if openspace.hasSceneGraphNode(n) then openspace.setPropertyValueSingle("Scene."..n..".Renderable.Enabled",v) end end;return {ready=true}')
        self.hidden={};self.camera=None

    def _guard(self,request,visual=False):
        if self.client is None:raise ValueError('Crie ou restaure uma partícula primeiro.')
        state=self.client.snapshot();expected=Client.guard(state);guard=request.get('guard')
        if not isinstance(guard,dict) or set(guard)!=set(expected):raise ValueError('Identidade e fase da partícula são obrigatórias.')
        for key in ['worker_id','experiment_id','edit_token','frame']:
            if guard[key]!=expected[key]:raise ValueError('A partícula mudou; atualize a leitura.')
        if type(guard['revision']) is not int or guard['revision']!=expected['revision']:raise ValueError('A revisão da partícula mudou.')
        t=scalar(guard['expected_time_s'])
        if visual:
            if not 0<=t<=expected['expected_time_s']:raise ValueError('Tempo de leitura inválido.')
        elif t!=expected['expected_time_s']:raise ValueError('A fase mudou; pause e atualize a leitura.')
        return state

    def _initial(self,request):
        state=self.lab.status();p=copy.deepcopy(state['physics']);layer=state['body_field_preview']
        if state['mode']!='experiment' or not p or not p['paused'] or len(p['bodies'])!=4 or not layer:raise ValueError('Abra uma cópia solar pausada e uma amostra magnética da Terra ou de Júpiter.')
        expected={k:p[k] for k in ['system_id','edit_token','revision','time']}|{'frame':p['contract']['frame']}
        guard=request.get('source_guard')
        if not isinstance(guard,dict) or set(guard)!=set(expected) or type(guard['revision']) is not int or type(guard['time']) not in (int,float) or guard!=expected:raise ValueError('A fase solar mudou; atualize a leitura.')
        r=copy.deepcopy(layer['reading']);earth=r['kind']=='scene_Earth_IGRF14_passive_point'
        species=request['species']
        if species not in ['proton','electron','neutral']:raise ValueError('Espécie da partícula inválida.')
        speed=scalar(request['speed_m_s']);pitch=scalar(request['pitch_deg'])
        if not 0<speed<=.01*299792458. or not 0<=pitch<=180:raise ValueError('Velocidade ou ângulo fora do regime declarado.')
        mass=CONSTANTS['electron_mass_kg' if species=='electron' else 'proton_mass_kg']['value']
        charge=0. if species=='neutral' else CONSTANTS['elementary_charge_C']['value']*(-1 if species=='electron' else 1)
        field=np.array(self._field(r));norm=float(np.linalg.norm(field));direction=field/norm
        axis=np.eye(3)[int(np.argmin(abs(direction)))];side=np.cross(direction,axis);side/=np.linalg.norm(side)
        velocity=(speed*(math.sin(math.radians(pitch))*side+math.cos(math.radians(pitch))*direction)).tolist()
        omega=abs(charge/mass)*norm
        dt=2*math.pi/omega/800 if omega else .001
        unit=speed*abs(math.sin(math.radians(pitch)))/omega if omega and abs(math.sin(math.radians(pitch)))>1e-6 else max(1e-6,speed*dt*64)
        params={'charge_C':float(charge),'mass_kg':mass,'dt_s':float(dt),'initial_position_m':r['point_ITRF93_m' if earth else 'point_SystemIII_m'],'initial_velocity_m_s':velocity}
        return p,r,params,float(unit),field.tolist()

    @staticmethod
    def _field(reading):
        key='field_model_T' if reading['kind']=='scene_Sun_Parker_prescribed_point' else 'field_ITRF93_T' if reading['kind']=='scene_Earth_IGRF14_passive_point' else 'field_SystemIII_T'
        return reading[key]

    def _initial_wind(self,request):
        state=self.lab.status();p=copy.deepcopy(state['physics'])
        if state['mode']!='experiment' or not p or not p['paused'] or len(p['bodies'])!=4:raise ValueError('Abra uma cópia solar pausada de quatro centros.')
        expected={k:p[k] for k in ['system_id','edit_token','revision','time']}|{'frame':p['contract']['frame']}
        guard=request.get('source_guard')
        if not isinstance(guard,dict) or set(guard)!=set(expected) or type(guard['revision']) is not int or type(guard['time']) not in (int,float) or guard!=expected:raise ValueError('A fase solar mudou; atualize a leitura.')
        from is4_wind_reading import read
        reading=read(p,request['coordinates'],request['wind_parameters']);species=request['species']
        if species not in ['proton','electron','neutral']:raise ValueError('Espécie da partícula inválida.')
        speed,pitch=scalar(request['relative_speed_m_s']),scalar(request['pitch_deg'])
        if not 0<speed<=.01*299792458. or not 0<=pitch<=180:raise ValueError('Velocidade relativa ou ângulo fora do regime.')
        mass=CONSTANTS['electron_mass_kg' if species=='electron' else 'proton_mass_kg']['value']
        charge=0. if species=='neutral' else CONSTANTS['elementary_charge_C']['value']*(-1 if species=='electron' else 1)
        field=np.array(reading['field_model_T']);norm=float(np.linalg.norm(field));direction=field/norm
        axis=np.eye(3)[int(np.argmin(abs(direction)))];side=np.cross(direction,axis);side/=np.linalg.norm(side)
        velocity=np.array(reading['wind_velocity_model_m_s'])+speed*(math.sin(math.radians(pitch))*side+math.cos(math.radians(pitch))*direction)
        omega=abs(charge/mass)*norm;dt=2*math.pi/omega/800 if omega else .01
        unit=speed*abs(math.sin(math.radians(pitch)))/omega if omega and abs(math.sin(math.radians(pitch)))>1e-6 else max(1e-6,speed*dt*64)
        parameters={'charge_C':float(charge),'mass_kg':mass,'dt_s':float(dt),'initial_position_m':reading['point_model_m'],'initial_velocity_m_s':velocity.tolist()}
        return p,reading,parameters,float(unit),field.tolist()

    def _publish(self):
        state=None if self.client is None else self.client.snapshot();view=None
        if self.stream:
            s=self.stream;confirmed=s.confirmed
            view={'physical_unit_m':s.unit,'visible':s.visible,'binding_sha256':s.binding,'pending_sequence':None if s.pending is None else s.pending['metadata']['sequence'],
                'native_nodes':{'frame':s.frame,'trajectory':s.trail,'focus':s.focus},'native':copy.deepcopy(s.latest_native),'confirmed_phase':None if confirmed is None else copy.deepcopy(confirmed['geometry']['phase']),
                'confirmed_metadata':None if confirmed is None else copy.deepcopy(confirmed['metadata']),
                'source_epoch':None if confirmed is None else copy.deepcopy(confirmed['geometry']['source_epoch'])}
        with self.lock:self.public={'active':self.client is not None,'worker':state,'view':view,'sample':copy.deepcopy(self.sample),'error':self.error,
            'checkpoint_available':self.store.path.is_file(),'branches':copy.deepcopy(self.branches),'branch_parent':self.branch_parent,
            'scope':('' if state is None else state['experiment']['source_scope']+' ')+'Uma carga-teste; campos, eixos e quatro centros congelados. Sem reação, colisões, plasma ou MHD.'}

    def _handle(self,request):
        name=request.get('command');extra={'create':{'source_guard','species','speed_m_s','pitch_deg'},'create_wind':{'source_guard','species','relative_speed_m_s','pitch_deg','coordinates','wind_parameters'},'advance':{'steps'},'set_rate':{'value'},'set_controls':{'controls'},'visible':{'visible'},'create_branch':{'name'},'load_branch':{'branch_id'}}
        without_guard={'create','create_wind','load_saved','leave'}
        if set(request)!={'command'}|extra.get(name,set())|({'guard'} if name not in without_guard else set()):raise ValueError('Campos exatos do comando de partícula são obrigatórios.')
        self.error=None;result=None
        if name in ['create','create_wind']:
            if self.client is not None:raise ValueError('Feche a vista atual antes de criar outra partícula.')
            p,r,params,unit,field=self._initial_wind(request) if name=='create_wind' else self._initial(request)
            client=Client(STORAGE)
            try:
                client.call('create',{'source_phase':p,'source_reading':r,'parameters':params,'controls':{'electric':True,'magnetic':True,'gravity':True}})
                self._hide();self._view(client.snapshot(),unit,field);self.client=client;self.branch_parent=None
            except Exception:client.close();self._restore();raise
        elif name=='load_saved':
            if self.client is not None:raise ValueError('Feche a vista atual antes de restaurar um arquivo.')
            if self.lab.status()['mode']!='experiment':raise ValueError('Abra o laboratório solar antes de restaurar a partícula.')
            view,candidate=self.store.restore_to(STORAGE);r=candidate.source_reading;earth=r['kind']=='scene_Earth_IGRF14_passive_point'
            field=self._field(r);unit=view['physical_unit_m']
            client=Client(STORAGE)
            try:
                client.call('load');self._hide();self._view(client.snapshot(),unit,field,view['visible']);self.client=client;self.branch_parent=None
            except Exception:client.close();self._restore();raise
        elif name=='leave':
            if self.client:
                try:self.client.call('pause')
                finally:self.client.close();self.client=None
            self._restore();self.sample=None
        else:
            visual=name in ['pause','visible','frame','create_branch'];state=self._guard(request,visual=visual)
            if name=='visible':self.stream.set_visible(request['visible'])
            elif name=='frame':self.stream.frame_camera()
            elif name=='restart':
                payload=self.client.call('export_payload',guard=request['guard'])['result']
                self.client.call('create',{'source_phase':payload['source_phase'],'source_reading':payload['source_reading'],'parameters':payload['parameters'],'controls':payload['controls']})
                self._view(self.client.snapshot(),self.stream.unit,self.stream.field);self.sample=None
            elif name in ['load','load_branch']:
                # Check pause and guard before replacing the worker's scratch manifest.
                if not state['paused']:raise ValueError('Pause a partícula antes de restaurar.')
                self.client.call('state')
                view,candidate=self.store.restore_to(STORAGE,request.get('branch_id'))
                self.client.call('load',guard=request['guard'])
                r=candidate.source_reading;earth=r['kind']=='scene_Earth_IGRF14_passive_point'
                self._view(self.client.snapshot(),view['physical_unit_m'],self._field(r),view['visible']);self.sample=None
                self.branch_parent=request.get('branch_id')
            elif name in ['save','create_branch']:
                if name=='create_branch':self.client.call('pause',guard=request['guard'])
                elif not state['paused']:raise ValueError('Pause a partícula antes de salvar.')
                self.client.call('save')
                particle=json.loads((STORAGE/'latest.json').read_text(encoding='utf-8'))
                result=self.store.save(particle,{'physical_unit_m':self.stream.unit,'visible':self.stream.visible},
                    **({'name':request['name'],'parent':self.branch_parent} if name=='create_branch' else {}))
                if name=='create_branch':self.branch_parent=result['branch']['id'];self.branches=self.store.catalog()
            elif name=='export':
                payload=self.client.call('export_payload',guard=request['guard'])['result']
                record={'schema':1,'kind':'is4_particle_export','particle':payload,'view':copy.deepcopy(self.stream.confirmed),'native':copy.deepcopy(self.stream.latest_native)}
                folder=HERE.parent/'particle-exports';folder.mkdir(exist_ok=True);path=folder/(uuid.uuid4().hex+'.json')
                path.write_text(json.dumps(record,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8');result={'export_file':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
            elif name in ['pause','resume','advance','set_controls','set_rate','sample']:
                reply=self.client.call(name,{k:request[k] for k in extra.get(name,set())},guard=request['guard']);result=reply.get('result')
                if name=='sample':self.sample=copy.deepcopy(result)
                elif name in ['advance','resume','set_controls']:self.sample=None
            else:raise ValueError('Comando de partícula desconhecido.')
        if self.stream and self.client:self.stream.update(self.client.snapshot())
        self._publish();return {'ok':True,'particle':self.status(),'result':result}

    def _run(self):
        try:
            while not self.closing:
                try:request,future=self.actions.get(timeout=.05)
                except queue.Empty:request=future=None
                if request is not None:
                    try:future.set_result(self._handle(request))
                    except Exception as error:self.error=str(error);self._publish();future.set_exception(error)
                try:
                    if self.stream and self.client:self.stream.update(self.client.snapshot())
                    self.native_failure_since=None
                except Exception as error:
                    self.error=str(error)
                    if self.native_failure_since is None:self.native_failure_since=time.monotonic()
                    if self.client and not self.client.snapshot()['paused']:
                        try:self.client.call('pause')
                        except Exception:pass
                self._publish()
        finally:
            try:self._restore()
            except Exception:pass
            if self.client:self.client.close();self.client=None
            if self.engine:self.engine.close();self.engine=None

    def close(self):
        self.closing=True;self.thread.join(timeout=20)
