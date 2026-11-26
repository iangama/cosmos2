"""Isolated teardown revision; only server and spatial lifecycle may change."""
from pathlib import Path
import ast
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=ROOT/'output/is6-spatial-product0.18.2';target=ROOT/'output/is6-spatial-product0.18.3'
if target.exists():raise FileExistsError('Preserve the previous candidate')
parent=base/'build-manifest.json';manifest=json.loads(parent.read_text())
assert all(sha(ROOT/n)==v for n,v in manifest['source_sha256'].items())
assert {p.relative_to(base/'app').as_posix():sha(p) for p in (base/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}==manifest['files_sha256']
audit=ROOT/'evidence/is6-spatial-profile-audit-20261102c.json';assert json.loads(audit.read_text())['accepted']
diagnostic=ROOT/'evidence/is6-active-shutdown-20261102a.json';d=json.loads(diagnostic.read_text())
assert d['completed'] and not d['accepted'] and d['process_result']==dict(app_exit=0,server_exit=1) and not d['processes_still_running']
stage=ROOT/'output/is6-product-staging-d/is6_laboratory.py';ast.parse(stage.read_text())
shutil.copytree(base/'app',target/'app',ignore=shutil.ignore_patterns('__pycache__','*.pyc'));shutil.copy2(stage,target/'app/is6_laboratory.py')
server=target/'app/server.py';s=server.read_text()
old='''        SPATIAL.close()
        SOLAR_ZONE.close()
        PARTICLES.close()
        LAB.close()
        ATLAS.close()
        server.server_close()'''
new='''        cleanup_errors = []
        for name, component in [('spatial',SPATIAL),('solar_zone',SOLAR_ZONE),('particles',PARTICLES),('laboratory',LAB),('atlas',ATLAS)]:
            try:
                component.close()
            except Exception as error:
                cleanup_errors.append(name+': '+str(error))
        server.server_close()
        if cleanup_errors:
            raise RuntimeError('Falhas no encerramento: '+'; '.join(cleanup_errors))'''
assert s.count(old)==1;s=s.replace(old,new);ast.parse(s);server.write_text(s,encoding='utf-8')
files={p.relative_to(target/'app').as_posix():sha(p) for p in (target/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
changed=sorted(n for n in files if files[n]!=manifest['files_sha256'].get(n));assert changed==['is6_laboratory.py','server.py']
sources=dict(manifest['source_sha256'])
for p in [Path(__file__),stage,parent,audit,diagnostic,ROOT/'IS-6-PRODUTO-REVISAO-D.md',ROOT/'scripts/launch-is6-spatial-revision-d.py']:sources[p.relative_to(ROOT).as_posix()]=sha(p)
assert all(sha(ROOT/n)==v for n,v in sources.items())
record=dict(candidate='0.18.3',accepted=False,promoted=False,files_sha256=files,source_sha256=sources,base_files_sha256=manifest['files_sha256'],base_manifest=parent.relative_to(ROOT).as_posix(),changed=changed,scope='Teardown revision only; own service/native shutdown verification required;0.18.2 evidence keeps its original scope.')
(target/'build-manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(prepared=True,candidate='0.18.3',changed=changed,accepted=False)))
