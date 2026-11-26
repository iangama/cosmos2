"""Append final C2-14 handoff artifacts to the local snapshot; never push."""
from pathlib import Path
import hashlib,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
BACKUP=ROOT.parent/'cosmos2-github-snapshot-20261103'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
dirty=subprocess.check_output(['git','status','--porcelain'],cwd=BACKUP,text=True)
assert all(line[3:]=='LEIA-PRIMEIRO.md' for line in dirty.splitlines()),dirty
assert sha(BACKUP/'LEIA-PRIMEIRO.md')==sha(ROOT/'LEIA-PRIMEIRO.md') if dirty else True
receipt=ROOT/'evidence/github-source-local-20261114e.json'
assert not receipt.exists()
base=json.loads((ROOT/'evidence/github-source-local-20261114d.json').read_text())
assert base['accepted'] and base['commit']==subprocess.check_output(['git','rev-parse','HEAD'],cwd=BACKUP,text=True).strip()
inventory_path=BACKUP/'snapshot-inventory.json'
inventory=json.loads(inventory_path.read_text())
rows={item['path']:item for item in inventory['files']}
names=['LEIA-PRIMEIRO.md','output/continuity-checkpoint-20261114-c214-8.txt','C2-14-ORBITAS-INTEGRACAO-RESULTADO-20261114.md','C2-14-ORBITAS-PERFIL-CONTRATO-20261114.md','evidence/c214-orbits-visual-20261114b.json','evidence/c214-orbits-profile-preparation-20261114a.json','scripts/prepare-c214-orbits-profile.py','scripts/finalize-c214-orbits-handoff-backup.py']
assert all((ROOT/name).is_file() for name in names)
for name in names:
 source,destination=ROOT/name,BACKUP/name
 if destination.exists():assert name in rows and (sha(destination)==rows[name]['sha256'] or (name=='LEIA-PRIMEIRO.md' and sha(destination)==sha(source)))
 seal=sha(source);destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)
 assert sha(source)==sha(destination)==seal
 rows[name]=dict(path=name,bytes=source.stat().st_size,sha256=seal)
inventory['files']=[rows[k] for k in sorted(rows)]
inventory_path.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
subprocess.run(['git','add','-A'],cwd=BACKUP,check=True)
subprocess.run(['git','commit','-q','-m','Registra passagem C2-14 e preparacao do perfil sem medicoes'],cwd=BACKUP,check=True)
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=BACKUP,text=True).strip()
assert not subprocess.check_output(['git','status','--porcelain'],cwd=BACKUP)
proof=dict(accepted=True,completed=True,local_only=True,push=False,revision=23,appendix=True,previous_commit=base['commit'],commit=commit,files=len(rows),appended=names,scope='Final handoff and profile preparation only; no performance measurements')
receipt.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(proof,ensure_ascii=False))
