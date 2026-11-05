"""K5D actor preview/cancel/commit on real archives, with zero native calls."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import sys
import traceback
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is6-layers-product0.21.1/app'
sys.path[:0] = [str(ROOT / 'output/is6-spatial-import-staging'), str(APP)]
import is6_spatial_import_laboratory as service
import is6_spatial_import_store as storage
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    folder = ROOT / ('output/is6-spatial-import-service-' + args.label)
    out = ROOT / ('evidence/is6-spatial-import-service-' + args.label + '.json')
    if folder.exists() or out.exists():
        raise FileExistsError('Preserve spatial service evidence')
    anchor = ROOT / 'evidence/is6-spatial-import-store-20261104b-r2.json'
    accepted = json.loads(anchor.read_text())
    assert accepted['accepted'] and accepted['completed'] and len(accepted['records']) == 24
    foundation = json.loads((ROOT / 'evidence/is6-spatial-import-20261104a.json').read_text())
    sources = dict(accepted['source_sha256'])
    for path in [anchor, Path(__file__), Path(service.__file__),
                 ROOT / 'output/is6-spatial-import-staging/is6_spatial_import_scene.py',
                 ROOT / 'IS-6-IMPORTACAO-ESPACIAL-K5D-SERVICO.md', APP.parent / 'build-manifest.json']:
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
    manifest = json.loads((APP.parent / 'build-manifest.json').read_text())
    for name, seal in manifest['files_sha256'].items():
        sources[(APP / name).relative_to(ROOT).as_posix()] = seal
    assert all(sha(ROOT / name) == seal for name, seal in sources.items())
    folder.mkdir()
    class Laboratory:
        def status(self):
            return dict(mode='atlas', physics=None)
    native_calls = []
    def no_native(code):
        native_calls.append(code)
        raise AssertionError('Spatial file import must not call the renderer')
    actor = service.SpatialLaboratory(Laboratory(), storage_folder=folder / 'records', native=no_native)
    result = dict(accepted=False, completed=False, source_sha256=sources, imports=[], refusals=[],
        owner_sha256=sha(ROOT / 'user/sessions/latest.json'), native_calls=None,
        scope='CPU spatial actor preview/cancel/commit only, real models and atomic store, atlas-state adapter. No simulated native success, HTTP/UI, native owner/restore, performance or IS6/v1 acceptance.')
    def command(name, **fields):
        return actor.command(dict(command=name, guard=actor.status()['guard'], **fields))
    def files():
        return {p.relative_to(folder).as_posix(): sha(p) for p in folder.rglob('*.json')}
    def refuse(label, request):
        before, disk = actor.status(), files()
        try:
            actor.command(request)
        except (ValueError, OSError) as error:
            result['refusals'].append(dict(case=label, error=str(error)))
        else:
            raise AssertionError('Invalid spatial request accepted: ' + label)
        after = actor.status()
        assert after['guard'] == before['guard'] and not after['active'] and not after['busy']
        assert after['import_preview'] == before['import_preview'] and files() == disk and not native_calls
    try:
        for row in foundation['conversions']:
            case = row['form'] + '-' + str(int(row['visible']))
            text = (ROOT / row['source_path']).read_bytes().decode('utf8')
            guard = actor.status()['guard']
            for label, fields in [
                ('missing source', dict(command='import_preview')),
                ('nontext source', dict(command='import_preview', source_text=None)),
                ('invalid JSON', dict(command='import_preview', source_text='{}')),
                ('extra field', dict(command='import_preview', source_text=text, extra=1)),
                ('unknown command', dict(command='unknown')),
                ('unavailable preview', dict(command='import_commit', source_text=text, preview_id='missing', name='Novo')),
                ('closed restore without live source', dict(command='branch_load', branch_id='a'*32, source_guard=None)),
            ]:
                refuse(case+' '+label, dict(guard=guard, **fields))
            refuse(case+' boolean revision', dict(command='import_preview', guard={**guard, 'revision':False}, source_text=text))
            disk = files()
            preview = command('import_preview', source_text=text)['spatial']['import_preview']
            assert preview['valid'] and preview['destination_instrument'] == 'spatial'
            assert preview['body_reference_id'] == 'sol:naif:10' and preview['view']['visible'] is row['visible']
            assert preview['configuration']['outer_radius_boundary_units'] == 8.
            assert preview['magnetic_sample_created'] is False and preview['scientific_resampling'] is False
            assert actor.status()['guard'] == guard and files() == disk and not actor.store.path.exists()
            command('import_cancel', preview_id=preview['id'])
            assert actor.status()['import_preview'] is None and actor.status()['guard'] == guard and files() == disk
            preview = command('import_preview', source_text=text)['spatial']['import_preview']
            previous_preview = preview
            preview = command('import_preview', source_text=text)['spatial']['import_preview']
            assert preview['id'] != previous_preview['id']
            for label, extra in [
                ('superseded preview', dict(preview_id=previous_preview['id'], source_text=text, name='Novo')),
                ('changed source', dict(preview_id=preview['id'], source_text=text+'\n', name='Novo')),
                ('unknown preview', dict(preview_id='missing', source_text=text, name='Novo')),
                ('invalid name', dict(preview_id=preview['id'], source_text=text, name=' ')),
            ]:
                refuse(case+' '+label, dict(command='import_commit', guard=guard, **extra))
            for operation in ['fsync', 'replace']:
                with patch.object(storage.os, operation, side_effect=OSError('Injected '+operation+' failure')):
                    refuse(case+' '+operation+' failure', dict(command='import_commit', guard=guard,
                        preview_id=preview['id'], source_text=text, name='Novo'))
                assert not list(folder.rglob('*.tmp')) and actor.status()['import_preview']['valid']
            imported = command('import_commit', preview_id=preview['id'], source_text=text, name='Espacial '+case)
            snapshot = actor.status()
            receipt = imported['result']
            branch = receipt['record']['branch']
            assert branch['parent'] is None and receipt['record']['lineage_parent'] == branch['id']
            assert receipt['record']['origin']['original_view'] == preview['view']
            assert snapshot['guard']['revision'] == guard['revision']+1 and snapshot['import_preview'] is None
            assert not snapshot['active'] and not snapshot['busy'] and not actor.store.path.exists() and not native_calls
            refuse(case+' replayed guard', dict(command='import_commit', guard=guard, preview_id=preview['id'], source_text=text, name='Novo'))
            refuse(case+' consumed preview', dict(command='import_commit', guard=snapshot['guard'], preview_id=preview['id'], source_text=text, name='Novo'))
            loaded = actor.store.load(branch['id'])
            assert loaded.origin['source_text'] == text and loaded.origin['source_sha256'] == preview['source_sha256']
            assert loaded.view == preview['view'] and loaded.payload == loaded.origin['artifact']
            result['imports'].append(dict(case=case, path=Path(receipt['path']).relative_to(ROOT).as_posix(),
                sha256=sha(Path(receipt['path'])), record=copy.deepcopy(receipt['record'])))
            print(json.dumps(dict(progress='import', case=case)), flush=True)
        assert len(actor.store.catalog()) == 6 and all(row['valid'] for row in actor.store.catalog())
        old_session = actor.status()['guard']['session_id']
        actor.close()
        assert not actor.thread.is_alive()
        actor = service.SpatialLaboratory(Laboratory(), storage_folder=folder / 'records', native=no_native)
        assert actor.status()['guard']['session_id'] != old_session and len(actor.status()['branches']) == 6
        assert all(row['valid'] for row in actor.status()['branches'])
        assert not actor.status()['active'] and not actor.store.path.exists() and not native_calls
        assert all(sha(ROOT / name) == seal for name, seal in sources.items())
        assert sha(ROOT / 'user/sessions/latest.json') == result['owner_sha256'] == 'ee9c4cc86e0696afde128ec319f98f6ad5b3932f27f8b5bd6a25d57a4025b825'
        result.update(accepted=True, completed=True, native_calls=len(native_calls),
                      latest_created=False, new_actor_session_preserved_catalog=True)
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        actor.close()
        result['actor_thread_closed'] = not actor.thread.is_alive()
        result['native_calls'] = len(native_calls)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
    print(json.dumps(dict(accepted=result['accepted'], imports=len(result['imports']), refusals=len(result['refusals']),
                         native_calls=result['native_calls'], failure=result.get('failure'))), flush=True)
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
