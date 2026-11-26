"""Bounded read-only osculating-angle definitions, snapshots and finite history."""
import copy
import json
import math
import re
import numpy as np

from physics import PHYSICAL_SCALE as U
from resonant_angles import instantaneous,basis,vector
from body_registry import MAX_BODIES
import gravity_harmonics

MAX_RECORDS=128
POLICY=('Ângulos críticos osculantes em plano inercial fixo, com primário explícito. '
    'Razão de períodos e arco amostrado não provam ressonância ou captura permanente. '
    'Leituras passivas, sem força adicional ou reinício do integrador.')


def empty():
    return {'schema':1,'revision':0,'definition':None,'events':[],'recording':False,
        'cadence_wall_s':1.,'samples':[],'dropped':0,'next_sequence':0}


def definition(value,known_ids):
    keys={'primary_id','inner_id','outer_id','j','plane_normal','plane_reference'}
    if not isinstance(value,dict) or set(value)!=keys:raise ValueError('Informe primário, dois orbitadores, razão e plano explícitos.')
    ids=[value[k] for k in ('primary_id','inner_id','outer_id')]
    if any(not isinstance(i,str) or i not in known_ids for i in ids) or len(set(ids))!=3:raise ValueError('Escolha três identidades ativas diferentes.')
    if type(value['j']) is not int or not 2<=value['j']<=9:raise ValueError('Use razão de primeira ordem j:(j−1), com j entre2e9.')
    x,y,z=basis(value['plane_normal'],value['plane_reference'])
    normal=vector(value['plane_normal']);reference=vector(value['plane_reference'])
    normalized=(abs(np.linalg.norm(normal)-1)<4e-15 and abs(np.linalg.norm(reference)-1)<4e-15 and abs(float(normal@reference))<4e-15)
    return copy.deepcopy(value) if normalized else {**copy.deepcopy(value),'plane_normal':z.tolist(),'plane_reference':x.tolist()}


def _event(configuration,operation,**payload):
    result=copy.deepcopy(configuration)
    if result['revision']>=4096:raise ValueError('Limite de configurações orbitais atingido.')
    result['revision']+=1;result['events'].append({'revision':result['revision'],'operation':operation,**copy.deepcopy(payload)})
    return result


def configure(configuration,request,active_ids,known_ids,bodies):
    operation=request.get('operation')
    if operation in ('definition','align_plane'):
        proposed=request.get('definition')
        if proposed is not None:
            if operation=='align_plane':
                proposed=copy.deepcopy(proposed)
                primary=next((b for b in bodies if b['id']==proposed.get('primary_id')),None)
                inner=next((b for b in bodies if b['id']==proposed.get('inner_id')),None)
                if primary is None or inner is None:raise ValueError('Primário e órbita interna precisam estar ativos.')
                r=np.asarray(inner['position'])-primary['position'];v=np.asarray(inner['velocity'])-primary['velocity']
                proposed.update(plane_normal=np.cross(r,v).tolist(),plane_reference=r.tolist())
            proposed=definition(proposed,active_ids)
        result=_event(configuration,'definition',definition=proposed);result['definition']=proposed
        if proposed is None:result['recording']=False
    elif operation=='capture':
        recording=request.get('recording');cadence=request.get('cadence_wall_s')
        if type(recording) is not bool or type(cadence) not in (int,float) or not math.isfinite(cadence) or not .25<=cadence<=5.:raise ValueError('Informe gravação e cadência real entre0,25e5s.')
        if recording and configuration['definition'] is None:raise ValueError('Defina o instrumento orbital antes de gravar.')
        result=_event(configuration,'capture',recording=recording,cadence_wall_s=cadence)
        result.update(recording=recording,cadence_wall_s=cadence)
    elif operation=='clear':
        result=_event(configuration,'clear');result.update(samples=[],dropped=0,next_sequence=0)
    else:raise ValueError('Operação de instrumento orbital desconhecida.')
    return result


def _phase_bodies(rows,known_ids):
    if not isinstance(rows,list) or len(rows)>3:raise ValueError('Snapshot orbital deve conter até três estados selecionados.')
    bodies=[];ids=[]
    for row in rows:
        if not isinstance(row,dict) or set(row)!={'id','GM_m3_s2','position_m','velocity_m_s'} or row.get('id') not in known_ids or row['id'] in ids:raise ValueError('Fonte orbital desconhecida ou duplicada.')
        gm=row['GM_m3_s2']
        if type(gm) not in (int,float) or not math.isfinite(gm) or not 1e-12<=gm/U['nominal_GM_unit_m3_s2']<=100:raise ValueError('GM orbital fora do domínio.')
        r=vector(row['position_m']);v=vector(row['velocity_m_s'])
        if np.linalg.norm(r)>1e17 or np.linalg.norm(v)>1e7:raise ValueError('Fase orbital SI fora do domínio.')
        ids.append(row['id']);bodies.append({'id':row['id'],'mass':gm/U['nominal_GM_unit_m3_s2'],
            'position':(r/U['length_unit_m']).tolist(),'velocity':(v/U['velocity_unit_m_s']).tolist()})
    return bodies


def _read(definition_value,rows,known_ids):
    bodies=_phase_bodies(rows,known_ids)
    needed=[definition_value[k] for k in ('primary_id','inner_id','outer_id')]
    if any(i not in [b['id'] for b in bodies] for i in needed):
        return {'available':False,'reason':'Corpo selecionado removido ou indisponível; identidade original preservada.'}
    try:
        d=definition_value
        result=instantaneous(bodies,d['primary_id'],d['inner_id'],d['outer_id'],d['j'],d['plane_normal'],d['plane_reference'])
        return {'available':True,'result':result}
    except ValueError as error:return {'available':False,'reason':'Fora do domínio orbital selecionado: '+str(error)}


def sample(configuration,state):
    d=configuration['definition']
    if d is None:raise ValueError('Defina primeiro o instrumento orbital.')
    selected={d[k] for k in ('primary_id','inner_id','outer_id')}
    rows=[{'id':b['id'],'GM_m3_s2':b['mass']*U['nominal_GM_unit_m3_s2'],
        'position_m':[v*U['length_unit_m'] for v in b['position']],
        'velocity_m_s':[v*U['velocity_unit_m_s'] for v in b['velocity']]} for b in state['bodies'] if b['id'] in selected]
    ids=[b['id'] for b in state['bodies']]
    return {**{k:copy.deepcopy(state[k]) for k in ('system_id','edit_token','revision','time','scientific_generation')},
        'frame':state['contract']['frame'],'configuration_revision':configuration['revision'],'definition':copy.deepcopy(d),
        'active_ids':ids,'selected_phase_si':rows,'force_contract':copy.deepcopy(state['contract']),
        'gravity_effects':copy.deepcopy(state.get('gravity_effects',{})),
        **_read(d,rows,ids)}


def append(configuration,state,elapsed):
    reading=sample(configuration,state);result=dict(configuration);prior=configuration['samples'][-1] if configuration['samples'] else None
    breaks=[]
    if prior:
        old=prior['reading']
        if any(old[k]!=reading[k] for k in ('edit_token','revision','configuration_revision')):breaks.append('state_or_definition_changed')
        if elapsed>1.5*configuration['cadence_wall_s']:breaks.append('cadence_gap')
        if reading['time']<=old['time']:breaks.append('physical_time_did_not_increase')
    record={'sequence':configuration['next_sequence'],'reading':reading,'cadence_wall_s':configuration['cadence_wall_s'],'wall_elapsed_s':elapsed,'break_before':breaks}
    result['samples']=configuration['samples']+[record];result['next_sequence']+=1
    if len(result['samples'])>MAX_RECORDS:result['samples']=result['samples'][-MAX_RECORDS:];result['dropped']+=1
    return result


def _summary(reading):
    result={k:copy.deepcopy(reading[k]) for k in ('time','revision','configuration_revision','frame','edit_token','available')}
    if reading['available']:
        r=reading['result'];result.update(period_ratio=r['outer_to_inner_period_ratio'],relative_offset=r['relative_offset_from_nominal'],critical_angles=copy.deepcopy(r['critical_angles']))
    else:result['reason']=reading['reason']
    return result


def public(configuration):
    rows=configuration['samples']
    return {k:copy.deepcopy(configuration[k]) for k in ('schema','revision','definition','recording','cadence_wall_s','dropped','next_sequence')}|{
        'sample_count':len(rows),'maximum_samples':MAX_RECORDS,'latest':_summary(rows[-1]['reading']) if rows else None,'policy':POLICY}


def curves(configuration):
    rows=[]
    for record in configuration['samples']:
        reading=record['reading'];d=reading['definition'];summary=_summary(reading)
        rows.append({'sequence':record['sequence'],'time_s':reading['time']*U['time_unit_s'],
            'definition':copy.deepcopy(d),'break_before':copy.deepcopy(record['break_before']),**summary})
    return {**public(configuration),'samples':rows}


def validate(configuration,known_ids,physical_time,system_id,current_revision,frame):
    if not isinstance(configuration,dict) or set(configuration)!=set(empty()) or type(configuration.get('schema')) is not int or configuration['schema']!=1:raise ValueError('Formato dos instrumentos orbitais incompatível.')
    if type(configuration['cadence_wall_s']) not in (int,float) or not math.isfinite(configuration['cadence_wall_s']):raise ValueError('Cadência orbital atual inválida.')
    revision=configuration['revision'];events=configuration['events']
    if type(revision) is not int or not 0<=revision<=4096 or not isinstance(events,list) or len(events)!=revision:raise ValueError('Histórico de configurações orbitais inválido.')
    active=None;recording=False;cadence=1.;definitions={0:None};cadences={0:1.};recordings={0:False};last_clear=0
    for number,event in enumerate(events,1):
        if not isinstance(event,dict) or type(event.get('revision')) is not int or event['revision']!=number:raise ValueError('Sequência orbital inválida.')
        operation=event.get('operation')
        if operation=='definition':
            if set(event)!={'revision','operation','definition'}:raise ValueError('Evento de definição orbital inválido.')
            active=None if event['definition'] is None else definition(event['definition'],known_ids)
            if active!=event['definition']:raise ValueError('Plano orbital histórico não normalizado.')
            if active is None:recording=False
        elif operation=='capture':
            if set(event)!={'revision','operation','recording','cadence_wall_s'}:raise ValueError('Evento de gravação orbital inválido.')
            recording=event['recording'];cadence=event['cadence_wall_s']
            if type(recording) is not bool or type(cadence) not in (int,float) or not math.isfinite(cadence) or not .25<=cadence<=5 or recording and active is None:raise ValueError('Cadência/gravação orbital histórica inválida.')
        elif operation=='clear':
            if set(event)!={'revision','operation'}:raise ValueError('Limpeza orbital inválida.')
            last_clear=number
        else:raise ValueError('Evento orbital desconhecido.')
        definitions[number]=copy.deepcopy(active);cadences[number]=cadence;recordings[number]=recording
    if configuration['definition']!=active or configuration['recording'] is not recording or configuration['cadence_wall_s']!=cadence:raise ValueError('Estado orbital não corresponde ao histórico de configuração.')
    rows=configuration['samples'];dropped=configuration['dropped'];following=configuration['next_sequence']
    if not isinstance(rows,list) or len(rows)>MAX_RECORDS or type(dropped) is not int or dropped<0 or type(following) is not int or following!=dropped+len(rows):raise ValueError('Janela orbital inválida.')
    previous_time=-1.;previous_reading=None
    for number,record in enumerate(rows,dropped):
        if not isinstance(record,dict) or set(record)!={'sequence','reading','cadence_wall_s','wall_elapsed_s','break_before'} or type(record['sequence']) is not int or record['sequence']!=number:raise ValueError('Registro orbital inválido.')
        reading=record['reading']
        required={'system_id','edit_token','revision','time','scientific_generation','frame','configuration_revision','definition','active_ids','selected_phase_si','force_contract','gravity_effects','available'}
        if not isinstance(reading,dict) or type(reading.get('available')) is not bool or set(reading)!=required|({'result'} if reading.get('available') else {'reason'}):raise ValueError('Formato da leitura orbital inválido.')
        cfgrev=reading['configuration_revision'];time=reading['time'];physrev=reading['revision']
        if type(cfgrev) is not int or not last_clear<=cfgrev<=revision or definitions.get(cfgrev) is None or not recordings[cfgrev] or reading['definition']!=definitions[cfgrev]:raise ValueError('Leitura orbital não corresponde à definição histórica.')
        if reading['system_id']!=system_id or reading['frame']!=frame or not isinstance(reading['edit_token'],str) or not re.fullmatch('[0-9a-f]{32}',reading['edit_token']):raise ValueError('Origem da leitura orbital incompatível.')
        if type(time) not in (int,float) or not math.isfinite(time) or not previous_time<=time<=physical_time or type(physrev) is not int or not 0<=physrev<=current_revision:raise ValueError('Tempo/revisão orbital fora do checkpoint.')
        previous_time=time
        ids=reading['active_ids']
        if not isinstance(ids,list) or not 1<=len(ids)<=MAX_BODIES or any(not isinstance(i,str) or i not in known_ids for i in ids) or len(set(ids))!=len(ids):raise ValueError('População orbital histórica inválida.')
        bodies=_phase_bodies(reading['selected_phase_si'],ids)
        expected_selected=[i for i in ids if i in {reading['definition'][k] for k in ('primary_id','inner_id','outer_id')}]
        if [b['id'] for b in bodies]!=expected_selected:raise ValueError('Snapshot orbital incompleto ou fora da ordem confirmada.')
        gravity_harmonics.validate(reading['gravity_effects'],ids)
        if not isinstance(reading['force_contract'],dict) or reading['force_contract'].get('frame')!=frame or len(json.dumps(reading['force_contract'],allow_nan=False))>20000:raise ValueError('Contrato de força orbital inválido.')
        if not isinstance(reading['scientific_generation'],dict) or reading['scientific_generation'].get('model_version') not in ('3.11.0','3.12.0','3.13.0'):raise ValueError('Geração dos instrumentos orbitais incompatível.')
        for key in ('cadence_wall_s','wall_elapsed_s'):
            if type(record[key]) not in (int,float) or not math.isfinite(record[key]):raise ValueError('Cadência orbital não finita.')
        if record['cadence_wall_s']!=cadences[cfgrev] or record['wall_elapsed_s']<0:raise ValueError('Cadência orbital não corresponde à configuração.')
        breaks=record['break_before']
        if not isinstance(breaks,list) or len(set(breaks))!=len(breaks) or any(k not in ('state_or_definition_changed','cadence_gap','physical_time_did_not_increase') for k in breaks):raise ValueError('Lacunas orbitais inválidas.')
        if previous_reading is not None:
            expected_breaks=[]
            if reading['revision']<previous_reading['revision'] or cfgrev<previous_reading['configuration_revision']:raise ValueError('Revisões orbitais históricas retrocedem.')
            if any(previous_reading[k]!=reading[k] for k in ('edit_token','revision','configuration_revision')):expected_breaks.append('state_or_definition_changed')
            if record['wall_elapsed_s']>1.5*record['cadence_wall_s']:expected_breaks.append('cadence_gap')
            if time<=previous_reading['time']:expected_breaks.append('physical_time_did_not_increase')
            if breaks!=expected_breaks:raise ValueError('Lacunas orbitais não correspondem à sequência original.')
        expected=_read(reading['definition'],reading['selected_phase_si'],ids)
        for key,value in expected.items():
            if reading.get(key)!=value:raise ValueError('Ângulos orbitais não correspondem ao snapshot SI original.')
        previous_reading=reading
    return copy.deepcopy(configuration)


def restore(manifest,known_ids,time,system_id,revision,frame):
    if 'orbital_instruments' in manifest:return validate(manifest['orbital_instruments'],known_ids,time,system_id,revision,frame)
    if manifest.get('saved_generation',{}).get('model_version') in ('3.11.0','3.12.0','3.13.0'):raise ValueError('Instrumentos orbitais ausentes no checkpoint3.11.')
    return empty()


def synthetic(preset):
    ratios={'resonant2':2.,'circulating18':1.8}
    if preset not in ratios:raise ValueError('Escolha cenário2:1 ou controle1,8:1.')
    ratio=ratios[preset];inner_mass=1e-5;outer_mass=.001
    a=((1+inner_mass)/(1+outer_mass)/ratio**2)**(1/3)
    bodies=[{'name':'Primário sintético','mass':1.,'position':[0.,0.,0.],'velocity':[0.,0.,0.]},
        {'name':'Orbitador interno','mass':inner_mass,'position':[a*.9,0.,0.],'velocity':[0.,math.sqrt((1+inner_mass)/a*1.1/.9),0.]},
        {'name':'Orbitador externo','mass':outer_mass,'position':[.99,0.,0.],'velocity':[0.,math.sqrt((1+outer_mass)*1.01/.99),0.]}]
    masses=np.array([b['mass'] for b in bodies]);center=sum((m*np.array(b['position']) for m,b in zip(masses,bodies)),start=np.zeros(3))/sum(masses)
    velocity=sum((m*np.array(b['velocity']) for m,b in zip(masses,bodies)),start=np.zeros(3))/sum(masses)
    for b in bodies:b['position']=(np.array(b['position'])-center).tolist();b['velocity']=(np.array(b['velocity'])-velocity).tolist()
    return bodies
