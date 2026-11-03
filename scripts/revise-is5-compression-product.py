"""Create0.17.1 without changing the preserved0.17.0 or scientific workers."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    base=ROOT/'output/is5-compression-product0.17.0'
    target=ROOT/'output/is5-compression-product0.17.1'
    if target.exists():raise FileExistsError('Preserve revision')
    manifest=json.loads((base/'build-manifest.json').read_text())
    assert all(sha(ROOT/n)==v for n,v in manifest['source_sha256'].items())
    assert {p.relative_to(base/'app').as_posix():sha(p) for p in (base/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}==manifest['files_sha256']
    diagnostic=ROOT/'evidence/is5-compression-cancel-cef-20261101b.json'
    result=json.loads(diagnostic.read_text())
    assert result['completed'] and not result['accepted'] and result['CEF']['hidden']
    assert result['server_state']['calculation']['cancellable'] and not result.get('cleanup_failure')
    assert all(sha(ROOT/n)==v for n,v in result['source_sha256'].items())
    shutil.copytree(base/'app',target/'app',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    script=target/'app/ui/is5-zone.js';s=script.read_text()
    old="if(response.ok&&!solarZonePending)solarZoneState=await response.json();"
    assert s.count(old)==1
    new="if(response.ok){const value=await response.json();if(solarZonePending){solarZoneState={...solarZoneState,busy:value.busy,calculation:value.calculation};}else solarZoneState=value;}"
    script.write_text(s.replace(old,new),encoding='utf-8')
    files={p.relative_to(target/'app').as_posix():sha(p) for p in (target/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert [n for n in files if files[n]!=manifest['files_sha256'][n]]==['ui/is5-zone.js']
    sources=dict(manifest['source_sha256'])
    for p in [base/'build-manifest.json',diagnostic,Path(__file__),ROOT/'scripts/launch-is5-compression-revision.py']:
        sources[p.relative_to(ROOT).as_posix()]=sha(p)
    record=dict(candidate='0.17.1',promoted=False,accepted=False,files_sha256=files,
                source_sha256=sources,base_files_sha256=manifest['files_sha256'],
                worker_receipt=manifest['worker_receipt'],
                scope='UI polling revision only; CEF/native/visual/profile acceptance pending.')
    (target/'build-manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert all(sha(base/'app'/n)==v for n,v in manifest['files_sha256'].items())
    print(json.dumps(dict(prepared=True,accepted=False,candidate=str(target),changed=['ui/is5-zone.js'])))


if __name__=='__main__':main()
