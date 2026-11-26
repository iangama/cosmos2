"""Candidate-local records with atomic, self-contained import provenance."""
from pathlib import Path
import copy
import hashlib
import json
import os
import uuid
import is6_layers_migration as migration

base = migration.store
checkpoint = migration.checkpoint
identifier = base.identifier
ROOT = base.ROOT


def decode(record):
    if isinstance(record, dict) and type(record.get('schema')) is int and record['schema'] == 1:
        scientific, visible = base.decode(record)
        return scientific, visible, None
    fields = {'schema', 'kind', 'id', 'name', 'parent', 'created_utc',
              'checkpoint', 'origin', 'record_sha256'}
    if not isinstance(record, dict) or set(record) != fields or type(record['schema']) is not int or record['schema'] != 2:
        raise ValueError('Registro com origem de importação completo obrigatório.')
    body = {k: v for k, v in record.items() if k != 'record_sha256'}
    if migration.contract.digest(body) != record['record_sha256']:
        raise ValueError('Checksum do registro importado diverge.')
    original_science, _ = migration.restore(record['origin'])
    local = {k: copy.deepcopy(v) for k, v in record.items() if k != 'origin'}
    local['schema'] = 1
    local['record_sha256'] = migration.contract.digest({k: v for k, v in local.items() if k != 'record_sha256'})
    scientific, visible = base.decode(local)
    if migration.contract.encoded(scientific) != migration.contract.encoded(original_science):
        raise ValueError('Referência atual difere da ciência de origem da importação.')
    return scientific, visible, copy.deepcopy(record['origin'])


class Store(base.Store):
    def _read(self, path):
        path = Path(path)
        if path.is_symlink() or not path.resolve().is_relative_to(self.folder):
            raise ValueError('Caminho do registro inválido.')
        if not path.is_file():
            raise ValueError('Não há referência composta salva neste caminho.')
        if path.stat().st_size > base.MAX_BYTES:
            raise ValueError('Registro composto excede o limite de tamanho.')
        raw = path.read_bytes()
        record = migration.parse(raw)
        scientific, visible, _ = decode(record)
        return record, scientific, visible

    def _record(self, scientific, visible, record_name, parent, origin=None):
        record = super()._record(scientific, visible, record_name, parent)
        if origin is not None:
            original, _ = migration.restore(origin)
            if migration.contract.encoded(original) != migration.contract.encoded(scientific):
                raise ValueError('Origem incompatível com a referência atual.')
            record.update(schema=2, origin=copy.deepcopy(origin))
            record['record_sha256'] = migration.contract.digest({k: v for k, v in record.items() if k != 'record_sha256'})
        return record

    def _write(self, path, record, *, replace):
        decode(record)
        encoded = (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf8')
        if len(encoded) > base.MAX_BYTES:
            raise ValueError('Registro composto excede o limite de tamanho.')
        path = Path(path)
        if path.is_symlink() or not path.resolve().is_relative_to(self.folder):
            raise ValueError('Destino do registro inválido.')
        if not replace and path.exists():
            raise FileExistsError('Preserve o registro composto anterior.')
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.tmp')
        try:
            with temporary.open('xb') as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return dict(path=path.as_posix(), sha256=hashlib.sha256(encoded).hexdigest(), record=self.summary(record))

    @staticmethod
    def summary(record):
        result = base.Store.summary(record)
        result['origin'] = None if record.get('origin') is None else migration.describe(record['origin'])
        return result

    def load(self, branch_id=None):
        path = self.path if branch_id is None else self.branches / (identifier(branch_id) + '.json')
        record, scientific, visible = self._read(path)
        if branch_id is not None and record['id'] != branch_id:
            raise ValueError('Identidade do ramo não corresponde ao arquivo.')
        return scientific, visible, self.summary(record), copy.deepcopy(record.get('origin'))

    def save(self, scientific, visible, *, record_name='Vista de camadas', parent=None, origin=None):
        return self._write(self.path, self._record(scientific, visible, record_name, parent, origin), replace=True)

    def branch(self, scientific, visible, *, record_name, parent=None, origin=None):
        record = self._record(scientific, visible, record_name, parent, origin)
        return self._write(self.branches / (record['id'] + '.json'), record, replace=False)

    def export(self, scientific, visible, *, parent=None, origin=None):
        record = self._record(scientific, visible, 'Referências exportadas', parent, origin)
        return self._write(self.exports / (record['id'] + '.json'), record, replace=False)

    def import_branch(self, package, *, record_name):
        scientific, visible = migration.restore(package)
        return self.branch(scientific, visible, record_name=record_name, parent=None, origin=package)
