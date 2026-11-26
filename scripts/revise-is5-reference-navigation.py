"""Preserve the first unaccepted visual candidate, then apply the reviewed CSS fix."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
candidate=ROOT/'output/is5-reference-product0.16.0'
manifest_path=candidate/'build-manifest.json'
manifest=json.loads(manifest_path.read_text())
rejected=json.loads((ROOT/'evidence/is5-reference-visual-review-20261029a.json').read_text())
assert rejected['accepted'] is False
app=candidate/'app'
assert all(sha(app/name)==value for name,value in manifest['files_sha256'].items())
preserved=ROOT/'output/is5-reference-navigation-revision-20261029b'
preserved.mkdir(exist_ok=False)
target=app/'ui/stellar-reference.css'
shutil.copy2(target,preserved/'stellar-reference-before.css')
shutil.copy2(manifest_path,preserved/'build-manifest-before.json')
shutil.copy2(ROOT/'output/is5-solar-reference-browser-staging/stellar-reference.css',target)
manifest['files_sha256']['ui/stellar-reference.css']=sha(target)
manifest['visual_revision']=dict(recipe_sha256=sha(Path(__file__)),
    previous_manifest_sha256=sha(preserved/'build-manifest-before.json'),
    reason='Enable read-only reference navigation while zone is active; opaque reference panel for legibility.')
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(changed=['ui/stellar-reference.css'],preserved=str(preserved))))
