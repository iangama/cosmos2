"""Selected finite Newtonian experiences; model definitions, never observations."""
from pathlib import Path
from functools import lru_cache
import copy,hashlib,json,math,re
from body_registry import digest,validate_population,name
from physics import PHYSICAL_SCALE
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())

def validate_descriptor(d,initial):
    keys={'id','label','goal','horizon_model_time','initial_conditions_sha256','expected_pair_indices','expected_escaper_index','display_marker_radius_m','display_min_view_distance_m','verification_times_model','construction','limitations','catalog_sha256'}
    if not isinstance(d,dict) or set(d)!=keys:raise ValueError('Descrição de experiência inválida.')
    if not isinstance(d['id'],str) or not re.fullmatch('[a-z0-9_]{1,40}',d['id']) or d['label']!=name(d['label']):raise ValueError('Nome/ID da experiência inválido.')
    if not isinstance(d['goal'],str) or not 1<=len(d['goal'])<=1000:raise ValueError('Objetivo de experiência inválido.')
    if d['initial_conditions_sha256']!=digest(initial):raise ValueError('Condições iniciais não correspondem ao modelo registrado.')
    if not isinstance(d['catalog_sha256'],str) or not re.fullmatch('[0-9a-f]{64}',d['catalog_sha256']):raise ValueError('Hash de catálogo inválido.')
    for key in ('horizon_model_time','display_marker_radius_m','display_min_view_distance_m'):
        value=d[key]
        if type(value) not in (int,float) or not math.isfinite(value) or not 0<value<=1e12:raise ValueError('Limite de experiência inválido.')
    times=d['verification_times_model']
    if not isinstance(times,list) or len(times)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in times) or not 0<times[0]<times[1]<=d['horizon_model_time']:raise ValueError('Instantes de verificação inválidos.')
    pair=d['expected_pair_indices'];escaper=d['expected_escaper_index'];n=len(initial)
    if n==2:
        if pair is not None or escaper is not None:raise ValueError('Par isolado não define troca com terceiro.')
    elif n==3:
        if not isinstance(pair,list) or len(pair)!=2 or any(type(i) is not int or not 0<=i<3 for i in pair) or pair[0]>=pair[1] or type(escaper) is not int or set(pair+[escaper])!={0,1,2}:raise ValueError('População de comparação inválida.')
    else:raise ValueError('Experiência exige2 ou3 massas.')
    if not isinstance(d['construction'],dict) or d['construction'].get('kind')!='local_curated_newtonian_point_mass_model' or d['construction'].get('observational_source') is not None:raise ValueError('Experiência não pode declarar fonte observada.')
    if not isinstance(d['limitations'],list) or any(not isinstance(v,str) for v in d['limitations']):raise ValueError('Limites da experiência inválidos.')
    return copy.deepcopy(d)

@lru_cache(maxsize=1)
def _catalog():
    raw=(ROOT/'data/science/gravity-experiments.json').read_bytes();value=json.loads(raw);sha=hashlib.sha256(raw).hexdigest()
    if value.get('schema')!=1 or value.get('source_kind')!='local_curated_model_initial_conditions':raise ValueError('Catálogo gravitacional inválido.')
    for m in value['models']:
        initial=validate_population(m['initial']);validate_descriptor({k:v for k,v in m.items() if k!='initial'}|{'catalog_sha256':sha},initial)
    return {**value,'sha256':sha,'physical_scale':PHYSICAL_SCALE}

def catalog():return copy.deepcopy(_catalog())
def model(identifier):
    c=_catalog();value=next((m for m in c['models'] if m['id']==identifier),None)
    if value is None:raise ValueError('Experiência gravitacional desconhecida.')
    return copy.deepcopy(value['initial']),{k:copy.deepcopy(v) for k,v in value.items() if k!='initial'}|{'catalog_sha256':c['sha256']}

def cluster(bodies,pair,third):
    by={b['id']:b for b in bodies};p,q,e=[by[i] for i in [*pair,third]];m=p['mass']+q['mass']
    center=[(p['mass']*x+q['mass']*y)/m for x,y in zip(p['position'],q['position'])];velocity=[(p['mass']*x+q['mass']*y)/m for x,y in zip(p['velocity'],q['velocity'])]
    r=[a-b for a,b in zip(e['position'],center)];v=[a-b for a,b in zip(e['velocity'],velocity)];distance=math.hypot(*r)
    if not distance:return None
    return {'specific_energy_canonical':.5*sum(x*x for x in v)-(m+e['mass'])/distance,'radial_velocity_canonical':sum(x*y for x,y in zip(r,v))/distance,'separation_canonical':distance}

def evaluate(bodies,seed,issued,time,events):
    d=seed.get('scenario')
    if d is None:return None
    initial=seed['initial'];ids=issued[:len(initial)];active={b['id'] for b in bodies};edited=any(e['type']!='set_attributes' for e in events)
    result={'definition':d,'conditions_edited':edited,'horizon_reached':time>=d['horizon_model_time'],'initial_ids':ids,'analysis':None}
    if not set(ids)<=active or len(bodies)!=len(ids):result['status']='modified_population';return result
    by={b['id']:b for b in bodies}
    if len(ids)==2:
        a,b=[by[i] for i in ids];r=math.dist(a['position'],b['position']);v=math.dist(a['velocity'],b['velocity']);dr=[x-y for x,y in zip(a['position'],b['position'])];dv=[x-y for x,y in zip(a['velocity'],b['velocity'])]
        result.update(status='isolated_flyby' if .5*v*v-(a['mass']+b['mass'])/r>0 else 'isolated_bound_pair',analysis={'pair':ids,'specific_energy_canonical':.5*v*v-(a['mass']+b['mass'])/r,'outward':sum(x*y for x,y in zip(dr,dv))>0,'separation_canonical':r})
        return result
    pairs=[]
    for i,j in [(0,1),(0,2),(1,2)]:
        a,b=by[ids[i]],by[ids[j]];mu=a['mass']+b['mass'];energy=.5*math.dist(a['velocity'],b['velocity'])**2-mu/math.dist(a['position'],b['position'])
        if energy<0:pairs.append((-mu/(2*energy),i,j))
    if not pairs:result['status']='no_instantaneous_bound_pair';return result
    a,i,j=min(pairs);k=next(k for k in range(3) if k not in (i,j));outer=cluster(bodies,[ids[i],ids[j]],ids[k]);hierarchy=outer is not None and outer['specific_energy_canonical']>0 and outer['radial_velocity_canonical']>0 and outer['separation_canonical']/a>30
    initial_bodies=[{'id':ids[i],**b} for i,b in enumerate(initial)];incoming=cluster(initial_bodies,ids[:2],ids[2])
    result.update(status='hierarchical_outgoing' if hierarchy else 'interaction_in_progress',analysis={'pair':[ids[i],ids[j]],'pair_indices':[i,j],'escaper':ids[k],'escaper_index':k,'binary_semimajor_canonical':a,'outer':outer,'separation_over_binary_a':outer['separation_canonical']/a if outer else None,'initial_incoming_cluster_energy_canonical':incoming['specific_energy_canonical'] if incoming else None,'matches_selected_model_outcome':hierarchy and [i,j]==d['expected_pair_indices'] and k==d['expected_escaper_index']})
    return result
