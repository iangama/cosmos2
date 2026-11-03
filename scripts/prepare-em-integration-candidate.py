"""Fork the frozen numeric-time candidate for C2-12 experience integration."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/c212-em-time-product'
DEST=ROOT/'output/c212-em-integration-product'
assert not DEST.exists()
owner=(ROOT/'user/sessions/latest.json').read_bytes()
frozen=json.loads((ROOT/'evidence/c212-em-time-candidate-frozen-check.json').read_bytes())
assert hashlib.sha256((ROOT/frozen['archive']).read_bytes()).hexdigest()==frozen['archive_sha256']
for name,digest in frozen['files_sha256'].items():
    normalized=name.replace('\\','/')
    if any(normalized.startswith('output/c212-em-time-product/'+folder+'/') for folder in ('app','em','em-cloud')):
        assert hashlib.sha256((ROOT/normalized).read_bytes()).hexdigest()==digest,normalized
for folder in ('app','em','em-cloud'):
    shutil.copytree(BASE/folder,DEST/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for folder in ('c212-em-worker/product','c212-em-cloud-worker/product','gravity-sessions'):
    (DEST/folder).mkdir(parents=True,exist_ok=True)
subprocess.run(['cmd.exe','/c','mklink','/J',str(DEST/'data'),str(ROOT/'data')],check=True,capture_output=True)
launcher=(ROOT/'scripts/start-c212-em-time-candidate.ps1').read_text()
launcher=launcher.replace('c212-em-time-product','c212-em-integration-product')
launcher=launcher.replace('explicit-unapproved-EM-numeric-time-controls-candidate','explicit-unapproved-EM-experience-integration-candidate')
launcher=launcher.replace('emTimeCandidate = $true;','emIntegrationCandidate = $true; emTimeCandidate = $true;')
(ROOT/'scripts/start-c212-em-integration-candidate.ps1').write_text(launcher)
assert (ROOT/'user/sessions/latest.json').read_bytes()==owner
receipt={'status':'separate_experience_integration_fork_before_edits',
         'base_archive':frozen['archive'],'base_archive_sha256':frozen['archive_sha256'],
         'owner_pointer_preserved':True,
         'source_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
                          for folder in ('app','em','em-cloud') for p in (DEST/folder).rglob('*') if p.is_file()},
         'scope':'Fresh storage and unchanged scientific/execution cores at fork. No installed promotion or inherited experience/performance acceptance.'}
(ROOT/'evidence/em-integration-candidate-prepared.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'candidate':str(DEST),'source_files':len(receipt['source_sha256'])}),flush=True)
