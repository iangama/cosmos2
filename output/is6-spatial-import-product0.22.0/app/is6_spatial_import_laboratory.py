"""Serial spatial-source import service with guarded, explicit restoration."""
from pathlib import Path
import copy
import queue
import threading
import time
import uuid

from is6_laboratory import SpatialLaboratory as BaseLaboratory
from is6_product_scene import Candidate, artifact, protocol
from is6_spatial_import_scene import Owner
import is6_spatial_import_store as storage

migration = storage.migration
PHASE_KEYS = ['system_id', 'edit_token', 'revision', 'time', 'bodies', 'atlas_initial', 'interventions']


class SpatialLaboratory(BaseLaboratory):
    def __init__(self, lab, *, storage_folder=None, native=None):
        self.lab = lab
        self.engine, self.topic = None, 0
        if native is not None:
            self._native = native
        default = Path(__file__).resolve().parent.parent / 'is6-spatial-import-service-records'
        self.store = storage.Store(storage_folder or default)
        self.reference, self.import_candidate, self.archived = None, None, False
        self.actions = queue.Queue(maxsize=1)
        self.lock = threading.Lock()
        self.admitted, self.transaction = False, None
        self.session_id, self.revision = uuid.uuid4().hex, 0
        self.owner, self.run, self.view, self.parent = None, None, None, None
        self.artifact_digest, self.sample = None, None
        self.catalog_signature, self.branch_catalog = None, []
        self.pending_cleanup, self.error = [], None
        self._publish()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _recovering(self):
        return bool(self.pending_cleanup or self.owner and (self.owner.faulted or self.owner.retired))

    def _publish(self):
        guard = dict(session_id=self.session_id, artifact_id=None if self.run is None else self.run.id, revision=self.revision)
        preview = self.import_candidate
        snapshot = dict(active=self.run is not None, error=self.error, guard=guard,
            checkpoint_available=self.store.path.is_file(), branches=self._catalog(), branch_parent=self.parent,
            artifact=None, scene=None, recovery_required=self._recovering(),
            import_preview=None if preview is None else dict(id=preview['id'], valid=preview['guard'] == guard,
                                                          **copy.deepcopy(preview['summary'])))
        if self.run is not None:
            p = self.run.payload
            b = p['binding']
            origin = storage.summary(self.reference)['origin']
            snapshot['artifact'] = dict(id=self.run.id, sha256=self.artifact_digest, configuration=copy.deepcopy(p['configuration']),
                source=dict(name=b['name'], body_id=b['body_id'], reference_id=b['body_reference_id'],
                    epoch=copy.deepcopy(b['epoch']), GM_m3_s2=b['source_configuration']['GM_m3_s2'],
                    Rref_m=b['source_configuration']['material_radius_m'], boundary=copy.deepcopy(b['boundary']),
                    boundary_provenance=copy.deepcopy(b['boundary_provenance']), scope=b['scope']),
                view=copy.deepcopy(self.view), sample=copy.deepcopy(self.sample), origin=origin,
                archived=self.archived, live_source_guard=artifact.body.guard(self.owner.display_phase))
            active = self.owner.active
            snapshot['scene'] = dict(frame=active.frame, wire=active.wire, focus=active.focus,
                ready_s=active.ready_s, binding=copy.deepcopy({k: v for k, v in active.prepared.items() if k != 'generation'}),
                presentation=copy.deepcopy(active.presentation))
            snapshot['scene']['binding'].pop('generation', None)
        with self.lock:
            self.public = snapshot

    def _phase_now(self, expected):
        state = self.lab.status()
        phase = state.get('physics')
        if state.get('mode') != 'experiment' or not phase or not phase.get('paused'):
            raise ValueError('A cópia orbital deve permanecer pausada.')
        if {k: phase.get(k) for k in PHASE_KEYS} != {k: expected.get(k) for k in PHASE_KEYS}:
            raise ValueError('A cópia orbital viva mudou; atualize a leitura antes de restaurar.')
        return copy.deepcopy(phase)

    def _current_reference(self):
        if self.reference is None or self.run is None:
            raise ValueError('Abra uma referência espacial primeiro.')
        # The actor's current parent changes only after a successful local
        # branch commit. Capsule transport is always derived from Reference.
        record = storage._record(self.run.payload, self.view, None, self.parent, self.reference.origin)
        return storage.decode(artifact.encoded(record))

    def _replace_reference(self, build, live_phase, *, archived):
        tx = dict(id=uuid.uuid4().hex, phase='preparing', started=time.monotonic(),
                  cancel=threading.Event(), finished=threading.Event())
        with self.lock:
            self.transaction = tx
        owner = self.owner or Owner(self._native, live_phase)
        candidate = None
        try:
            reference = build()
            run = artifact.Run.restore(reference.payload)
            preferences = reference.view
            sample = run.sample(preferences)
            digest = artifact.digest(run.payload)
            protocol.check_cancel(tx['cancel'])
            self._phase_now(live_phase)
            candidate = Candidate(self._native, run, self.store.folder / 'previews' / uuid.uuid4().hex)
            candidate.attach(tx['cancel'])
            protocol.check_cancel(tx['cancel'])
            self._phase_now(live_phase)
            with self.lock:
                protocol.check_cancel(tx['cancel'])
                tx['phase'] = 'committing'
            owner.commit(candidate, visible=preferences['visible'], cancel=tx['cancel'])
            self.owner, self.run, self.view, self.parent = owner, run, preferences, reference.lineage_parent
            self.reference, self.archived = reference, archived
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

    def _apply(self, request):
        fields = {'create': {'source_guard', 'body_id', 'configuration'}, 'configure': {'configuration'},
            'load_saved': {'source_guard'}, 'load': set(), 'branch_load': {'branch_id', 'source_guard'},
            'set_view': {'view'}, 'save': set(), 'branch_create': {'name'}, 'export': set(),
            'get_artifact': set(), 'leave': set(), 'import_preview': {'source_text'},
            'import_cancel': {'preview_id'}, 'import_commit': {'preview_id', 'source_text', 'name'}}
        name = request.get('command')
        if not isinstance(name, str) or name not in fields or set(request) != {'command', 'guard'} | fields[name]:
            raise ValueError('Campos exatos do comando da malha obrigatórios.')
        self._guard(request)
        if name != 'leave' and self._recovering():
            raise ValueError('Restauração nativa pendente; feche a vista para recuperar.')
        if name == 'import_preview':
            if not isinstance(request['source_text'], str):
                raise ValueError('Conteúdo JSON do arquivo obrigatório.')
            package = migration.preview(request['source_text'].encode('utf8'))
            self.import_candidate = dict(id=uuid.uuid4().hex, guard=copy.deepcopy(request['guard']),
                package=package, summary=migration.describe(package))
            return dict(preview_id=self.import_candidate['id'], **copy.deepcopy(self.import_candidate['summary']))
        if name in {'import_cancel', 'import_commit'}:
            preview = self.import_candidate
            if preview is None or request['preview_id'] != preview['id']:
                raise ValueError('A prévia de importação mudou; valide o arquivo novamente.')
            if name == 'import_cancel':
                self.import_candidate = None
                return dict(import_cancelled=True)
            if preview['guard'] != request['guard']:
                raise ValueError('A vista mudou após a prévia; valide o arquivo novamente.')
            if request['source_text'] != preview['package']['source_text']:
                raise ValueError('O arquivo mudou após a prévia; valide o novo conteúdo.')
            saved = self.store.import_branch(preview['package'], name=request['name'])
            self.import_candidate = None
            self.revision += 1
            return saved
        if name == 'leave':
            answer = super()._apply(request)
            self.reference, self.import_candidate, self.archived = None, None, False
            return answer
        if name == 'create':
            if self.run is not None:
                raise ValueError('A malha já está aberta; feche a vista antes de criar outra.')
            phase = self._source(request)
            config = artifact.configuration(request['configuration'])
            selection = dict(body_id=request['body_id'], source_guard=request['source_guard'])
            def build():
                run = artifact.Run.create(phase, selection, config)
                return storage.Reference.local(run, run.default_view())
            return self._replace_reference(build, phase, archived=False)
        if name in {'load_saved', 'branch_load', 'load'}:
            if name == 'load':
                if self.run is None:
                    raise ValueError('Abra uma malha ou use Restaurar vista salva.')
                phase = self._phase_now(self.owner.display_phase)
                branch_id = None
            else:
                phase = self._source(request)
                if self.owner is not None:
                    self._phase_now(self.owner.display_phase)
                branch_id = artifact.identity(request['branch_id']) if name == 'branch_load' else None
            return self._replace_reference(lambda: self.store.load(branch_id), phase, archived=True)
        if self.run is None:
            raise ValueError('Abra uma referência espacial primeiro.')
        if name == 'configure':
            if self.reference.origin is not None:
                raise ValueError('A referência importada conserva a configuração original. Crie uma nova referência para recalcular.')
            config = artifact.configuration(request['configuration'])
            current = self._phase_now(self.owner.display_phase)
            old = self.run.payload
            def build():
                run = artifact.Run.create(old['phase'], old['selection'], config)
                return storage.decode(artifact.encoded(storage._record(run.payload, run.default_view(), None, self.parent, None)))
            return self._replace_reference(build, current, archived=self.archived)
        if name in {'set_view', 'get_artifact'}:
            return super()._apply(request)
        reference = self._current_reference()
        if name == 'save':
            return self.store.save(reference)
        if name == 'export':
            return self.store.export(reference)
        saved = self.store.branch(reference, name=request['name'])
        self.parent = saved['record']['branch']['id']
        self.revision += 1
        return saved

    def close(self):
        try:
            super().close()
        finally:
            if not self.thread.is_alive():
                self.reference, self.import_candidate, self.archived = None, None, False
                with self.lock:
                    self.public['import_preview'] = None
