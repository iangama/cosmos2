"""Seal the exact K5 first/restart, direct visual review and process evidence."""
from pathlib import Path
import hashlib
import json
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'output/is6-layers-product0.21.1/app'))
import is6_layers_import_store_v2 as storage
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
out = ROOT / 'evidence/is6-layers-import-cut-20261104t.json'
if out.exists():
    raise FileExistsError('Preserve consolidated evidence')
labels = ['20261104s', '20261104t']
paths = [*[ROOT / ('evidence/is6-layers-import-native-' + label + '.json') for label in labels],
         ROOT / 'evidence/is6-layers-import-visual-20261104t.json',
         *[ROOT / ('evidence/is6-layers-import-native-process-' + label + '.json') for label in labels]]
sources = {Path(__file__).relative_to(ROOT).as_posix(): sha(Path(__file__))}
receipts = []
for path in paths:
    record = json.loads(path.read_text())
    assert record['accepted'] and record['completed'], path
    for name, seal in record['source_sha256'].items():
        assert name not in sources or sources[name] == seal, name
        sources[name] = seal
    sources[path.relative_to(ROOT).as_posix()] = sha(path)
    receipts.append(record)
first, restart, visual = receipts[:3]
assert first['phase'] == 'first' and restart['phase'] == 'restart'
assert len(first['checks']) == 5 and len(restart['checks']) == 7
assert len(first['refusals']) == 11 and len(first['captures']) == 8 and len(restart['captures']) == 7
assert all(item['text_mutations_during_idle']==0 for record in [first,restart] for item in record['captures'])
assert len(visual['captures']) == 15 and set(first['imports']) == {'399', '599'}
assert first['source_phase']['system_id'] != restart['new_live_identity']
assert restart['archived_source_identity'] == first['sciences']['599']['spatial']['phase']['system_id']
assert restart['new_live_identity'] != restart['archived_source_identity']
assert first['sciences'] == restart['sciences']
assert any(a['cancel_reply'] and a['load_reply']['status'] == 400 for a in restart['cancellation_attempts'])
for target, item in first['imports'].items():
    assert sha(ROOT / item['source']) == item['source_sha256'] == item['origin']['source_sha256']
    sources[item['source']] = item['source_sha256']
    root = next(v for v in first['stored_archives'] if v['path'].endswith('/branches/' + item['branch_id'] + '.json'))
    assert json.loads((ROOT / root['path']).read_text())['parent'] is None
for label, record in zip(labels, [first, restart], strict=True):
    archive = ROOT / ('output/is6-layers-import-native-' + label + '/executed-sources-and-records.zip')
    assert sha(archive) == record['archive_sha256']
    expected = dict(record['source_sha256'])
    for item in record['stored_archives']:
        path = ROOT / item['path']
        assert sha(path) == item['sha256']
        scientific, visible, origin = storage.decode(json.loads(path.read_text()))
        assert origin is not None
        target = scientific['magnetic']['body_reference_id'].split(':')[-1]
        assert scientific == first['sciences'][target]
        assert origin['source_sha256'] == first['imports'][target]['source_sha256']
        expected[item['path']] = item['sha256']
        sources[item['path']] = item['sha256']
    with zipfile.ZipFile(archive) as z:
        assert len(z.namelist()) == len(set(z.namelist())) and set(z.namelist()) == set(expected)
        assert all(hashlib.sha256(z.read(name)).hexdigest() == seal for name, seal in expected.items())
    sources[archive.relative_to(ROOT).as_posix()] = sha(archive)
manifest_path = ROOT / 'output/is6-layers-product0.21.1/build-manifest.json'
manifest = json.loads(manifest_path.read_text())
assert manifest['candidate'] == '0.21.1' and manifest['promoted'] is False
app = manifest_path.parent / 'app'
actual = {p.relative_to(app).as_posix(): sha(p) for p in app.rglob('*')
          if p.is_file() and '__pycache__' not in p.parts}
assert actual == manifest['files_sha256']
assert all(sha(ROOT / name) == seal for name, seal in sources.items())
assert sha(ROOT / 'user/sessions/latest.json') == first['owner_sha256'] == restart['owner_sha256']
result = dict(accepted=True, completed=True, candidate='0.21.1', promoted=False,
              source_sha256=sources, receipts=[p.relative_to(ROOT).as_posix() for p in paths],
              confirmations=12, reviewed_images=15, refusals=11, imported_formats=2,
              owner_sha256=first['owner_sha256'],
              scope='K5 compound import/persistence/restart functional and visual slice only; no own performance, spatial-only import, promotion or complete IS6/v1 acceptance.')
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}))
