"""Fork frozen partial I into isolated J for actual-viewport camera and scene UI."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'output/c212-em-framing-product'
DEST = ROOT / 'output/c212-em-viewport-product'
assert not DEST.exists()
owner = (ROOT / 'user/sessions/latest.json').read_bytes()
frozen = json.loads((ROOT / 'evidence/em-framing-candidate-frozen-check.json').read_bytes())
assert hashlib.sha256((ROOT / frozen['archive']).read_bytes()).hexdigest() == frozen['archive_sha256']
assert frozen['promotion'] is False and frozen['whole_C2_12_accepted'] is False
for name, digest in frozen['files_sha256'].items():
    if name.startswith('output/c212-em-framing-product/'):
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
for folder in ('app', 'em', 'em-cloud'):
    shutil.copytree(BASE / folder, DEST / folder, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
for folder in ('c212-em-worker/product', 'c212-em-cloud-worker/product', 'gravity-sessions'):
    (DEST / folder).mkdir(parents=True, exist_ok=True)
subprocess.run(['cmd.exe', '/c', 'mklink', '/J', str(DEST / 'data'), str(ROOT / 'data')], check=True, capture_output=True)
launcher = (ROOT / 'scripts/start-c212-em-framing-candidate.ps1').read_text()
launcher = launcher.replace('c212-em-framing-product', 'c212-em-viewport-product')
launcher = launcher.replace('explicit-unapproved-EM-framing-and-potential-headroom-candidate', 'explicit-unapproved-EM-viewport-and-scene-layout-candidate')
launcher = launcher.replace('emFramingCandidate = $true;', 'emViewportCandidate = $true; emFramingCandidate = $true;')
(ROOT / 'scripts/start-c212-em-viewport-candidate.ps1').write_text(launcher)
(DEST / 'LEIA-CANDIDATA.md').write_text('# C2-12 — candidata J\n\nCópia separada de I parcial congelada. Núcleos/workers byteiguais.\nÁrea útil nativa e legenda compacta ainda exigem implementação,execução,\ninspeção visual,persistência,referências e três perfis próprios.\nSem promoção ou aceite global C2-12.\n')
assert (ROOT / 'user/sessions/latest.json').read_bytes() == owner
report = {'status': 'J_isolated_fork_of_frozen_partial_I_before_changes', 'base_archive': frozen['archive'],
          'base_archive_sha256': frozen['archive_sha256'], 'owner_pointer_preserved': True,
          'source_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                            for folder in ('app', 'em', 'em-cloud') for p in (DEST / folder).rglob('*') if p.is_file()},
          'scope': 'Independent storage; no inherited formal or visual acceptance. Preserve installed3.13 and frozen I.'}
(ROOT / 'evidence/em-viewport-candidate-prepared.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': report['status'], 'files': len(report['source_sha256'])}), flush=True)
