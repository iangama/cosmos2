"""K5B provenance survival, old-record compatibility and write-failure atomicity."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import subprocess
import sys
import traceback
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'output/is6-layers-migration-staging'),
               str(ROOT / 'output/is6-layers-product0.20.1/app')]
import is6_layers_import_store_v2 as storage
migration = storage.migration
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    parser.add_argument('--migration-label', default='20261104h')
    parser.add_argument('--reopen', action='store_true')
    args = parser.parse_args()
    for label in [args.label, args.migration_label]:
        if not label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
            parser.error('Invalid label')
    folder = ROOT / ('output/is6-layers-import-store-' + args.label)
    if args.reopen:
        expected = json.loads((folder / 'expected-before-reopen.json').read_text())
        for item in expected:
            path = ROOT / item['path']
            assert sha(path) == item['sha256']
            science, visible, origin = storage.decode(json.loads(path.read_text()))
            assert migration.contract.digest(science) == item['scientific_sha256']
            assert visible == item['visible'] and origin['import_sha256'] == item['import_sha256']
        print(json.dumps(dict(accepted=True, reopened=len(expected))))
        return 0
    out = ROOT / ('evidence/is6-layers-import-store-' + args.label + '.json')
    if folder.exists() or out.exists():
        raise FileExistsError('Preserve import-store evidence')
    anchor = ROOT / ('evidence/is6-layers-migration-' + args.migration_label + '.json')
    accepted = json.loads(anchor.read_text())
    assert accepted['accepted'] and accepted['completed'] and len(accepted['roundtrips']) == 24
    sources = dict(accepted['source_sha256'])
    for path in [anchor, Path(__file__), Path(storage.__file__)]:
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
    packages = [item for item in accepted['roundtrips'] if item['name'].startswith('current-')]
    assert len(packages) == 8
    for item in packages:
        sources[item['path']] = item['sha256']
    assert all(sha(ROOT / n) == seal for n, seal in sources.items())
    folder.mkdir()
    store = storage.Store(folder / 'records')
    result = dict(accepted=False, completed=False, source_sha256=sources, roundtrips=[],
                  refusals=[], write_failures=[], records=[], owner_sha256=sha(ROOT / 'user/sessions/latest.json'),
                  scope='K5B CPU atomic import store only; no service, UI, native restore, spatial-only import, throughput or full IS6/v1 acceptance.')
    expected = []
    def refuse(name, action):
        try:
            action()
        except (ValueError, OSError) as error:
            result['refusals'].append(dict(name=name, error=str(error)))
        else:
            raise AssertionError('Invalid record accepted: ' + name)
    def add_record(path):
        record = json.loads(path.read_text())
        science, visible, origin = storage.decode(record)
        item = dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path),
                    scientific_sha256=migration.contract.digest(science), visible=visible,
                    import_sha256=origin['import_sha256'])
        expected.append(item)
    try:
        for item in packages:
            package = json.loads((ROOT / item['path']).read_text())
            science, visible = migration.restore(package)
            # A valid old-format local save remains readable without an origin.
            store.save(science, visible)
            normal = store.path.read_bytes()
            assert store.load()[3] is None
            imported = store.import_branch(package, record_name='Importação ' + item['name'])
            assert store.path.read_bytes() == normal and imported['record']['parent'] is None
            branch = imported['record']['id']
            got, flags, summary, origin = store.load(branch)
            assert got == science and flags == visible and origin == package
            assert summary['origin'] == migration.describe(package)
            changed = {k: not v for k, v in visible.items()}
            saved = store.save(got, changed, parent=branch, origin=origin)
            assert store.load()[0] == science and store.load()[1] == changed and store.load()[3] == package
            child = store.branch(got, changed, record_name='Filho importado', parent=branch, origin=origin)
            assert child['record']['parent'] == branch
            exported = store.export(got, changed, parent=branch, origin=origin)
            for entry in [imported, child, exported]:
                path = Path(entry['path'])
                decoded, current_visible, current_origin = storage.decode(json.loads(path.read_text()))
                assert decoded == science and current_origin == package
                assert current_visible == (visible if entry is imported else changed)
                add_record(path)
            latest = store.path.read_bytes()
            record = json.loads(latest)
            altered = copy.deepcopy(record)
            altered['checkpoint']['scientific']['magnetic']['field_norm_T'] *= 2
            env = altered['checkpoint']
            env['scientific_sha256'] = migration.contract.digest(env['scientific'])
            env['checkpoint_sha256'] = migration.contract.digest({k: v for k, v in env.items() if k != 'checkpoint_sha256'})
            altered['record_sha256'] = migration.contract.digest({k: v for k, v in altered.items() if k != 'record_sha256'})
            refuse(item['name'] + '-resigned-target-science', lambda: storage.decode(altered))
            other = copy.deepcopy(record)
            other['origin']['source_sha256'] = '0' * 64
            other['origin']['import_sha256'] = migration.contract.digest({k: v for k, v in other['origin'].items() if k != 'import_sha256'})
            other['record_sha256'] = migration.contract.digest({k: v for k, v in other.items() if k != 'record_sha256'})
            refuse(item['name'] + '-resigned-origin', lambda: storage.decode(other))
            for operation in ['replace', 'fsync']:
                with patch.object(storage.os, operation, side_effect=OSError('Injected write failure')):
                    try:
                        store.save(got, visible, parent=branch, origin=origin)
                    except OSError:
                        pass
                    else:
                        raise AssertionError('Injected failure ignored')
                assert store.path.read_bytes() == latest and not list(store.folder.rglob('*.tmp'))
                result['write_failures'].append(dict(case=item['name'], operation=operation, previous_bytes_preserved=True))
            refuse(item['name'] + '-path-escape', lambda: store._write(folder / 'escaped.json', record, replace=False))
            assert not (folder / 'escaped.json').exists()
            # Returning to a plain local record clears provenance explicitly.
            store.save(got, flags)
            assert store.load()[3] is None and store.load()[2]['origin'] is None
            result['roundtrips'].append(dict(case=item['name'], branch_id=branch, child_id=child['record']['id'], visible=visible, changed=changed))
        assert len(store.catalog()) == 16 and all(row['valid'] for row in store.catalog())
        result['records'] = expected
        (folder / 'expected-before-reopen.json').write_text(json.dumps(expected, ensure_ascii=False) + '\n', encoding='utf8')
        python = ROOT / '.tooling/python/Scripts/python.exe'
        reopened = subprocess.run([str(python), '-Xutf8', str(Path(__file__)), '--label', args.label,
                                  '--migration-label', args.migration_label, '--reopen'], cwd=ROOT,
                                 check=True, capture_output=True, text=True, encoding='utf8')
        result['fresh_interpreter'] = json.loads(reopened.stdout)
        assert result['fresh_interpreter'] == dict(accepted=True, reopened=24)
        assert all(sha(ROOT / n) == seal for n, seal in sources.items())
        assert sha(ROOT / 'user/sessions/latest.json') == result['owner_sha256']
        archive = folder / 'executed-sources-inputs-outputs.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
            for name in sources:
                z.write(ROOT / name, name)
            for path in [*[ROOT / e['path'] for e in expected], folder / 'expected-before-reopen.json', store.path]:
                z.write(path, path.relative_to(ROOT).as_posix())
        result.update(accepted=True, completed=True, archive_sha256=sha(archive))
    except Exception:
        result['failure'] = traceback.format_exc()
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    print(json.dumps(dict(accepted=result['accepted'], roundtrips=len(result['roundtrips']),
                         refusals=len(result['refusals']), write_failures=len(result['write_failures']),
                         failure=result.get('failure', '').splitlines()[-1:])))
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
