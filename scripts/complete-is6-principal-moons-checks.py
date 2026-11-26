"""Finish the already-authorized local checks after the one active profile; never rerun it."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'output/is6-moons-completion-20261111a'
PROFILE=ROOT/'evidence/is6-principal-moons-navigation-profile-20261111a.json'
PYTHON=ROOT/'.tooling/python/Scripts/python.exe'


def main():
    FOLDER.mkdir(exist_ok=False)
    result=dict(completed=False,steps=[],started_utc=datetime.now(timezone.utc).isoformat(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    status=FOLDER/'result.json'
    def persist():status.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    def run(name,script,args=(),native=True):
        log=FOLDER/(name+'.log')
        with log.open('xb') as stream:
            done=subprocess.run([str(PYTHON) if native else sys.executable,'-Xutf8',script,*args],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        row=dict(name=name,exit=done.returncode,log=log.relative_to(ROOT).as_posix());result['steps'].append(row);persist()
        print(json.dumps(row),flush=True)
        return done.returncode
    def handoff():
        session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
        text=('ATUALIZAÇÃO AUTOMÁTICA DOS TESTES LOCAIS\n'
            +'Consultar output/is6-moons-completion-20261111a/result.json e logs.\n'
            +'Resultados de subprocessos:'+json.dumps(result['steps'],ensure_ascii=False)+'\n'
            +'Sessão atual:'+json.dumps({k:session.get(k) for k in ['app','server','launcher','serverScript']})+'\n'
            +'Não repetir perfil15janelas20261111a. Ler seu auditor e recusas, se houver.\n'
            +'As duas capturas do catálogo ainda exigem revisão visual humana.\n'
            +'Atalho novo Abrir-Planetas-e-Luas.cmd; versão0.24 e atalho anterior preservados.\n'
            +'Backupv13 label20261111d será executado a seguir; ver recibo/resultado antes de repetir.\n'
            +'V1segue7/21;IS6incompleto;K5Arecusado;nenhum push.\n\n')
        p=ROOT/'PASSAGEM-COTA.txt';p.write_text(text+p.read_text(),encoding='utf8')
        (ROOT/'LEIA-PRIMEIRO.md').write_text('COSMOS2 — CONTINUIDADE DOS TESTES LOCAIS0.25.1\n\nLer AGENTS.md e topo dePASSAGEM-COTA.txt.\nConsultar output/is6-moons-completion-20261111a/result.json antes de qualquer\nreexecução. Perfil15 de20261111a é único e não deve ser repetido.\nApp deve permanecer aberto; sessão atual emoutput/session.json.\nCatálogo16 teve capturas que ainda precisam revisão visual.\nBackupv13 label20261111d:conferir recibo e commit local. Nenhum push.\nV1segue7/21;IS6incompleto;K5Arecusado. Sem subagentes.\n',encoding='utf8')
    persist()
    try:
        while True:
            profile=json.loads(PROFILE.read_text())
            if profile.get('completed') or profile.get('failure'):break
            time.sleep(3)
        run('profile-audit','scripts/audit-is6-principal-moons-navigation-profile.py',['--label','20261111a'])
        run('journey','scripts/verify-native-is6-principal-moons-journey.py',['--label','20261111a'])
        run('catalog-page','scripts/verify-native-is6-principal-moons-catalog-page.py',['20261111a'])
        run('reopen','scripts/verify-is6-moons-app-reopen.py',['--label','20261111a'])
        handoff()
        code=run('source-backup','scripts/sync-github-source-snapshot-v13.py',['--label','20261111d'],native=False)
        if code==0:
            repo=ROOT.parent/'cosmos2-github-snapshot-20261103'
            with (FOLDER/'git.log').open('xb') as log:
                for args in [['git','-c','core.whitespace=cr-at-eol','diff','--check','--','*.py','*.md','*.cmd'],
                             ['git','add','-A'],['git','commit','-q','-m','Preserve sixteen-body native navigation, own profile and Unicode favorites locally']]:
                    subprocess.run(args,cwd=repo,stdout=log,stderr=subprocess.STDOUT,check=True)
            commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip();result['local_commit']=commit
            sync=ROOT/'evidence/github-source-sync-20261111d.json';data=json.loads(sync.read_text())
            receipt=ROOT/'evidence/github-source-local-20261111d.json'
            assert not receipt.exists()
            receipt.write_text(json.dumps(dict(accepted=True,local_only=True,commit=commit,files=data['files'],sync_receipt_sha256=hashlib.sha256(sync.read_bytes()).hexdigest(),scope='Partial local source/evidence snapshot. No push.'),indent=2)+'\n')
            p=ROOT/'PASSAGEM-COTA.txt';p.write_text('BACKUP LOCAL CONCLUÍDO:'+commit+';recibos20261111d. Nenhum push.\n\n'+p.read_text(),encoding='utf8')
        result['completed']=True
        result['all_steps_zero']=all(s['exit']==0 for s in result['steps'])
    except Exception:result['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
