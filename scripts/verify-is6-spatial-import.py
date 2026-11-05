"""K5D CPU proof from real saved/branch/export solar records, with no native calls."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'output/is6-spatial-import-staging'))
import is6_spatial_import as migration

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reopen')
    args = parser.parse_args()
    if args.reopen:
        package = migration.open_package(Path(args.reopen).read_bytes())
        print(json.dumps(dict(artifact_sha256=package['artifact_sha256'], source_sha256=package['source_sha256'], view=package['view'])))
        return
    out = ROOT / 'evidence/is6-spatial-import-20261104a.json'
    folder = ROOT / 'output/is6-spatial-import-20261104a'
    if out.exists() or folder.exists():
        raise FileExistsError('Preserve spatial import evidence')
    folder.mkdir()
    old = ROOT / 'output/is6-spatial-product0.18.2/spatial-checkpoints'
    def solar(path):
        record = json.loads(path.read_text(encoding='utf8'))
        return record['artifact']['binding']['body_reference_id'] == 'sol:naif:10'
    paths = dict(saved=old / 'saved.json',
                 branch=next(p for p in sorted(old.glob('branches/*.json')) if solar(p)),
                 export=next(p for p in sorted(old.glob('exports/*.json')) if solar(p)))
    originals = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths.values()}
    sources = {p.relative_to(ROOT).as_posix(): sha(p) for p in [Path(__file__), Path(migration.__file__), migration.CONTRACT]}
    r = dict(accepted=False, completed=False, source_sha256=sources, original_files=originals,
             owner_sha256=sha(ROOT / 'user/sessions/latest.json'), conversions=[], refusals=[], fresh_reopens=[],
             scope='CPU-only spatial-source capsule foundation, real solar archives and visibility variants; no atomic destination store, UI, native restoration, magnetic sampling or product acceptance.')
    def refused(label, raw, reader=migration.preview):
        try:
            reader(raw)
        except ValueError as error:
            r['refusals'].append(dict(case=label, error=str(error)))
        else:
            raise AssertionError('Accepted invalid case: ' + label)
    try:
        for form, path in paths.items():
            original = path.read_bytes()
            record = migration.parse(original)
            for visible in [False, True]:
                value = copy.deepcopy(record)
                value['view']['visible'] = visible
                value['record_sha256'] = migration.digest({k: v for k, v in value.items() if k != 'record_sha256'})
                raw = original if visible is record['view']['visible'] else json.dumps(value, sort_keys=True, indent=2).encode()
                name = form + '-' + str(int(visible))
                source_path = folder / (name + '-source.json')
                source_path.write_bytes(raw)
                package = migration.preview(raw)
                package_path = folder / (name + '-package.json')
                package_path.write_text(json.dumps(package, sort_keys=True, indent=2) + '\n', encoding='utf8')
                reopened = migration.open_package(package_path.read_bytes())
                assert reopened == package and package['source_text'].encode('utf8') == raw
                run, view, decoded = migration.open_source(raw)
                assert package['artifact'] == decoded['artifact'] and package['view'] == view
                restored = migration.artifact.Run.restore(package['artifact'])
                assert restored.sample(package['view']) == run.sample(view)
                assert package['original_lineage'] == dict(branch=decoded['branch'], lineage_parent=decoded['lineage_parent'])
                assert package['policy'] == dict(destination_instrument='spatial', destination_parent=None, scientific_resampling=False, magnetic_sample_created=False)
                assert package['artifact']['binding']['body_reference_id'] == 'sol:naif:10'
                assert package['artifact']['configuration']['outer_radius_boundary_units'] == 8.
                fresh = subprocess.run([sys.executable, '-Xutf8', str(Path(__file__)), '--reopen', str(package_path)], capture_output=True, text=True, encoding='utf8', timeout=90)
                assert fresh.returncode == 0, fresh.stderr
                proof = json.loads(fresh.stdout)
                assert proof == dict(artifact_sha256=package['artifact_sha256'], source_sha256=package['source_sha256'], view=view)
                r['fresh_reopens'].append(proof)
                r['conversions'].append(dict(form=form, visible=visible, source_path=source_path.relative_to(ROOT).as_posix(), source_sha256=sha(source_path), package_path=package_path.relative_to(ROOT).as_posix(), package_sha256=sha(package_path), artifact_sha256=package['artifact_sha256'], original_bytes_preserved=raw == original, sample=run.sample(view)))
        baseline = paths['saved'].read_bytes()
        for label, raw in [('Empty', b''), ('Not object', b'[]'), ('Duplicate JSON', b'{"schema":1,"schema":1}'), ('NaN', b'{"x":NaN}'), ('Overflow', b'{"x":1e999}'), ('UTF8', b'\xff'), ('Oversize', b' ' * (migration.MAX_SOURCE_BYTES + 1))]:
            refused(label, raw)
        mutations = [
            ('Extra field', lambda x: x.update(extra=True)),
            ('Boolean schema', lambda x: x.update(schema=True)),
            ('Wrong kind', lambda x: x.update(kind='compound')),
            ('Unknown generation', lambda x: x['artifact']['generation'].update(version='9.9.9')),
            ('Invalid artifact ID', lambda x: x['artifact'].update(id='../saved')),
            ('Changed epoch', lambda x: x['artifact']['phase'].update(time=x['artifact']['phase']['time']+1)),
            ('Changed mesh', lambda x: x['artifact']['mesh']['physical_vertices_relative_m'][100].__setitem__(0, x['artifact']['mesh']['physical_vertices_relative_m'][100][0]+1)),
            ('Azimuth outside mesh', lambda x: x['view'].update(selected_azimuth_index=96)),
            ('Radius outside mesh', lambda x: x['view'].update(selected_radial_index=65)),
            ('Reference outside mesh', lambda x: x['view'].update(reference_radial_index=-1)),
            ('Numeric visibility', lambda x: x['view'].update(visible=1)),
            ('Invalid source lineage', lambda x: x.update(lineage_parent='../saved')),
        ]
        for label, edit in mutations:
            value=migration.parse(baseline);edit(value)
            value['record_sha256']=migration.digest({k:v for k,v in value.items() if k!='record_sha256'})
            refused(label+' with recalculated source seal', json.dumps(value).encode())
        package=migration.preview(baseline)
        for label, edit in [
            ('Invented magnetic sample', lambda x:x['policy'].update(magnetic_sample_created=True)),
            ('Implicit resampling', lambda x:x['policy'].update(scientific_resampling=True)),
            ('Implicit local lineage', lambda x:x['policy'].update(destination_parent='f'*32)),
            ('Changed source bytes', lambda x:x.update(source_text=x['source_text']+'\n')),
            ('Changed output view', lambda x:x['view'].update(selected_radial_index=1)),
            ('Extra package field', lambda x:x.update(extra=True))]:
            value=copy.deepcopy(package);edit(value)
            value['package_sha256']=migration.digest({k:v for k,v in value.items() if k!='package_sha256'})
            refused(label+' with recalculated package seal', json.dumps(value).encode(), migration.open_package)
        assert len(r['conversions'])==len(r['fresh_reopens'])==6 and len(r['refusals'])==25
        assert all(sha(ROOT / p)==seal for p,seal in originals.items())
        assert sha(ROOT / 'user/sessions/latest.json')==r['owner_sha256']
        assert all(sha(ROOT / p)==seal for p,seal in sources.items())
        r.update(accepted=True, completed=True, generation=migration.generation())
    except Exception:
        r['failure']=traceback.format_exc()
    finally:
        out.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(accepted=r['accepted'], conversions=len(r['conversions']), refusals=len(r['refusals']), fresh_reopens=len(r['fresh_reopens']), failure=r.get('failure'))))
    return 0 if r['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
