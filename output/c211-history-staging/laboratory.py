"""Own the worker and render its snapshots without blocking OpenSpace's frame loop."""
from concurrent.futures import Future, TimeoutError as FutureTimeout
from collections import deque
from pathlib import Path
import json
import copy
import math
import os
import queue
import subprocess
import sys
import threading
import time
from body_attributes import rotation_euler
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
SCALE = 1e9

class Laboratory:
    def __init__(self):
        self.actions = queue.Queue()
        self.lock = threading.Lock()
        self.latest = None
        self.mode = 'atlas'
        self.error = None
        self.latency = None
        self.engine_ready = False
        self.worker = None
        self.worker_events = queue.Queue()
        self.engine = None
        self.topic = 0
        self.command_id = 0
        self.worker_stderr = deque(maxlen=20)
        self.trace_lock = threading.Lock()
        self.trace_file = ROOT/'output'/f'laboratory-trace-{os.getpid()}.jsonl'
        self.trace_file.parent.mkdir(parents=True,exist_ok=True)
        self.rendered_sequence = None
        self.rendered_count = 0
        self.rendered_labels = False
        self.rendered_nodes = []
        self.physical_radii=False
        self.axes_body=None
        self.rendered_attributes={}
        self.orbit_nodes=[]
        self.orbit_preview=None
        self.probe_preview=None
        self.instrument_nodes=[]
        self.instruments_preview=None
        self.field_nodes=[]
        self.fields_preview=None
        self.fields_public=None
        self.field_reading=None
        self.fields_visible=True
        self.instrument_comparison=None
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def status(self):
        with self.lock:
            return {'mode':self.mode, 'physics':self.latest, 'error':self.error,
                    'display':{'physical_radii':self.physical_radii,'axes_body':self.axes_body},
                    'orbit_preview':self.orbit_preview,
                    'probe_preview':self.probe_preview,
                    'instruments_preview':self.instruments_preview,
                    'fields_preview':self.fields_public,'field_reading':self.field_reading,
                    'fields_visible':self.fields_visible,
                    'instrument_comparison':self.instrument_comparison,
                    'engine_connected':self.engine_ready, 'command_latency_ms':self.latency,
                    'checkpoint_available':(ROOT/'user'/'sessions'/'latest.json').is_file()}

    def command(self, action):
        future = Future()
        queued = time.perf_counter()
        self._trace('action_queued',command=action.get('command'))
        self.actions.put((action, future))
        try:
            result = future.result(timeout=15)
            self._trace('action_replied',command=action.get('command'),elapsed_ms=(time.perf_counter()-queued)*1000)
            return result
        except FutureTimeout:
            if future.done():
                raise
            # An already running mutation may have applied. Never repeat it silently.
            cancelled = future.cancel()
            self._trace('action_timeout',command=action.get('command'),cancelled_before_start=cancelled)
            raise TimeoutError('O laboratório não confirmou o comando em 15 s. Consulte o estado antes de repetir uma alteração.') from None

    def _trace(self,event,**fields):
        with self.trace_lock:
            with self.trace_file.open('a',encoding='utf-8') as f:
                f.write(json.dumps({'event':event,'monotonic_s':time.perf_counter(),**fields},allow_nan=False)+'\n')

    def close(self):
        self.stop_event.set()
        self.thread.join(timeout=10)

    def _start_worker(self):
        if self.worker and self.worker.poll() is None:
            return
        self.worker = subprocess.Popen([sys.executable,'-u',str(ROOT/'app'/'worker.py')],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.worker_events = queue.Queue()
        self.worker_stderr.clear()
        owned_worker,events = self.worker,self.worker_events
        def reader():
            try:
                for line in owned_worker.stdout:
                    message = json.loads(line)
                    if message['type'] == 'snapshot':
                        with self.lock:
                            self.latest = message
                    else:
                        self._trace('worker_message',type=message.get('type'),id=message.get('id'),
                                    revision=message.get('revision'),elapsed_ms=message.get('elapsed_ms'))
                        events.put(message)
            except Exception as error:
                self._trace('worker_reader_error',detail=f'{type(error).__name__}: {error}')
                events.put({'type':'error','message':'Falha na leitura do processo físico: '+str(error)})
            finally:
                events.put({'type':'error','message':'O processo físico encerrou.'})
        def stderr_reader():
            for line in owned_worker.stderr:
                self.worker_stderr.append(line.rstrip())
        threading.Thread(target=reader,daemon=True).start()
        threading.Thread(target=stderr_reader,daemon=True).start()
        ready = self.worker_events.get(timeout=5)
        if ready.get('type') != 'ready':
            raise RuntimeError(ready.get('message','Worker initialization failed'))

    def _worker_command(self, command):
        self._start_worker()
        self.command_id += 1
        identifier = self.command_id
        began = time.perf_counter()
        self._trace('worker_command_sent',id=identifier,command=command.get('command'))
        self.worker.stdin.write(json.dumps({**command,'id':identifier})+'\n')
        self.worker.stdin.flush()
        while True:
            remaining = 5-(time.perf_counter()-began)
            try:
                response = self.worker_events.get(timeout=max(0,remaining))
            except queue.Empty:
                with self.lock:
                    revision = self.latest.get('revision') if self.latest else None
                self._trace('worker_ack_timeout',id=identifier,command=command.get('command'),
                            latest_revision=revision,stderr=list(self.worker_stderr))
                raise TimeoutError(f'O processo físico não confirmou {command.get("command")} (id {identifier}) em 5 s; revisão observada {revision}. A alteração pode ter sido aplicada.') from None
            if response.get('type') == 'error':
                raise ValueError(response.get('message','Physics error'))
            if response.get('id') == identifier:
                with self.lock:
                    self.latency = (time.perf_counter()-began)*1000
                self._trace('worker_ack_matched',id=identifier,elapsed_ms=self.latency)
                return response

    def _lua(self, code, wait=False):
        if self.engine is None:
            # This OpenSpace transport does not answer WebSocket control-frame pings.
            # Request/response timeouts cover application liveness instead.
            self.engine = connect('ws://127.0.0.1:4682',open_timeout=3,ping_interval=None,close_timeout=1)
            self.engine.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
            with self.lock:
                self.engine_ready = True
        self.topic += 1
        self.engine.send(json.dumps({'topic':self.topic,'type':'luascript',
            'payload':{'script':code,'return':wait}}))
        if wait:
            began = time.perf_counter()
            self._trace('renderer_wait_started',topic=self.topic)
            response = json.loads(self.engine.recv(timeout=5))
            if response.get('topic') != self.topic:
                raise RuntimeError('Unexpected renderer response')
            self._trace('renderer_replied',topic=self.topic,elapsed_ms=(time.perf_counter()-began)*1000)
            return response.get('payload',{}).get('1',{})

    @staticmethod
    def _marker_size(body,index,imported):
        if body.get('display_marker_radius_m'):return body['display_marker_radius_m']
        return (4e8 if body.get('reference_id')=='sol:naif:10' else 8e7 if body.get('reference_id')=='sol:naif:399' else 4e7) if imported and body['origin']['kind']=='atlas_copy' else (4e8 if index==0 else 1.2e8)

    @staticmethod
    def _freeze_anchor(anchor):
        return 'local n=openspace.navigation.getNavigationState("Root");if n.Anchor=="'+anchor+'" then local p=openspace.worldPosition(n.Anchor);local r=openspace.worldPosition("LabRoot");openspace.setPropertyValueSingle("Scene.LabCameraAnchor.Translation.Position",{p[1]-r[1],p[2]-r[2],p[3]-r[3]});n.Anchor="LabCameraAnchor";openspace.navigation.setNavigationState(n) end;'

    def _clear_orbit(self):
        if self.orbit_nodes:self._lua(self._freeze_anchor('LabOrbitFrame')+''.join('openspace.removeSceneGraphNode("'+node+'");' for node in self.orbit_nodes)+'return {ready=true}',True)
        with self.lock:self.orbit_nodes=[];self.orbit_preview=None

    def _clear_instruments(self):
        if self.instrument_nodes:
            code=''.join(self._freeze_anchor(node) for node in self.instrument_nodes)
            code+=''.join('openspace.removeSceneGraphNode("'+node+'");' for node in self.instrument_nodes)
            self._lua(code+'return {ready=true}',True)
        with self.lock:self.instrument_nodes=[];self.instruments_preview=None;self.instrument_comparison=None

    def _show_instruments(self,result):
        from instrument_scene import prepare
        with self.lock:initial=self.latest.get('atlas_initial')
        create,render=prepare(result,initial)
        cleanup=''.join('if openspace.hasSceneGraphNode("'+node+'") then openspace.removeSceneGraphNode("'+node+'") end;' for node in render['nodes'])
        code='local ok,err=pcall(function() '+create+' end);if not ok then '+cleanup+'error(err) end;'
        code+=''.join(self._freeze_anchor(node) for node in self.instrument_nodes)
        code+=''.join('openspace.removeSceneGraphNode("'+node+'");' for node in self.instrument_nodes)
        if self._lua(code+'return {ready=true}',True).get('ready') is not True:
            raise RuntimeError('O motor não confirmou as marcas das sondas.')
        with self.lock:self.instrument_nodes=render['nodes'];self.instruments_preview={**result,'render':render}

    def _clear_fields(self):
        if self.field_nodes:
            code=''.join(self._freeze_anchor(node) for node in self.field_nodes)
            code+=''.join('openspace.removeSceneGraphNode("'+node+'");' for node in reversed(self.field_nodes))
            if self._lua(code+'return {ready=true}',True).get('ready') is not True:
                raise RuntimeError('O motor não confirmou a remoção do mapa de campo.')
        with self.lock:
            self.field_nodes=[];self.fields_preview=None;self.fields_public=None;self.field_reading=None;self.fields_visible=True

    def _show_fields(self,result):
        from field_scene import prepare
        with self.lock:initial=self.latest.get('atlas_initial')
        create,render=prepare(result,initial)
        cleanup=''.join('if openspace.hasSceneGraphNode("'+node+'") then openspace.removeSceneGraphNode("'+node+'") end;' for node in reversed(render['nodes']))
        code='local ok,err=pcall(function() '+create+' end);if not ok then '+cleanup+'error(err) end;'
        code+=''.join(self._freeze_anchor(node) for node in self.field_nodes)
        code+=''.join('openspace.removeSceneGraphNode("'+node+'");' for node in reversed(self.field_nodes))
        if self._lua(code+'return {ready=true}',True).get('ready') is not True:
            raise RuntimeError('O motor não confirmou a geometria do mapa de campo.')
        # Poll only the small legend/receipt. Full SI samples stay in the backend
        # for selected readings/export, instead of serializing them every250ms.
        summary={k:copy.deepcopy(v) for k,v in result.items() if k not in ('shell','cut','source_snapshot_si')}
        for layer in ('shell','cut'):
            value=result[layer]
            summary[layer]=None if value is None else {
                'sample_count':len(value['samples']),
                'invalid_samples':sum(not s['valid'] for s in value['samples']),
                'drawn_arrows':sum(a['drawn'] for a in value['geometry']['arrows']),
                'arrow_length_m':value['geometry']['length_m']}
        if result['cut']:
            cut=result['cut'];summary['cut'].update(grid=cut['grid'],arrow_grid_stride=cut['arrow_grid_stride'],
                levels_J_kg=[c['potential_J_kg'] for c in cut['equipotentials']['contours']],
                contour_segment_counts=[len(c['segments_m']) for c in cut['equipotentials']['contours']],
                invalid_cells=len(cut['equipotentials']['invalid_cells']),plateau_cells=len(cut['equipotentials']['plateau_cells']),
                level_policy=cut['level_policy'],interpolation=cut['equipotentials']['interpolation'])
        summary['render']=render
        with self.lock:
            self.field_nodes=render['nodes'];self.fields_preview={**result,'render':render};self.fields_public=summary
            self.field_reading=None;self.fields_visible=True

    def _show_orbit(self, result):
        from orbit_scene import prepare
        with self.lock:initial=self.latest.get('atlas_initial')
        create,render=prepare(result,initial);nodes=render['nodes']
        cleanup=''.join('if openspace.hasSceneGraphNode("'+node+'") then openspace.removeSceneGraphNode("'+node+'") end;' for node in nodes)
        code='local ok,err=pcall(function() '+create+' end);if not ok then '+cleanup+'error(err) end;'
        code+=self._freeze_anchor('LabOrbitFrame')
        code+='openspace.setPropertyValueSingle("Scene.LabOrbitFrame.Translation.Position",{'+','.join(format(v,'.17g') for v in render['frame_position_render_m'])+'});'
        code+=''.join('openspace.removeSceneGraphNode("'+node+'");' for node in self.orbit_nodes)+'return {ready=true}'
        if self._lua(code,True).get('ready') is not True:raise RuntimeError('O motor não confirmou a prévia orbital.')
        with self.lock:self.orbit_nodes=nodes;self.orbit_preview={**result,'render':render}

    @staticmethod
    def _body_scene(body, index, imported):
        # JSON's ASCII \u escapes are not Lua escapes. Keep UTF-8 text literal.
        literal=lambda value:json.dumps(value,ensure_ascii=False)
        node,label=body['scene_node'],body['label_node'];name=literal(body['name'])
        display_name=literal(body['name'] if len(body['name'])<=24 else body['name'][:23]+'…')
        texture='central.ppm' if index==0 else 'orbiter.ppm'
        size=Laboratory._marker_size(body,index,imported)
        code='openspace.addSceneGraphNode({Identifier="%s",Parent="LabRoot",Transform={Translation={Type="StaticTranslation",Position={0,0,0}}},Renderable={Type="RenderableSphereImageLocal",Size=%.17g,Segments=16,Texture=openspace.absPath("${COSMOS2}/data/markers/%s")},GUI={Name=%s}});'%(node,size,texture,name)
        enabled='true' if index==0 and body['origin']['kind']!='deterministic_fixture' else 'false'
        code+='openspace.addSceneGraphNode({Identifier="%s",Parent="%s",Transform={Translation={Type="StaticTranslation",Position={0,0,%.17g}}},Renderable={Type="RenderableLabel",Text=%s,FontSize=50,Size=6,MinMaxSize={12,18},OrientationOption="Camera View Direction",EnableFading=false,Enabled=%s},GUI={Name=%s,Focusable=false}});'%(label,node,size*1.5,display_name,enabled,literal('Rótulo '+body['name']))
        code+='openspace.addSceneGraphNode({Identifier="%s",Parent="%s",Transform={Rotation={Type="StaticRotation",Rotation={0,0,0}},Scale={Type="StaticScale",Scale=%.17g}},Renderable={Type="RenderableCartesianAxes",Enabled=false},GUI={Name="Eixos de orientacao",Focusable=false}});'%(body['spin_node'],node,size*1.4)
        surface={'sol:naif:399':'textures/earth.jpg','sol:naif:301':'textures/moon.png'}.get(body.get('reference_id'),'markers/'+texture)
        code+='openspace.addSceneGraphNode({Identifier="%s",Parent="%s",Transform={Rotation={Type="StaticRotation",Rotation={0,0,0}}},Renderable={Type="RenderableSphereImageLocal",Size=1,Segments=64,Texture=openspace.absPath("${COSMOS2}/data/%s"),Enabled=false},GUI={Name="Esfera geometrica",Focusable=false}});'%(body['shape_node'],node,surface)
        return code

    def _sync_scene(self):
        with self.lock:state=self.latest
        current=[(b['scene_node'],b['label_node']) for b in state['bodies']]
        removed=[pair for pair in self.rendered_nodes if pair not in current]
        ids='{'+','.join('"'+pair[0]+'"' for pair in removed)+'}'
        # A frozen anchor preserves the full camera basis before its target vanishes
        # or before the bounding-box anchor moves. Surviving body anchors keep following.
        code='local n=openspace.navigation.getNavigationState("Root");local freeze=n.Anchor=="LabFrame";for _,id in ipairs('+ids+') do if n.Anchor==id then freeze=true end end;if freeze then local p=openspace.worldPosition(n.Anchor);local r=openspace.worldPosition("LabRoot");openspace.setPropertyValueSingle("Scene.LabCameraAnchor.Translation.Position",{p[1]-r[1],p[2]-r[2],p[3]-r[3]});n.Anchor="LabCameraAnchor";openspace.navigation.setNavigationState(n) end;'
        for node,label in removed:code+=f'openspace.removeSceneGraphNode("{node.replace("LabBody_","LabShape_")}");openspace.removeSceneGraphNode("{node.replace("LabBody_","LabSpin_")}");openspace.removeSceneGraphNode("{label}");openspace.removeSceneGraphNode("{node}");'
        for i,body in enumerate(state['bodies']):
            if current[i] not in self.rendered_nodes:code+=self._body_scene(body,i,bool(state.get('atlas_initial')))
        self._lua(code+'return {ready=true}',True)
        self.rendered_nodes=current;self.rendered_count=len(current);self.rendered_sequence=None
        self.rendered_attributes={b['id']:self.rendered_attributes[b['id']] for b in state['bodies'] if b['id'] in self.rendered_attributes}
        if self.axes_body not in [b['id'] for b in state['bodies']]:self.axes_body=None

    def _make_scene(self, count):
        self._clear_scene()
        with self.lock:
            state=self.latest;initial = state.get('atlas_initial')
        self._lua('openspace.addSceneGraphNode({Identifier="LabRoot",Transform={Translation={Type="StaticTranslation",Position={1e14,0,0}}}});return {ready=true}',True)
        self.rendered_count = count
        self.rendered_nodes=[]
        # Bound each scene transaction: 128 bodies have 512 display nodes.
        # Waiting between small batches lets the engine initialize GL resources
        # without exceeding the normal renderer response deadline.
        for start in range(0,count,8):
            batch=state['bodies'][start:start+8]
            self.rendered_nodes.extend((b['scene_node'],b['label_node']) for b in batch)
            code=''.join(self._body_scene(body,start+i,bool(initial)) for i,body in enumerate(batch))
            self._lua(code+'return {ready=true}',True)
        code=''
        positions=self._display_positions(state['bodies'],initial)
        extent = max(state.get('display_min_view_distance_m',3e10)*2,2.4*max(math.hypot(*p) for p in positions))
        code += f'openspace.addSceneGraphNode({{Identifier="LabGrid",Parent="LabRoot",Renderable={{Type="RenderableGrid",Size={{{extent:.17g},{extent:.17g}}},Segments={{12,12}},Color={{0.12,0.25,0.32}},Opacity=0.35}}}});'
        center = [(min(p[k] for p in positions)+max(p[k] for p in positions))/2 for k in range(3)]
        code += 'openspace.addSceneGraphNode({Identifier="LabFrame",Parent="LabRoot",Transform={Translation={Type="StaticTranslation",Position={' + ','.join(format(v,'.17g') for v in center) + '}}}});'
        code += 'openspace.addSceneGraphNode({Identifier="LabCameraAnchor",Parent="LabRoot",Transform={Translation={Type="StaticTranslation",Position={0,0,0}}}});'
        code += 'openspace.addSceneGraphNode({Identifier="LabOrbitFrame",Parent="LabRoot",Transform={Translation={Type="StaticTranslation",Position={0,0,0}}}});'
        code += 'openspace.addSceneGraphNode({Identifier="LabPairFrame",Parent="LabRoot",Transform={Translation={Type="StaticTranslation",Position={0,0,0}}}});'
        code += 'openspace.addSceneGraphNode({Identifier="LabBarycenter",Parent="LabRoot",Transform={Translation={Type="StaticTranslation",Position={0,0,0}}},Renderable={Type="RenderableLabel",Text="Baricentro",FontSize=50,Size=6,MinMaxSize={12,18},OrientationOption="Camera View Direction",EnableFading=false,Enabled=false},GUI={Name="Baricentro ativo",Focusable=false}});'
        code += 'openspace.addSceneGraphNode({Identifier="LabProbe",Parent="LabRoot",Transform={Translation={Type="StaticTranslation",Position={0,0,0}}},Renderable={Type="RenderableLabel",Text="+ Sonda",FontSize=50,Size=6,MinMaxSize={14,20},OrientationOption="Camera View Direction",EnableFading=false,Enabled=false},GUI={Name="Amostra pontual congelada",Focusable=false}});'
        anchor = 'LabFrame'
        camera = [0, -5e10, 6e10]
        if state.get('experiment'):
            distance=max(state['display_min_view_distance_m'],2.2*max(math.dist(p,center) for p in positions));camera=[0,-distance,distance*.6]
        if initial and len(positions)>1:
            delta = [positions[1][k]-positions[0][k] for k in range(3)]
            distance = math.sqrt(sum(v*v for v in delta))
            side = [-delta[1],delta[0],0]
            norm = math.sqrt(sum(v*v for v in side))
            if norm < 1e-8:
                side,norm = [1,0,0],1
            camera = [v/norm*distance*1.6 for v in side]
            anchor = 'LabFrame'
        code += f'openspace.navigation.setNavigationState({{Anchor="{anchor}",ReferenceFrame="LabRoot",Position={{{",".join(format(v,".17g") for v in camera)}}},Up={{0,0,1}}}});return {{ready=true}}'
        self._lua(code,True)
        self.rendered_count = count
        self.rendered_nodes=[(b['scene_node'],b['label_node']) for b in state['bodies']]
        self.rendered_attributes={}
        if self.axes_body not in [b['id'] for b in state['bodies']]:self.axes_body=None
        self.rendered_labels = True
        self.rendered_sequence = None
        with self.lock:self.probe_preview=None

    def _clear_scene(self):
        if not self.rendered_count:
            return
        self._clear_orbit()
        self._clear_instruments()
        self._clear_fields()
        code = 'openspace.navigation.setNavigationState({Anchor="Earth",Position={-16000000,-17000000,10000000},Up={0,0,1}});'
        code += ''.join(f'openspace.removeSceneGraphNode("{node.replace("LabBody_","LabShape_")}");openspace.removeSceneGraphNode("{node.replace("LabBody_","LabSpin_")}");openspace.removeSceneGraphNode("{label}");openspace.removeSceneGraphNode("{node}");' for node,label in self.rendered_nodes)
        code += 'openspace.removeSceneGraphNode("LabFrame");openspace.removeSceneGraphNode("LabCameraAnchor");'
        code += 'openspace.removeSceneGraphNode("LabOrbitFrame");openspace.removeSceneGraphNode("LabBarycenter");'
        code += 'openspace.removeSceneGraphNode("LabPairFrame");'
        code += 'openspace.removeSceneGraphNode("LabProbe");'
        code += 'openspace.removeSceneGraphNode("LabGrid");openspace.removeSceneGraphNode("LabRoot");return {removed=true}'
        self._lua(code,True)
        self.rendered_count = 0
        self.rendered_labels = False
        self.rendered_nodes=[]
        self.rendered_attributes={}
        with self.lock:self.probe_preview=None

    @staticmethod
    def _display_positions(bodies, initial):
        matrix = initial['j2000_to_render_frame'] if initial else None
        return [[sum(row[k]*body['position'][k] for k in range(3))*SCALE for row in matrix]
                if matrix else [v*SCALE for v in body['position']] for body in bodies]

    def _apply(self, action):
        name = action.get('command')
        if name in ('configure_history','clear_history','history_curves','history_point','export_history','compare_instruments'):
            if self.mode!='experiment':raise ValueError('Abra o laboratório primeiro.')
            if name=='compare_instruments':
                from probe_comparison import compare
                with self.lock:preview=copy.deepcopy(self.instruments_preview)
                if preview is None or action.get('system_id')!=preview['system_id'] or action.get('reading_edit_token')!=preview['edit_token'] or action.get('reading_time')!=preview['time'] or action.get('reading_revision')!=preview['revision'] or action.get('reading_instruments_revision')!=preview['instruments_revision']:
                    raise ValueError('Leitura mudou; selecione duas sondas do mesmo instante confirmado.')
                result=compare(preview,action.get('first_id'),action.get('second_id'))
                with self.lock:self.instrument_comparison=result
                return result
            if name=='export_history':
                from artifacts import export_json
                with self.lock:state=copy.deepcopy(self.latest)
                identity={'system_id':state['system_id'],'edit_token':state['edit_token']}
                data=self._worker_command({'command':'history_export',**identity})['result']
                return export_json('instrument-history',{'schema':1,'history':data,'origin_kind':state['origin_kind'],
                    'atlas_initial':state.get('atlas_initial'),'frame':state['contract']['frame'],
                    'scientific_generation':state['scientific_generation']})
            ack=self._worker_command(action)
            if name=='history_point':self._show_instruments(ack['result']['reading'])
            return ack
        if name in ('configure_fields','sample_fields','clear_fields','set_fields_visible','select_field_sample','export_fields'):
            if self.mode!='experiment':raise ValueError('Abra o laboratório primeiro.')
            if name=='clear_fields':
                self._clear_fields();return {'command':name}
            if name=='set_fields_visible':
                visible=action.get('visible')
                if type(visible) is not bool:raise ValueError('Visibilidade do campo inválida.')
                if self.fields_preview is None:raise ValueError('Meça o campo antes de alterar sua exibição.')
                code=''.join('openspace.setPropertyValueSingle("Scene.'+m['node']+'.Renderable.Enabled",'+str(visible).lower()+');' for m in self.fields_preview['render']['meshes'])
                if self._lua(code+'return {ready=true}',True).get('ready') is not True:raise RuntimeError('O motor não confirmou a visibilidade do campo.')
                with self.lock:self.fields_visible=visible
                return {'command':name,'visible':visible}
            if name=='select_field_sample':
                layer,index=action.get('layer'),action.get('index')
                if self.fields_preview is None or action.get('map_id')!=self.fields_preview['render']['id']:
                    raise ValueError('O mapa mudou; selecione uma amostra da leitura atual.')
                value=self.fields_preview.get(layer) if layer in ('shell','cut') else None
                if value is None or type(index) is not int or not 0<=index<len(value['samples']):raise ValueError('Índice de amostra inválido.')
                reading={key:copy.deepcopy(self.fields_preview[key]) for key in ('system_id','edit_token','revision','time','frame','fields_revision')}
                reading.update(map_id=self.fields_preview['render']['id'],layer=layer,sample=copy.deepcopy(value['samples'][index]))
                with self.lock:self.field_reading=reading
                return reading
            if name=='export_fields':
                from artifacts import export_json
                with self.lock:preview=copy.deepcopy(self.fields_preview);state=copy.deepcopy(self.latest)
                if preview is None:raise ValueError('Meça o mapa antes de exportar.')
                stale=any(preview[k]!=state[k] for k in ('system_id','edit_token','revision','time')) or preview['fields_revision']!=state['field_layers']['revision']
                return export_json('gravity-fields',{'schema':1,'definition':state['field_layers'],'reading':preview,'reading_is_stale':stale,
                    'origin_kind':state['origin_kind'],'atlas_initial':state.get('atlas_initial')})
            ack=self._worker_command(action)
            if name=='sample_fields':
                self._show_fields(ack['result'])
                # The command response also stays bounded for the browser.
                ack={**ack,'result':self.fields_public}
            else:self._clear_fields()
            return ack
        if name in ('configure_instruments','sample_instruments','clear_instrument_readings','export_instruments'):
            if self.mode!='experiment':raise ValueError('Abra o laboratório primeiro.')
            if name=='clear_instrument_readings':
                self._clear_instruments();return {'command':name}
            if name=='export_instruments':
                from artifacts import export_json
                with self.lock:
                    preview=copy.deepcopy(self.instruments_preview)
                    state=copy.deepcopy(self.latest)
                if preview is None:raise ValueError('Meça as sondas antes de exportar.')
                stale=any(preview[key]!=state[key] for key in ('system_id','edit_token','revision','time')) or preview['instruments_revision']!=state['instruments']['revision']
                return export_json('gravity-instruments',{'schema':1,'definitions':state['instruments'],
                                   'reading':preview,'reading_is_stale':stale,
                                   'origin_kind':state['origin_kind'],'atlas_initial':state.get('atlas_initial')})
            ack=self._worker_command(action)
            if name=='sample_instruments':self._show_instruments(ack['result'])
            else:self._clear_instruments()
            return ack
        if name in ('probe','clear_probe'):
            if self.mode!='experiment':raise ValueError('Abra o laboratório primeiro.')
            if name=='clear_probe':
                self._lua('openspace.setPropertyValueSingle("Scene.LabProbe.Renderable.Enabled",false);return {ready=true}',True)
                with self.lock:self.probe_preview=None
                return {'command':name}
            ack=self._worker_command(action);result=ack['result']
            with self.lock:initial=self.latest.get('atlas_initial')
            point=self._display_positions([{'position':[v/SCALE for v in result['position_m']]}],initial)[0]
            self._lua('openspace.setPropertyValueSingle("Scene.LabProbe.Translation.Position",{'+','.join(format(v,'.17g') for v in point)+'});openspace.setPropertyValueSingle("Scene.LabProbe.Renderable.Enabled",true);return {ready=true}',True)
            with self.lock:self.probe_preview=result
            return ack
        if name in ('orbit','clear_orbit'):
            if self.mode!='experiment':raise ValueError('Abra o laboratório primeiro.')
            if name=='clear_orbit':self._clear_orbit();return {'command':name}
            ack=self._worker_command(action);self._show_orbit(ack['result']);return ack
        if name=='display':
            if self.mode!='experiment':raise ValueError('Abra o laboratório primeiro.')
            radius=action.get('physical_radii');axes=action.get('axes_body')
            with self.lock:ids=[b['id'] for b in self.latest['bodies']]
            if type(radius) is not bool or axes is not None and axes not in ids:raise ValueError('Modo de exibição inválido.')
            with self.lock:self.physical_radii,self.axes_body=radius,axes
            self.rendered_sequence=None;self._render()
            return {'command':'display'}
        if name == 'import_atlas':
            ack = self._worker_command(action)
            with self.lock:
                count = len(self.latest['bodies'])
            self._make_scene(count)
            with self.lock:
                self.mode = 'experiment'
            self.rendered_sequence = None
            self._render()
            return ack
        if name == 'enter':
            self._start_worker()
            ack = self._worker_command({'command':'snapshot'})
            with self.lock:
                count = len(self.latest['bodies'])
            if self.mode != 'experiment' or count != self.rendered_count:
                self._make_scene(count)
            with self.lock:
                self.mode = 'experiment'
            return ack
        if name == 'atlas':
            if self.worker:
                self._worker_command({'command':'pause'})
            self._lua('openspace.navigation.setNavigationState({Anchor="Earth",Position={-16000000,-17000000,10000000},Up={0,0,1}});return {ready=true}',True)
            self._clear_scene()
            with self.lock:
                self.mode = 'atlas'
            return {'command':'atlas'}
        if name not in ('load_experiment','pause','resume','reset','set_mass','set_body','set_attributes','create_body','remove_body','new_system','restart_seed','rate','save','load','restart_atlas'):
            raise ValueError('Comando desconhecido')
        if self.mode != 'experiment':
            raise ValueError('Abra o laboratório primeiro.')
        ack = self._worker_command(action)
        if name in ('load_experiment','reset','load','restart_atlas','new_system','restart_seed'):
            with self.lock:
                count = len(self.latest['bodies'])
                if name=='load_experiment':self.physical_radii=False;self.axes_body=None
            self._make_scene(count)
        elif name in ('create_body','remove_body'):
            self._sync_scene()
        self.rendered_sequence = None
        return ack

    def _render(self):
        with self.lock:
            state = self.latest
            mode = self.mode
        if mode != 'experiment' or state is None:
            return
        key = (state['sequence'],state['revision'],state['time'],state['system_id'],self.physical_radii,self.axes_body)
        if key == self.rendered_sequence:
            return
        code = '';updates={}
        positions = self._display_positions(state['bodies'], state.get('atlas_initial'))
        for i,position in enumerate(positions):
            body=state['bodies'][i];a=body['attributes'];node=body['scene_node'];spin=body['spin_node'];surface=body['shape_node']
            xyz = ','.join(format(v,'.17g') for v in position)
            size=a['radius_m'] if self.physical_radii and a['radius_m'] else self._marker_size(body,i,bool(state.get('atlas_initial')))
            visible=not self.physical_radii or a['radius_m'] is not None and a['radius_m']>0
            cached=self.rendered_attributes.get(body['id'],{});shape=(size,visible,self.physical_radii,a['radius_m']);axes_visible=body['id']==self.axes_body and visible;q=tuple(a['orientation_wxyz'])
            code += f'openspace.setPropertyValueSingle("Scene.{node}.Translation.Position",{{{xyz}}});'
            if cached.get('shape')!=shape:
                code += f'openspace.setPropertyValueSingle("Scene.{node}.Renderable.Size",{self._marker_size(body,i,bool(state.get("atlas_initial"))):.17g});'
                code += f'openspace.setPropertyValueSingle("Scene.{node}.Renderable.Enabled",{str(not self.physical_radii).lower()});'
                code += f'openspace.setPropertyValueSingle("Scene.{surface}.Renderable.Size",{(a["radius_m"] or 1):.17g});openspace.setPropertyValueSingle("Scene.{surface}.Renderable.Enabled",{str(self.physical_radii and visible).lower()});'
                code += f'openspace.setPropertyValueSingle("Scene.{body["label_node"]}.Translation.Position",{{0,0,{size*1.5:.17g}}});openspace.setPropertyValueSingle("Scene.{spin}.Scale.Scale",{size*1.4:.17g});'
            if cached.get('orientation')!=q:
                euler=rotation_euler(q,state['atlas_initial']['j2000_to_render_frame'] if state.get('atlas_initial') else None)
                code += f'openspace.setPropertyValueSingle("Scene.{spin}.Rotation.Rotation",{{{",".join(format(v,".17g") for v in euler)}}});'
                code += f'openspace.setPropertyValueSingle("Scene.{surface}.Rotation.Rotation",{{{",".join(format(v,".17g") for v in euler)}}});'
            if cached.get('axes_visible')!=axes_visible:code+=f'openspace.setPropertyValueSingle("Scene.{spin}.Renderable.Enabled",{str(axes_visible).lower()});'
            updates[body['id']]={'shape':shape,'orientation':q,'axes_visible':axes_visible}
        center = [(min(p[k] for p in positions)+max(p[k] for p in positions))/2 for k in range(3)]
        xyz = ','.join(format(v,'.17g') for v in center)
        code += f'openspace.setPropertyValueSingle("Scene.LabFrame.Translation.Position",{{{xyz}}});'
        barycenter=self._display_positions([{'position':state['conservation']['current']['barycenter']}],state.get('atlas_initial'))[0]
        code += 'openspace.setPropertyValueSingle("Scene.LabBarycenter.Translation.Position",{'+','.join(format(v,'.17g') for v in barycenter)+'});'
        pair=(state.get('experiment',{}).get('analysis') or {}).get('pair')
        if pair and len(pair)==2:
            bodies=[b for b in state['bodies'] if b['id'] in pair];mass=sum(b['mass'] for b in bodies)
            center=[sum(b['mass']*b['position'][k] for b in bodies)/mass for k in range(3)]
            point=self._display_positions([{'position':center}],state.get('atlas_initial'))[0]
            code+='openspace.setPropertyValueSingle("Scene.LabPairFrame.Translation.Position",{'+','.join(format(v,'.17g') for v in point)+'});'
        self._lua(code)
        self.rendered_attributes.update(updates)
        self.rendered_sequence = key

    def _run(self):
        try:
            while not self.stop_event.is_set():
                try:
                    action,future = self.actions.get(timeout=1/60)
                except queue.Empty:
                    action,future = None,None
                try:
                    if action is not None:
                        if not future.set_running_or_notify_cancel():
                            continue
                        self._trace('action_started',command=action.get('command'))
                        response = self._apply(action)
                        with self.lock:
                            self.error = None
                        future.set_result({'ok':True,'ack':response})
                    self._render()
                except Exception as error:
                    self._trace('action_or_renderer_error',command=action.get('command') if action else None,
                                detail=f'{type(error).__name__}: {error}')
                    with self.lock:
                        self.error = None if isinstance(error,ValueError) else str(error) or type(error).__name__
                    if future and not future.done():
                        future.set_exception(error)
                    # Rejected input did not affect the renderer. Closing its socket
                    # here delayed the next pause and let a running model evolve.
                    if isinstance(error,ValueError):continue
                    # Do not accumulate renderer work when the window has closed.
                    self.rendered_attributes={}
                    if self.engine is not None:
                        self.engine.close()
                        self.engine = None
                    with self.lock:
                        self.engine_ready = False
                    self.stop_event.wait(.25)
        finally:
            if self.worker and self.worker.poll() is None:
                try:
                    self.worker.stdin.write('{"command":"quit"}\n');self.worker.stdin.flush()
                    self.worker.wait(timeout=3)
                except (OSError,subprocess.TimeoutExpired):
                    self.worker.kill();self.worker.wait()
            if self.engine:
                self.engine.close()
