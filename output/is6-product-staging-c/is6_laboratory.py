"""Serial spatial instrument, immutable runs and cancellable hidden preparations."""
from concurrent.futures import Future
from pathlib import Path
import copy
import queue
import threading
import time
import uuid

from is4_laboratory import ParticleLaboratory
from is6_product_scene import Owner, Candidate, artifact, protocol

HERE = Path(__file__).resolve().parent


class SpatialLaboratory:
    _native = ParticleLaboratory._native

    def __init__(self, lab, *, storage=None, native=None):
        self.lab = lab
        self.engine, self.topic = None, 0
        if native is not None:
            self._native = native
        self.store = artifact.Store(storage or HERE.parent / 'spatial-checkpoints')
        self.actions = queue.Queue(maxsize=1)
        self.lock = threading.Lock()
        self.admitted, self.transaction = False, None
        self.session_id, self.revision = uuid.uuid4().hex, 0
        self.owner, self.run, self.view, self.parent = None, None, None, None
        self.artifact_digest, self.sample = None, None
        self.catalog_signature, self.branch_catalog = None, []
        self.pending_cleanup = []
        self.error = None
        self.public = dict(active=False, busy=False, error=None)
        self._publish()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def status(self):
        with self.lock:
            result = copy.deepcopy(self.public)
            result['busy'] = self.admitted
            tx = self.transaction
            result['transaction'] = None if tx is None else dict(
                id=tx['id'], phase=tx['phase'], cancellable=tx['phase']=='preparing',
                elapsed_s=time.monotonic()-tx['started'])
            return result

    def command(self, request):
        if not isinstance(request, dict):
            raise ValueError('Comando da malha deve ser um objeto.')
        with self.lock:
            if self.admitted:
                raise ValueError('Aguarde a confirmação da malha em andamento.')
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
            raise RuntimeError('Cancelamento sem limpeza confirmada: ' + tx['cleanup_error'])
        return dict(ok=True, cancelled_transaction_id=tx['id'], spatial=self.status())

    def _publish(self):
        snapshot = dict(active=self.run is not None, error=self.error,
                        guard=dict(session_id=self.session_id, artifact_id=None if self.run is None else self.run.id, revision=self.revision),
                        checkpoint_available=self.store.path.is_file(), branches=self._catalog(),
                        branch_parent=self.parent, artifact=None, scene=None,
                        recovery_required=bool(self.pending_cleanup or self.owner and self.owner.faulted))
        if self.run:
            p = self.run._payload
            b = p['binding']
            snapshot['artifact'] = dict(id=self.run.id, sha256=self.artifact_digest, configuration=copy.deepcopy(p['configuration']),
                source=dict(name=b['name'], body_id=b['body_id'], reference_id=b['body_reference_id'],
                    epoch=copy.deepcopy(b['epoch']), GM_m3_s2=b['source_configuration']['GM_m3_s2'],
                    Rref_m=b['source_configuration']['material_radius_m'], boundary=copy.deepcopy(b['boundary']),
                    boundary_provenance=copy.deepcopy(b['boundary_provenance']), scope=b['scope']),
                view=copy.deepcopy(self.view), sample=copy.deepcopy(self.sample))
            active = self.owner.active
            snapshot['scene'] = dict(frame=active.frame, wire=active.wire, focus=active.focus,
                                     ready_s=active.ready_s, binding=copy.deepcopy({k:v for k,v in active.prepared.items() if k!='generation'}),
                                     presentation=copy.deepcopy(active.presentation))
            # Renderer generation is pinned in the manifest, not duplicated in polls.
            snapshot['scene']['binding'].pop('generation', None)
        with self.lock:
            self.public = snapshot

    def _catalog(self):
        signature = []
        for path in sorted(self.store.branches.glob('*.json')):
            try:
                stat = path.stat()
                signature.append((path.name, stat.st_size, stat.st_mtime_ns))
            except FileNotFoundError:
                # An external rename may race directory enumeration.
                signature.append((path.name, None, None))
        if signature != self.catalog_signature:
            self.branch_catalog = self.store.catalog()
            self.catalog_signature = signature
        return copy.deepcopy(self.branch_catalog)

    def _guard(self, request):
        expected = dict(session_id=self.session_id, artifact_id=None if self.run is None else self.run.id, revision=self.revision)
        g = request.get('guard')
        if not isinstance(g, dict) or type(g.get('revision')) is not int or g != expected:
            raise ValueError('A vista da malha mudou; atualize a leitura.')

    def _source(self, request):
        state = self.lab.status()
        p = state.get('physics')
        if state.get('mode') != 'experiment' or not p or not p['paused'] or len(p['bodies']) != 4:
            raise ValueError('Crie uma cópia solar pausada de quatro corpos.')
        for key in ['body_field_preview', 'fields_preview', 'orbit_preview', 'instruments_preview', 'probe_preview']:
            if state.get(key):
                raise ValueError('Feche as camadas e sondas orbitais antes de abrir a malha.')
        g = request.get('source_guard')
        if not isinstance(g, dict) or type(g.get('revision')) is not int or type(g.get('time')) not in (int, float) or g != artifact.body.guard(p):
            raise ValueError('A fase solar mudou; atualize a leitura.')
        return copy.deepcopy(p)

    def _replace(self, build, phase):
        tx = dict(id=uuid.uuid4().hex, phase='preparing', started=time.monotonic(),
                  cancel=threading.Event(), finished=threading.Event())
        with self.lock:
            self.transaction = tx
        owner = self.owner or Owner(self._native, phase)
        candidate = None
        try:
            run, view, parent = build()
            protocol.check_cancel(tx['cancel'])
            sample = run.sample(view)
            digest = artifact.digest(run._payload)
            protocol.check_cancel(tx['cancel'])
            # Publish cancellable status before disk preparation/native attachment.
            candidate = Candidate(self._native, run, self.store.folder / 'previews' / uuid.uuid4().hex)
            candidate.attach(tx['cancel'])
            protocol.check_cancel(tx['cancel'])
            with self.lock:
                protocol.check_cancel(tx['cancel'])
                tx['phase'] = 'committing'
            owner.commit(candidate, visible=view['visible'], cancel=tx['cancel'])
            self.owner, self.run, self.view, self.parent = owner, run, view, parent
            self.artifact_digest, self.sample = digest, sample
            candidate = None
            self.revision += 1
            self.error = owner.error
            return sample
        finally:
            try:
                if candidate is not None:
                    candidate.close()
            except Exception as error:
                tx['cleanup_error'] = str(error)
                self.pending_cleanup.append(candidate)
            if owner.faulted:
                self.owner = owner
            with self.lock:
                tx['phase'] = 'closing'
            # Signalled by the actor only after publishing preserved/current state.

    def _apply(self, r):
        name = r.get('command')
        fields = {'create': {'source_guard', 'body_id', 'configuration'},
                  'configure': {'configuration'}, 'load_saved': {'source_guard'},
                  'load': set(), 'branch_load': {'branch_id'}, 'set_view': {'view'},
                  'save': set(), 'branch_create': {'name'}, 'export': set(),
                  'get_artifact': set(), 'leave': set()}
        if name not in fields or set(r) != {'command', 'guard'} | fields[name]:
            raise ValueError('Campos exatos do comando da malha obrigatórios.')
        self._guard(r)
        if name != 'leave' and (self.pending_cleanup or self.owner and self.owner.faulted):
            raise ValueError('Restauração nativa pendente; feche a vista para recuperar.')
        if name in {'create', 'load_saved'}:
            if self.run is not None:
                raise ValueError('A malha já está aberta; use Recalcular ou feche a vista.')
            phase = self._source(r)
            if name == 'create':
                config = artifact.configuration(r['configuration'])
                selection = dict(body_id=r['body_id'], source_guard=r['source_guard'])
                def build():
                    run = artifact.Run.create(phase, selection, config)
                    return run, run.default_view(), None
            else:
                build = self.store.load
            return self._replace(build, phase)
        if name == 'leave':
            if self.owner:
                self.owner.close()
            for pending in list(self.pending_cleanup):
                pending.close()
                self.pending_cleanup.remove(pending)
            self.owner, self.run, self.view, self.parent = None, None, None, None
            self.artifact_digest, self.sample = None, None
            self.revision += 1
            return None
        if self.run is None:
            raise ValueError('Abra uma malha primeiro.')
        if name == 'configure':
            config = artifact.configuration(r['configuration'])
            old = self.run._payload
            def build():
                run = artifact.Run.create(old['phase'], old['selection'], config)
                return run, run.default_view(), self.parent
            return self._replace(build, self.owner.current_phase)
        if name in {'load', 'branch_load'}:
            return self._replace(lambda: self.store.load(r.get('branch_id')), self.owner.current_phase)
        if name == 'set_view':
            view = artifact.view(r['view'], self.run._payload['configuration'])
            sample = self.run.sample(view)
            old = self.view
            if view['visible'] != old['visible']:
                try:
                    self.owner.active.set_visible(view['visible'])
                    if self.owner.active.read_native()['draw'] is not view['visible']:
                        raise ValueError('Visibilidade da malha não confirmada.')
                except Exception:
                    try:
                        self.owner.active.set_visible(old['visible'])
                    except Exception as error:
                        self.owner.faulted = True
                        self.owner.error = 'Visibilidade anterior não restaurada: ' + str(error)
                    raise
            self.view = view
            self.sample = sample
            self.revision += 1
            return sample
        if name == 'get_artifact':
            return self.run.payload
        if name == 'export':
            return self.store.export(self.run, self.view, parent=self.parent)
        saved = self.store.save(self.run, self.view, name=r['name'] if name=='branch_create' else None, parent=self.parent)
        if name == 'branch_create':
            self.parent = saved['branch']['id']
            self.revision += 1
        return saved

    def _run(self):
        while True:
            request, future = self.actions.get()
            closing = request.get('command') == '_close'
            value, failure = None, None
            try:
                self.error = None
                if closing:
                    if self.owner:
                        self.owner.close()
                    for pending in self.pending_cleanup:
                        pending.close()
                    self.owner, self.run, self.view, self.parent = None, None, None, None
                    self.artifact_digest, self.sample = None, None
                else:
                    value = self._apply(request)
            except Exception as error:
                self.error = str(error)
                failure = error
            try:
                self._publish()
            except Exception as error:
                # A polling snapshot must not undo an acknowledged native commit.
                self.error = 'Falha ao atualizar leitura: ' + str(error)
                failure = failure or error
            with self.lock:
                tx = self.transaction
                self.transaction, self.admitted = None, False
            if tx:
                tx['finished'].set()
            if failure:
                future.set_exception(failure)
            else:
                future.set_result(dict(ok=True, spatial=self.status(), result=value))
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
        self.command(dict(command='_close'))
        self.thread.join(timeout=2)
