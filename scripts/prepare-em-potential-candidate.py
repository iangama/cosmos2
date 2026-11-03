"""Fork frozen EM0.4 and verified potential helpers; no native/UI wiring yet."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'output/c212-em-v04-product';DEST=ROOT/'output/c212-em-potential-product';STAGE=ROOT/'output/c212-em-potential-staging'
if DEST.exists():raise ValueError('Preserve the existing potential candidate')
frozen=json.loads((ROOT/'evidence/c212-em-v04-candidate-frozen-check.json').read_bytes())
for name,digest in frozen['files_sha256'].items():
    name=name.replace('\\','/')
    if name.startswith('output/c212-em-v04-product/'):
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
receipts=[]
for name in ('em-potential-check.json','em-potential-worker-check.json','em-potential-mesh-check.json'):
    p=ROOT/'evidence'/name;r=json.loads(p.read_bytes());receipts.append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    for file,digest in r['source_sha256'].items():assert hashlib.sha256((ROOT/file.replace('\\','/')).read_bytes()).hexdigest()==digest,file
owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes()
for folder in ('app','em'):shutil.copytree(BASE/folder,DEST/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for p in STAGE.glob('*.py'):shutil.copyfile(p,DEST/'app'/p.name)
sys.path.insert(0,str(DEST/'em'));sys.path.insert(0,str(DEST/'app'))
from em_experiment import Experiment,generation
from em_native import NativeEM
storage=DEST/'c212-em-worker/product';storage.mkdir(parents=True);copies=[]
for source in (BASE/'c212-em-worker/product').glob('*.json'):
    record=json.loads(source.read_bytes())
    if not isinstance(record,dict) or not {'generation','payload','sha256'}<=set(record):continue
    assert record.get('schema')==4 and record['generation']==generation(),source.name
    Experiment.load(source);target=storage/source.name;shutil.copyfile(source,target)
    digest=hashlib.sha256(source.read_bytes()).hexdigest();assert hashlib.sha256(target.read_bytes()).hexdigest()==digest
    adjunct=source.with_name(source.stem+'.view.json')
    if adjunct.exists():
        envelope=json.loads(adjunct.read_bytes());payload=envelope['payload']
        canonical=json.dumps(payload,sort_keys=True,allow_nan=False,separators=(',',':')).encode()
        assert set(envelope)=={'payload','sha256'} and hashlib.sha256(canonical).hexdigest()==envelope['sha256'] and payload['checkpoint_sha256']==digest
        NativeEM.validate_view(payload['view']);shutil.copyfile(adjunct,storage/adjunct.name)
    copies.append({'file':source.name,'sha256':digest,'same_generation_no_migration':True,'native_view_copied':adjunct.exists()})
launcher=(ROOT/'scripts/start-c212-em-v04-candidate.ps1').read_text().replace('c212-em-v04-product','c212-em-potential-product')
launcher=launcher.replace('emCandidate = $true;','emCandidate = $true; emPotentialCandidate = $true;')
(ROOT/'scripts/start-c212-em-potential-candidate.ps1').write_text(launcher)
(DEST/'LEIA-POTENCIAL.md').write_text('''# Candidata de potencial — preparada, ainda sem integração

Fork da candidata EM0.4 congelada. Núcleo e geração0.4 foram copiados sem alterar
bytes científicos. Checkpoints/câmera experimentais permanecem na mesma geração;
nenhum arquivo do dono foi convertido. Helpers em_potential/em_slice/
em_potential_mesh foram copiados após conferir os três recibos isolados.

Ainda não há botão/endpoint/camada nativa de potencial nesta candidata. O launcher
próprio existe, mas não foi executado/verificado. O perfil128 aprovado pertence
à0.4 congelada; não aprova uma futura camada adicional. Manter o instalado3.13.

Próximo: ligar sample_slice sob command_lock, confirmar guardas no worker,
publicar nós SM preparados atomicamente e remover os anteriores só após sucesso.
Preservar o mapa anterior se falhar antes de publicar; erro de exibição tem ACK
distinto do resultado numérico. Legenda de níveisV e cortez, toggle independente
deE/B/atuação, congelamento com fontes/geração/instante próprios, sonda/exporte,
limpeza Atlas↔EM e persistência visual explicitamente versionada. Não alterar o
editor científico0.4 sem nova geração/migração. Depois medir camadas/recursos.
''')
assert owner.read_bytes()==original
report={'status':'isolated_potential_candidate_fork_prepared_helpers_not_wired_or_launched',
        'base_frozen_archive_sha256':frozen['archive_sha256'],'scientific_generation':generation(),'copied_checkpoints':copies,
        'verified_helper_receipts':receipts,'owner_pointer_preserved':True,
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (*STAGE.glob('*.py'),Path(__file__))},
        'scope':'Prepared fork only. Same scientific generation, no migration or installed promotion. Potential native/CEF/persistence integration and performance remain pending.'}
(ROOT/'evidence/em-potential-candidate-prepared-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'copied_checkpoints':len(copies),'owner_pointer_preserved':True}))
