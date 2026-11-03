"""Isolated instantaneous electrostatic many-body model with pair reactions.

Velocity Verlet in SI, <=128 finite classical charges, no external fields,
magnetic self-fields, radiation, gravity, collisions or quantum atomic orbits.
"""
from dataclasses import dataclass
import math
import numpy as np
from em_fields import K_E,MAX_SOURCES,SPEED_LIMIT_M_S,scalar,vector,Model,Source
from em_particles import DomainExit

@dataclass(frozen=True)
class Phase:
    position_m: tuple
    velocity_m_s: tuple
    time_s: float=0.

    def __post_init__(self):
        if not 1<=len(self.position_m)<=MAX_SOURCES or len(self.velocity_m_s)!=len(self.position_m):raise ValueError('Population1..128 with one velocity per charge required')
        object.__setattr__(self,'position_m',tuple(vector(v) for v in self.position_m))
        velocities=tuple(vector(v) for v in self.velocity_m_s)
        if any(math.hypot(*v)>SPEED_LIMIT_M_S for v in velocities):raise DomainExit('Velocity exceeds0.01c')
        object.__setattr__(self,'velocity_m_s',velocities)
        value=scalar(self.time_s)
        if value<0:raise ValueError('Nonnegative model time required')
        object.__setattr__(self,'time_s',value)

@dataclass(frozen=True)
class System:
    ids: tuple
    charge_C: tuple
    mass_kg: tuple
    exclusion_radius_m: tuple

    def __post_init__(self):
        ids=tuple(self.ids)
        if not 1<=len(ids)<=MAX_SOURCES or len(set(ids))!=len(ids) or any(not isinstance(i,str) or not 1<=len(i)<=128 for i in ids):raise ValueError('Unique bounded charge identities required')
        object.__setattr__(self,'ids',ids)
        for field in ('charge_C','mass_kg','exclusion_radius_m'):
            values=tuple(scalar(v) for v in getattr(self,field))
            if len(values)!=len(ids) or field!='charge_C' and any(v<=0 for v in values):raise ValueError('One charge, positive mass and radius per body required')
            object.__setattr__(self,field,values)

    def _pairs(self,position):
        position=np.array(position,dtype=float)
        if position.shape!=(len(self.ids),3) or not np.isfinite(position).all():raise ValueError('Position population mismatch')
        i,j=np.triu_indices(len(self.ids),1);delta=position[i]-position[j]
        radius=np.linalg.norm(delta,axis=1)
        exclusion=np.array(self.exclusion_radius_m)
        if not np.isfinite(radius).all() or np.any(radius<=exclusion[i]+exclusion[j]):raise DomainExit('Pair enters declared exclusion')
        return position,i,j,delta,radius

    def force_potential(self,position):
        position,i,j,delta,radius=self._pairs(position)
        charges=np.array(self.charge_C);coupling=K_E*charges[i]*charges[j]
        force_pair=((coupling/radius)/radius)[:,None]*(delta/radius[:,None])
        force=np.zeros_like(position);np.add.at(force,i,force_pair);np.add.at(force,j,-force_pair)
        potential=math.fsum((coupling/radius).tolist())
        if not np.isfinite(force).all() or not math.isfinite(potential):raise DomainExit('Unrepresentable pair force or energy')
        return force,potential

    def diagnostics(self,phase):
        if not isinstance(phase,Phase):raise ValueError('Synchronized phase required')
        x=np.array(phase.position_m);v=np.array(phase.velocity_m_s);m=np.array(self.mass_kg)
        if len(x)!=len(self.ids):raise ValueError('Phase population mismatch')
        _,potential=self.force_potential(x);momenta=m[:,None]*v
        kinetic=.5*math.fsum((m*np.sum(v*v,axis=1)).tolist())
        momentum=np.sum(momenta,axis=0);angular=np.sum(np.cross(x,momenta),axis=0)
        values=[kinetic,potential,*momentum,*angular]
        if not np.isfinite(values).all():raise DomainExit('Unrepresentable diagnostic')
        return {'kinetic_J':kinetic,'potential_J':potential,'energy_J':kinetic+potential,
            'energy_scale_J':kinetic+abs(potential),'momentum_kg_m_s':momentum.tolist(),
            'angular_momentum_kg_m2_s':angular.tolist()}

    def field_snapshot(self,phase,exclude_id=None):
        self._pairs(phase.position_m)
        if exclude_id is not None and exclude_id not in self.ids:raise ValueError('Unknown excluded identity')
        return Model(tuple(Source(id,x,r,q) for id,x,r,q in zip(self.ids,phase.position_m,self.exclusion_radius_m,self.charge_C) if id!=exclude_id))

    def step(self,phase,dt_s,*,acting=True):
        if not isinstance(phase,Phase) or len(phase.position_m)!=len(self.ids):raise ValueError('Matching synchronized phase required')
        if type(acting) is not bool:raise ValueError('Explicit physical control required')
        dt=scalar(dt_s)
        if dt<=0:raise ValueError('Positive timestep required')
        end=phase.time_s+dt
        if not math.isfinite(end) or end<=phase.time_s:raise DomainExit('Unrepresentable time advance')
        x=np.array(phase.position_m);v=np.array(phase.velocity_m_s);mass=np.array(self.mass_kg)[:,None]
        force,_=self.force_potential(x);half=v+.5*dt*force/mass if acting else v
        proposed=x+dt*half
        _,i,j,relative,_=self._pairs(x)
        relative_drift=(proposed[i]-proposed[j])-relative
        length=np.sum(relative_drift**2,axis=1)
        dot=-np.sum(relative*relative_drift,axis=1)
        fraction=np.clip(np.divide(dot,length,out=np.zeros_like(dot),where=length!=0),0,1)
        closest=np.linalg.norm(relative+fraction[:,None]*relative_drift,axis=1)
        radii=np.array(self.exclusion_radius_m)
        if np.any(closest<=radii[i]+radii[j]):raise DomainExit('Pair drift crosses excluded domain')
        updated_force,_=self.force_potential(proposed)
        updated=half+.5*dt*updated_force/mass if acting else half
        if not np.isfinite([half,proposed,updated]).all():raise DomainExit('Unrepresentable electrostatic trial')
        if np.any(np.linalg.norm(half,axis=1)>SPEED_LIMIT_M_S):raise DomainExit('Half-step exceeds0.01c')
        return Phase(tuple(map(tuple,proposed)),tuple(map(tuple,updated)),end)
