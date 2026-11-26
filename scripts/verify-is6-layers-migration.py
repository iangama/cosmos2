"""K5A real-model conversions, resigned corruption and independent reopen."""
from pathlib import Path
import argparse
import copy
import hashlib
import itertools
import json
import subprocess
import sys
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    parser.add_argument('--legacy-fixtures', action='store_true')
    parser.add_argument('--reopen', action='store_true')
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    folder = ROOT / ('output/is6-layers-migration-' + args.label)
    if args.legacy_fixtures:
        sys.path[:0] = [str(ROOT / 'output/is6-layers-persistence-staging'),
                       str(ROOT / 'output/is6-layers-product0.19.1/app')]
        import is6_layers_checkpoint as legacy
        native = json.loads((ROOT / 'evidence/is6-layers-native-20261103a.json').read_text())
        assert native['accepted']
        for case in native['cases']:
            for spatial, magnetic in itertools.product([False, True], repeat=2):
                visible = dict(spatial=spatial, magnetic=magnetic)
                value = legacy.create(case['artifact'], visible)
                path = folder / ('legacy-' + case['body'] + '-' + str(int(spatial)) + str(int(magnetic)) + '.json')
                assert not path.exists()
                path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf8')
        return 0
    sys.path[:0] = [str(ROOT / 'output/is6-layers-migration-staging'),
                   str(ROOT / 'output/is6-layers-product0.20.1/app')]
    import is6_layers_migration as migration
    checkpoint, contract = migration.checkpoint, migration.contract
    if args.reopen:
        expected = json.loads((folder / 'expected-before-reopen.json').read_text())
        rows = []
        for item in expected:
            path = ROOT / item['path']
            assert sha(path) == item['sha256']
            scientific, visible = migration.restore(json.loads(path.read_text()))
            assert contract.digest(scientific) == item['scientific_sha256'] and visible == item['visible']
            rows.append(item['path'])
        print(json.dumps(dict(accepted=True, reopened=len(rows))))
        return 0
    out = ROOT / ('evidence/is6-layers-migration-' + args.label + '.json')
    if out.exists() or folder.exists():
        raise FileExistsError('Preserve migration evidence')
    folder.mkdir()
    anchor = ROOT / 'evidence/is6-layers-storage-cut-20261104f.json'
    accepted = json.loads(anchor.read_text())
    assert accepted['accepted'] and accepted['candidate'] == '0.20.1'
    # CPU checks need the sealed model sources and receipts, without nesting
    # earlier binary archives or visual images inside each later archive.
    sources = {p: seal for p, seal in accepted['source_sha256'].items()
               if Path(p).suffix.lower() not in {'.zip', '.png'}}
    for p in [anchor, Path(__file__), Path(migration.__file__),
              ROOT / 'evidence/is6-layers-native-20261103a.json',
              ROOT / 'output/is6-layers-persistence-staging/is6_layers_checkpoint.py',
              ROOT / 'output/is6-layers-product0.19.1/app/is6_layer_contract.py',
              ROOT / 'IS-6-COEXISTENCIA-MIGRACAO-K5-CONTRATO.md']:
        sources[p.relative_to(ROOT).as_posix()] = sha(p)
    assert all(sha(ROOT / p) == seal for p, seal in sources.items())
    result = dict(accepted=False, completed=False, source_sha256=sources,
                  roundtrips=[], refusals=[], original_files_before={}, original_files_after={},
                  owner_sha256=sha(ROOT / 'user/sessions/latest.json'),
                  scope='K5A CPU explicit import only; no service, native scene, product import/store, spatial-only conversion, migration performance or whole IS6/v1 acceptance.')
    expected = []
    def raw(value):
        return json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf8')
    def refuse(name, action):
        try:
            action()
        except (ValueError, TypeError) as error:
            result['refusals'].append(dict(name=name, error=str(error)))
        else:
            raise AssertionError('Invalid import accepted: ' + name)
    def resign(value):
        value['import_sha256'] = contract.digest({k: v for k, v in value.items() if k != 'import_sha256'})
        return value
    def check(name, data, scientific, visible):
        package = migration.preview(data)
        got, flags = migration.restore(json.loads(raw(package)))
        assert got == scientific and flags == visible
        assert package['source_text'].encode('utf8') == data
        description = migration.describe(package)
        assert description['scientific_sha256'] == contract.digest(scientific)
        assert description['body_reference_id'] == scientific['spatial']['binding']['body_reference_id']
        assert description['epoch'] == scientific['spatial']['binding']['epoch']
        path = folder / ('converted-' + name + '.json')
        path.write_bytes(raw(package) + b'\n')
        item = dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path),
                    scientific_sha256=contract.digest(scientific), visible=visible)
        expected.append(item)
        result['roundtrips'].append(dict(name=name, description=description, **item))
        for tag, mutate in [
                ('target-visibility', lambda v: v['checkpoint']['visible'].update(spatial=not visible['spatial'])),
                ('source-bytes-hash', lambda v: v.update(source_sha256='0' * 64)),
                ('source-format', lambda v: v.update(source_format='unknown')),
                ('changes', lambda v: v.update(changes=[])),
                ('converter-version', lambda v: v['generation'].update(version='old')),
                ('schema-bool', lambda v: v.update(schema=True)),
                ('extra-field', lambda v: v.update(extra=1))]:
            bad = copy.deepcopy(package)
            mutate(bad)
            refuse(name + '-' + tag, lambda bad=resign(bad): migration.restore(bad))
        corrupt = copy.deepcopy(package)
        source = migration.parse(data)
        envelope = source['checkpoint'] if source['kind'] == 'independent_layer_store_record' else source
        envelope['scientific']['magnetic']['field_norm_T'] *= 2
        envelope['scientific_sha256'] = contract.digest(envelope['scientific'])
        envelope['checkpoint_sha256'] = contract.digest({k: v for k, v in envelope.items() if k != 'checkpoint_sha256'})
        if source['kind'] == 'independent_layer_store_record':
            source['record_sha256'] = contract.digest({k: v for k, v in source.items() if k != 'record_sha256'})
        corrupted_raw = raw(source)
        refuse(name + '-resigned-source-science', lambda: migration.preview(corrupted_raw))
        corrupt.update(source_text=corrupted_raw.decode('utf8'),
                       source_sha256=hashlib.sha256(corrupted_raw).hexdigest())
        refuse(name + '-resigned-package-and-source', lambda: migration.restore(resign(corrupt)))
    try:
        python = ROOT / '.tooling/python/Scripts/python.exe'
        subprocess.run([str(python), '-Xutf8', str(Path(__file__)), '--label', args.label, '--legacy-fixtures'], cwd=ROOT, check=True)
        legacy_files = sorted(folder.glob('legacy-*.json'))
        assert len(legacy_files) == 8
        result['original_files_before'] = {p.relative_to(ROOT).as_posix(): sha(p) for p in legacy_files}
        for path in legacy_files:
            data = path.read_bytes()
            value = migration.parse(data)
            check(path.stem, data, value['scientific'], value['visible'])
        native = json.loads((ROOT / 'evidence/is6-layers-storage-native-20261104e.json').read_text())
        for target, scientific in native['sciences'].items():
            for spatial, magnetic in itertools.product([False, True], repeat=2):
                visible = dict(spatial=spatial, magnetic=magnetic)
                suffix = target + '-' + str(int(spatial)) + str(int(magnetic))
                envelope = checkpoint.create(scientific, visible)
                check('current-' + suffix, raw(envelope), scientific, visible)
                record = migration.store.Store(folder / 'fixture-store')._record(scientific, visible, 'Fixture ' + target, None)
                check('record-' + suffix, raw(record), scientific, visible)
        assert len(expected) == 24
        for name, data in [('duplicate-JSON', b'{"schema":1,"schema":1}'),
                           ('NaN', b'{"value":NaN}'), ('Infinity', b'{"value":Infinity}'),
                           ('overflow-number', b'{"value":1e999}'), ('array', b'[]'),
                           ('non-UTF8', b'\xff'), ('empty', b'')]:
            refuse(name, lambda data=data: migration.preview(data))
        good = migration.parse(legacy_files[0].read_bytes())
        for name, mutate in [
                ('unknown-generation', lambda v: v['generation'].update(version='unknown')),
                ('legacy-path-alias', lambda v: v['generation']['source_sha256'].update({'elsewhere.py': '0' * 64})),
                ('numeric-visible', lambda v: v['visible'].update(magnetic=1)),
                ('missing-visible', lambda v: v['visible'].pop('spatial')),
                ('wrong-body', lambda v: v['scientific']['magnetic'].update(body_id='another-body')),
                ('wrong-epoch', lambda v: v['scientific']['magnetic']['epoch'].update(utc='2000-01-01T00:00:00Z'))]:
            bad = copy.deepcopy(good)
            mutate(bad)
            bad['scientific_sha256'] = contract.digest(bad['scientific'])
            bad['checkpoint_sha256'] = contract.digest({k: v for k, v in bad.items() if k != 'checkpoint_sha256'})
            refuse(name, lambda data=raw(bad): migration.preview(data))
        # JSON whitespace/BOM are part of the original byte identity, preserved exactly.
        package = migration.preview(b'\xef\xbb\xbf' + legacy_files[0].read_bytes().replace(b'\n', b'\r\n'))
        migration.restore(package)
        (folder / 'expected-before-reopen.json').write_bytes(raw(expected) + b'\n')
        opened = subprocess.run([str(python), '-Xutf8', str(Path(__file__)), '--label', args.label, '--reopen'],
                                cwd=ROOT, check=True, capture_output=True, text=True, encoding='utf8')
        result['fresh_interpreter'] = json.loads(opened.stdout)
        assert result['fresh_interpreter'] == dict(accepted=True, reopened=24)
        result['original_files_after'] = {p.relative_to(ROOT).as_posix(): sha(p) for p in legacy_files}
        assert result['original_files_after'] == result['original_files_before']
        assert all(sha(ROOT / p) == seal for p, seal in sources.items())
        assert sha(ROOT / 'user/sessions/latest.json') == result['owner_sha256']
        archive = folder / 'executed-sources-inputs-outputs.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
            for name in sources:
                z.write(ROOT / name, name)
            for path in [*legacy_files, *[ROOT / item['path'] for item in expected], folder / 'expected-before-reopen.json']:
                z.write(path, path.relative_to(ROOT).as_posix())
        result.update(accepted=True, completed=True, archive_sha256=sha(archive))
    except Exception:
        result['failure'] = traceback.format_exc()
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    print(json.dumps(dict(accepted=result['accepted'], roundtrips=len(result['roundtrips']),
                         refusals=len(result['refusals']), failure=result.get('failure', '').splitlines()[-1:])))
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
