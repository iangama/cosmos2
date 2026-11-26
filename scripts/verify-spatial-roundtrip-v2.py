"""CPU-only current/legacy spatial roundtrips, sealed origins and bounded atomic failure."""
from pathlib import Path
import copy
import hashlib
import json
import sys
import traceback

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'output/spatial-roundtrip-v2-offline-20261121a'
OUT=ROOT/'evidence/spatial-roundtrip-v2-offline-20261121a.json'
PARENT=ROOT/'output/original-flow-hotfix-product0.27.6'
sys.path.insert(0,str(PARENT/'app'));sys.path.insert(0,str(ROOT/'scripts/spatial-roundtrip-v2'))
import is6_spatial_import_v2 as migration
import is6_spatial_import_store_v2 as storage


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not FOLDER.exists() and not OUT.exists();FOLDER.mkdir()
    source=PARENT/'is6-spatial-import-service-records/exports/f6dee22dbd064d8686fe05629cc07092.json'
    raw=source.read_bytes();document=json.loads(raw)
    manifest=json.loads((PARENT/'build-manifest.json').read_text(encoding='utf8'))
    old_python={name:digest for name,digest in manifest['files_sha256'].items() if name.endswith('.py')}
    proof=dict(accepted=False,completed=False,checks=[],source_file=source.relative_to(ROOT).as_posix(),source_sha256=sha(source),
      source_sha256_files={str(path.relative_to(ROOT)).replace('\\','/'):sha(path) for path in [Path(__file__),*migration.FILES]},
      scope='CPU-only versioned importer/store tests against the exact file exported by native0.27.6. No renderer, live application, API or native acceptance. Legacy model/import/store/laboratory modules remain unchanged. Writer/byte/depth failures are explicit isolated fault injections.')
    def check(name,**data):proof['checks'].append(dict(name=name,passed=True,**data))
    def refused(operation):
        try:operation()
        except (ValueError,OSError):return
        raise AssertionError('The malformed/over-budget operation was accepted')
    try:
        package=migration.preview(raw)
        assert package['schema']==2 and package['source_text'].encode('utf8')==raw
        assert package['source_sha256']==sha(source) and package['artifact']==document['artifact'] and package['view']==document['view']
        assert package['policy']==dict(destination_instrument='spatial',destination_parent=None,scientific_resampling=False,magnetic_sample_created=False)
        check('current-native-export-preserves-exact-bytes-science-view-and-policy')
        store=storage.Store(FOLDER/'records')
        first=store.import_branch(package,name='Origem espacial atual')
        first_id=first['record']['branch']['id'];reference=store.load(first_id)
        assert reference.origin['source_text'].encode('utf8')==raw and reference.payload==document['artifact']
        assert reference.branch['parent'] is None
        check('current-import-gets-new-local-identity-and-complete-origin',branch=first_id)
        saved=store.save(reference);assert store.load().payload==reference.payload
        exported=store.export(reference);export_raw=Path(exported['path']).read_bytes()
        roundtrip=migration.preview(export_raw)
        second=store.import_branch(roundtrip,name='Origem espacial reexportada');again=store.load(second['record']['branch']['id'])
        assert again.payload==reference.payload and again.origin['source_text'].encode('utf8')==export_raw
        assert json.loads(again.origin['source_text'])['origin']['source_text'].encode('utf8')==raw
        check('save-export-reimport-preserves-both-generations-of-origin')
        legacy={key:copy.deepcopy(value) for key,value in document.items() if key not in {'origin','record_sha256'}}
        legacy.update(schema=1,kind='is6_spatial_body_mesh_checkpoint');legacy['record_sha256']=migration.digest(legacy)
        legacy_raw=migration.artifact.encoded(legacy)
        legacy_package=migration.preview(legacy_raw);assert legacy_package['schema']==1
        old=store.import_branch(legacy_package,name='Envelope legado isolado');assert store.load(old['record']['branch']['id']).origin['source_text'].encode('utf8')==legacy_raw
        check('legacy-schema1-retains-the-original-importer-and-generation',fixture='Legacy envelope reconstructed only in this isolated test from unchanged native artifact/view.')
        bad=reference.record;bad['origin']['source_sha256']='0'*64
        bad['origin']['package_sha256']=migration.digest({k:v for k,v in bad['origin'].items() if k!='package_sha256'})
        bad['record_sha256']=migration.digest({k:v for k,v in bad.items() if k!='record_sha256'})
        refused(lambda:storage.decode(migration.artifact.encoded(bad)))
        check('recomputed-outer-seals-do-not-admit-a-forged-source-hash')
        bad=reference.record;bad['origin']['policy']['scientific_resampling']=True
        bad['origin']['package_sha256']=migration.digest({k:v for k,v in bad['origin'].items() if k!='package_sha256'})
        bad['record_sha256']=migration.digest({k:v for k,v in bad.items() if k!='record_sha256'})
        refused(lambda:storage.decode(migration.artifact.encoded(bad)))
        check('recomputed-outer-seals-do-not-change-the-import-policy')
        before={p.name:sha(p) for p in store.exports.glob('*.json')};previous=store._atomic
        def fail(*args,**kwargs):raise OSError('Isolated writer fault')
        store._atomic=fail
        try:refused(lambda:store.export(reference))
        finally:store._atomic=previous
        assert {p.name:sha(p) for p in store.exports.glob('*.json')}==before
        assert sha(store.path)==saved['sha256']
        check('writer-failure-preserves-existing-save-and-exports')
        old_limit=migration.MAX_SOURCE_BYTES;migration.MAX_SOURCE_BYTES=1
        try:refused(lambda:store.export(reference))
        finally:migration.MAX_SOURCE_BYTES=old_limit
        assert {p.name:sha(p) for p in store.exports.glob('*.json')}==before
        check('export-byte-budget-failure-does-not-create-an-unimportable-export',fault_injection='Source/export byte limit temporarily reduced to1 in this isolated process.')
        token=migration.DEPTH.set(migration.MAX_ORIGIN_DEPTH)
        try:refused(lambda:migration.preview(raw))
        finally:migration.DEPTH.reset(token)
        check('nested-origin-budget-is-enforced',fault_injection='Validation entered at the configured maximum depth.')
        assert sha(source)==proof['source_sha256']
        assert all(sha(PARENT/name)==digest for name,digest in old_python.items())
        proof['parent_python_unchanged']=len(old_python);proof.update(accepted=True,completed=True)
    except Exception:proof['failure']=traceback.format_exc()
    finally:OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:proof.get(k) for k in ['accepted','completed','checks','failure']},ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
