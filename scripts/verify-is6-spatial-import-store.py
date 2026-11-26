"""K5D atomic spatial-origin storage: real archives, tampering and processes."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
import time
import traceback
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'output/is6-spatial-import-staging'))
import is6_spatial_import_store as storage

migration, artifact = storage.migration, storage.artifact
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, allow_nan=False) + '\n', encoding='utf8')


def resign(record):
    record['record_sha256'] = artifact.digest({k: v for k, v in record.items() if k != 'record_sha256'})
    return record


def origin_resign(record):
    origin = record['origin']
    origin['package_sha256'] = artifact.digest({k: v for k, v in origin.items() if k != 'package_sha256'})
    return resign(record)


def worker(args, folder):
    if args.worker == 'reopen':
        expected = json.loads((folder / 'expected-before-reopen.json').read_text())
        for row in expected:
            path = ROOT / row['path']
            assert sha(path.read_bytes()) == row['sha256']
            ref = storage.decode(path.read_bytes())
            assert storage.summary(ref) == row['summary']
            assert ref.sample() == row['sample']
            if row['operation'] != 'export':
                store = storage.Store(path.parent.parent if row['operation'] in {'import', 'child'} else path.parent)
                loaded = store.load(None if row['operation'] == 'latest' else path.stem)
                assert loaded.record == ref.record
        print(json.dumps(dict(accepted=True, records=len(expected), source_cases=6)), flush=True)
        return 0
    if args.worker == 'lock':
        try:
            store = storage.Store(folder / 'lock-records')
        except OSError as error:
            print(json.dumps(dict(acquired=False, error=type(error).__name__)), flush=True)
        else:
            with store.writer():
                print(json.dumps(dict(acquired=True)), flush=True)
        return 0
    if args.worker == 'race':
        (folder / ('ready-' + args.worker_id)).write_text('ready')
        deadline = time.monotonic() + 30
        while not (folder / 'start-race').exists():
            if time.monotonic() >= deadline:
                raise TimeoutError('Race barrier not released')
            time.sleep(.01)
        store = storage.Store(folder / 'budget-records')
        package = (ROOT / args.package).read_bytes()
        try:
            receipt = store.import_branch(package, name='Concorrência ' + args.worker_id)
        except ValueError as error:
            if 'limit 32' not in str(error):
                raise
            print(json.dumps(dict(accepted=False, reason='branch-budget')), flush=True)
        else:
            print(json.dumps(dict(accepted=True, id=receipt['record']['branch']['id'])), flush=True)
        return 0
    if args.worker == 'interrupt':
        store = storage.Store(folder / 'interrupted-records')
        package = migration.open_package((ROOT / args.package).read_bytes())
        ref = storage.decode(artifact.encoded(storage._record(package['artifact'], package['view'], None, None, package)))
        def interrupted_replace(source, destination):
            (folder / 'interrupt-at-replace').write_text(str(source), encoding='utf8')
            while True:
                time.sleep(.05)
        with patch.object(storage.os, 'replace', side_effect=interrupted_replace):
            store.save(ref)
        raise AssertionError('Interrupt worker unexpectedly committed')
    raise ValueError('Unknown worker')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    parser.add_argument('--worker', choices=['reopen', 'lock', 'race', 'interrupt'])
    parser.add_argument('--worker-id', default='a')
    parser.add_argument('--package')
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    folder = ROOT / ('output/is6-spatial-import-store-' + args.label)
    if args.worker:
        return worker(args, folder)
    out = ROOT / ('evidence/is6-spatial-import-store-' + args.label + '.json')
    if out.exists() or folder.exists():
        raise FileExistsError('Preserve spatial store evidence')
    anchor = ROOT / 'evidence/is6-spatial-import-20261104a.json'
    proof = json.loads(anchor.read_text())
    assert proof['accepted'] and proof['completed'] and len(proof['conversions']) == 6
    paths = [anchor, Path(__file__), Path(storage.__file__), *storage.FILES, Path(migration.__file__)]
    sources = {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in paths}
    sources.update(proof['source_sha256'])
    sources.update(proof['original_files'])
    for row in proof['conversions']:
        for key in ['source_path', 'package_path']:
            path = ROOT / row[key]
            sources[row[key]] = sha(path.read_bytes())
    assert all(sha((ROOT / name).read_bytes()) == seal for name, seal in sources.items())
    folder.mkdir()
    result = dict(accepted=False, completed=False, source_sha256=sources,
        owner_sha256=sha((ROOT / 'user/sessions/latest.json').read_bytes()), roundtrips=[], refusals=[],
        write_failures=[], records=[], concurrency={}, interruption={},
        scope='K5D CPU spatial schema2 atomic store only; six archived solar inputs. No service/UI/native integration, magnetic sampling, profile or IS6/v1 acceptance.')
    processes = []
    expected = []
    def command(*extra):
        return [sys.executable, '-Xutf8', str(Path(__file__)), '--label', args.label, *extra]
    def refuse(name, action):
        try:
            action()
        except (ValueError, OSError) as error:
            result['refusals'].append(dict(case=name, error=str(error)))
        else:
            raise AssertionError('Invalid case accepted: ' + name)
    def remember(path, operation):
        path = Path(path)
        ref = storage.decode(path.read_bytes())
        expected.append(dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path.read_bytes()),
                             operation=operation, summary=storage.summary(ref), sample=ref.sample()))
    def await_file(path, children):
        deadline = time.monotonic() + 45
        while not path.exists():
            if any(child.poll() is not None for child in children):
                raise AssertionError('Worker ended before signaling: ' + str([p.communicate() for p in children]))
            if time.monotonic() >= deadline:
                raise TimeoutError('Worker barrier timed out: ' + str(path))
            time.sleep(.02)
    try:
        store = storage.Store(folder / 'records')
        for row in proof['conversions']:
            package = migration.open_package((ROOT / row['package_path']).read_bytes())
            current_case = row['form'] + '-' + str(int(row['visible']))
            plain = storage.Reference.local(artifact.Run.restore(package['artifact']), package['view'])
            store.save(plain)
            previous_latest = store.path.read_bytes()
            assert store.load().origin is None
            imported = store.import_branch(package, name='Importação ' + current_case)
            branch_id = imported['record']['branch']['id']
            root_path = Path(imported['path'])
            root_bytes = root_path.read_bytes()
            assert store.path.read_bytes() == previous_latest
            loaded = store.load(branch_id)
            assert loaded.origin == package and loaded.payload == package['artifact'] and loaded.view == package['view']
            assert loaded.branch['parent'] is None and loaded.lineage_parent == branch_id
            legacy = package['original_lineage']
            old_ids = {legacy['lineage_parent']}
            if legacy['branch'] is not None:
                old_ids.update([legacy['branch']['id'], legacy['branch']['parent']])
            assert branch_id not in old_ids and not old_ids.intersection({p.stem for p in store.branches.glob('*.json')})
            changed = loaded.view
            changed['visible'] = not changed['visible']
            changed['selected_radial_index'] = 3
            changed['selected_azimuth_index'] = 7
            changed['reference_radial_index'] = 64
            saved = store.save(loaded, changed)
            latest = store.load()
            assert latest.origin == package and latest.view == changed and latest.lineage_parent == branch_id
            assert root_path.read_bytes() == root_bytes
            assert saved['record']['origin']['original_view'] == package['view']
            # Public copies do not permit mutation of the validated reference.
            projected = loaded.origin
            projected['view']['visible'] = not projected['view']['visible']
            assert loaded.origin == package
            child = store.branch(latest, name='Filho ' + current_case)
            child_ref = store.load(child['record']['branch']['id'])
            assert child_ref.branch['parent'] == branch_id and child_ref.origin == package
            exported = store.export(child_ref)
            export_ref = storage.decode(Path(exported['path']).read_bytes())
            assert export_ref.origin == package and export_ref.view == changed
            assert export_ref.lineage_parent == child_ref.branch['id']
            assert export_ref.payload == package['artifact']
            assert loaded.sample() == artifact.Run.restore(package['artifact']).sample(package['view'])
            for receipt, operation in [(imported, 'import'), (child, 'child'), (exported, 'export')]:
                remember(receipt['path'], operation)
            # Preserve each latest separately for a later fresh interpreter.
            latest_folder = folder / ('latest-' + current_case)
            latest_store = storage.Store(latest_folder)
            # The local ancestry is part of the self-contained test namespace.
            for path in store.branches.glob('*.json'):
                (latest_store.branches / path.name).write_bytes(path.read_bytes())
            latest_store.path.write_bytes(store.path.read_bytes())
            remember(latest_store.path, 'latest')
            baseline = store.path.read_bytes()
            for operation in ['fsync', 'replace']:
                with patch.object(storage.os, operation, side_effect=OSError('Injected ' + operation + ' failure')):
                    try:
                        store.save(loaded)
                    except OSError:
                        pass
                    else:
                        raise AssertionError('Injected latest failure ignored')
                assert store.path.read_bytes() == baseline and root_path.read_bytes() == root_bytes
                assert not list(store.folder.rglob('*.tmp'))
                result['write_failures'].append(dict(case=current_case, method='save', operation=operation, confirmed_bytes_preserved=True))
            result['roundtrips'].append(dict(case=current_case, imported_branch=branch_id, child=child_ref.branch['id'],
                source_sha256=package['source_sha256'], artifact_sha256=package['artifact_sha256'],
                original_view=package['view'], current_view=changed, original_bytes_preserved=True))
            print(json.dumps(dict(progress='roundtrip', case=current_case)), flush=True)

        baseline = store.path.read_bytes()
        good = storage.decode(baseline)
        mutations = [
            ('Extra record field', lambda r: r.update(extra=True)),
            ('Boolean schema', lambda r: r.update(schema=True)),
            ('Legacy schema', lambda r: r.update(schema=1)),
            ('Wrong kind', lambda r: r.update(kind='compound')),
            ('Different valid destination identity', lambda r: r['artifact'].update(id='d'*32)),
            ('Changed destination phase', lambda r: r['artifact']['phase'].update(time=r['artifact']['phase']['time']+1)),
            ('Unknown generation', lambda r: r['artifact']['generation'].update(version='9.9.9')),
            ('Changed mesh', lambda r: r['artifact']['mesh']['physical_vertices_relative_m'][100].__setitem__(0, 1.)),
            ('Numeric visibility', lambda r: r['view'].update(visible=1)),
            ('Radial index outside mesh', lambda r: r['view'].update(selected_radial_index=65)),
            ('Azimuth outside mesh', lambda r: r['view'].update(selected_azimuth_index=96)),
            ('Missing origin capsule fields', lambda r: r.update(origin={})),
            ('Origin view changed', lambda r: r['origin']['view'].update(selected_radial_index=0)),
            ('Origin old lineage changed', lambda r: r['origin']['original_lineage'].update(lineage_parent='a'*32)),
            ('Origin source checksum changed', lambda r: r['origin'].update(source_sha256='0'*64)),
            ('Origin phase changed', lambda r: r['origin']['artifact']['phase'].update(time=123.)),
            ('Invented magnetic sampling', lambda r: r['origin']['policy'].update(magnetic_sample_created=True)),
            ('Implicit scientific resampling', lambda r: r['origin']['policy'].update(scientific_resampling=True)),
            ('Source IDs as destination parent', lambda r: r['origin']['policy'].update(destination_parent='b'*32)),
            ('Invalid local lineage', lambda r: r.update(lineage_parent='../saved')),
        ]
        for label, edit in mutations:
            value = copy.deepcopy(good.record)
            edit(value)
            if isinstance(value.get('origin'), dict) and value['origin']:
                origin_resign(value)
            else:
                resign(value)
            refuse(label + ' with recalculated seals', lambda v=value: storage.decode(artifact.encoded(v)))
        for label, raw in [('Empty', b''), ('Array', b'[]'), ('Duplicate key', b'{"schema":2,"schema":2}'),
                           ('NaN', b'{"x":NaN}'), ('Overflow', b'{"x":1e999}'), ('Invalid UTF8', b'\xff')]:
            refuse(label, lambda v=raw: storage.decode(v))
        invalid = copy.deepcopy(good.record)
        invalid['record_sha256'] = '0'*64
        refuse('Record checksum', lambda: storage.decode(artifact.encoded(invalid)))
        refuse('Invalid branch name', lambda: store.branch(good, name=' '))
        refuse('Path escaping before write', lambda: store._atomic(folder / 'escaped.json', baseline, replace=False))
        refuse('Outside output namespace', lambda: storage.Store(ROOT / 'forbidden-spatial-store'))
        assert not (folder / 'escaped.json').exists() and not (ROOT / 'forbidden-spatial-store').exists()

        # Invalid origin remains invalid in the catalog even after resigning.
        bad_id = good.lineage_parent
        path = store.branches / (bad_id + '.json')
        saved_branch = path.read_bytes()
        value = json.loads(saved_branch)
        value['origin']['policy']['magnetic_sample_created'] = True
        write_json(path, origin_resign(value))
        rows = store.catalog()
        assert not next(r for r in rows if r['id'] == bad_id)['valid']
        refuse('Catalog origin tampering also blocks load', lambda: store.load(bad_id))
        path.write_bytes(saved_branch)
        assert len(store.catalog()) == 12 and all(r['valid'] for r in store.catalog())

        # More I/O failures cover new branches, exports and import confirmation.
        for method in ['branch', 'export', 'import_branch']:
            for operation in ['fsync', 'replace']:
                before = {p.relative_to(store.folder).as_posix(): sha(p.read_bytes()) for p in store.folder.rglob('*.json')}
                with patch.object(storage.os, operation, side_effect=OSError('Injected ' + operation + ' failure')):
                    def action():
                        if method == 'branch':
                            return store.branch(good, name='Falha')
                        if method == 'export':
                            return store.export(good)
                        return store.import_branch(good.origin, name='Falha')
                    try:
                        action()
                    except OSError:
                        pass
                    else:
                        raise AssertionError('Injected ' + method + ' failure ignored')
                after = {p.relative_to(store.folder).as_posix(): sha(p.read_bytes()) for p in store.folder.rglob('*.json')}
                assert after == before and not list(store.folder.rglob('*.tmp'))
                result['write_failures'].append(dict(case='all-confirmed-records', method=method, operation=operation, confirmed_bytes_preserved=True))

        # Full local graph checks, without resolving any archived source IDs.
        graph = storage.Store(folder / 'graph-records')
        local = storage.Reference.local(artifact.Run.restore(good.payload), good.view)
        root = graph.branch(local, name='Raiz')
        root_id = root['record']['branch']['id']
        child = graph.branch(graph.load(root_id), name='Filho')
        child_id = child['record']['branch']['id']
        root_path = Path(root['path'])
        clean_root = root_path.read_bytes()
        for label, edit in [
            ('Missing local parent', lambda r: r['branch'].update(parent='e'*32)),
            ('Self parent', lambda r: r['branch'].update(parent=root_id)),
            ('Local cycle', lambda r: r['branch'].update(parent=child_id)),
            ('Branch filename identity', lambda r: (r['branch'].update(id='c'*32), r.update(lineage_parent='c'*32))),
            ('Branch lineage mismatch', lambda r: r.update(lineage_parent=child_id)),
            ('Extra branch metadata', lambda r: r['branch'].update(extra=True)),
            ('Path parent', lambda r: r['branch'].update(parent='../saved'))]:
            value = json.loads(clean_root)
            edit(value)
            write_json(root_path, resign(value))
            refuse(label + ' with recalculated seal', lambda: graph.load(root_id))
            root_path.write_bytes(clean_root)
        graph.save(graph.load(child_id))
        clean_latest = graph.path.read_bytes()
        value = json.loads(clean_latest)
        value['branch'] = json.loads(clean_root)['branch']
        value['lineage_parent'] = root_id
        write_json(graph.path, resign(value))
        refuse('Latest masquerading as branch', graph.load)
        graph.path.write_bytes(clean_latest)

        # Bounds are enforced before opening an oversized record/destination.
        assert storage.MAX_BYTES == 64*1024*1024 and storage.MAX_BRANCHES == 32
        oversized = graph.folder / 'oversized.json'
        with oversized.open('wb') as stream:
            stream.truncate(storage.MAX_BYTES + 1)
        with patch.object(Path, 'open', side_effect=AssertionError('Oversized path was opened')):
            refuse('Read 64MiB pre-open budget', lambda: graph._read_file(oversized))
            refuse('Write 64MiB pre-open budget', lambda: graph._atomic(graph.path, b' '*(storage.MAX_BYTES+1), replace=True))
        oversized.unlink()
        with patch.object(storage, 'MAX_BYTES', len(clean_latest)-1):
            refuse('Serialized record write limit', lambda: graph.save(graph.load(child_id)))
        assert graph.path.read_bytes() == clean_latest
        alias = graph.folder / 'alias.json'
        alias.symlink_to(graph.path)
        refuse('Symlink record', lambda: graph._read_file(alias))
        alias.unlink()

        lock_store = storage.Store(folder / 'lock-records')
        with lock_store.writer():
            locked = subprocess.run(command('--worker', 'lock'), capture_output=True, text=True, timeout=20, check=True)
            assert json.loads(locked.stdout)['acquired'] is False, locked.stdout
        released = subprocess.run(command('--worker', 'lock'), capture_output=True, text=True, timeout=20, check=True)
        assert json.loads(released.stdout)['acquired'] is True
        result['concurrency']['process_lock'] = dict(blocked_second_process=True, released_after_owner=True)

        # Two simultaneous import confirmations compete for the last slot.
        budget = storage.Store(folder / 'budget-records')
        for index in range(31):
            identifier = format(index+1, '032x')
            value = storage._record(local.payload, local.view, dict(id=identifier, parent=None, name='Orçamento'), identifier, None)
            write_json(budget.branches / (identifier+'.json'), value)
        package_path = proof['conversions'][0]['package_path']
        children = [subprocess.Popen(command('--worker', 'race', '--worker-id', name, '--package', package_path), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for name in ['a', 'b']]
        processes.extend(children)
        for name in ['a', 'b']:
            await_file(folder / ('ready-' + name), children)
        (folder / 'start-race').write_text('start')
        race = []
        for child_process in children:
            stdout, stderr = child_process.communicate(timeout=60)
            assert child_process.returncode == 0, stderr
            race.append(json.loads(stdout))
        assert sorted(row['accepted'] for row in race) == [False, True]
        assert len(list(budget.branches.glob('*.json'))) == 32
        refuse('Branch 33', lambda: budget.branch(local, name='Excesso'))
        result['concurrency']['last_slot'] = dict(outcomes=race, confirmed_branches=32)

        # Kill a process after fsync and before replace. Reopen removes only
        # our abandoned temp and retains every committed byte and capsule.
        interrupted = storage.Store(folder / 'interrupted-records')
        interrupted.save(local)
        before = interrupted.path.read_bytes()
        unknown_temp = interrupted.folder / '.unrelated.tmp'
        unknown_temp.write_bytes(b'preserve unrelated file')
        child_process = subprocess.Popen(command('--worker', 'interrupt', '--package', package_path), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        processes.append(child_process)
        await_file(folder / 'interrupt-at-replace', [child_process])
        pending = Path((folder / 'interrupt-at-replace').read_text())
        assert pending.exists() and interrupted.path.read_bytes() == before
        child_process.terminate()
        child_process.communicate(timeout=15)
        assert pending.exists() and interrupted.path.read_bytes() == before
        reopened = storage.Store(interrupted.folder)
        assert reopened.load().origin is None and reopened.path.read_bytes() == before
        assert not pending.exists() and unknown_temp.read_bytes() == b'preserve unrelated file'
        result['interruption'] = dict(killed_before_replace=True, confirmed_bytes_preserved=True,
                                     orphan_temp_recovered=True, unrelated_file_preserved=True)

        write_json(folder / 'expected-before-reopen.json', expected)
        fresh = subprocess.run(command('--worker', 'reopen'), capture_output=True, text=True, timeout=300, check=True)
        result['fresh_interpreter'] = json.loads(fresh.stdout)
        assert result['fresh_interpreter'] == dict(accepted=True, records=24, source_cases=6)
        assert len(result['roundtrips']) == 6 and len(result['write_failures']) == 18
        assert all(sha((ROOT / name).read_bytes()) == seal for name, seal in sources.items())
        assert sha((ROOT / 'user/sessions/latest.json').read_bytes()) == result['owner_sha256']
        assert result['owner_sha256'] == 'ee9c4cc86e0696afde128ec319f98f6ad5b3932f27f8b5bd6a25d57a4025b825'
        result.update(accepted=True, completed=True, records=expected, generation=storage.generation())
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        for child_process in processes:
            if child_process.poll() is None:
                child_process.terminate()
                child_process.communicate(timeout=15)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    print(json.dumps(dict(accepted=result['accepted'], roundtrips=len(result['roundtrips']),
        refusals=len(result['refusals']), write_failures=len(result['write_failures']),
        fresh=result.get('fresh_interpreter'), failure=result.get('failure'))), flush=True)
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
