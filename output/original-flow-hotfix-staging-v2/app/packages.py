"""Read-only local data manifests and explicit streaming integrity checks."""
from pathlib import Path, PurePosixPath
import copy
import datetime
import hashlib
import json
import re
import threading

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())


class PackageStore:
    def __init__(self, root=ROOT, manifest='data/packages/catalog.json'):
        self.root = Path(root).resolve()
        raw = (self.root / manifest).read_bytes()
        self.manifest_sha256 = hashlib.sha256(raw).hexdigest()
        self.manifest = json.loads(raw)
        self.results = {}
        self.lock = threading.Lock()
        self.jobs = threading.BoundedSemaphore(1)
        self._validate()

    def _path(self, relative):
        if not isinstance(relative, str) or '\\' in relative or ':' in relative:
            raise ValueError('Caminho de dados inválido no manifesto.')
        parts = PurePosixPath(relative)
        if parts.is_absolute() or not parts.parts or parts.parts[0] != 'data' or '..' in parts.parts or str(parts) != relative:
            raise ValueError('Arquivo do pacote deve ficar em data/.')
        path = self.root / relative
        if not path.resolve().is_relative_to(self.root / 'data'):
            raise ValueError('Arquivo do pacote sai de data/ por link simbólico.')
        return path

    def _validate(self):
        if self.manifest.get('schema') != 1 or not isinstance(self.manifest.get('packages'), list):
            raise ValueError('Esquema de manifesto incompatível.')
        ids, paths = set(), set()
        for package in self.manifest['packages']:
            identifier = package.get('id')
            if not isinstance(identifier, str) or not identifier or identifier in ids:
                raise ValueError('ID de pacote ausente/duplicado.')
            ids.add(identifier)
            for key in ('name', 'version', 'content_kind', 'credits', 'terms', 'coverage', 'units', 'frame'):
                if key not in package:
                    raise ValueError('Metadado do pacote ausente: ' + key)
            if not isinstance(package.get('files'), list) or not package['files']:
                raise ValueError('Pacote sem arquivos.')
            for item in package['files']:
                path = item.get('path')
                self._path(path)
                if path in paths or type(item.get('bytes')) is not int or item['bytes'] < 0 or not isinstance(item.get('sha256'), str) or not re.fullmatch('[0-9a-f]{64}', item['sha256']):
                    raise ValueError('Arquivo/tamanho/hash inválido ou duplicado.')
                if item.get('hash_origin') not in ('preserved_acquisition_receipt', 'pinned_local_definition_v1',
                                                  'preserved_local_extraction_record', 'pinned_local_extraction_v1'):
                    raise ValueError('Origem do hash ausente.')
                paths.add(path)

    @staticmethod
    def _stamp(stat):
        return (stat.st_size, stat.st_mtime_ns, stat.st_ino)

    def catalog(self):
        result = copy.deepcopy(self.manifest)
        result['manifest_sha256'] = self.manifest_sha256
        result['verification_scope'] = 'Explicit reads verify content; cached result uses size/mtime/file identity. No continuous monitoring or provider signature.'
        with self.lock:
            previous = copy.deepcopy(self.results)
        for package in result['packages']:
            cached = previous.get(package['id'])
            current = []
            for item in package['files']:
                try:
                    path = self._path(item['path'])
                    stat = path.stat()
                    state = 'present_unverified' if stat.st_size == item['bytes'] else 'size_mismatch'
                    item['local'] = {'status': state, 'bytes': stat.st_size}
                    current.append(self._stamp(stat))
                except FileNotFoundError:
                    item['local'] = {'status': 'missing', 'bytes': None}
                    current.append(None)
                except (OSError, ValueError) as error:
                    item['local'] = {'status': 'unreadable', 'error': str(error), 'bytes': None}
                    current.append(None)
            package['total_bytes'] = sum(item['bytes'] for item in package['files'])
            package['last_verification'] = None
            if cached:
                package['last_verification'] = cached['report']
                package['verification_cache_current'] = current == cached['stamps']
            else:
                package['verification_cache_current'] = False
        return result

    def verify(self, identifier):
        package = next((p for p in self.manifest['packages'] if p['id'] == identifier), None)
        if package is None:
            raise ValueError('Pacote desconhecido.')
        if not self.jobs.acquire(blocking=False):
            raise RuntimeError('Aguarde a verificação de conteúdo em andamento.')
        try:
            files, stamps = [], []
            for item in package['files']:
                entry = {'path': item['path'], 'expected_bytes': item['bytes'], 'expected_sha256': item['sha256']}
                stamp = None
                try:
                    path = self._path(item['path'])
                    before = path.stat()
                    digest = hashlib.sha256()
                    count = 0
                    with path.open('rb') as stream:
                        while block := stream.read(1024 * 1024):
                            count += len(block)
                            digest.update(block)
                    after = path.stat()
                    actual = digest.hexdigest()
                    changed = self._stamp(before) != self._stamp(after)
                    entry.update(actual_bytes=count, actual_sha256=actual,
                                 status='changed_during_read' if changed else 'size_mismatch' if count != item['bytes'] else 'hash_mismatch' if actual != item['sha256'] else 'verified')
                    stamp = self._stamp(after)
                except FileNotFoundError:
                    entry['status'] = 'missing'
                except (OSError, ValueError) as error:
                    entry.update(status='unreadable', error=str(error))
                files.append(entry)
                stamps.append(stamp)
            report = {'package_id': identifier, 'version': package['version'],
                      'manifest_sha256': self.manifest_sha256,
                      'verified_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      'status': 'verified' if all(f['status'] == 'verified' for f in files) else 'failed',
                      'files': files, 'expected_total_bytes': sum(f['bytes'] for f in package['files']),
                      'scope': 'Local content SHA256 against pinned manifest, not provider signature.'}
            with self.lock:
                self.results[identifier] = {'report': copy.deepcopy(report), 'stamps': stamps}
            return report
        finally:
            self.jobs.release()


_STORE = None
_STORE_LOCK = threading.Lock()


def store():
    global _STORE
    with _STORE_LOCK:
        if _STORE is None:
            _STORE = PackageStore()
        return _STORE
