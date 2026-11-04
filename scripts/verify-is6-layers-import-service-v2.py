"""K5C actor import commands with real files/models and zero native calls."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import sys
import traceback
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'output/is6-layers-migration-staging'),
               str(ROOT / 'output/is6-layers-product0.20.1/app')]
import is6_layers_import_laboratory as service
import is6_layers_import_store_v2 as storage
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    parser.add_argument('--store-label', default='20261104j2')
    args = parser.parse_args()
    for label in [args.label, args.store_label]:
        if not label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
            parser.error('Invalid label')
    folder = ROOT / ('output/is6-layers-import-service-' + args.label)
    out = ROOT / ('evidence/is6-layers-import-service-' + args.label + '.json')
    if folder.exists() or out.exists():
        raise FileExistsError('Preserve service evidence')
    anchor = ROOT / ('evidence/is6-layers-import-store-' + args.store_label + '.json')
    accepted = json.loads(anchor.read_text())
    assert accepted['accepted'] and accepted['completed']
    sources = dict(accepted['source_sha256'])
    for p in [anchor, Path(__file__), Path(service.__file__),
              ROOT / 'output/is6-layers-migration-20261104h/legacy-399-01.json',
              ROOT / 'output/is6-layers-migration-20261104h/legacy-599-01.json']:
        sources[p.relative_to(ROOT).as_posix()] = sha(p)
    assert all(sha(ROOT / p) == seal for p, seal in sources.items())
    folder.mkdir()
    class Laboratory:
        def status(self):
            return dict(mode='atlas', physics=None)
    native_calls = []
    def no_native(code):
        native_calls.append(code)
        raise AssertionError('Importing a branch must not call the renderer')
    actor = service.LayerLaboratory(Laboratory(), storage=folder / 'previews', native=no_native)
    result = dict(accepted=False, completed=False, source_sha256=sources, refusals=[], imports=[],
                  owner_sha256=sha(ROOT / 'user/sessions/latest.json'),
                  scope='CPU actor import preview/cancel/commit only, with real validation/storage and atlas-state adapter; no simulated native success, HTTP/UI, scene restore or performance acceptance.')
    def command(operation, **fields):
        return actor.command(dict(command=operation, guard=actor.status()['guard'], **fields))
    def files():
        return {p.relative_to(folder).as_posix(): sha(p) for p in folder.rglob('*.json')}
    def refuse(name, request):
        before, disk = actor.status(), files()
        try:
            actor.command(request)
        except (ValueError, OSError) as error:
            result['refusals'].append(dict(name=name, error=str(error)))
        else:
            raise AssertionError('Invalid request accepted: ' + name)
        after = actor.status()
        assert after['guard'] == before['guard'] and not after['active'] and not after['busy']
        assert after['import_preview'] == before['import_preview'] and files() == disk and not native_calls
    try:
        for target in ['399', '599']:
            path = ROOT / ('output/is6-layers-migration-20261104h/legacy-' + target + '-01.json')
            text = path.read_bytes().decode('utf8')
            before = actor.status()
            guard = before['guard']
            for tag, request in [
                    ('missing-text', dict(command='import_preview', guard=guard)),
                    ('non-text', dict(command='import_preview', guard=guard, source_text=None)),
                    ('invalid-JSON', dict(command='import_preview', guard=guard, source_text='{}')),
                    ('extra-field', dict(command='import_preview', guard=guard, source_text=text, extra=1)),
                    ('boolean-revision', dict(command='import_preview', guard={**guard, 'revision': False}, source_text=text)),
                    ('no-preview-commit', dict(command='import_commit', guard=guard, preview_id='missing', source_text=text, name='Importado'))]:
                refuse(target + '-' + tag, request)
            disk = files()
            preview = command('import_preview', source_text=text)['layers']['import_preview']
            assert preview['valid'] and preview['body_reference_id'] == 'sol:naif:' + target
            assert actor.status()['guard'] == guard and files() == disk
            command('import_cancel', preview_id=preview['id'])
            assert actor.status()['import_preview'] is None and actor.status()['guard'] == guard and files() == disk
            preview = command('import_preview', source_text=text)['layers']['import_preview']
            for tag, fields in [
                    ('changed-file', dict(source_text=text + '\n', name='Importado', preview_id=preview['id'])),
                    ('unknown-preview', dict(source_text=text, name='Importado', preview_id='missing')),
                    ('invalid-name', dict(source_text=text, name=' ', preview_id=preview['id']))]:
                refuse(target + '-' + tag, dict(command='import_commit', guard=guard, **fields))
            with patch.object(storage.os, 'replace', side_effect=OSError('Injected import write failure')):
                refuse(target + '-write-failure', dict(command='import_commit', guard=guard, preview_id=preview['id'], source_text=text, name='Importado'))
            assert not list(folder.rglob('*.tmp')) and actor.status()['import_preview']['valid']
            imported = command('import_commit', preview_id=preview['id'], source_text=text, name='Importação ' + target)
            snapshot = actor.status()
            assert snapshot['guard']['revision'] == guard['revision'] + 1 and snapshot['import_preview'] is None
            assert not snapshot['active'] and not actor.store.path.exists() and not native_calls
            entry = imported['result']['record']
            assert entry['parent'] is None and entry['origin']['body_reference_id'] == 'sol:naif:' + target
            refuse(target + '-replayed-commit', dict(command='import_commit', guard=guard, preview_id=preview['id'], source_text=text, name='Duplicado'))
            refuse(target + '-consumed-preview', dict(command='import_commit', guard=snapshot['guard'], preview_id=preview['id'], source_text=text, name='Duplicado'))
            science, visible, summary, origin = actor.store.load(entry['id'])
            assert visible == dict(spatial=False, magnetic=True)
            assert storage.migration.contract.digest(science) == preview['scientific_sha256']
            assert origin['source_text'] == text and summary['origin'] == entry['origin']
            result['imports'].append(copy.deepcopy(entry))
        assert len(actor.store.catalog()) == 2 and all(row['valid'] for row in actor.store.catalog())
        assert all(sha(ROOT / p) == seal for p, seal in sources.items())
        assert sha(ROOT / 'user/sessions/latest.json') == result['owner_sha256']
        result.update(accepted=True, completed=True, native_calls=len(native_calls), latest_created=False)
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        actor.close()
    archive = folder / 'executed-sources-inputs-records.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in sources:
            z.write(ROOT / name, name)
        for path in actor.store.branches.glob('*.json'):
            z.write(path, path.relative_to(ROOT).as_posix())
    result['archive_sha256'] = sha(archive)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    print(json.dumps(dict(accepted=result['accepted'], imports=len(result['imports']),
                         refusals=len(result['refusals']), native_calls=len(native_calls),
                         failure=result.get('failure', '').splitlines()[-1:])))
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
