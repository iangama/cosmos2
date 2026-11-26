"""Finish the authorized local snapshot/commit and persist its plain-text handoff."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
BACKUP=ROOT.parent/'cosmos2-github-snapshot-20261103'
label='20261112c'
progress=ROOT/f'output/is6-expanded-backup-{label}-progress.json'
assert not progress.exists()
state=dict(pid=os.getpid(),state='starting',push=False)
def persist():progress.write_text(json.dumps(state,indent=2)+'\n')
persist()
try:
    assert json.loads((ROOT/'evidence/is6-expanded-journey-service-20261112b.json').read_text())['accepted']
    assert json.loads((ROOT/'evidence/is6-expanded-journey-http-20261112b.json').read_text())['accepted']
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=BACKUP)
    state['state']='copying';persist()
    subprocess.run([str(ROOT/'.tooling/python/Scripts/python.exe'),'-Xutf8','scripts/sync-github-source-snapshot-v16.py','--label',label],cwd=ROOT,check=True)
    sync_path=ROOT/f'evidence/github-source-sync-{label}.json';sync=json.loads(sync_path.read_text());assert sync['accepted']
    state['state']='committing';persist()
    subprocess.run(['git','add','-A'],cwd=BACKUP,check=True)
    subprocess.run(['git','commit','-q','-m','Preserva preparação0.27 e admissão16-4-16 com passagem atual'],cwd=BACKUP,check=True)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=BACKUP,text=True).strip()
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=BACKUP)
    receipt=dict(accepted=True,local_only=True,commit=commit,files=sync['files'],sync_receipt_sha256=hashlib.sha256(sync_path.read_bytes()).hexdigest(),scope='Partial local source/evidence snapshot, no push.')
    (ROOT/f'evidence/github-source-local-{label}.json').write_text(json.dumps(receipt,indent=2)+'\n')
    header=f'BACKUPv16 LOCAL CONCLUÍDO:{commit};{sync["files"]}arquivos;recibos20261112c. Nenhum push.\n'
    passage=ROOT/'PASSAGEM-COTA.txt';passage.write_text(header+'\n'+passage.read_text(encoding='utf8'),encoding='utf8')
    leia=ROOT/'LEIA-PRIMEIRO.md';text=leia.read_text(encoding='utf8');first,rest=text.split('\n',1)
    leia.write_text(first+'\n\n'+header+rest,encoding='utf8')
    archive=ROOT/'output/handoff-archive/cota-20261112c-final.txt';archive.write_bytes(passage.read_bytes())
    state.update(state='complete',commit=commit,files=sync['files'],handoff=str(archive));persist()
    print(json.dumps(state),flush=True)
except BaseException as error:
    state.update(state='failed',error=repr(error));persist();raise
