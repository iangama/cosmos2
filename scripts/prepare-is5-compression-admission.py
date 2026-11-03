"""Build0.17.2 after preserving native refusal evidence and bridge acceptance."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    base=ROOT/'output/is5-compression-product0.17.1';target=ROOT/'output/is5-compression-product0.17.2'
    if target.exists():raise FileExistsError('Preserve admission candidate')
    parent=base/'build-manifest.json';manifest=json.loads(parent.read_text())
    assert all(sha(ROOT/n)==v for n,v in manifest['source_sha256'].items())
    assert {p.relative_to(base/'app').as_posix():sha(p) for p in (base/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}==manifest['files_sha256']
    diagnostic=ROOT/'evidence/is5-compression-refusal-native-20261101a.json'
    result=json.loads(diagnostic.read_text())
    assert result['completed'] and not result.get('failure') and not result.get('cleanup_failure')
    assert len(result['cases'])==6 and all(c['preserved'] and c['elapsed_s']>2. for c in result['cases'])
    bridge=ROOT/'evidence/is5-compression-bridge-20261101a.json'
    for p in [diagnostic,bridge]:
        r=json.loads(p.read_text());assert all(sha(ROOT/n)==v for n,v in r['source_sha256'].items())
    assert json.loads(bridge.read_text())['accepted']
    stage=ROOT/'output/is5-compression-admission-staging/is5_laboratory.py'
    shutil.copytree(base/'app',target/'app',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copy2(stage,target/'app/is5_laboratory.py')
    files={p.relative_to(target/'app').as_posix():sha(p) for p in (target/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert [n for n in files if files[n]!=manifest['files_sha256'][n]]==['is5_laboratory.py']
    sources=dict(manifest['source_sha256'])
    for p in [parent,diagnostic,bridge,stage,Path(__file__),ROOT/'scripts/launch-is5-compression-admission.py']:
        sources[p.relative_to(ROOT).as_posix()]=sha(p)
    record=dict(candidate='0.17.2',promoted=False,accepted=False,files_sha256=files,source_sha256=sources,
                base_files_sha256=manifest['files_sha256'],worker_receipt=manifest['worker_receipt'],
                scope='Bridge admission revision only; native/visual/profile acceptance pending.')
    (target/'build-manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert all(sha(base/'app'/n)==v for n,v in manifest['files_sha256'].items())
    print(json.dumps(dict(prepared=True,accepted=False,candidate=str(target),changed=['is5_laboratory.py'])))


if __name__=='__main__':main()
