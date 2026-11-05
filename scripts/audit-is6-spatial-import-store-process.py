"""Complete the frozen B proof after Windows refused the optional symlink fixture."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'output/is6-spatial-import-staging'))
import is6_spatial_import_store as storage
artifact = storage.artifact
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, allow_nan=False) + '\n', encoding='utf8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    source = ROOT / ('evidence/is6-spatial-import-store-' + args.label + '.json')
    out = source.with_name(source.stem + '-r2.json')
    if out.exists():
        raise FileExistsError('Preserve completion audit')
    original = json.loads(source.read_text(encoding='utf8'))
    assert original['accepted'] is False and original['completed'] is False
    assert 'WinError 1314' in original['failure'] and 'alias.symlink_to' in original['failure']
    assert len(original['roundtrips']) == 6 and len(original['write_failures']) == 18
    assert len(original['refusals']) == 42
    sources = dict(original['source_sha256'])
    for path in [source, Path(__file__)]:
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
    assert all(sha(ROOT / name) == seal for name, seal in sources.items())
    folder = ROOT / ('output/is6-spatial-import-store-' + args.label)
    proof = json.loads((ROOT / 'evidence/is6-spatial-import-20261104a.json').read_text())
    verifier = ROOT / 'scripts/verify-is6-spatial-import-store.py'
    result = {**original, 'accepted': False, 'completed': False, 'source_sha256': sources,
        'original_verifier_failure': original['failure'], 'records': [], 'concurrency': {}, 'interruption': {},
        'symlink_fixture': dict(executed=False, reason='Windows WinError1314: optional fixture creation lacks privilege; no privilege or policy changes.'),
        'scope': 'Combined B CPU proof plus independent process/reopen completion for the unchanged spatial store. Optional symlink fixture not executed. No service/UI/native integration, magnetic sampling, performance or IS6/v1 acceptance.'}
    result.pop('failure', None)
    processes = []
    def command(*extra):
        return [sys.executable, '-Xutf8', str(verifier), '--label', args.label, *extra]
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
        for case, source_case in zip(original['roundtrips'], proof['conversions'], strict=True):
            assert case['case'] == source_case['form'] + '-' + str(int(source_case['visible']))
            package = storage.migration.open_package((ROOT / source_case['package_path']).read_bytes())
            branch = store.load(case['imported_branch'])
            child = store.load(case['child'])
            assert branch.origin == child.origin == package
            assert branch.branch['parent'] is None and child.branch['parent'] == case['imported_branch']
            assert branch.view == case['original_view'] and child.view == case['current_view']
            assert branch.payload == child.payload == package['artifact']
            exports = []
            for path in store.exports.glob('*.json'):
                # Select by local lineage metadata, then fully validate below.
                if json.loads(path.read_text())['lineage_parent'] == case['child']:
                    exports.append(path)
            assert len(exports) == 1
            paths = [(store.branches / (case['imported_branch']+'.json'), 'import'),
                     (store.branches / (case['child']+'.json'), 'child'), (exports[0], 'export'),
                     (folder / ('latest-'+case['case']) / 'saved.json', 'latest')]
            for path, operation in paths:
                reference = storage.decode(path.read_bytes())
                assert reference.origin == package and reference.payload == package['artifact']
                assert reference.view == (case['original_view'] if operation == 'import' else case['current_view'])
                result['records'].append(dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), operation=operation,
                    summary=storage.summary(reference), sample=reference.sample()))
            print(json.dumps(dict(progress='revalidated', case=case['case'])), flush=True)

        lock_store = storage.Store(folder / 'lock-records')
        with lock_store.writer():
            locked = subprocess.run(command('--worker', 'lock'), capture_output=True, text=True, timeout=20, check=True)
            assert json.loads(locked.stdout)['acquired'] is False, locked.stdout
        released = subprocess.run(command('--worker', 'lock'), capture_output=True, text=True, timeout=20, check=True)
        assert json.loads(released.stdout)['acquired'] is True
        result['concurrency']['process_lock'] = dict(blocked_second_process=True, released_after_owner=True)

        local = storage.Reference.local(artifact.Run.restore(branch.payload), branch.view)
        budget = storage.Store(folder / 'budget-records')
        assert not list(budget.branches.glob('*.json'))
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
        try:
            budget.branch(local, name='Excesso')
        except ValueError as error:
            assert 'limit 32' in str(error)
            result['refusals'].append(dict(case='Branch 33', error=str(error)))
        else:
            raise AssertionError('Accepted branch 33')
        result['concurrency']['last_slot'] = dict(outcomes=race, confirmed_branches=32)

        interrupted = storage.Store(folder / 'interrupted-records')
        interrupted.save(local)
        before = interrupted.path.read_bytes()
        unknown = interrupted.folder / '.unrelated.tmp'
        unknown.write_bytes(b'preserve unrelated file')
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
        assert not pending.exists() and unknown.read_bytes() == b'preserve unrelated file'
        result['interruption'] = dict(killed_before_replace=True, confirmed_bytes_preserved=True,
                                     orphan_temp_recovered=True, unrelated_file_preserved=True)

        expected_path = folder / 'expected-before-reopen.json'
        assert not expected_path.exists()
        write_json(expected_path, result['records'])
        fresh = subprocess.run(command('--worker', 'reopen'), capture_output=True, text=True, timeout=300, check=True)
        result['fresh_interpreter'] = json.loads(fresh.stdout)
        assert result['fresh_interpreter'] == dict(accepted=True, records=24, source_cases=6)
        assert all(sha(ROOT / name) == seal for name, seal in sources.items())
        assert sha(ROOT / 'user/sessions/latest.json') == result['owner_sha256'] == 'ee9c4cc86e0696afde128ec319f98f6ad5b3932f27f8b5bd6a25d57a4025b825'
        result.update(accepted=True, completed=True, generation=storage.generation())
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        for child_process in processes:
            if child_process.poll() is None:
                child_process.terminate()
                child_process.communicate(timeout=15)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    print(json.dumps(dict(accepted=result['accepted'], records=len(result['records']), refusals=len(result['refusals']),
                         fresh=result.get('fresh_interpreter'), failure=result.get('failure'))), flush=True)
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
