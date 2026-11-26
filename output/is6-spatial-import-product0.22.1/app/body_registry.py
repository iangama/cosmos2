"""Stable scientific identities, source links and checkpoint3 validation."""
from pathlib import Path
from functools import lru_cache
import copy
import hashlib
import json
import math
import platform
import re
import rebound
import numpy as np
from physics import CONTRACT, PHYSICAL_SCALE

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
MAX_BODIES=256
CUSTOM_CONTRACT={**copy.deepcopy(CONTRACT),'frame':'user_defined_initial_origin_inertial',
                 'units':{'system':'canonical','G':1.0},'epoch':None,
                 'time':'elapsed model time; no absolute UTC/TDB epoch assigned'}
ID_PATTERN=re.compile(r'(?:p(?:0|[1-9][0-9]{0,2})|exp:[0-9a-f]{32}:(?:naif:(?:10|399|301|599)|body:[0-9a-f]{32}))')

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False).encode()).hexdigest()

def valid_system(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{32}',value):raise ValueError('Identificador de sistema inválido.')
    return value

def name(value):
    if not isinstance(value,str) or not 1<=len(value.strip())<=80 or any(ord(c)<32 or ord(c)==127 for c in value):raise ValueError('Nome do corpo deve ter1–80 caracteres sem controles.')
    return value.strip()

def scene_nodes(identifier):
    suffix=hashlib.sha256(identifier.encode()).hexdigest()[:24]
    return {'scene_node':'LabBody_'+suffix,'label_node':'LabLabel_'+suffix,'spin_node':'LabSpin_'+suffix,'shape_node':'LabShape_'+suffix}

def fixture_metadata(count):
    return [{'id':f'p{i}','name':f'Corpo p{i}','origin':{'kind':'deterministic_fixture','seed_index':i}} for i in range(count)]

def atlas_metadata(initial):
    return [{'id':b['id'],'name':b['name'],'reference_id':b['reference_id'],
             'origin':{'kind':'atlas_copy','source_branch_id':initial['branch_id']}} for b in initial['bodies']]

def validate_registry(rows,issued,system_id,seed_count,initial):
    valid_system(system_id)
    if not isinstance(rows,list) or not 1<=len(rows)<=MAX_BODIES:raise ValueError('População deve ter1–256 corpos ativos.')
    if not isinstance(issued,list) or len(issued)!=len(set(x for x in issued if isinstance(x,str))) or any(not isinstance(x,str) or not ID_PATTERN.fullmatch(x) for x in issued):raise ValueError('Histórico de IDs emitidos inválido.')
    sources={b['id']:b for b in initial['bodies']} if initial else {}
    source_ids=set(sources) if initial else {f'p{i}' for i in range(seed_count or 0)}
    for identifier in issued:
        if identifier not in source_ids and not identifier.startswith('exp:'+system_id+':body:'):raise ValueError('ID emitido não pertence ao sistema ou à origem registrada.')
    ids=set()
    for row in rows:
        if not isinstance(row,dict) or set(row)-{'id','name','origin','reference_id'}:raise ValueError('Registro do corpo inválido.')
        identifier=row.get('id');origin=row.get('origin',{})
        if not isinstance(identifier,str) or not ID_PATTERN.fullmatch(identifier) or identifier in ids or identifier not in issued:raise ValueError('ID ausente, duplicado ou não emitido.')
        if row.get('name')!=name(row.get('name')) or not isinstance(origin,dict):raise ValueError('Nome/origem de corpo inválido.')
        kind=origin.get('kind')
        if kind=='atlas_copy':
            source=sources.get(identifier)
            if source is None or row.get('reference_id')!=source['reference_id'] or origin!={'kind':'atlas_copy','source_branch_id':initial['branch_id']}:raise ValueError('Vínculo com fonteAtlas inválido.')
        elif kind=='deterministic_fixture':
            index=origin.get('seed_index')
            if type(seed_count)!=int or type(index)!=int or not 0<=index<seed_count or identifier!=f'p{index}' or set(origin)!={'kind','seed_index'} or row.get('reference_id') is not None:raise ValueError('Identidade de fixture inválida.')
        elif kind=='user_model':
            if origin!={'kind':'user_model'} or not identifier.startswith('exp:'+system_id+':body:') or row.get('reference_id') is not None:raise ValueError('Objeto criado não pode receber uma fonte observada.')
        else:raise ValueError('Origem de corpo desconhecida.')
        ids.add(identifier)
    return copy.deepcopy(rows)

def phases_si(request):
    mass=request.get('mass_kg')
    if type(mass) not in (int,float) or not math.isfinite(mass) or not 1e-12<=mass/PHYSICAL_SCALE['mass_unit_kg']<=100:raise ValueError('Massa fora do domínio do editor.')
    vectors=[]
    for key,limit,scale in [('position_m',1e17,PHYSICAL_SCALE['length_unit_m']),('velocity_m_s',1e7,PHYSICAL_SCALE['velocity_unit_m_s'])]:
        value=request.get(key)
        if not isinstance(value,list) or len(value)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in value) or math.hypot(*value)>limit:raise ValueError('Vetor SI inválido ou fora do domínio: '+key)
        vectors.append([v/scale for v in value])
    return {'mass':mass/PHYSICAL_SCALE['mass_unit_kg'],'position':vectors[0],'velocity':vectors[1]}

def validate_population(initial):
    rows=initial if isinstance(initial,list) else [initial]
    if not 1<=len(rows)<=MAX_BODIES:raise ValueError('População inicial deve conter1–256 corpos.')
    checked=[]
    for b in rows:
        if not isinstance(b,dict) or set(b)!={'name','mass','position','velocity'} or b.get('name')!=name(b.get('name')):raise ValueError('Corpo inicial inválido.')
        mass=b['mass']
        if type(mass) not in (int,float) or not math.isfinite(mass) or not 1e-12<=mass<=100:raise ValueError('Massa inicial fora do domínio.')
        for key,limit in [('position',1e17/PHYSICAL_SCALE['length_unit_m']),('velocity',1e7/PHYSICAL_SCALE['velocity_unit_m_s'])]:
            value=b[key]
            if not isinstance(value,list) or len(value)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in value) or math.hypot(*value)>limit:raise ValueError('Fase inicial fora do domínio.')
        if any(math.dist(b['position'],p['position'])<1e-12 for p in checked):raise ValueError('População inicial tem partículas coincidentes.')
        checked.append(copy.deepcopy(b))
    return checked

def validate_user_seed(seed):
    if not isinstance(seed,dict) or set(seed) not in ({'kind','initial'},{'kind','initial','scenario'},{'kind','initial','orbital_preset'}) or seed.get('kind')!='user_system':raise ValueError('Invalid user-system seed')
    initial=validate_population(seed['initial'])
    if 'orbital_preset' in seed:
        d=seed['orbital_preset']
        if not isinstance(d,dict) or set(d)!={'id','initial_conditions_sha256','observational_source'} or d['id'] not in ('resonant2','circulating18') or d['initial_conditions_sha256']!=digest(initial) or d['observational_source'] is not None or len(initial)!=3:raise ValueError('Invalid synthetic orbital preset origin')
    if 'scenario' in seed:
        from gravity_experiments import validate_descriptor
        validate_descriptor(seed['scenario'],initial)
    return initial

@lru_cache(maxsize=3)
def generation(kind):
    return {'schema':1,'model_id':'cosmos2:editable-newtonian-'+kind,'model_version':'3.13.0',
            'candidate_extension':{'id':'is3-body-fields','version':'0.7.1','initial_format':'solar_four_physical_centers/1.0.0',
                'code_sha256':{p:hashlib.sha256(Path(__file__).with_name(p).read_bytes()).hexdigest() for p in ['solar_contract.py','solar_catalog.py','solar_import.py','import_dispatch.py','solar_tides.py','earth_magnetism.py','geomagnetism.py','jupiter_magnetism.py','jrm33.py','body_field_geometry.py','body_field_scene.py','body_field_layer.py','body_field_lines.py','body_field_view.py','body_field_maps.py','body_field_map_geometry.py','body_field_map_layer.py','body_field_points.py']}},
            'code_sha256':{p:hashlib.sha256((Path(__file__).with_name(Path(p).name) if Path(__file__).with_name(Path(p).name).is_file() else ROOT/p).read_bytes()).hexdigest() for p in ['app/cloud_transport.py','app/cloud_driver.py','app/test_cloud.py','app/resonant_angles.py','app/orbital_instruments.py','app/equilibrium_tide.py','app/material_driver.py','app/material_tides.py','app/j2_field.py','app/gravity_harmonics.py','app/physics.py','app/session.py','app/body_registry.py','app/body_attributes.py','app/orbital_diagnostics.py','app/gravity_experiments.py','app/gravity_field.py','app/gravity_instruments.py','app/field_layers.py','app/field_geometry.py','app/field_sections.py','app/instrument_history.py','app/probe_comparison.py','app/branch_store.py','app/worker.py']},
            'data_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['data/science/canonical-units.json','data/science/gravity-experiments.json','data/science/igrf14coeffs.txt','output/is3-earth-orientation-staging/earth_000101_270118_261022.bpc','evidence/is3-earth-orientation-acquisition-20261023.json','data/spice/pck00011.tpc','data/spice/naif0012.tls','output/is3-body-points-product/app/jrm33-coefficients.json','evidence/is3-jupiter-orientation-acquisition-20261023b.json']},
            'runtime':{'python':platform.python_version(),'rebound':rebound.__version__,'numpy':np.__version__}}
