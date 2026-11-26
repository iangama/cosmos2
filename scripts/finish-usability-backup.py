"""Make one local source/evidence snapshot after native collection has stopped; never push."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import traceback

ROOT=Path(__file__).resolve().parents[1]
BACKUP=ROOT.parent/'cosmos2-github-snapshot-20261103'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    progress=ROOT/'output/curation-backup-20261114f.json'
    receipt=ROOT/'evidence/github-source-local-20261114f.json'
    assert not progress.exists() and not receipt.exists()
    state=dict(state='checking',local_only=True,push=False)
    def persist():progress.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    persist()
    try:
        for label in ['20261114a','20261114b']:
            host=json.loads((ROOT/f'evidence/c214-orbits-profile-host-{label}.json').read_text())
            assert host['state']=='failed' and host['owner_restored'] and not host.get('cleanup_failure')
        assert not subprocess.check_output(['git','status','--porcelain'],cwd=BACKUP)
        previous=subprocess.check_output(['git','rev-parse','HEAD'],cwd=BACKUP,text=True).strip()
        state['state']='copying';persist()
        subprocess.run([sys.executable,'-Xutf8',str(ROOT/'scripts/sync-github-source-snapshot-v24.py'),'--label','20261114f'],cwd=ROOT,check=True)
        sync_path=ROOT/'evidence/github-source-sync-20261114f.json'
        sync=json.loads(sync_path.read_text());assert sync['accepted'] and sync['completed']
        state['state']='committing';persist()
        subprocess.run(['git','add','-A'],cwd=BACKUP,check=True)
        subprocess.run(['git','commit','-q','-m','Preserva curadoria do fluxo original, rascunho de correcao e ensaios C2-14'],cwd=BACKUP,check=True)
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=BACKUP,text=True).strip()
        assert not subprocess.check_output(['git','status','--porcelain'],cwd=BACKUP)
        proof=dict(accepted=True,completed=True,local_only=True,push=False,revision=24,previous_commit=previous,commit=commit,
                   files=sync['files'],sync_receipt_sha256=sha(sync_path),scope='Local partial source and evidence backup. Does not install or accept the prepared user-flow fix.')
        receipt.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        state.update(state='complete',commit=commit,files=sync['files'])
    except Exception:state.update(state='failed',failure=traceback.format_exc())
    persist()
    print(json.dumps(state,ensure_ascii=False),flush=True)
    return 0 if state['state']=='complete' else 1


if __name__=='__main__':raise SystemExit(main())
