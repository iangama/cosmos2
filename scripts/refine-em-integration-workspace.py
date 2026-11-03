"""Apply the staged workspace and read-only SI instruments to separate G only."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
CANDIDATE=ROOT/'output/c212-em-integration-product'
STAGED=ROOT/'scripts/em-integration-ui'
receipt=ROOT/'evidence/em-integration-workspace-prepared.json'
assert CANDIDATE.exists() and not receipt.exists()
before=json.loads((ROOT/'evidence/em-integration-candidate-prepared.json').read_bytes())
for name,digest in before['source_sha256'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
owner=(ROOT/'user/sessions/latest.json').read_bytes()

for filename in ('style.css','workspace.js','particle.js','species.json'):
    shutil.copyfile(STAGED/filename,CANDIDATE/'app/ui/em'/filename)
shutil.copyfile(STAGED/'em.html',CANDIDATE/'app/ui/em.html')
shutil.copyfile(STAGED/'em_measurements.py',CANDIDATE/'app/em_measurements.py')

path=CANDIDATE/'app/ui/em/app.js';source=path.read_text()
old='if(window.renderPotentialEM)window.renderPotentialEM();'
assert source.count(old)==1
source=source.replace(old,old+'if(window.renderParticle)window.renderParticle();if(window.renderWorkspace)window.renderWorkspace();')
path.write_text(source)

path=CANDIDATE/'app/ui/em/native.js';source=path.read_text()
old="e.preventDefault();run(async()=>{await nativeRequest('leave');location.href='/';});"
assert source.count(old)==1
path.write_text(source.replace(old,"e.preventDefault();if(pending)return;run(async()=>{await nativeRequest('leave');location.href='/';});"))

path=CANDIDATE/'app/em_laboratory.py';source=path.read_text()
old="            if name in ('configure_potential','sample_potential','probe_potential'):return self._potential_command(value)"
assert source.count(old)==1
new="""            if name=='measure_particle':
                required={'command','system_id','edit_token','revision','frame','expected_time_s'}
                if set(value)!=required:raise ValueError('Exact measurement guard fields required')
                self._worker({**value,'command':'probe','position_m':[0,0,0]})
                from em_measurements import measure
                reading=measure(self._current())
                return {'type':'ack','command':name,'paused':True,'result':reading,'artifact':self._artifact(reading)}
"""+old
path.write_text(source.replace(old,new))

path=CANDIDATE/'app/em_native.py';source=path.read_text()
old="'Scale':3*DISPLAY_SCALE}},'Renderable':{'Type':'RenderableCartesianAxes'}"
assert source.count(old)==1
source=source.replace(old,"'Scale':1.5*DISPLAY_SCALE}},'Renderable':{'Type':'RenderableCartesianAxes','XColor':[.55,.25,.25],'YColor':[.25,.5,.32],'ZColor':[.3,.4,.65]}")
path.write_text(source)

path=CANDIDATE/'app/ui/index.html';source=path.read_text()
assert 'CANDIDATA EM 0.4' in source
path.write_text(source.replace('CANDIDATA EM 0.4','CANDIDATA DE INTEGRAÇÃO EM'))
(CANDIDATE/'LEIA-CANDIDATA.md').write_text(
    '# C2-12 — candidata G de integração, ainda parcial\n\n'
    'Cópia de F com storage próprio. Núcleos científico0.4 e nuvem/helper/worker\n'
    'preservados byte a byte; sem instalação ou aceite herdado da nova interface.\n'
    'Interface: um painel por vez, pausa sempre acessível, escala100–150%,\n'
    'editor da partícula definida e referências de carga/massa CODATA2022.\n'
    'Instrumentos leem uma fase confirmada; força emN, potência emW e balanço\n'
    'da matéria emJ. Trabalho declarado por diferença do potencial estático\n'
    'desde a referência física; campos/reservatórios/radiação ficam fora.\n'
    'Executar pelo launcher start-c212-em-integration-candidate.ps1.\n'
    'Conferir recibos atuais de evidence; preparação não é prova de execução.\n'
    'Catálogo planetário, malha relativística e aceite geralC2-12 pendentes.\n',encoding='utf-8')
for folder in ('em','em-cloud'):
    for base in (ROOT/'output/c212-em-time-product'/folder).rglob('*'):
        if base.is_file() and '__pycache__' not in base.parts:
            relative=base.relative_to(ROOT/'output/c212-em-time-product')
            assert base.read_bytes()==(CANDIDATE/relative).read_bytes(),str(relative)
assert (ROOT/'user/sessions/latest.json').read_bytes()==owner
files=[p for folder in ('app','em','em-cloud') for p in (CANDIDATE/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
report={'status':'workspace_and_particle_editor_prepared_awaiting_real_CEF_and_instrument_audit',
        'owner_pointer_preserved':True,'small_and_cloud_scientific_and_worker_sources_byte_identical_to_F':True,
        'source_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        'staged_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in STAGED.iterdir() if p.is_file()},
        'scope':'Local separate G candidate. No experience, performance or installation acceptance inherited from preparation.'}
receipt.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'candidate':str(CANDIDATE)}),flush=True)
