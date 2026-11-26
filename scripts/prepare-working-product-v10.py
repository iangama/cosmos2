"""Freeze the HTTP/UI-accepted point lens as the next local working revision."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'output/original-flow-hotfix-product0.28.4'
STAGE=ROOT/'output/c214-point-lens-ui-staging-v2'
BACKEND=ROOT/'output/c214-point-lens-service-staging'
TARGET=ROOT/'output/original-flow-hotfix-product0.29.0'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not TARGET.exists()
    names=['c214-point-lens-offline-20261121b.json','c214-point-lens-geometry-20261121a.json','c214-point-lens-http-20261121a.json','c214-point-lens-ui-20261121b.json']
    for name in names:
        gate=json.loads((ROOT/'evidence'/name).read_text());assert gate['accepted'] and gate['completed']
        assert all(sha(ROOT/n)==s for n,s in gate.get('source_sha256',{}).items())
    previous=json.loads((PARENT/'build-manifest.json').read_text())
    prepared=json.loads((STAGE/'preparation.json').read_text())
    backend=json.loads((BACKEND/'preparation.json').read_text())
    assert all(sha(PARENT/n)==s for n,s in previous['files_sha256'].items())
    assert all(sha(STAGE/n)==s for n,s in prepared['files_sha256'].items())
    admitted={n:s for n,s in backend['files_sha256'].items() if not n.startswith('app/ui/')}
    assert all(prepared['files_sha256'][n]==s for n,s in admitted.items())
    for folder in ['app','data']:shutil.copytree(STAGE/folder,TARGET/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    files={p.relative_to(TARGET).as_posix():sha(p) for folder in ['app','data'] for p in (TARGET/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    old={n:s for n,s in previous['files_sha256'].items() if n.endswith('.py') and n not in ['app/server.py','app/artifacts.py']}
    changed=[n for n,s in old.items() if files[n]!=s]
    assert len(old)==143 and sorted(changed)==['app/forces.py','app/science_contracts.py']
    added=[n for n in files if n not in previous['files_sha256']]
    assert sorted(added)==['app/point_lens.py','app/point_lens_force_adapter.py','app/ui/point-lens-view.js']
    manifest=dict(schema=3,candidate='0.29.0',promoted=False,native_user_flow_accepted=False,files_sha256=files,
      parent_product=PARENT.relative_to(ROOT).as_posix(),parent_manifest_sha256=sha(PARENT/'build-manifest.json'),
      inherited_scientific_python=143,scientific_python_unchanged=141,changed_scientific_python=changed,
      changed_app_files=[n for n in previous['files_sha256'] if files[n]!=previous['files_sha256'][n]],added_app_files=added,
      backend_files_sha256=admitted,ui_preparation_sha256=sha(STAGE/'preparation.json'),
      proof_sha256={name:sha(ROOT/'evidence'/name) for name in names},preparation_script_sha256=sha(Path(__file__)),
      scope='Local point-lens delivery candidate: source/lens/observer geometry, two images and parity/flux, singular ring, truthful symbolic views and probes, curated conditions/error/recovery. All141 other inherited science modules unchanged; two catalog/contract modules extended andtwo lens modules added. Server and prior numerical backends intact. Native original-path pending; no full C2-14/final integration or transferred orbit-profile acceptance.')
    (TARGET/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(prepared=True,candidate='0.29.0',scientific_python_unchanged=141,changed_science=changed,added=added,selected=False)))


if __name__=='__main__':main()
