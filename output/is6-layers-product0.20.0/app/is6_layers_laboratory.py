"""Serial coordinated-layer service; frozen models and one native owner."""
from concurrent.futures import Future
from pathlib import Path
import copy
import math
import queue
import sys
import threading
import time
import uuid
from websockets.exceptions import ConnectionClosed

from is4_laboratory import ParticleLaboratory
from is6_product_scene import protocol
import is6_layer_contract as contract
from is6_layers_saved_scene import Owner
from is6_layers_store import Store, identifier


def magnetic_reading(phase, body_id, request):
    if not isinstance(request, dict):
        raise ValueError('Informe o modelo e as coordenadas da amostra magnética.')
    body = next((b for b in phase['bodies'] if b['id'] == body_id), None)
    if body is None:
        raise ValueError('Corpo ausente na fase solar.')
    if body['reference_id'] == 'sol:naif:399':
        expected = {'model', 'latitude_deg', 'longitude_deg', 'altitude_m'}
        model = 'IGRF14'
    elif body['reference_id'] == 'sol:naif:599':
        expected = {'model', 'radius_m', 'latitude_deg', 'longitude_east_deg', 'degree'}
        model = 'JRM33'
    else:
        raise ValueError('Este corpo não possui modelo magnético interno adotado nesta vista.')
    if set(request) != expected or request['model'] != model:
        raise ValueError('Modelo e campos exatos da amostra magnética obrigatórios.')
    for key in expected - {'model', 'degree'}:
        value = request[key]
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError('Coordenadas magnéticas devem ser números finitos.')
    if model == 'IGRF14':
        return contract.earth_magnetism.read(phase, body_id, request['latitude_deg'], request['longitude_deg'], request['altitude_m'])
    if type(request['degree']) is not int or request['degree'] != 13:
        raise ValueError('Esta vista adota JRM33 grau 13.')
    return contract.jupiter_magnetism.read(phase, body_id, request['radius_m'], request['latitude_deg'], request['longitude_east_deg'], request['degree'])


class LayerLaboratory:
    _native = ParticleLaboratory._native

    def __init__(self, lab, *, storage=None, native=None):
        self.lab = lab
        self.folder = Path(storage or Path(__file__).resolve().parents[1] / 'layer-previews')
        self.store = Store(self.folder.parent / 'layer-checkpoints')
        self.catalog_signature, self.branch_catalog = None, []
        self.parent, self.loaded_record, self.archived = None, None, False
        self.engine, self.topic = None, 0
        if native is not None:
            self._native = native
        self.actions = queue.Queue(maxsize=1)
        self.lock = threading.Lock()
        self.session_id, self.revision = uuid.uuid4().hex, 0
        self.admitted, self.transaction = False, None
        self.owner = self.run = self.reading = self.scientific = self.artifact_digest = None
        self.error, self.public = None, {}
        self._publish()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def status(self):
        with self.lock:
            result = copy.deepcopy(self.public)
            result['busy'] = self.admitted
            tx = self.transaction
            result['transaction'] = None if tx is None else dict(id=tx['id'], phase=tx['phase'],
                cancellable=tx['phase'] == 'preparing', elapsed_s=time.monotonic()-tx['started'])
            return result

    def command(self, request, *, _internal=False):
        if not isinstance(request, dict) or request.get('command') == '_close' and not _internal:
            raise ValueError('Comando público de camadas inválido.')
        with self.lock:
            if self.admitted:
                raise ValueError('Aguarde a confirmação das camadas em andamento.')
            self.admitted = True
        future = Future()
        try:
            self.actions.put_nowait((copy.deepcopy(request), future))
        except Exception:
            with self.lock:
                self.admitted = False
            raise
        return future.result(timeout=70)

    def cancel(self, request):
        if not isinstance(request, dict) or set(request) != {'transaction_id'}:
            raise ValueError('ID exato da preparação obrigatório.')
        with self.lock:
            tx = self.transaction
            if tx is None or request['transaction_id'] != tx['id'] or tx['phase'] != 'preparing':
                raise ValueError('A preparação mudou ou já está sendo confirmada.')
            tx['cancel'].set()
        if not tx['finished'].wait(20):
            raise TimeoutError('Cancelamento solicitado; a limpeza ainda não foi confirmada.')
        if tx.get('cleanup_error'):
            raise RuntimeError('Limpeza das camadas pendente: ' + tx['cleanup_error'])
        return dict(ok=True, cancelled_transaction_id=tx['id'], layers=self.status())

    def _recovering(self):
        return bool(self.owner and (self.owner.faulted or self.owner.prepared or self.owner.retired))

    def _publish(self):
        snapshot = dict(active=self.run is not None, error=self.error, recovery_required=self._recovering(),
            guard=dict(session_id=self.session_id, artifact_id=None if self.run is None else self.run.id, revision=self.revision),
            artifact=None, scene=None, checkpoint_available=self.store.path.is_file(), branches=self._catalog(),
            branch_parent=self.parent, loaded_record=copy.deepcopy(self.loaded_record))
        if self.run:
            pair = self.owner.active
            payload = self.run.payload
            snapshot['artifact'] = dict(id=self.run.id, sha256=self.artifact_digest,
                source=copy.deepcopy(payload['binding']), configuration=copy.deepcopy(payload['configuration']),
                visible=copy.deepcopy(pair.visible), spatial_sample=self.run.sample(self.run.default_view()),
                magnetic=copy.deepcopy(self.reading), admission=copy.deepcopy(self.scientific['admission']),
                frozen=True, archived=self.archived, physical_coupling=False,
                live_source_guard=contract.artifact.body.guard(self.owner.display_phase))
            snapshot['scene'] = dict(spatial_frame=pair.spatial.frame, spatial_wire=pair.spatial.wire,
                magnetic_frame=pair.magnetic.frame, magnetic_nodes=list(pair.magnetic.draw_nodes))
        with self.lock:
            self.public = snapshot

    def _catalog(self):
        signature=[]
        for path in sorted(self.store.branches.glob('*.json')):
            try:
                stat=path.stat();signature.append((path.name,stat.st_size,stat.st_mtime_ns))
            except FileNotFoundError:signature.append((path.name,None,None))
        if signature!=self.catalog_signature:
            self.branch_catalog=self.store.catalog();self.catalog_signature=signature
        return copy.deepcopy(self.branch_catalog)

    def _guard(self, request):
        expected = dict(session_id=self.session_id, artifact_id=None if self.run is None else self.run.id, revision=self.revision)
        supplied = request.get('guard')
        if not isinstance(supplied, dict) or type(supplied.get('revision')) is not int or supplied != expected:
            raise ValueError('A vista de camadas mudou; atualize a leitura.')

    def _source(self, request):
        state = self.lab.status()
        phase = state.get('physics')
        if state.get('mode') != 'experiment' or not phase or not phase['paused'] or len(phase['bodies']) != 4:
            raise ValueError('Crie uma cópia solar pausada de quatro corpos.')
        if any(state.get(key) for key in ['body_field_preview', 'fields_preview', 'orbit_preview', 'instruments_preview', 'probe_preview']):
            raise ValueError('Feche as prévias e sondas orbitais antes de abrir as camadas.')
        guard = request.get('source_guard')
        if not isinstance(guard, dict) or type(guard.get('revision')) is not int or type(guard.get('time')) not in (int, float) or guard != contract.artifact.body.guard(phase):
            raise ValueError('A fase solar mudou; atualize a leitura.')
        return copy.deepcopy(phase)

    def _create(self, request):
        if self.run is not None:
            raise ValueError('Feche a vista atual antes de criar outro par de camadas.')
        phase = self._source(request)
        config = contract.artifact.configuration(request['configuration'])
        expected = {**contract.artifact.DEFAULT_CONFIGURATION, 'outer_radius_boundary_units': 3.}
        if config != expected:
            raise ValueError('Esta vista adota plano XY, 65×96, 1–3 Rref e ampliação 200.')
        reading = magnetic_reading(phase, request['body_id'], request['magnetic'])
        tx = dict(id=uuid.uuid4().hex, phase='preparing', started=time.monotonic(),
                  cancel=threading.Event(), finished=threading.Event())
        with self.lock:
            self.transaction = tx
        self.owner = Owner(self._native, phase)
        try:
            run = contract.artifact.Run.create(phase, dict(body_id=request['body_id'], source_guard=request['source_guard']), config)
            protocol.check_cancel(tx['cancel'])
            pair = self.owner.prepare(run, reading, self.folder / uuid.uuid4().hex)
            protocol.check_cancel(tx['cancel'])
            scientific = dict(schema=1, kind='independent_frozen_layer_pair', spatial=run.payload,
                              magnetic=copy.deepcopy(reading), admission=copy.deepcopy(pair.plan))
            digest = contract.digest(scientific)
            with self.lock:
                protocol.check_cancel(tx['cancel'])
                tx['phase'] = 'committing'
            visible = dict(spatial=True, magnetic=True)
            self.owner.commit(pair, visible)
            self.run, self.reading, self.scientific = run, reading, scientific
            self.artifact_digest = digest
            self.parent, self.loaded_record, self.archived = None, None, False
            self.revision += 1
            self.error = self.owner.error
            return dict(artifact_id=run.id, sha256=self.artifact_digest)
        except Exception:
            if not self.owner.faulted:
                try:
                    self.owner.close()
                except Exception as error:
                    tx['cleanup_error'] = str(error)
                    self.owner.faulted = True
                else:
                    self.owner = None
            raise
        finally:
            with self.lock:
                tx['phase'] = 'closing'

    def _leave(self):
        if self.owner:
            self.owner.close()
        self.owner = self.run = self.reading = self.scientific = self.artifact_digest = None
        self.parent, self.loaded_record, self.archived = None, None, False
        self.revision += 1

    def _current_phase(self):
        state=self.lab.status();phase=state.get('physics')
        if state.get('mode')!='experiment' or not phase or not phase['paused']:
            raise ValueError('A cópia orbital deve permanecer pausada.')
        keys=['system_id','edit_token','revision','time','bodies','atlas_initial','interventions']
        if {k:phase[k] for k in keys}!={k:self.owner.display_phase[k] for k in keys}:
            raise ValueError('A cópia orbital viva mudou; feche a vista antes de restaurar.')
        return copy.deepcopy(phase)

    def _restore(self,saved,live_phase,*,branch):
        scientific,visible,record=saved
        run=contract.artifact.Run.restore(scientific['spatial']);reading=copy.deepcopy(scientific['magnetic'])
        digest=contract.digest(scientific)
        tx=dict(id=uuid.uuid4().hex,phase='preparing',started=time.monotonic(),cancel=threading.Event(),finished=threading.Event())
        with self.lock:self.transaction=tx
        owner=self.owner or Owner(self._native,run.payload['phase'],display_phase=live_phase)
        self.owner=owner;pair=None
        try:
            protocol.check_cancel(tx['cancel'])
            pair=owner.prepare(run,reading,self.folder/uuid.uuid4().hex)
            protocol.check_cancel(tx['cancel'])
            with self.lock:
                protocol.check_cancel(tx['cancel']);tx['phase']='committing'
            owner.commit(pair,visible)
            self.run,self.reading,self.scientific=run,reading,copy.deepcopy(scientific)
            self.artifact_digest=digest;self.archived=True;self.loaded_record=record
            self.parent=record['id'] if branch else record['parent']
            self.revision+=1;self.error=owner.error
            return dict(restored_record=record,sha256=digest)
        except Exception:
            if pair is not None and pair in owner.prepared:
                try:pair.close();owner.prepared.remove(pair)
                except Exception as error:tx['cleanup_error']=str(error);owner.faulted=True
            if self.run is None and not self._recovering() and owner.active is None:self.owner=None
            raise
        finally:
            with self.lock:tx['phase']='closing'

    def _apply(self, request):
        fields = {'create': {'source_guard', 'body_id', 'configuration', 'magnetic'},
                  'set_visibility': {'visible'}, 'get_artifact': set(), 'leave': set(),
                  'load_saved': {'source_guard'}, 'load': set(), 'branch_load': {'branch_id'},
                  'save': set(), 'branch_create': {'name'}, 'export': set()}
        name = request.get('command')
        if not isinstance(name, str) or name not in fields or set(request) != {'command', 'guard'} | fields[name]:
            raise ValueError('Campos exatos do comando de camadas obrigatórios.')
        self._guard(request)
        if name != 'leave' and self._recovering():
            raise ValueError('Restauração nativa pendente; feche a vista para recuperar.')
        if name == 'leave':
            self._leave()
            return None
        if name == 'create':
            return self._create(request)
        if name == 'load_saved':
            if self.run is not None:raise ValueError('A vista já está aberta; use Restaurar salva.')
            phase=self._source(request)
            return self._restore(self.store.load(),phase,branch=False)
        if self.run is None:
            raise ValueError('Abra um par de camadas primeiro.')
        if name in {'load','branch_load'}:
            phase=self._current_phase()
            branch_id=identifier(request['branch_id']) if name=='branch_load' else None
            return self._restore(self.store.load(branch_id),phase,branch=name=='branch_load')
        if name=='save':
            return self.store.save(self.scientific,self.owner.active.visible,parent=self.parent)
        if name=='branch_create':
            saved=self.store.branch(self.scientific,self.owner.active.visible,record_name=request['name'],parent=self.parent)
            self.parent=saved['record']['id'];self.revision+=1
            return saved
        if name=='export':
            return self.store.export(self.scientific,self.owner.active.visible,parent=self.parent)
        if name == 'get_artifact':
            return dict(scientific=copy.deepcopy(self.scientific), visible=copy.deepcopy(self.owner.active.visible), sha256=self.artifact_digest)
        visible = request['visible']
        if not isinstance(visible, dict) or set(visible) != {'spatial', 'magnetic'} or any(type(v) is not bool for v in visible.values()):
            raise ValueError('Informe dois estados de visibilidade booleanos explícitos.')
        self.owner.visibility(visible)
        self.revision += 1
        return copy.deepcopy(self.owner.active.visible)

    def _run(self):
        while True:
            request, future = self.actions.get()
            closing = request.get('command') == '_close'
            value, failure = None, None
            try:
                self.error = None
                if closing:
                    self._leave()
                else:
                    value = self._apply(request)
            except Exception as error:
                self.error, failure = str(error), error
            try:
                self._publish()
            except Exception as error:
                self.error = 'Falha ao atualizar leitura das camadas: ' + str(error)
                failure = failure or error
            with self.lock:
                tx = self.transaction
                self.transaction, self.admitted = None, False
            if tx:
                tx['finished'].set()
            if failure:
                future.set_exception(failure)
            else:
                future.set_result(dict(ok=True, layers=self.status(), result=value))
            if closing:
                if self.engine:
                    self.engine.close()
                return

    def close(self):
        with self.lock:
            tx = self.transaction
            if tx and tx['phase'] == 'preparing':
                tx['cancel'].set()
        if tx:
            tx['finished'].wait(25)
        try:
            self.command(dict(command='_close'), _internal=True)
        except (ConnectionError, ConnectionClosed) as error:
            print('Layer app shutdown: native cleanup unconfirmed; renderer transport unavailable: ' + str(error), file=sys.stderr, flush=True)
        finally:
            self.thread.join(timeout=2)
        if self.thread.is_alive():
            raise TimeoutError('Thread de camadas não encerrou.')
