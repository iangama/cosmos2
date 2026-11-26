"""Bounded static body-particle experiment and sealed, isolated JSON checkpoint."""
from pathlib import Path
from dataclasses import asdict
import copy
import hashlib
import json
import math
import os
import platform
import time
import uuid
import numpy as np
import scipy
from is4_body_snapshot import Snapshot,digest
from is4_particles import Phase,DomainExit,boris_step
from is4_values import scalar,vector

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
HERE=Path(__file__).resolve().parent
CORE=['is4_values.py','is4_domains.py','is4_particles.py','is4_body_snapshot.py','is4_experiment.py','is4_wind_field.py','is4_wind_snapshot.py','is4_wind_diagnostics.py','is4_wind_reading.py']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
IMPORTED_SHA={name:sha(HERE/name) for name in CORE}
MAX_QUANTUM=256
MAX_STEPS=1_000_000
MAX_TRAIL=513
MAX_EVENTS=128


def generation():
    if any(sha(HERE/name)!=value for name,value in IMPORTED_SHA.items()):raise ValueError('Restart after scientific source changes')
    return {'schema':1,'id':'cosmos2:is4-static-prescribed-particle','version':'0.2.0','code_sha256':dict(IMPORTED_SHA),
        'runtime':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__}}


def integer(value,low,high):
    if type(value) is not int or not low<=value<=high:raise ValueError('Integer outside declared budget')
    return value


def controls(value):
    if not isinstance(value,dict) or set(value)!={'electric','magnetic','gravity'} or any(type(v) is not bool for v in value.values()):
        raise ValueError('Explicit independent physical controls required')
    return dict(value)


def parameters(value):
    keys={'charge_C','mass_kg','dt_s','initial_position_m','initial_velocity_m_s'}
    if not isinstance(value,dict) or set(value)!=keys:raise ValueError('Explicit SI particle parameters required')
    result={key:scalar(value[key]) for key in ['charge_C','mass_kg','dt_s']}
    if result['mass_kg']<=0 or result['dt_s']<=0:raise ValueError('Positive mass and timestep required')
    for key in ['initial_position_m','initial_velocity_m_s']:result[key]=list(vector(value[key]))
    Phase(tuple(result['initial_position_m']),tuple(result['initial_velocity_m_s']))
    return result


def phase_record(value):
    keys={'position_m','velocity_m_s','time_s','position_origin_m','position_offset_m'}
    if not isinstance(value,dict) or set(value)!=keys:raise ValueError('Complete synchronized phase required')
    if value['position_origin_m'] is None or value['position_offset_m'] is None:raise ValueError('Saved origin and displacement are mandatory')
    return Phase(**value)


def add_sum(pair,value):
    total,correction=pair;trial=total+value
    correction+=((total-trial)+value) if abs(total)>=abs(value) else ((value-trial)+total)
    if not math.isfinite(trial) or not math.isfinite(correction):raise DomainExit('Unrepresentable accumulated work')
    return (trial,correction)


class Experiment:
    def __init__(self,storage,scene_phase,reading,particle_parameters,physical_controls):
        self.storage=Path(storage).resolve()
        if not self.storage.is_relative_to((ROOT/'output').resolve()):raise ValueError('IS4 staging storage must remain under output')
        self.parameters=parameters(particle_parameters);self.controls=controls(physical_controls)
        self.is_wind=isinstance(reading,dict) and reading.get('kind')=='scene_Sun_Parker_prescribed_point'
        if self.is_wind:
            from is4_wind_reading import validate
            self.model=validate(scene_phase,reading)
        else:self.model=Snapshot(scene_phase,reading)
        self.source_phase=copy.deepcopy(scene_phase);self.source_reading=copy.deepcopy(reading)
        self.phase=Phase(tuple(self.parameters['initial_position_m']),tuple(self.parameters['initial_velocity_m_s']))
        if not self.model.segment_in_domain(self.phase.position_m,self.phase.position_m):raise ValueError('Initial phase outside adopted domain')
        self.execution_preferences={'particle_s_per_wall_s':min(1e6,max(1e-15,self.parameters['dt_s']*200))}
        self.scientific_generation=generation();self.id=uuid.uuid4().hex;self.edit_token=uuid.uuid4().hex
        self.revision=0;self.step_index=0;self.events=[];self.trail=[asdict(self.phase)];self.termination=None
        self.reference=self.phase;self.work={'electric':(0.,0.),'gravity':(0.,0.)}
        self._validate_energy();self.storage.mkdir(parents=True,exist_ok=True)

    def _validate_energy(self):
        mass=self.parameters['mass_kg'];velocity=self.phase.velocity_m_s
        kinetic=.5*mass*math.fsum(v*v for v in velocity)
        if not math.isfinite(kinetic) or kinetic==0. and any(v!=0. for v in velocity):raise ValueError('Unrepresentable particle energy')

    def advance_steps(self,count):
        integer(count,1,MAX_QUANTUM)
        if self.step_index+count>MAX_STEPS:raise ValueError('Total particle-step budget exceeded')
        if self.termination is not None:return {'accepted_steps':0,'termination':copy.deepcopy(self.termination)}
        accepted=0
        for _ in range(count):
            try:
                trial,diagnostic=boris_step(self.model,self.phase,self.parameters['charge_C'],self.parameters['mass_kg'],self.parameters['dt_s'],
                    electric_acting=self.controls['electric'],magnetic_acting=self.controls['magnetic'],gravity_acting=self.controls['gravity'])
                kinetic=.5*self.parameters['mass_kg']*math.fsum(v*v for v in trial.velocity_m_s)
                if not math.isfinite(kinetic) or kinetic==0. and any(v!=0. for v in trial.velocity_m_s):raise DomainExit('Unrepresentable particle energy')
                work={key:add_sum(self.work[key],diagnostic[key+'_work_J']) for key in self.work}
            except DomainExit as error:
                self.termination={'kind':'integration_guard','message':str(error),'time_s':self.phase.time_s,'step_index':self.step_index}
                break
            self.phase=trial;self.work=work;self.step_index+=1;accepted+=1
            self.trail.append(asdict(trial))
            if len(self.trail)>MAX_TRAIL:del self.trail[0]
        return {'accepted_steps':accepted,'termination':copy.deepcopy(self.termination)}

    def set_controls(self,value):
        replacement=controls(value)
        if replacement==self.controls:return False
        if len(self.events)>=MAX_EVENTS:raise ValueError('Intervention history budget exceeded')
        event={'kind':'physical_controls','revision':self.revision+1,'time_s':self.phase.time_s,'step_index':self.step_index,
            'before':self.controls,'after':replacement}
        self.events.append(copy.deepcopy(event));self.controls=replacement;self.revision+=1
        self.reference=self.phase;self.work={'electric':(0.,0.),'gravity':(0.,0.)};self.termination=None
        return True

    def sample(self):
        field=self.model.evaluate(self.phase.position_m);mass=self.parameters['mass_kg']
        delta_K=.5*mass*math.fsum((self.phase.velocity_m_s[k]-self.reference.velocity_m_s[k])*
            (self.phase.velocity_m_s[k]+self.reference.velocity_m_s[k]) for k in range(3))
        gravity_delta=mass*self.model.potential_difference(self.reference.position_m,self.phase.position_m) if self.controls['gravity'] else 0.
        electric_delta=0.
        if self.is_wind:
            from is4_wind_diagnostics import potential_differences
            potential=potential_differences(self.model,self.phase.position_origin_m,self.reference.position_offset_m,self.phase.position_offset_m)
            gravity_delta=mass*potential['gravity_potential_change_J_kg'] if self.controls['gravity'] else 0.
            electric_delta=self.parameters['charge_C']*potential['electric_potential_change_V'] if self.controls['electric'] else 0.
        return {'electric_potential_change_J':electric_delta,'total_static_energy_change_J':delta_K+gravity_delta+electric_delta,
            'phase':asdict(self.phase),'field':field,'controls':dict(self.controls),'kinetic_change_J':delta_K,
            'gravity_potential_change_J':gravity_delta,'mechanical_energy_change_J':delta_K+gravity_delta,
            'electric_work_J':math.fsum(self.work['electric']),'gravity_work_J':math.fsum(self.work['gravity']),
            'reference_time_s':self.reference.time_s,'clock':'independent_particle_seconds','snapshot_epoch':copy.deepcopy(self.source_reading['epoch'])}

    def payload(self):
        if generation()!=self.scientific_generation:raise ValueError('Scientific generation changed')
        return {'schema':2,'kind':'is4_static_prescribed_particle','scientific_generation':copy.deepcopy(self.scientific_generation),
            'id':self.id,'edit_token':self.edit_token,'revision':self.revision,'step_index':self.step_index,
            'source_phase':copy.deepcopy(self.source_phase),'source_reading':copy.deepcopy(self.source_reading),
            'configuration_sha256':self.model.configuration_sha256,'parameters':copy.deepcopy(self.parameters),'controls':dict(self.controls),'execution_preferences':dict(self.execution_preferences),
            'phase':asdict(self.phase),'reference':asdict(self.reference),'work':{k:list(v) for k,v in self.work.items()},
            'events':copy.deepcopy(self.events),'trail':copy.deepcopy(self.trail),'termination':copy.deepcopy(self.termination)}

    def save(self):
        payload=self.payload();record={**payload,'manifest_sha256':digest(payload)}
        text=json.dumps(record,sort_keys=True,ensure_ascii=True,allow_nan=False,indent=2)+'\n'
        temporary=self.storage/('latest.'+uuid.uuid4().hex+'.tmp');destination=self.storage/'latest.json'
        try:
            with temporary.open('x',encoding='utf-8',newline='\n') as stream:
                stream.write(text);stream.flush();os.fsync(stream.fileno())
            deadline=time.monotonic()+2.
            while True:
                try:os.replace(temporary,destination);break
                except PermissionError:
                    if time.monotonic()>=deadline:raise
                    time.sleep(.01)
        finally:
            if temporary.exists():temporary.unlink()
        return {'path':str(destination),'sha256':sha(destination),'manifest_sha256':record['manifest_sha256']}

    @classmethod
    def load(cls,storage):
        path=Path(storage)/'latest.json';record=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(record,dict):raise ValueError('Checkpoint object required')
        payload={k:v for k,v in record.items() if k!='manifest_sha256'}
        if digest(payload)!=record.get('manifest_sha256'):raise ValueError('Checkpoint seal differs')
        keys={'schema','kind','scientific_generation','id','edit_token','revision','step_index','source_phase','source_reading',
            'configuration_sha256','parameters','controls','execution_preferences','phase','reference','work','events','trail','termination'}
        if set(payload)!=keys or type(payload['schema']) is not int or payload['schema']!=2 or payload['kind']!='is4_static_prescribed_particle':raise ValueError('Checkpoint schema differs')
        if payload['scientific_generation']!=generation():raise ValueError('Checkpoint scientific generation differs; migration required')
        for key in ['id','edit_token']:
            v=payload[key]
            if not isinstance(v,str) or len(v)!=32 or any(c not in '0123456789abcdef' for c in v):raise ValueError('Invalid experiment identity')
        candidate=cls(storage,payload['source_phase'],payload['source_reading'],payload['parameters'],payload['controls'])
        if candidate.model.configuration_sha256!=payload['configuration_sha256']:raise ValueError('Frozen snapshot differs')
        phase,reference=phase_record(payload['phase']),phase_record(payload['reference'])
        initial=tuple(candidate.parameters['initial_position_m']);steps=integer(payload['step_index'],0,MAX_STEPS)
        for state in [phase,reference]:
            if state.position_origin_m!=initial or not candidate.model.segment_in_domain(state.position_m,state.position_m):raise ValueError('Particle origin/domain differs')
        if reference.time_s>phase.time_s:raise ValueError('Energy reference is in the future')
        expected=steps*candidate.parameters['dt_s']
        if not math.isfinite(expected):raise ValueError('Unrepresentable checkpoint clock')
        tolerance=max(8*math.ulp(expected)*max(1,steps),8*math.ulp(candidate.parameters['dt_s']))
        if abs(phase.time_s-expected)>tolerance:raise ValueError('Particle step counter and time differ')
        revision=integer(payload['revision'],0,MAX_EVENTS);events=payload['events']
        if not isinstance(events,list) or len(events)!=revision:raise ValueError('Intervention count differs')
        previous_time=0.;previous_step=0;previous_controls=None
        for index,event in enumerate(events,1):
            if not isinstance(event,dict) or set(event)!={'kind','revision','time_s','step_index','before','after'} or event['kind']!='physical_controls' or type(event['revision']) is not int or event['revision']!=index:raise ValueError('Invalid intervention')
            before,after=controls(event['before']),controls(event['after']);event_time=scalar(event['time_s']);event_step=integer(event['step_index'],previous_step,steps)
            if abs(event_time-event_step*candidate.parameters['dt_s'])>tolerance:raise ValueError('Intervention step/time differ')
            if not previous_time<=event_time<=phase.time_s or before==after or previous_controls is not None and before!=previous_controls:raise ValueError('Intervention order differs')
            previous_time,previous_step,previous_controls=event_time,event_step,after
        if events and (events[-1]['after']!=candidate.controls or events[-1]['time_s']!=reference.time_s):raise ValueError('Control/reference event differs')
        if not events and asdict(reference)!=asdict(candidate.phase):raise ValueError('Initial energy reference differs')
        work=payload['work']
        if not isinstance(work,dict) or set(work)!={'electric','gravity'}:raise ValueError('Explicit compensated work required')
        parsed_work={}
        for key,value in work.items():
            if not isinstance(value,list) or len(value)!=2:raise ValueError('Compensated sum pair required')
            parsed_work[key]=tuple(scalar(v) for v in value)
        if (not candidate.is_wind or not candidate.controls['electric'] or candidate.parameters['charge_C']==0.) and parsed_work['electric']!=(0.,0.):raise ValueError('Inactive or prescribed-zero electric force cannot accumulate work')
        if not candidate.controls['gravity'] and parsed_work['gravity']!=(0.,0.):raise ValueError('Inactive gravity cannot accumulate work')
        trail=payload['trail']
        if not isinstance(trail,list) or len(trail)!=min(MAX_TRAIL,steps+1):raise ValueError('Recent trajectory length differs')
        parsed_trail=[phase_record(row) for row in trail]
        if asdict(parsed_trail[-1])!=asdict(phase):raise ValueError('Recent trajectory endpoint differs')
        for index,state in enumerate(parsed_trail):
            if state.position_origin_m!=initial or not candidate.model.segment_in_domain(state.position_m,state.position_m):raise ValueError('Saved trajectory origin/domain differs')
            expected=(steps-len(trail)+1+index)*candidate.parameters['dt_s']
            if abs(state.time_s-expected)>tolerance:raise ValueError('Saved trajectory time differs')
        termination=payload['termination']
        if termination is not None:
            if isinstance(termination,dict):
                integer(termination.get('step_index'),steps,steps);scalar(termination.get('time_s'))
            if not isinstance(termination,dict) or set(termination)!={'kind','message','time_s','step_index'} or termination['kind']!='integration_guard' or not isinstance(termination['message'],str) or termination['time_s']!=phase.time_s or termination['step_index']!=steps:raise ValueError('Stopped phase differs')
        preferences=payload['execution_preferences']
        if not isinstance(preferences,dict) or set(preferences)!={'particle_s_per_wall_s'}:raise ValueError('Explicit particle playback preference required')
        rate=scalar(preferences['particle_s_per_wall_s'])
        if not 1e-15<=rate<=1e6:raise ValueError('Particle playback preference outside declared range')
        candidate.execution_preferences={'particle_s_per_wall_s':rate}
        candidate.phase=phase;candidate.reference=reference;candidate.id=payload['id'];candidate.edit_token=uuid.uuid4().hex
        candidate.step_index=steps;candidate.revision=revision;candidate.events=copy.deepcopy(events);candidate.work=parsed_work
        candidate.trail=[asdict(s) for s in parsed_trail];candidate.termination=copy.deepcopy(termination)
        candidate._validate_energy()
        mass=candidate.parameters['mass_kg']
        delta_K=.5*mass*math.fsum((phase.velocity_m_s[k]-reference.velocity_m_s[k])*(phase.velocity_m_s[k]+reference.velocity_m_s[k]) for k in range(3))
        total_work=math.fsum([*parsed_work['electric'],*parsed_work['gravity']])
        scale=.5*mass*math.fsum(v*v for state in [phase,reference] for v in state.velocity_m_s)+abs(total_work)
        if abs(delta_K-total_work)>1e-9*scale+8*math.ulp(scale):raise ValueError('Checkpoint work and kinetic change differ')
        return candidate
