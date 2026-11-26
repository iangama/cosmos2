"""Record a pre-execution guard correction to the prepared0.26.0 packet."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PRODUCT=ROOT/'output/is6-dynamics16-product0.26.0'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest_path=PRODUCT/'build-manifest.json'
manifest=json.loads(manifest_path.read_text(encoding='utf8'))
assert not any((ROOT/'evidence').glob('is6-dynamics16-service-*.json')), 'Never change an executed packet'
assert all(sha(PRODUCT/'app'/n)==s for n,s in manifest['files_sha256'].items())
assert 'preflight_correction' not in manifest
before=sha(manifest_path)
path=PRODUCT/'app/server.py'
text=path.read_text(encoding='utf8')
old="            elif self.path == '/api/dynamics16/experiment':\n                from dynamics16_runtime import create"
new="            elif self.path == '/api/dynamics16/experiment':\n                if any(s.get('active') or s.get('busy') or s.get('recovery_required') for s in [LAYERS.status(), SPATIAL.status(), SOLAR_ZONE.status(), PARTICLES.status()]):\n                    raise ValueError('Feche o instrumento ativo antes de criar a dinâmica dos16centros.')\n                from dynamics16_runtime import create"
assert text.count(old)==1
text=text.replace(old,new)
compile(text,str(path),'exec')
path.write_text(text,encoding='utf8')
manifest['files_sha256']['server.py']=sha(path)
manifest['source_sha256'][Path(__file__).relative_to(ROOT).as_posix()]=sha(Path(__file__))
manifest['preflight_correction']=dict(parent_manifest_sha256=before,
    reason='Static review: new endpoint must reject every active/recovering bench before entering dynamics; no product service, worker or UI has executed.')
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(prepared=True,service_executed=False,preflight_corrected=True)))
