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
        object.__setattr__(self,'_position_array',_readonly(np.array(self.position_m,dtype=float)))
        object.__setattr__(self,'_velocity_array',_readonly(np.array(self.velocity_m_s,dtype=float)))


def _readonly(array):
    array.flags.writeable=False
    return array


def _row_dot3(a,b):
    # Same left-to-right three-component sum, without a tiny row reduction.
    return (a[:,0]*b[:,0]+a[:,1]*b[:,1])+a[:,2]*b[:,2]


def _row_norm3(a):
    return np.sqrt(_row_dot3(a,a))


def _internal_phase(position,velocity,time_s):
    """Internal path only after shape/finiteness/speed/time checks in step.

    The public constructor and checkpoint loader retain strict scalar/vector
    validation. No unchecked user array enters this path.
    """
    phase=object.__new__(Phase)
    object.__setattr__(phase,'position_m',tuple(map(tuple,position.tolist())))
    object.__setattr__(phase,'velocity_m_s',tuple(map(tuple,velocity.tolist())))
    object.__setattr__(phase,'time_s',time_s)
    object.__setattr__(phase,'_position_array',_readonly(position))
    object.__setattr__(phase,'_velocity_array',_readonly(velocity))
    return phase


def _check_final_speed(velocity):
    norms=_row_norm3(velocity)
    # The public domain uses math.hypot. A wide fallback band makes the
    # vectorized decision insensitive to rounding at the exact0.01c boundary.
    near=np.abs(norms-SPEED_LIMIT_M_S)<=1e-12*SPEED_LIMIT_M_S
    if np.any(norms[~near]>SPEED_LIMIT_M_S) or any(math.hypot(*v)>SPEED_LIMIT_M_S for v in velocity[near]):
        raise DomainExit('Velocity exceeds0.01c')

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
        i,j=np.triu_indices(len(ids),1)
        charge=np.array(self.charge_C);radius=np.array(self.exclusion_radius_m)
        object.__setattr__(self,'_i',_readonly(i));object.__setattr__(self,'_j',_readonly(j))
        object.__setattr__(self,'_scatter',_readonly(np.concatenate((i,j))))
        object.__setattr__(self,'_coupling',_readonly(K_E*charge[i]*charge[j]))
        object.__setattr__(self,'_pair_exclusion',_readonly(radius[i]+radius[j]))
        object.__setattr__(self,'_mass_column',_readonly(np.array(self.mass_kg)[:,None]))
        object.__setattr__(self,'_force_cache',None)

    def _pairs(self,position):
        position=np.asarray(position,dtype=float)
        if position.shape!=(len(self.ids),3) or not np.isfinite(position).all():raise ValueError('Position population mismatch')
        i,j=self._i,self._j;delta=position[i]-position[j]
        radius=_row_norm3(delta)
        if not np.isfinite(radius).all() or np.any(radius<=self._pair_exclusion):raise DomainExit('Pair enters declared exclusion')
        return position,i,j,delta,radius

    def _force_geometry(self,position):
        position=np.asarray(position,dtype=float)
        cached=self._force_cache
        key=position.tobytes()
        if cached is not None and position.shape==cached[0] and key==cached[1]:
            return cached[2:6]
        position,i,j,delta,radius=self._pairs(position)
        coupling=self._coupling
        energy_terms=coupling/radius
        force_pair=(energy_terms/radius)[:,None]*(delta/radius[:,None])
        # Match the old contribution order: all i additions, then all j
        # reactions. Each coordinate uses the same ordered pair list.
        force=np.column_stack([np.bincount(self._scatter,weights=np.concatenate((force_pair[:,k],-force_pair[:,k])),minlength=len(self.ids)) for k in range(3)]).astype(float,copy=False)
        if not np.isfinite(force).all():raise DomainExit('Unrepresentable pair force or energy')
        # The integrator needs force only. A conservative finite bound certifies
        # representable potential without a Python list/fsum every step. Near
        # overflow, retain the original fsum and its exact refusal behavior.
        with np.errstate(over='ignore',invalid='ignore'):bound=np.sum(np.abs(energy_terms))
        potential=None
        if not math.isfinite(bound) or bound>np.finfo(float).max/2:
            potential=math.fsum(energy_terms.tolist())
            if not math.isfinite(potential):raise DomainExit('Unrepresentable pair energy')
        values=(_readonly(force),potential,_readonly(delta),_readonly(radius))
        object.__setattr__(self,'_force_cache',(position.shape,key,*values,_readonly(energy_terms)))
        return values

    def force_potential(self,position):
        force,potential,_,_=self._force_geometry(position)
        if potential is None:
            potential=math.fsum(self._force_cache[6].tolist())
            if not math.isfinite(potential):raise DomainExit('Unrepresentable pair energy')
            object.__setattr__(self,'_force_cache',self._force_cache[:3]+(potential,)+self._force_cache[4:])
        # No caller can alter the private force cache through a returned array.
        return force.copy(),potential

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
        try:return self._step(phase,dt_s,acting=acting)
        except Exception:
            object.__setattr__(self,'_force_cache',None)
            raise

    def _step(self,phase,dt_s,*,acting=True):
        if not isinstance(phase,Phase) or len(phase.position_m)!=len(self.ids):raise ValueError('Matching synchronized phase required')
        if type(acting) is not bool:raise ValueError('Explicit physical control required')
        dt=scalar(dt_s)
        if dt<=0:raise ValueError('Positive timestep required')
        end=phase.time_s+dt
        if not math.isfinite(end) or end<=phase.time_s:raise DomainExit('Unrepresentable time advance')
        x=phase._position_array;v=phase._velocity_array;mass=self._mass_column
        force,_,relative,_=self._force_geometry(x);half=v+.5*dt*force/mass if acting else v
        proposed=x+dt*half
        updated_force,_,updated_relative,_=self._force_geometry(proposed)
        i,j=self._i,self._j
        relative_drift=updated_relative-relative
        length=_row_dot3(relative_drift,relative_drift)
        dot=-_row_dot3(relative,relative_drift)
        fraction=np.clip(np.divide(dot,length,out=np.zeros_like(dot),where=length!=0),0,1)
        closest=_row_norm3(relative+fraction[:,None]*relative_drift)
        if np.any(closest<=self._pair_exclusion):raise DomainExit('Pair drift crosses excluded domain')
        updated=half+.5*dt*updated_force/mass if acting else half
        if not np.isfinite([half,proposed,updated]).all():raise DomainExit('Unrepresentable electrostatic trial')
        if np.any(_row_norm3(half)>SPEED_LIMIT_M_S):raise DomainExit('Half-step exceeds0.01c')
        _check_final_speed(updated)
        return _internal_phase(proposed,updated,end)
