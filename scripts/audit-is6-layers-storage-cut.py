"""Seal the specific 0.20.1 K4 functional, visual and process evidence."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
out = ROOT / 'evidence/is6-layers-storage-cut-20261104f.json'
if out.exists():
    raise FileExistsError('Preserve consolidated evidence')

labels = ['20261104e', '20261104f']
native_paths = [ROOT / ('evidence/is6-layers-storage-native-' + label + '.json') for label in labels]
paths = [*native_paths,
         ROOT / 'evidence/is6-layers-storage-visual-20261104f.json',
         ROOT / 'evidence/is6-layers-native-process-20261104e-r2.json',
         ROOT / 'evidence/is6-layers-native-process-20261104f.json']
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
assert len(first['checks']) == 5 and len(restart['checks']) == 6
assert len(first['refusals']) == 6 and len(first['captures']) == len(restart['captures']) == 6
assert len(visual['captures']) == 12
assert first['source_phase']['system_id'] != restart['new_live_identity']
assert restart['archived_source_identity'] == first['source_phase']['system_id']
assert any(a['cancel_reply'] and a['load_reply']['status'] == 400 for a in restart['cancellation_attempts'])
assert set(first['sciences']) == set(restart['sciences']) == {'399', '599'}
assert first['sciences'] == restart['sciences']
for label, record in zip(labels, [first, restart], strict=True):
    archive = ROOT / ('output/is6-layers-storage-native-' + label + '/executed-sources-and-records.zip')
    assert sha(archive) == record['archive_sha256']
    expected = dict(record['source_sha256'])
    for item in record['stored_archives']:
        expected[item['path']] = item['sha256']
    with zipfile.ZipFile(archive) as z:
        assert len(z.namelist()) == len(set(z.namelist())) and set(z.namelist()) == set(expected)
        assert all(hashlib.sha256(z.read(name)).hexdigest() == seal for name, seal in expected.items())
    sources[archive.relative_to(ROOT).as_posix()] = sha(archive)
    for item in record['stored_archives']:
        sources[item['path']] = item['sha256']
manifest_path = ROOT / 'output/is6-layers-product0.20.1/build-manifest.json'
manifest = json.loads(manifest_path.read_text())
assert manifest['candidate'] == '0.20.1' and manifest['promoted'] is False
app = manifest_path.parent / 'app'
actual = {p.relative_to(app).as_posix(): sha(p) for p in app.rglob('*')
          if p.is_file() and '__pycache__' not in p.parts}
assert actual == manifest['files_sha256']
assert all(sha(ROOT / name) == seal for name, seal in sources.items())
assert sha(ROOT / 'user/sessions/latest.json') == first['owner_sha256'] == restart['owner_sha256']
result = dict(accepted=True, completed=True, candidate='0.20.1', promoted=False,
              source_sha256=sources, receipts=[p.relative_to(ROOT).as_posix() for p in paths],
              confirmations=11, reviewed_images=12, refusals=6,
              owner_sha256=first['owner_sha256'],
              scope='K4 0.20.1 functional/visual persistence and restart only; no performance, legacy migration, promotion or complete IS6/v1 acceptance.')
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}))
