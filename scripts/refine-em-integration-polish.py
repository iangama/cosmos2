"""Preserve G's executed interface before minor Portuguese text refinement."""
from pathlib import Path
import hashlib
import json
import shutil
import tarfile

ROOT=Path(__file__).resolve().parents[1];G=ROOT/'output/c212-em-integration-product'
archive=ROOT/'output/em-integration-before-polish-20261021.tar.gz'
receipt=ROOT/'evidence/em-integration-polish-prepared.json'
assert not archive.exists() and not receipt.exists()
owner=(ROOT/'user/sessions/latest.json').read_bytes()
ui=json.loads((ROOT/'evidence/em-integration-native-ui-release1-check.json').read_bytes())
assert ui['completed'] and not ui['JS_errors']
names=dict(ui['source_sha256'])
for name in ('scripts/verify-em-integration-measurements.py','evidence/em-integration-measurements-check.json',
             'evidence/em-integration-native-ui-release1-check.json','evidence/em-integration-navigation-release1-check.json',
             'evidence/em-integration-restart-check.json'):
    names[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
with tarfile.open(archive,'w:gz') as tar:
    for name,digest in sorted(names.items()):
        path=ROOT/name;assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,name
        tar.add(path,arcname=name.replace('\\','/'))

def replace(path,old,new):
    text=path.read_text();assert text.count(old)==1,(str(path),old)
    path.write_text(text.replace(old,new))

replace(G/'app/em_measurements.py',
    'Local uniform-field reference. Exact helix reference requires uniform B, no acting E and no spatially varying sources.',
    'Referência local para B uniforme. A hélice de referência exige B uniforme e ausência de força elétrica.')
replace(G/'app/ui/em/particle.js',"'Partícula: '+m.particle.id", "'Partícula: '+(m.particle.id==='test-particle'?'partícula de teste':m.particle.id)")
replace(G/'app/ui/em/native.js',"c.objects.length+' marcadores'", "c.objects.length+(c.objects.length===1?' marcador':' marcadores')")
replace(G/'app/ui/em/app.js',":'Comando confirmado: '+command;",
    ":(window.commandDescription?window.commandDescription(command):'Condição confirmada.');")
path=G/'app/ui/em/workspace.js'
path.write_text(path.read_text()+"""
window.commandDescription=name=>({
  pause:'Experimento pausado.',resume:'Experimento em evolução.',advance:'Passo concluído.',
  load_preset:'Experiência carregada pausada.',load:'Fase retomada pausada.',
  save:'Fase, vista e preferências de tempo salvas.',edit:'Alteração física confirmada.',
  set_controls:'Atuação física confirmada.',set_visual:'Camada ou seleção atualizada.',
  set_rate:'Ritmo solicitado atualizado.',set_timestep:'Passo de integração atualizado.',
  field_map:'Campos medidos no instante confirmado.',trace_fields:'Linhas de referência calculadas.',
  measure_particle:'Força e energia medidas no instante confirmado.'
}[name]||'Condição confirmada.');
""")
for name in ('particle.js','workspace.js'):
    shutil.copyfile(G/'app/ui/em'/name,ROOT/'scripts/em-integration-ui'/name)
shutil.copyfile(G/'app/em_measurements.py',ROOT/'scripts/em-integration-ui/em_measurements.py')
assert (ROOT/'user/sessions/latest.json').read_bytes()==owner
report={'status':'Portuguese_UI_text_refined_after_preserving_executed_sources',
        'before_archive':str(archive.relative_to(ROOT)).replace('\\','/'),
        'before_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
        'before_files_sha256':names,'owner_pointer_preserved':True,
        'scope':'Human-facing labels and explanation only. Force/energy formulas and all em/em-cloud scientific and worker sources unchanged. Restart required to load the new parent module.'}
receipt.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='before_files_sha256'}),flush=True)
