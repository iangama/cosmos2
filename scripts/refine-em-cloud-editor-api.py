"""Preserve first H refusal; allow a bounded full source model on its API."""
from pathlib import Path
import hashlib
import json
import tarfile
ROOT=Path(__file__).resolve().parents[1];H=ROOT/'output/c212-em-cloud-editor-product'
archive=ROOT/'output/em-cloud-editor-before-api-fix-20261021.tar.gz'
assert not archive.exists()
names=[*sorted((H/'app').rglob('*')),ROOT/'scripts/verify-em-cloud-editor-ui.py',ROOT/'evidence/em-cloud-editor-ui-initial-check.json']
with tarfile.open(archive,'w:gz') as tar:
    for p in names:
        if p.is_file() and '__pycache__' not in p.parts:tar.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
path=H/'app/server.py';source=path.read_text();old='            if not 0 < length <= 8192:'
assert source.count(old)==1
source=source.replace(old,"            limit = 262144 if self.path == '/api/em-cloud/command' else 8192\n            if not 0 < length <= limit:")
path.write_text(source)
paths=[path]
for path in (ROOT/'scripts/em-cloud-editor-ui/cloud-workspace.js',H/'app/ui/em/cloud-workspace.js'):
    source=path.read_text();assert "let cloudPanel='experience';" in source
    source=source.replace("let cloudPanel='experience';","let cloudPanel='experience',cloudPopulationKey=null;")
    source=source.replace("function renderCloudWorkspace(){","function renderCloudWorkspace(){\n  if(state){const key=state.system_id+'|'+state.edit_token;if(key!==cloudPopulationKey){cloudPopulationKey=key;const value=String(state.count);if(![...$('count').options].some(o=>o.value===value))$('count').add(new Option(value,value));$('count').value=value;}}")
    path.write_text(source);paths.append(path)
report={'status':'H_full_source_model_API_bound_and_population_form_prepared',
        'reason':'Real initial CEF refused128sources at inherited8192byte HTTP limit; not a science/core refusal.',
        'before_archive':str(archive.relative_to(ROOT)),'before_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
        'cloud_command_limit_bytes':262144,'other_endpoint_limit_bytes':8192,
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
(ROOT/'evidence/em-cloud-editor-api-fix-prepared.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
