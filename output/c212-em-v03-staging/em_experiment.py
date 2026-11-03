"""Exact synchronized EM continuation and bounded, sealed prototype checkpoints.

Separate schema from the installed gravitational Session. No historical owner
checkpoint is read, migrated or overwritten by this prototype.
"""
from dataclasses import asdict
from pathlib import Path
import hashlib
import json
import math
import os
import uuid
from em_fields import Model,Source,lorentz,scalar
from em_particles import Phase as TestPhase,boris_step
from em_mutual import System,Phase as MutualPhase

ROOT=Path(__file__).resolve().parent
VERSION='0.3.0'
MAX_CHECKPOINT_BYTES=2*1024*1024

def generation():
    return {'model':'cosmos2:SI-electromagnetic-prototype','version':VERSION,
        'files_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
            ('em_fields.py','em_particles.py','em_mutual.py','em_experiment.py','em_editor.py','em_migrate.py','constants.json')}}

def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(',',':')).encode()

class Experiment:
    def __init__(self,mode,model,phase,dt_s,controls,*,charge_C=None,mass_kg=None):
        self.mode=mode;self.model=model;self.phase=phase;self.dt_s=scalar(dt_s)
        if self.dt_s<=0:raise ValueError('Positive integration step required')
        expected={'electric_acting','magnetic_acting'} if mode=='test_particle' else {'acting'}
        if not isinstance(controls,dict) or set(controls)!=expected or any(type(v) is not bool for v in controls.values()):raise ValueError('Exact physical control set required')
        self.controls=dict(controls)
        if mode=='test_particle':
            if not isinstance(model,Model) or not isinstance(phase,TestPhase):raise ValueError('Prescribed sources and synchronized test phase required')
            self.charge_C=scalar(charge_C);self.mass_kg=scalar(mass_kg)
            if not lorentz(model,phase.position_m,phase.velocity_m_s,self.charge_C,self.mass_kg,**controls)['valid']:raise ValueError('Initial phase outside model domain')
        elif mode=='mutual_electrostatic':
            if not isinstance(model,System) or not isinstance(phase,MutualPhase) or charge_C is not None or mass_kg is not None:raise ValueError('Mutual system and phase required; test-particle parameters forbidden')
            model.diagnostics(phase)
        else:raise ValueError('Unknown EM regime')
        from em_editor import default_editor
        self.editor=default_editor(self)

    def advance(self,steps=1):
        if type(steps) is not int or not 1<=steps<=4096:raise ValueError('Bounded integer step count1..4096 required')
        for _ in range(steps):
            if self.mode=='test_particle':
                trial,_=boris_step(self.model,self.phase,self.charge_C,self.mass_kg,self.dt_s,**self.controls)
            else:trial=self.model.step(self.phase,self.dt_s,**self.controls)
            # Commit one successful physical step. A later domain error preserves
            # the actual last valid phase; it never labels the requested end time.
            self.phase=trial
        return self.phase

    def payload(self):
        state={'mode':self.mode,'phase':asdict(self.phase),'dt_s':self.dt_s,'controls':dict(self.controls)}
        if self.mode=='test_particle':state.update(model=asdict(self.model),particle={'charge_C':self.charge_C,'mass_kg':self.mass_kg})
        else:state['system']=asdict(self.model)
        return state

    def save(self,path):
        from em_editor import validate_editor
        payload=self.payload();body={'schema':3,'generation':generation(),'payload':payload,'editor':validate_editor(self,self.editor)}
        envelope={**body,'sha256':hashlib.sha256(canonical(body)).hexdigest()}
        raw=canonical(envelope)
        if len(raw)>MAX_CHECKPOINT_BYTES:raise ValueError('Oversized EM checkpoint')
        path=Path(path);temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
        try:
            with temporary.open('xb') as stream:
                stream.write(raw);stream.flush();os.fsync(stream.fileno())
            temporary.replace(path)
        finally:temporary.unlink(missing_ok=True)

    @classmethod
    def load(cls,path):
        path=Path(path)
        if path.stat().st_size>MAX_CHECKPOINT_BYTES:raise ValueError('Oversized EM checkpoint')
        record=read_envelope(path)
        if record['schema']!=3 or set(record)!={'schema','generation','payload','editor','sha256'}:raise ValueError('Unknown EM checkpoint schema; explicit migration to EM0.3 required')
        if record['generation']!=generation():raise ValueError('Scientific generation changed; explicit migration required')
        trial=cls.from_payload(record['payload'])
        from em_editor import validate_editor
        trial.editor=validate_editor(trial,record['editor'])
        return trial

    @classmethod
    def from_payload(cls,p):
        if not isinstance(p,dict) or p.get('mode') not in ('test_particle','mutual_electrostatic'):raise ValueError('Unknown EM regime')
        common={'mode','phase','dt_s','controls'}
        if p['mode']=='test_particle':
            if set(p)!=common|{'model','particle'} or set(p['model'])!={'sources','uniform_E_V_m','uniform_B_T'} or set(p['particle'])!={'charge_C','mass_kg'}:raise ValueError('Unexpected prescribed-source checkpoint fields')
            if not isinstance(p['model']['sources'],(list,tuple)) or len(p['model']['sources'])>128:raise ValueError('Unbounded source list')
            sources=tuple(Source(**s) for s in p['model']['sources'])
            model=Model(sources,p['model']['uniform_E_V_m'],p['model']['uniform_B_T']);phase=TestPhase(**p['phase'])
            return cls(p['mode'],model,phase,p['dt_s'],p['controls'],**p['particle'])
        if set(p)!=common|{'system'}:raise ValueError('Unexpected mutual checkpoint fields')
        return cls(p['mode'],System(**p['system']),MutualPhase(**p['phase']),p['dt_s'],p['controls'])


def read_envelope(path):
        path=Path(path)
        if path.stat().st_size>MAX_CHECKPOINT_BYTES:raise ValueError('Oversized EM checkpoint')
        def pairs(items):
            result={}
            for key,value in items:
                if key in result:raise ValueError('Duplicate JSON key')
                result[key]=value
            return result
        def constant(value):raise ValueError('Nonfinite JSON constant '+value)
        record=json.loads(path.read_bytes(),object_pairs_hook=pairs,parse_constant=constant)
        if not isinstance(record,dict) or type(record.get('schema')) is not int or record['schema'] not in (1,2,3):raise ValueError('Unknown EM checkpoint schema')
        expected={'schema','generation','payload','sha256'}|({'editor'} if record['schema']>=2 else set())
        if set(record)!=expected:raise ValueError('Unexpected EM checkpoint envelope fields')
        body={k:v for k,v in record.items() if k!='sha256'}
        if hashlib.sha256(canonical(body)).hexdigest()!=record['sha256']:raise ValueError('EM checkpoint integrity mismatch')
        return record
