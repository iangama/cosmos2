"""Serial solar-zone instrument with an explicitly archived native source."""
from pathlib import Path
from concurrent.futures import Future
import copy
import json
import queue
import threading
import time
import uuid
from is5_compression_client import Client
from is5_compression_artifact import Store, core, parameters, active_channels
from is4_laboratory import ParticleLaboratory
from is4_stream_scene import lua

HERE = Path(__file__).resolve().parent


class SolarLaboratory:
    _native = ParticleLaboratory._native

    def __init__(self, lab):
        self.lab = lab
        self.actions = queue.Queue(maxsize=16)
        self.lock = threading.Lock()
        self.public = {'active': False, 'busy': False, 'error': None}
        self.storage = HERE.parent / 'solar-zone-checkpoints'
        self.storage.mkdir(parents=True, exist_ok=True)
        self.client = self.engine = self.camera = self.scene = None
        self.hidden = {}
        self._calculation = None
        self._branch_parent = None
        self._command_admitted = False
        self.topic = 0
        self.playing = False
        self.rate = 8
        self.next_sample = 0
        self.error = None
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def status(self):
        with self.lock:
            result = copy.deepcopy(self.public)
            result['busy'] = bool(result.get('busy') or self._command_admitted)
            tx = self._calculation
            result['calculation'] = None if tx is None else dict(
                transaction_id=tx['id'], phase=tx['phase'], cancellable=tx['phase']=='calculating',
                elapsed_wall_s=time.monotonic()-tx['started'])
            return result

    def command(self, request):
        if not isinstance(request, dict):
            raise ValueError('Comando da zona solar deve ser um objeto.')
        closing = request.get('command') == '_close'
        with self.lock:
            if not closing and (self._command_admitted or self.public.get('busy')):
                raise ValueError('Aguarde a confirmação do cálculo em andamento.')
            if not closing:
                self._command_admitted = True
        future = Future()
        try:
            self.actions.put_nowait((copy.deepcopy(request), future))
        except queue.Full:
            with self.lock:
                if not closing:self._command_admitted = False
            raise ValueError('Aguarde os comandos da zona solar em andamento.')
        return future.result(timeout=720)

    def _publish(self, busy=False):
        value = dict(active=self.client is not None, busy=busy, error=self.error,
                     worker=None if self.client is None else dict(self.client.snapshot(),branch_parent=self._branch_parent),
                     playing=self.playing, samples_per_wall_s=self.rate,
                     scene=copy.deepcopy(self.scene),
                     checkpoint_available=(self.storage / 'saved.json').is_file())
        with self.lock:
            self.public = value

    def _hide(self):
        if self.camera is not None:
            return
        state = self.lab.status()
        p = state['physics']
        self.camera = self._native('return {navigation=openspace.navigation.getNavigationState("Root")}')['navigation']
        names = ['LabGrid', 'LabBarycenter', 'LabProbe']
        for body in p['bodies']:
            names += [body[k] for k in ('scene_node', 'label_node', 'shape_node', 'spin_node') if body.get(k)]
        layer = state.get('body_field_preview')
        if layer:
            names += [m['node'] for m in layer['render']['meshes']] + [layer['render']['label_node']]
        self.hidden = self._native('local f={};for _,n in ipairs(' + lua(names) + ') do if openspace.hasSceneGraphNode(n) then local ok,v=pcall(openspace.propertyValue,"Scene."..n..".Renderable.Enabled");if ok and type(v)=="boolean" then f[n]=v;openspace.setPropertyValueSingle("Scene."..n..".Renderable.Enabled",false) end end end;return {flags=f}')['flags']

    def _attach(self, state):
        source = state['source']
        if self.scene is not None:
            # Retain initialized GL resources during a scientific artifact swap.
            old = copy.deepcopy(self.scene)
            node, label = old['node'], old['label_node']
            try:
                confirmed = self._native('openspace.setPropertyValueSingle("Scene.' + node + '.Translation.Position",' + lua(source['center_render_m']) + ');return {position=openspace.propertyValue("Scene.' + node + '.Translation.Position")}')
                if confirmed['position'] != source['center_render_m']:
                    raise ValueError('A fonte solar arquivada não foi confirmada.')
                self._frame(node)
            except Exception:
                self._native('openspace.setPropertyValueSingle("Scene.' + node + '.Translation.Position",' + lua(old['center_render_m']) + ');return {ready=true}')
                raise
            self.scene = dict(old, source_binding_sha256=source['binding_sha256'],
                              source_epoch=source['epoch'], center_render_m=confirmed['position'])
            return
        node = 'IS5Sun_' + uuid.uuid4().hex
        label = node + '_Label'
        position = lua(source['center_render_m'])
        text = lua('Sol arquivado')
        code = 'openspace.addSceneGraphNode({Identifier="' + node + '",Parent="LabRoot",Transform={Translation={Type="StaticTranslation",Position=' + position + '}},Renderable={Type="RenderableSphereImageLocal",Size=4e8,Segments=32,Texture=openspace.absPath("${COSMOS2}/data/markers/central.ppm")},GUI={Name="Sol arquivado · zona prescrita"}});'
        code += 'openspace.addSceneGraphNode({Identifier="' + label + '",Parent="' + node + '",Transform={Translation={Type="StaticTranslation",Position={-5e8,0,6e8}}},Renderable={Type="RenderableLabel",RenderBinMode="Overlay",Text=' + text + ',FontSize=50,Size=8,MinMaxSize={14,22},OrientationOption="Camera View Direction",EnableFading=false},GUI={Name="Fonte arquivada",Focusable=false}});return {ready=true}'
        try:
            self._native(code)
            deadline = time.monotonic() + 15
            while self._native('return openspace.cosmos2SceneInitialization()')['cpu_initializing']:
                if time.monotonic() > deadline:
                    raise TimeoutError('A cena da fonte solar não inicializou no prazo.')
                time.sleep(.025)
            confirmed = self._native('return {position=openspace.propertyValue("Scene.' + node + '.Translation.Position"),enabled=openspace.propertyValue("Scene.' + node + '.Renderable.Enabled"),text=openspace.propertyValue("Scene.' + label + '.Renderable.Text")}')
            if confirmed['position'] != source['center_render_m'] or not confirmed['enabled']:
                raise ValueError('A cena não confirmou a posição da fonte arquivada.')
            self._frame(node)
        except Exception:
            self._remove(node, label)
            raise
        old = self.scene
        self.scene = dict(node=node, label_node=label, source_binding_sha256=source['binding_sha256'],
                          source_epoch=source['epoch'], center_render_m=confirmed['position'],
                          label=confirmed['text'], confirmed=True, marker_radius_m=4e8,
                          scope='Marcador gráfico do Sol arquivado; sem raio do núcleo ou emissão espacial.')
        if old:
            self._remove(old['node'], old['label_node'])

    def _frame(self, node=None):
        node = node or self.scene['node']
        self._native('openspace.navigation.setNavigationState({Anchor="' + node + '",ReferenceFrame="Root",Position={0,-6e9,2e9},Up={0,0,1}});return {ready=true}')

    def _remove(self, node, label):
        self._native('if openspace.hasSceneGraphNode("' + label + '") then openspace.removeSceneGraphNode("' + label + '") end;if openspace.hasSceneGraphNode("' + node + '") then openspace.removeSceneGraphNode("' + node + '") end;return {ready=true}')

    def _restore(self):
        # Move the camera before removing its archived anchor.
        if self.camera is not None:
            self._native('openspace.navigation.setNavigationState(' + lua(self.camera) + ');return {ready=true}')
        if self.scene:
            self._remove(self.scene['node'], self.scene['label_node'])
        if self.hidden:
            self._native('for n,v in pairs(' + lua(self.hidden) + ') do if openspace.hasSceneGraphNode(n) then openspace.setPropertyValueSingle("Scene."..n..".Renderable.Enabled",v) end end;return {ready=true}')
        self.scene = self.camera = None
        self.hidden = {}

    @staticmethod
    def _thermal_state(client):
        state=client.snapshot()
        if state['configuration']['mode']!='prescribed_density':
            raise ValueError('Arquivo sem programa de densidade não pertence a este instrumento.')
        return state

    def _guard(self, request):
        if self.client is None:
            raise ValueError('Crie ou restaure a zona solar primeiro.')
        guard = request.get('guard')
        if not isinstance(guard, dict) or type(guard.get('revision')) is not int or guard != Client.guard(self.client.snapshot()):
            raise ValueError('A zona solar mudou; atualize a leitura.')

    def _apply(self, request):
        name = request.get('command')
        fields = {'create': {'source_guard', 'configuration'}, 'configure': {'configuration'},
                  'sample': {'index'}, 'set_view': {'view'}, 'branch_create': {'name'},
                  'branch_load': {'branch_id'}, 'set_rate': {'value'}}
        names = {'create', 'load_saved', 'leave', 'configure', 'sample', 'set_view', 'branch_create',
                 'branch_load', 'save', 'load', 'get_result', 'export', 'restart', 'new_worker',
                 'play', 'pause', 'set_rate', 'frame'}
        expected = {'command'} | fields.get(name, set()) | ({'guard'} if name not in {'create', 'load_saved'} else set())
        if name not in names or set(request) != expected:
            raise ValueError('Campos do comando da zona solar incompatíveis.')
        if name in {'create','configure'} and (not isinstance(request.get('configuration'),dict) or request['configuration'].get('mode')!='prescribed_density'):
            raise ValueError('Este instrumento exige densidade prescrita e configuração completa.')
        if name in {'create','configure'}:
            # Reject malformed proposals before starting the candidate processes.
            # The worker still repeats all admission and trajectory checks.
            configuration=request['configuration']
            required={'parameters','density_history','acting','channel_switches','mode','include_coulomb','include_screening'}
            if set(configuration)!=required:
                raise ValueError('Complete Coulomb scenario configuration required')
            if not isinstance(configuration['acting'],dict) or not isinstance(configuration['channel_switches'],dict):
                raise ValueError('Explicit force/channel switches required')
            if not isinstance(configuration['parameters'],dict) or set(configuration['parameters'])!=set(core.base.DEFAULT_PARAMETERS):
                raise ValueError('Exact initial-zone parameter fields required')
            p=parameters(configuration['parameters'])
            core.density_program(configuration['density_history'],p)
            active_channels(configuration['acting'],configuration['channel_switches'])
            ce=configuration['include_coulomb'];sc=configuration['include_screening']
            if type(ce) is not bool or type(sc) is not bool or sc and not ce:
                raise ValueError('Coulomb mode/options invalid')
        if name not in {'create', 'load_saved'}:
            self._guard(request)
        if name in {'create', 'load_saved'}:
            if self.client is not None:
                raise ValueError('Feche a zona solar antes de abrir outra.')
            lab = self.lab.status()
            p = lab['physics']
            if lab['mode'] != 'experiment' or not p or not p['paused'] or len(p['bodies']) != 4:
                raise ValueError('Abra uma cópia solar pausada de quatro centros.')
            if name == 'create':
                expected = {k: p[k] for k in ('system_id', 'edit_token', 'revision', 'time')} | {'frame': p['contract']['frame']}
                guard = request['source_guard']
                if not isinstance(guard, dict) or type(guard.get('revision')) is not int or type(guard.get('time')) not in (int, float) or guard != expected:
                    raise ValueError('A fase solar mudou; atualize a leitura.')
            payload = {'source_phase':p,'configuration':request['configuration']} if name=='create' else {}
            self._compute('create' if name=='create' else 'load',payload)
        elif name == 'leave':
            self._branch_parent=None
            self.playing = False
            self._restore()
            self.client.close()
            self.client = None
        elif name in {'load', 'branch_load', 'new_worker'}:
            self.playing = False
            action='branch_load' if name=='branch_load' else 'load'
            self._compute(action,{'branch_id':request['branch_id']} if action=='branch_load' else {})
        elif name in {'configure','restart'}:
            self.playing=False
            previous=self.client.call('get_result')['result']
            config=request['configuration'] if name=='configure' else previous['configuration']
            preferences=copy.deepcopy(self.client.snapshot()['view']);preferences['selected_index']=0
            self._compute('create',{'source_phase':previous['source_phase'],'configuration':config},
                          preferences=preferences,retain_parent=True)
        elif name in {'play', 'pause'}:
            self.playing = name == 'play' and self.client.snapshot()['view']['selected_index'] < 240
            self.next_sample = time.monotonic() + 1 / self.rate
        elif name == 'set_rate':
            if type(request['value']) is not int or request['value'] not in (2, 8, 24):
                raise ValueError('Escolha2,8ou24amostras calculadas/s.')
            self.rate = request['value']
        elif name == 'frame':
            self._frame()
        elif name == 'get_result':
            return self.client.call('get_result')['result']
        else:
            self.playing = False
            extra = {k: request[k] for k in fields.get(name, set())}
            if name == 'branch_create':
                extra['parent'] = self._branch_parent
            result=self.client.call(name, extra)['result']
            if name=='branch_create':self._branch_parent=result['branch']['id']
            return result

    def cancel(self, request):
        """Short HTTP route: never wait behind the long scene-command mutex."""
        if not isinstance(request,dict) or set(request)!={'transaction_id'}:
            raise ValueError('Identidade exata do cálculo requerida.')
        with self.lock:
            tx=self._calculation
            if tx is None or request['transaction_id']!=tx['id'] or tx['phase']!='calculating':
                raise ValueError('O cálculo mudou ou já está sendo confirmado.')
            tx['cancelled'].set()
            candidate=tx['client']
            tx['quit_requested']=candidate is not None
        # The science owner confirms its child is dead before acknowledging quit.
        # _compute owns Client.close(), so two threads never close its pipes.
        if candidate is not None and candidate.process.poll() is None:
            try:candidate.call('quit')
            except (ValueError,RuntimeError):
                if candidate.process.poll() is None:raise
        if not tx['finished'].wait(5):
            raise TimeoutError('Cancelamento solicitado; aguarde a confirmação do processo.')
        return dict(ok=True,cancelled_transaction_id=tx['id'],zone=self.status())

    def _compute(self, action, payload, preferences=None, retain_parent=False):
        """Compute in a candidate; only a successful commit replaces confirmed data."""
        previous=self.client
        tx=dict(id=uuid.uuid4().hex,phase='calculating',client=None,quit_requested=False,started=time.monotonic(),
                cancelled=threading.Event(),finished=threading.Event())
        with self.lock:
            if self._calculation is not None:raise ValueError('Cálculo já em andamento.')
            self._calculation=tx
        candidate=None
        try:
            candidate=Client(self.storage)
            with self.lock:tx['client']=candidate
            if tx['cancelled'].is_set():raise ValueError('Cálculo cancelado; cenário anterior preservado.')
            candidate.call(action,payload)
            if tx['cancelled'].is_set():raise ValueError('Cálculo cancelado; cenário anterior preservado.')
            if preferences is not None:candidate.call('set_view',{'view':preferences})
            with self.lock:
                if tx['cancelled'].is_set():raise ValueError('Cálculo cancelado; cenário anterior preservado.')
                tx['phase']='committing'
            try:
                self._hide()
                self._attach(self._thermal_state(candidate))
            except Exception:
                if previous is None:self._restore()
                raise
            # No cancellable operation follows this confirmed scene commit.
            parent=self._branch_parent if retain_parent else candidate.snapshot()['branch_parent']
            self.client=candidate;candidate=None;self._branch_parent=parent
            if previous is not None:
                try:previous.close()
                except Exception as error:self.error='Cálculo confirmado; fechamento do processo anterior: '+str(error)
        except Exception:
            if tx['cancelled'].is_set():raise ValueError('Cálculo cancelado; cenário anterior preservado.') from None
            raise
        finally:
            with self.lock:tx['phase']='closing'
            try:
                if candidate is not None:
                    # The cancelling HTTP thread owns the outstanding quit call.
                    # Wait for that exit before close() may issue another quit.
                    if tx['quit_requested']:
                        try:candidate.process.wait(5)
                        except Exception:pass
                    candidate.close()
            finally:
                with self.lock:self._calculation=None
                tx['finished'].set()

    def _run(self):
        self._publish()
        while True:
            try:
                request, future = self.actions.get(timeout=.04)
            except queue.Empty:
                if self.playing and self.client and time.monotonic() >= self.next_sample:
                    try:
                        i = min(240, self.client.snapshot()['view']['selected_index'] + 1)
                        self.client.call('sample', {'index': i})
                        self.playing = i < 240
                        self.next_sample = time.monotonic() + 1 / self.rate
                    except Exception as error:
                        self.error = str(error)
                        self.playing = False
                    self._publish()
                continue
            if request.get('command') == '_close':
                try:
                    if self.client:
                        self.client.close()
                        self.client = None
                    if self.scene or self.camera:
                        self._restore()
                except Exception as error:
                    # The renderer may already have exited before server teardown.
                    self.error = str(error)
                finally:
                    if self.engine:
                        self.engine.close()
                    future.set_result(True)
                return
            self.error = None
            self._publish(busy=True)
            try:
                result = self._apply(request)
                self._publish()
                future.set_result(dict(ok=True, zone=self.status(), result=result))
            except Exception as error:
                self.error = str(error)
                self.playing = False
                self._publish()
                future.set_exception(error)
            finally:
                with self.lock:self._command_admitted = False

    def close(self):
        with self.lock:
            tx=self._calculation
            identifier=tx['id'] if tx is not None and tx['phase']=='calculating' else None
        if identifier is not None:
            try:self.cancel({'transaction_id':identifier})
            except (ValueError,TimeoutError):pass
        self.command({'command': '_close'})
        self.thread.join(timeout=2)
