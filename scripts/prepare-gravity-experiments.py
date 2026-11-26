"""Pin verified local models and provenance; never downloads observational conditions."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
raw=json.loads((ROOT/'output/gravity-experiment-candidates.json').read_text())
verified=json.loads((ROOT/'evidence/gravity-experiment-candidates-check.json').read_text());assert {r['model'] for r in verified['models']}=={'flyby','capture','ejection'}
labels={'flyby':'Encontro hiperbólico','capture':'Captura por troca','ejection':'Ejeção de uma tripla'}
goals={'flyby':'Compare a aproximação e o afastamento de duas massas livres. A energia positiva do par impede captura conservativa de dois corpos.','capture':'Um visitante inicialmente livre troca energia com um binário. Observe a captura do visitante e a saída de um membro antigo.','ejection':'Um terceiro corpo inicialmente ligado ao conjunto ganha energia e se afasta, enquanto o binário fica mais ligado.'}
models=[]
for key in ['flyby','capture','ejection']:
 m=raw['models'][key];names={'flyby':['Massa A','Massa B'],'capture':['Massa A','Companheiro B','Visitante C'],'ejection':['Massa A','Companheiro B','Terceiro C']}[key];initial=[{'name':names[i],**b} for i,b in enumerate(m['initial'])]
 encoded=json.dumps(initial,sort_keys=True,ensure_ascii=True,allow_nan=False).encode()
 models.append({'id':key,'label':labels[key],'goal':goals[key],'horizon_model_time':m['horizon'],'initial':initial,'initial_conditions_sha256':hashlib.sha256(encoded).hexdigest(),'expected_pair_indices':None if key=='flyby' else [0,2] if key=='capture' else [0,1],'expected_escaper_index':None if key=='flyby' else 1 if key=='capture' else 2,'display_marker_radius_m':3e5,'display_min_view_distance_m':3e6,'verification_times_model':[m['horizon']*2/3,m['horizon']],'construction':{'kind':'local_curated_newtonian_point_mass_model','base_parameters':m['source_parameters'],'similarity_scaling':raw['scaling'],'observational_source':None},'limitations':['Condições de modelo, sem corpos observados.','Gravidade pontual newtoniana, sem colisões, marés, J2 ou GR.','Captura/escape verificados em intervalo finito, sem garantia eterna.']})
catalog={'schema':1,'version':'1.0.0','frame':'user_defined_initial_origin_inertial','units':'canonical G=1; SI binding in canonical-units.json','source_kind':'local_curated_model_initial_conditions','concept_reference':'https://arxiv.org/abs/astro-ph/9604015','models':models}
path=ROOT/'data/science/gravity-experiments.json';path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'file':str(path),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}))

verified.update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size,url=None,definition_file='data/science/gravity-experiments.json',producer='scripts/prepare-gravity-experiments.py')
(ROOT/'evidence/gravity-experiment-candidates-check.json').write_text(json.dumps(verified,indent=2)+'\n',encoding='utf-8')
