"""Static SI reference fields, exclusion domains and independently applied Lorentz terms.

Isolated C2-12 prototype: fixed point charges, ideal dipoles, uniform backgrounds.
No evolving sources, retarded fields, radiation or reaction on the sources.
"""
from dataclasses import dataclass
from pathlib import Path
import json
import math
import numpy as np

CONSTANTS=json.loads(Path(__file__).with_name('constants.json').read_text())
EPSILON_0=CONSTANTS['vacuum_electric_permittivity_F_m']['value']
MU_0=CONSTANTS['vacuum_magnetic_permeability_N_A2']['value']
C=CONSTANTS['speed_of_light_m_s']['value']
K_E=1/(4*math.pi*EPSILON_0)
MAX_SOURCES=128
SPEED_LIMIT_M_S=.01*C

def vector(value):
    if not isinstance(value,(tuple,list,np.ndarray)) or len(value)!=3:
        raise ValueError('Three finite SI vector components required')
    if any(isinstance(v,(bool,np.bool_)) or not isinstance(v,(int,float,np.integer,np.floating)) or not math.isfinite(v) for v in value):
        raise ValueError('Three finite SI vector components required')
    return tuple(float(v) for v in value)

def scalar(value):
    if isinstance(value,(bool,np.bool_)) or not isinstance(value,(int,float,np.integer,np.floating)) or not math.isfinite(value):
        raise ValueError('Finite SI scalar required')
    return float(value)

@dataclass(frozen=True)
class Source:
    id: str
    position_m: tuple
    exclusion_radius_m: float
    charge_C: float=0.
    magnetic_moment_A_m2: tuple=(0.,0.,0.)

    def __post_init__(self):
        if not isinstance(self.id,str) or not 1<=len(self.id)<=128:raise ValueError('Stable source ID required')
        object.__setattr__(self,'position_m',vector(self.position_m))
        object.__setattr__(self,'magnetic_moment_A_m2',vector(self.magnetic_moment_A_m2))
        object.__setattr__(self,'charge_C',scalar(self.charge_C))
        radius=scalar(self.exclusion_radius_m)
        if radius<=0:raise ValueError('Positive declared exclusion radius required')
        object.__setattr__(self,'exclusion_radius_m',radius)

@dataclass(frozen=True)
class Model:
    sources: tuple=()
    uniform_E_V_m: tuple=(0.,0.,0.)
    uniform_B_T: tuple=(0.,0.,0.)

    def __post_init__(self):
        sources=tuple(self.sources)
        if len(sources)>MAX_SOURCES or any(not isinstance(s,Source) for s in sources):raise ValueError('At most128 validated static sources')
        if len({s.id for s in sources})!=len(sources):raise ValueError('Duplicate source identity')
        object.__setattr__(self,'sources',sources)
        object.__setattr__(self,'uniform_E_V_m',vector(self.uniform_E_V_m))
        object.__setattr__(self,'uniform_B_T',vector(self.uniform_B_T))

    def evaluate(self,position_m):
        point=np.array(vector(position_m));geometry=[];excluded=[]
        for source in self.sources:
            delta=point-np.array(source.position_m);distance=math.hypot(*delta)
            if not math.isfinite(distance):raise ValueError('Unrepresentable source distance')
            geometry.append((source,delta,distance))
            if distance<=source.exclusion_radius_m:excluded.append(source.id)
        if excluded:
            return {'valid':False,'position_m':point.tolist(),'reason':'inside_or_on_source_exclusion','source_ids':excluded}
        electric=[np.array(self.uniform_E_V_m)];magnetic=[np.array(self.uniform_B_T)]
        potential=[-float(np.dot(electric[0],point))]
        for source,delta,radius in geometry:
            direction=delta/radius
            electric.append((K_E*source.charge_C/radius)/radius*direction)
            potential.append(K_E*source.charge_C/radius)
            moment=np.array(source.magnetic_moment_A_m2)
            magnetic.append(((MU_0/(4*math.pi)/radius)/radius)/radius*(3*direction*np.dot(moment,direction)-moment))
        E=[math.fsum(v[k] for v in electric) for k in range(3)]
        B=[math.fsum(v[k] for v in magnetic) for k in range(3)]
        phi=math.fsum(potential)
        scales=[math.fsum(math.hypot(*v) for v in values) for values in (electric,magnetic)]
        if not all(math.isfinite(v) for v in [*E,*B,phi,*scales]):raise ValueError('Fields outside representable SI domain')
        return {'valid':True,'position_m':point.tolist(),'electric_field_V_m':E,'magnetic_field_T':B,
            'electric_potential_V':phi,'electric_scale_V_m':scales[0],'magnetic_scale_T':scales[1],
            'potential_zero':'uniform term at coordinate origin; charge terms at infinity',
            'source_ids':[s.id for s in self.sources]}

def lorentz(model,position_m,velocity_m_s,charge_C,mass_kg,*,electric_acting=True,magnetic_acting=True):
    if type(electric_acting) is not bool or type(magnetic_acting) is not bool:raise ValueError('Explicit physical controls required')
    velocity=np.array(vector(velocity_m_s));charge=scalar(charge_C);mass=scalar(mass_kg)
    if mass<=0 or math.hypot(*velocity)>SPEED_LIMIT_M_S:raise ValueError('Positive mass and nonrelativistic velocity <=0.01c required')
    reference=model.evaluate(position_m)
    if not reference['valid']:return {'valid':False,'reference':reference}
    E=np.array(reference['electric_field_V_m']);B=np.array(reference['magnetic_field_T'])
    electric=charge*E if electric_acting else np.zeros(3)
    magnetic=charge*np.cross(velocity,B) if magnetic_acting else np.zeros(3)
    force=electric+magnetic;acceleration=force/mass
    if not np.isfinite([electric,magnetic,force,acceleration]).all():raise ValueError('Force outside representable SI domain')
    powers=[float(np.dot(f,velocity)) for f in (electric,magnetic)]
    if not all(math.isfinite(p) for p in powers):raise ValueError('Power outside representable SI domain')
    return {'valid':True,'reference':reference,'electric_force_N':electric.tolist(),'magnetic_force_N':magnetic.tolist(),
        'force_N':force.tolist(),'acceleration_m_s2':acceleration.tolist(),
        'electric_power_W':powers[0],'magnetic_power_W':powers[1],
        'electric_acting':electric_acting,'magnetic_acting':magnetic_acting}
