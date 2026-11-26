"""Independent acquisition pins, integrity failures and per-property copy semantics."""
from pathlib import Path
import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from packages import PackageStore
from atlas import states
from atlas_import import prepare, experiment_subset, digest
from session import Session

store = PackageStore()
manifest = store.catalog()
assert len(manifest['packages']) == 14
reports = []
for package in manifest['packages']:
    for item in package['files']:
        if item.get('hash_origin') == 'preserved_local_extraction_record':
            metadata = json.loads((ROOT / item['receipt']).read_text(encoding='utf-8-sig'))
            rows = [metadata['rate']] if 'rate' in metadata else list(metadata['rates'].values())
            assert any(row['sha256'] == item['sha256'] and row['raw_file'] == Path(item['path']).name for row in rows)
        elif item['receipt']:
            receipt = json.loads((ROOT / item['receipt']).read_text(encoding='utf-8-sig'))
            rows = list(receipt['files'].values()) if isinstance(receipt, dict) and isinstance(receipt.get('files'), dict) else receipt['files'] if isinstance(receipt, dict) and isinstance(receipt.get('files'), list) else receipt if isinstance(receipt, list) else [receipt]
            assert any(row['sha256'] == item['sha256'] and row['bytes'] == item['bytes'] and row['url'] == item['source_url'] for row in rows)
    report = store.verify(package['id'])
    assert report['status'] == 'verified', report
    reports.append(report)
assert all(p['verification_cache_current'] for p in store.catalog()['packages'])
registered = {item['path'] for p in manifest['packages'] for item in p['files']}
assert {'data/science/' + p.name for p in (ROOT / 'data/science').iterdir() if p.is_file()} <= registered

# Isolated package: corruption of the same size, changed size and missing file.
with tempfile.TemporaryDirectory() as folder:
    root = Path(folder); (root / 'data/packages').mkdir(parents=True)
    path = root / 'data/sample.bin'; original = b'original data'; path.write_bytes(original)
    example = copy.deepcopy(manifest)
    example['packages'] = [copy.deepcopy(manifest['packages'][-1])]
    example['packages'][0]['files'] = [{'path': 'data/sample.bin', 'bytes': len(original), 'sha256': hashlib.sha256(original).hexdigest(), 'hash_origin': 'pinned_local_definition_v1'}]
    manifest_file = root / 'data/packages/catalog.json'
    manifest_file.write_text(json.dumps(example))
    isolated = PackageStore(root); identifier = example['packages'][0]['id']
    assert isolated.verify(identifier)['status'] == 'verified'
    path.write_bytes(b'corrupt! data')
    assert len(path.read_bytes()) == len(original)
    assert isolated.catalog()['packages'][0]['verification_cache_current'] is False
    assert isolated.verify(identifier)['files'][0]['status'] == 'hash_mismatch'
    path.write_bytes(b'x')
    assert isolated.verify(identifier)['files'][0]['status'] == 'size_mismatch'
    path.unlink()
    assert isolated.verify(identifier)['files'][0]['status'] == 'missing'
    for unsafe in ('../sample.bin', 'data/../sample.bin', '/data/sample.bin', 'data\\sample.bin', 'data/C:sample.bin'):
        bad = copy.deepcopy(example); bad['packages'][0]['files'][0]['path'] = unsafe
        manifest_file.write_text(json.dumps(bad))
        try:
            PackageStore(root)
        except ValueError:
            pass
        else:
            raise AssertionError('Unsafe manifest path accepted: ' + unsafe)
    bad = copy.deepcopy(example); bad['packages'].append(copy.deepcopy(bad['packages'][0]))
    manifest_file.write_text(json.dumps(bad))
    try:
        PackageStore(root)
    except ValueError:
        pass
    else:
        raise AssertionError('Duplicate package accepted')
    # Windows may lack permission to create symlinks. The Linux counterpart
    # checks escaping symlinks separately, without claiming it ran here.

source = states(utc='2026-10-11T12:00:00Z')
observer = source['observer']
assert observer['coordinate_origin_naif_id'] == '0' and observer['light_time_applied'] is False
assert observer['emission_et_tdb_s'] is None and observer['reception_et_tdb_s'] is None
assert observer['state_epoch_et_tdb_s'] == source['epoch']['et_tdb_s']
assert source['packages_manifest_sha256'] == store.manifest_sha256
for body in source['bodies']:
    properties = {p['id']: p for p in body['properties']}
    assert len(properties) == 7
    assert properties['position']['value'] == body['position_m'] and properties['velocity']['value'] == body['velocity_m_s']
    assert properties['orientation']['value'] == body['body_to_j2000']
    assert all(p['uncertainty']['value'] is None for p in properties.values())
    for key in ('position', 'velocity'):
        assert properties[key]['epoch'] == source['epoch'] and properties[key]['frame'] == 'SSB / J2000-ICRF'
    if body['naif_id']=='699':
        assert properties['mass']['value'] is None and properties['GM']['value'] is None
    else:
        assert properties['mass']['value'] == properties['GM']['value'] / 6.67430e-11
        assert properties['mass']['known_uncertainty_contribution_from_G_only_kg'] > 0
    if body['naif_id'] == '10':
        assert properties['shape']['value'] is None and properties['texture']['value'] is None
    else:
        assert properties['texture']['epoch'] is None
        assert all(t['acquisition_epoch'] is None for t in properties['texture']['value'])

initial = prepare(experiment_subset(source))
with tempfile.TemporaryDirectory() as folder:
    session = Session(folder); session.import_atlas(initial)
    assert initial['source']['observer'] == observer
    assert all(b['reference_properties'] == original['properties'] for b, original in zip(initial['bodies'], source['bodies']))
    session.set_mass(initial['bodies'][0]['id'], 2)
    session.save(); before = session.state(); session.load()
    assert session.state()['atlas_initial'] == before['atlas_initial']
    moved = Path(folder) / 'sessao movida'
    moved.mkdir()
    shutil.copy2(Path(folder) / 'latest.json', moved / 'latest.json')
    checkpoint_manifest = json.loads((moved / 'latest.json').read_text())
    shutil.copy2(Path(folder) / checkpoint_manifest['binary'], moved / checkpoint_manifest['binary'])
    reopened = Session(moved); reopened.load()
    assert reopened.state()['atlas_initial'] == before['atlas_initial'] and reopened.state()['bodies'] == before['bodies']
    current = session.state()
    for kind in ('observer', 'position_property', 'GM_property', 'epoch_property'):
        broken = copy.deepcopy(initial)
        if kind == 'observer':
            broken['source']['observer']['light_time_applied'] = True
        elif kind == 'position_property':
            broken['bodies'][0]['reference_properties'][0]['value'][0] += 1
        elif kind == 'GM_property':
            broken['bodies'][0]['reference_properties'][2]['value'] *= 2
        else:
            broken['bodies'][0]['reference_properties'][0]['epoch']['et_tdb_s'] += 1
        broken['initial_state_sha256'] = digest({k: v for k, v in broken.items() if k != 'initial_state_sha256'})
        try:
            session.import_atlas(broken)
        except ValueError:
            pass
        else:
            raise AssertionError('Inconsistent property/observer accepted')
        assert session.state() == current

report = {'packages': len(manifest['packages']), 'files': sum(len(p['files']) for p in manifest['packages']),
          'total_bytes': sum(p['total_bytes'] for p in manifest['packages']), 'manifest_sha256': store.manifest_sha256,
          'acquisition_receipts_independently_matched': True, 'content_verifications': reports,
          'all_current_scientific_data_registered': True,
          'isolated_corrupt_same_size_changed_size_missing': True, 'invalid_paths_and_duplicates_refused': True,
          'property_records': 28, 'geometric_observer_no_light_time': True,
          'unknown_not_zero': True, 'reference_properties_preserved_after_edit_checkpoint': True,
          'checkpoint_moved_to_folder_with_spaces': True,
          'inconsistent_metadata_refused_without_mutation': 4,
          'scope': 'Local manifest integrity and declared solar metadata. No general installer or apparent observing model.'}
(ROOT / 'evidence/packages-properties-check.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'content_verifications'}, indent=2))
