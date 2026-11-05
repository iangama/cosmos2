"""Bounded worker-to-GPU handoff and one selection anchor, with native receipts."""
from pathlib import Path
import copy
import json
import time

import cloud_transport as wire
from cloud_scene import selected_nodes
from physics import PHYSICAL_SCALE as U


def literal(value):
    if isinstance(value, bool): return str(value).lower()
    if isinstance(value, str): return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (int, float)): return repr(value)
    if isinstance(value, list): return '{'+','.join(literal(v) for v in value)+'}'
    if isinstance(value, dict): return '{'+','.join(k+'='+literal(v) for k,v in value.items())+'}'
    raise TypeError(value)


class CloudBridge:
    def __init__(self, laboratory, path):
        self.lab, self.path = laboratory, Path(path)
        self.binding = None
        self.pending = self.confirmed = self.reading = None
        self.confirmed_xyz = None
        self.selection = False
        self.last_poll = 0.
        self.failure_since = None
        self.transport_error = None
        self.public = None

    def clear(self):
        if self.binding:
            code = self.lab._freeze_anchor('C2CloudSelection')
            for node in ('C2CloudSelectionLabel','C2CloudSelection','C2CloudStream'):
                code += 'if openspace.hasSceneGraphNode('+literal(node)+') then openspace.removeSceneGraphNode('+literal(node)+') end;'
            self.lab._lua(code+'return {ready=true}', True)
        self.binding = None
        self.failure_since = None
        self.transport_error = None
        self.pending = self.confirmed = self.reading = self.confirmed_xyz = None
        self.selection = False
        with self.lab.lock: self.public = None

    @staticmethod
    def binding_for(state):
        c = state['test_particle_cloud']
        return (state['system_id'],state['edit_token'],c['cloud_id'],c['source_id'],
                state['contract']['frame'],c['test_particles'])

    def update(self, state, force=False):
        if not state.get('test_particle_cloud'):
            self.clear()
            return
        binding = self.binding_for(state)
        if self.binding != binding:
            self.clear()
            self.binding = binding
            if not self._publish(state):
                self.binding=None
                return
            node = {'Identifier':'C2CloudStream','Parent':'LabRoot',
                'Renderable':{'Type':'RenderablePointCloud','ConfirmedCloud':{
                    'File':self.path.as_posix(),'SystemId':binding[0],'EditToken':binding[1],
                    'CloudId':binding[2],'SourceId':binding[3],'Frame':binding[4],
                    'Count':binding[5],'TimeUnitS':U['time_unit_s']},
                    'Unit':'m','UseCaching':False,'Texture':{'Enabled':False},
                    'SizeSettings':{'ScaleExponent':7.1,'ScaleFactor':1.,
                        'EnableMaxSizeControl':True,'MaxSize':.15},
                    'Coloring':{'FixedColor':[.35,.8,.88]},'UseAdditiveBlending':False},
                'GUI':{'Name':'Partículas de teste sem massa'}}
            self.lab._lua('openspace.addSceneGraphNode('+literal(node)+');return {ready=true}',True)
        if not force and self.pending is None and self.confirmed and state.get('cloud_transport',{}).get('status')=='published' and state.get('cloud_transport',{}).get('metadata',{}).get('sequence',0) <= self.confirmed['metadata']['sequence']: return
        if not force and time.perf_counter()-self.last_poll < 1/60: return
        self.last_poll = time.perf_counter()
        response = self.lab._lua('return {status=openspace.propertyValue("Scene.C2CloudStream.Renderable.ConfirmedCloudStatus")}', True)
        if not isinstance(response.get('status'),str): return
        native = json.loads(response['status'])
        if native.get('state') == 'rejected':
            raise RuntimeError('O motor recusou o pacote de partículas: '+str(native))
        if self.pending and native.get('state') == 'accepted' and native.get('gpu_buffer_uploaded') and native.get('metadata') == self.pending[0]:
            self.confirmed = native
            self.confirmed_xyz = self.pending[1]
            self.pending = None
            if self.selection:
                position = self.confirmed_xyz[self.reading['index']].tolist()
                self.lab._lua('openspace.setPropertyValueSingle("Scene.C2CloudSelection.Translation.Position",'+literal(position)+');')
        with self.lab.lock:
            self.public = {'native':copy.deepcopy(self.confirmed),
                'pending_sequence':None if self.pending is None else self.pending[0]['sequence'],
                'reading':copy.deepcopy(self.reading),
                'reading_is_stale':bool(self.reading and any(self.reading[k] != v for k,v in
                    [('system_id',state['system_id']),('edit_token',state['edit_token']),('time_model',state['time'])])),
                'selection_follows_confirmed_positions':self.selection,
                'transport_error':self.transport_error,
                'scope':'Uma fonte newtoniana; partículas sem massa, sem reação ou interação entre si. Dados SI float64; gráfico quantizado float32.'}
        if self.pending is None:
            self._publish(state)

    def _transient(self, error):
        self.transport_error=str(error)
        if self.failure_since is None:self.failure_since=time.perf_counter()
        if time.perf_counter()-self.failure_since>2.:
            raise RuntimeError('Transporte de partículas indisponível por mais de2s: '+str(error))
        return False

    def _publish(self, state):
        transport = state.get('cloud_transport',{})
        if transport.get('status') != 'published':
            return self._transient(transport.get('error','aguardando worker'))
        minimum = 0 if self.confirmed is None else self.confirmed['metadata']['sequence']
        if transport['metadata']['sequence'] <= minimum: return
        try:
            packet = Path(transport['packet_path']).read_bytes()
            meta, xyz = wire.decode(packet,*self.binding,minimum)
            if meta['sequence'] <= minimum: return
            wire.publish(self.path,packet)
        except PermissionError as error:
            return self._transient(error)
        self.failure_since=None
        self.transport_error=None
        self.pending = (meta,xyz)
        return True

    def select(self, action):
        with self.lab.lock: state = self.lab.latest
        if not state.get('paused') or not state.get('test_particle_cloud'):
            raise ValueError('Pause a nuvem antes de medir uma partícula.')
        request = {**action,'command':'cloud_point'}
        point = self.lab._worker_command(request)['result']
        deadline = time.perf_counter()+5
        while time.perf_counter() < deadline:
            with self.lab.lock: state = self.lab.latest
            self.update(state,force=True)
            if self.confirmed and self.confirmed['metadata']['time_model'] == point['time_model']:
                nodes = selected_nodes(self.confirmed,point,'LabRoot')
                if self.confirmed_xyz[point['index']].tolist() != point['position_m']:
                    raise RuntimeError('A seleção SI divergiu do pacote confirmado.')
                if self.selection:
                    code = 'openspace.setPropertyValueSingle("Scene.C2CloudSelection.Translation.Position",'+literal(point['position_m'])+');'
                    code += 'openspace.setPropertyValueSingle("Scene.C2CloudSelectionLabel.Renderable.Text",'+literal('tp '+str(point['index']))+');'
                else:
                    code = ''.join('openspace.addSceneGraphNode('+literal(n)+');' for n in nodes)
                self.lab._lua(code+'return {ready=true}',True)
                self.reading,self.selection = point,True
                self.update(state,force=True)
                return {'command':'select_cloud_particle','result':point}
            time.sleep(.02)
        raise TimeoutError('O motor ainda não confirmou o instante da leitura individual.')

    def export(self, action):
        from artifacts import export_json
        with self.lab.lock: state = self.lab.latest
        cloud = state.get('test_particle_cloud')
        if not cloud or any(action.get(k) != v for k,v in [('system_id',state['system_id']),
                ('edit_token',state['edit_token']),('cloud_id',cloud['cloud_id'])]):
            raise ValueError('A nuvem mudou; consulte a identidade atual antes de exportar.')
        if action['command'] == 'export_cloud_reading':
            if self.reading is None: raise ValueError('Meça uma partícula antes de exportar a leitura.')
            stale = self.reading['time_model'] != state['time']
            data = {'schema':1,'kind':'massless_test_particle_reading',
                'reading':copy.deepcopy(self.reading),'reading_is_stale':stale,
                'scientific_generation':copy.deepcopy(state['scientific_generation'])}
            result = export_json('test-particle-reading',data)
            return {'command':action['command'],'export_file':result['export_file'],'reading_is_stale':stale}
        if not state['paused']: raise ValueError('Pause a nuvem antes de exportar as posições confirmadas.')
        deadline = time.perf_counter()+5
        while time.perf_counter()<deadline:
            self.update(state,force=True)
            if self.confirmed and self.confirmed['metadata']['time_model'] == state['time']:
                meta = self.confirmed['metadata']
                body = state['bodies'][0]
                data = {'schema':1,'kind':'massless_test_particle_positions',
                    'metadata':copy.deepcopy(meta),'particle_id_pattern':'tp:'+cloud['cloud_id']+':{index}',
                    'index_origin':0,'particle_mass_kg':0.,'backreaction':False,'mutual_test_gravity':False,
                    'positions_m':self.confirmed_xyz.tolist(),
                    'source_si':{'id':body['id'],
                        'mass_kg':body['mass']*U['nominal_GM_unit_m3_s2']/U['G_m3_kg_s2'],
                        'position_m':[v*U['length_unit_m'] for v in body['position']],
                        'velocity_m_s':[v*U['velocity_unit_m_s'] for v in body['velocity']]},
                    'scientific_generation':copy.deepcopy(state['scientific_generation']),
                    'scope':'Todas as posições científicas SI float64 no instante confirmado, antes da quantização gráfica. Índices estáveis nesta população; velocidades individuais somente na leitura selecionada.'}
                result = export_json('test-particle-positions',data)
                return {'command':action['command'],'export_file':result['export_file'],
                    'count':meta['count'],'time_s':meta['time_s']}
            time.sleep(.02)
        raise TimeoutError('A cena ainda não confirmou o instante de exportação.')
