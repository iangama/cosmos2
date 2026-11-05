"""Atomic spatial references with the complete, immutable source capsule."""
from contextlib import contextmanager
from pathlib import Path
import copy
import hashlib
import json
import os
import time
import uuid

import is6_spatial_import as migration

ROOT = migration.ROOT
artifact = migration.artifact
MAX_BYTES = 64 * 1024 * 1024
MAX_BRANCHES = 32
FILES = [Path(__file__), ROOT / 'IS-6-IMPORTACAO-ESPACIAL-K5D-ARMAZENAMENTO.md']
sha = lambda raw: hashlib.sha256(raw).hexdigest()
IMPORTED = {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in FILES}
FIELDS = {'schema', 'kind', 'artifact', 'view', 'branch', 'lineage_parent', 'origin', 'record_sha256'}
KIND = 'is6_spatial_body_mesh_checkpoint_with_origin'


def generation():
    if any(sha((ROOT / name).read_bytes()) != seal for name, seal in IMPORTED.items()):
        raise ValueError('Restart after spatial-import store source changes')
    return dict(schema=1, id='cosmos2:is6-spatial-import-store', version='0.1.0',
                source_sha256=dict(IMPORTED), source_import=migration.generation())


def branch_name(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 80 or value != value.strip():
        raise ValueError('Spatial branch name must have 1..80 trimmed characters')
    value.encode('utf8')
    return value


def _record(payload, preferences, branch, lineage, origin):
    body = dict(schema=2, kind=KIND, artifact=copy.deepcopy(payload), view=copy.deepcopy(preferences),
                branch=copy.deepcopy(branch), lineage_parent=lineage, origin=copy.deepcopy(origin))
    return {**body, 'record_sha256': artifact.digest(body)}


class Reference:
    """Validated value; public projections cannot change its science or origin.

    New local references use local(). Imported references come from Store.load
    or import_branch. Store operations carry the origin without a separate,
    optional provenance argument that a caller could accidentally omit.
    """
    def __init__(self, record, run):
        self._record = copy.deepcopy(record)
        self._run = run

    @classmethod
    def local(cls, run, preferences):
        if not isinstance(run, artifact.Run):
            raise ValueError('Accepted spatial Run required')
        return decode(artifact.encoded(_record(run.payload, preferences, None, None, None)))

    @property
    def record(self):
        return copy.deepcopy(self._record)

    @property
    def payload(self):
        return copy.deepcopy(self._record['artifact'])

    @property
    def view(self):
        return copy.deepcopy(self._record['view'])

    @property
    def origin(self):
        return copy.deepcopy(self._record['origin'])

    @property
    def branch(self):
        return copy.deepcopy(self._record['branch'])

    @property
    def lineage_parent(self):
        return self._record['lineage_parent']

    def sample(self):
        return self._run.sample(self.view)


def decode(raw):
    """Fully validate one envelope; Store additionally checks the local graph."""
    gen = generation()
    record = migration.parse(raw, MAX_BYTES)
    if set(record) != FIELDS or type(record['schema']) is not int or record['schema'] != 2 or record['kind'] != KIND:
        raise ValueError('Complete spatial checkpoint with origin required')
    if artifact.digest({k: v for k, v in record.items() if k != 'record_sha256'}) != record['record_sha256']:
        raise ValueError('Spatial import record seal differs')
    lineage, branch = record['lineage_parent'], record['branch']
    if lineage is not None:
        artifact.identity(lineage)
    if branch is not None:
        if not isinstance(branch, dict) or set(branch) != {'id', 'parent', 'name'}:
            raise ValueError('Spatial import branch fields differ')
        artifact.identity(branch['id'])
        branch_name(branch['name'])
        if lineage != branch['id']:
            raise ValueError('Spatial import branch lineage differs')
        if branch['parent'] is not None:
            artifact.identity(branch['parent'])
            if branch['parent'] == branch['id']:
                raise ValueError('Spatial import branch is its own parent')
    run = artifact.Run.restore(record['artifact'])
    artifact.view(record['view'], run.payload['configuration'])
    if record['origin'] is not None:
        origin = migration.open_package(artifact.encoded(record['origin']))
        if artifact.encoded(origin['artifact']) != artifact.encoded(run.payload):
            raise ValueError('Spatial destination artifact differs from its source capsule')
    if generation() != gen:
        raise ValueError('Spatial import store generation changed during validation')
    return Reference(record, run)


def summary(reference):
    """Projection of an already validated reference, never an admission check."""
    record = reference.record
    origin = record['origin']
    description = None
    if origin is not None:
        binding = origin['artifact']['binding']
        description = dict(source_format=origin['source_format'], source_sha256=origin['source_sha256'],
            package_sha256=origin['package_sha256'], artifact_sha256=origin['artifact_sha256'],
            body_reference_id=binding['body_reference_id'], epoch=copy.deepcopy(binding['epoch']),
            original_view=copy.deepcopy(origin['view']), original_lineage=copy.deepcopy(origin['original_lineage']),
            destination_instrument='spatial', magnetic_sample_created=False, scientific_resampling=False)
    return dict(branch=record['branch'], lineage_parent=record['lineage_parent'],
                artifact_id=record['artifact']['id'], artifact_sha256=artifact.digest(record['artifact']),
                view=record['view'], origin=description, record_sha256=record['record_sha256'])


class Store:
    def __init__(self, folder):
        requested = Path(folder)
        self.folder = requested.resolve()
        if requested.is_symlink() or not self.folder.is_relative_to((ROOT / 'output').resolve()):
            raise ValueError('Spatial import records must remain under output')
        self.folder.mkdir(parents=True, exist_ok=True)
        self.branches = self._path(self.folder / 'branches')
        self.exports = self._path(self.folder / 'exports')
        self.branches.mkdir(exist_ok=True)
        self.exports.mkdir(exist_ok=True)
        self.path = self.folder / 'saved.json'
        # A crashed writer can leave an uncommitted temporary. Only our own
        # exact temporary names are reclaimed, under the same process lock.
        with self.writer():
            pass

    def _path(self, path):
        path = Path(path)
        resolved = path.resolve()
        if path.is_symlink() or not resolved.is_relative_to(self.folder):
            raise ValueError('Spatial import record escaped its store')
        # Also reject an intermediate symlink, even if it points inside.
        if any(p.is_symlink() for p in path.parents if p != self.folder and p.is_relative_to(self.folder)):
            raise ValueError('Spatial import directory alias is not a record location')
        return resolved

    @contextmanager
    def writer(self):
        lock = self._path(self.folder / 'writer.lock')
        with lock.open('a+b') as handle:
            if handle.tell() == 0:
                handle.write(b'0')
                handle.flush()
            until = time.monotonic() + 2
            while True:
                try:
                    handle.seek(0)
                    if os.name == 'nt':
                        import msvcrt
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic() >= until:
                        raise
                    time.sleep(.01)
            try:
                self._cleanup_temporaries()
                yield
            finally:
                handle.seek(0)
                if os.name == 'nt':
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _cleanup_temporaries(self):
        for folder in [self.folder, self.branches, self.exports]:
            for path in folder.glob('.*.tmp'):
                pieces = path.name[1:-4].rsplit('.', 1)
                if len(pieces) != 2:
                    continue
                base, nonce = pieces
                try:
                    artifact.identity(nonce)
                    if folder == self.folder:
                        if base != 'saved.json':
                            continue
                    else:
                        if not base.endswith('.json'):
                            continue
                        artifact.identity(base[:-5])
                except ValueError:
                    continue
                self._path(path).unlink()

    def _read_file(self, path, branch_id=None):
        path = self._path(path)
        if path.stat().st_size > MAX_BYTES:
            raise ValueError('Spatial import record byte budget exceeded')
        with path.open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
        reference = decode(raw)
        if branch_id is None:
            if reference.branch is not None:
                raise ValueError('Latest/export spatial record cannot masquerade as a branch')
        elif reference.branch is None or reference.branch['id'] != artifact.identity(branch_id):
            raise ValueError('Local spatial branch identity differs from its filename')
        return reference

    def _ancestry(self, reference):
        branch = reference.branch
        seen = set() if branch is None else {branch['id']}
        cursor = reference.lineage_parent if branch is None else branch['parent']
        while cursor is not None:
            artifact.identity(cursor)
            if cursor in seen:
                raise ValueError('Local spatial branch cycle')
            if len(seen) >= MAX_BRANCHES:
                raise ValueError('Local spatial ancestry exceeds branch budget')
            seen.add(cursor)
            parent = self._read_file(self.branches / (cursor + '.json'), cursor)
            cursor = parent.branch['parent']

    def load(self, branch_id=None):
        path = self.path if branch_id is None else self.branches / (artifact.identity(branch_id) + '.json')
        reference = self._read_file(path, branch_id)
        self._ancestry(reference)
        return reference

    def _atomic(self, path, raw, *, replace):
        # The byte bound is checked before opening either destination or temp.
        if not 0 < len(raw) <= MAX_BYTES:
            raise ValueError('Spatial import record byte budget exceeded')
        path = self._path(path)
        if not replace and path.exists():
            raise FileExistsError('Preserve existing spatial branch/export')
        temporary = self._path(path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.tmp'))
        try:
            with temporary.open('xb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            until = time.monotonic() + 2
            while True:
                try:
                    os.replace(temporary, path)
                    temporary = None
                    break
                except PermissionError:
                    if time.monotonic() >= until:
                        raise
                    time.sleep(.01)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def _commit(self, reference, preferences, *, mode, name=None):
        if not isinstance(reference, Reference):
            raise ValueError('Validated spatial Reference required')
        gen = generation()
        source = reference.record
        current_view = source['view'] if preferences is None else preferences
        # Validate the draft, including science/origin, before taking a lock.
        draft = decode(artifact.encoded(_record(source['artifact'], current_view, None,
                                               source['lineage_parent'], source['origin'])))
        if mode not in {'latest', 'branch', 'export'}:
            raise ValueError('Unknown spatial import store operation')
        if mode == 'branch':
            branch_name(name)
        with self.writer():
            self._ancestry(draft)
            branch, lineage = None, draft.lineage_parent
            path = self.path
            if mode in {'branch', 'export'}:
                if mode == 'branch' and len(list(self.branches.glob('*.json'))) >= MAX_BRANCHES:
                    raise ValueError('Spatial branch limit 32 reached')
                excluded = {source['artifact']['id']}
                if source['origin'] is not None:
                    old = source['origin']['original_lineage']
                    excluded.add(old['lineage_parent'])
                    if old['branch'] is not None:
                        excluded.update([old['branch']['id'], old['branch']['parent']])
                while True:
                    identifier = uuid.uuid4().hex
                    path = (self.branches if mode == 'branch' else self.exports) / (identifier + '.json')
                    if identifier not in excluded and not path.exists():
                        break
                if mode == 'branch':
                    branch = dict(id=identifier, parent=lineage, name=name)
                    lineage = identifier
            record = _record(draft.payload, draft.view, branch, lineage, draft.origin)
            raw = (json.dumps(record, sort_keys=True, ensure_ascii=True, allow_nan=False) + '\n').encode('utf8')
            if len(raw) > MAX_BYTES:
                raise ValueError('Spatial import record byte budget exceeded')
            if generation() != gen:
                raise ValueError('Spatial import store generation changed before commit')
            # No fallible provenance write follows the single atomic commit.
            receipt = dict(path=str(path), sha256=sha(raw), record=summary(Reference(record, draft._run)))
            self._atomic(path, raw, replace=mode == 'latest')
        return receipt

    def save(self, reference, preferences=None):
        return self._commit(reference, preferences, mode='latest')

    def branch(self, reference, *, name, preferences=None):
        return self._commit(reference, preferences, mode='branch', name=name)

    def export(self, reference, preferences=None):
        return self._commit(reference, preferences, mode='export')

    def import_branch(self, package, *, name):
        raw = package if type(package) is bytes else artifact.encoded(package)
        origin = migration.open_package(raw)
        reference = decode(artifact.encoded(_record(origin['artifact'], origin['view'], None, None, origin)))
        return self.branch(reference, name=name)

    def catalog(self):
        paths = sorted(self.branches.glob('*.json'))
        if len(paths) > MAX_BRANCHES:
            raise ValueError('Spatial branch catalog exceeds budget 32')
        result = []
        for path in paths:
            try:
                reference = self.load(path.stem)
                result.append(dict(id=path.stem, name=reference.branch['name'], valid=True,
                                   validation='Full artifact, source capsule and local ancestry.', **summary(reference)))
            except (ValueError, OSError, TypeError) as error:
                result.append(dict(id=path.stem, name='Arquivo inválido', valid=False, error=str(error)))
        return result
