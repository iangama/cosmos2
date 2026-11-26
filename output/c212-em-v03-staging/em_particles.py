"""Synchronized drift/Boris-velocity/drift test particle prototype in static SI fields.

Positions AND velocities describe the same full-step time. No hidden half-step
velocity is exported. A failed trial never mutates the caller's last valid phase.
"""
from dataclasses import dataclass
import math
import numpy as np
from em_fields import scalar,vector,SPEED_LIMIT_M_S

class DomainExit(ValueError):
    pass

@dataclass(frozen=True)
class Phase:
    position_m: tuple
    velocity_m_s: tuple
    time_s: float=0.

    def __post_init__(self):
        object.__setattr__(self,'position_m',vector(self.position_m))
        object.__setattr__(self,'velocity_m_s',vector(self.velocity_m_s))
        value=scalar(self.time_s)
        if value<0:raise ValueError('Nonnegative model time required')
        if math.hypot(*self.velocity_m_s)>SPEED_LIMIT_M_S:raise DomainExit('Velocity exceeds0.01c')
        object.__setattr__(self,'time_s',value)

def _segment_in_domain(model,start,end):
    delta=end-start;length=float(np.dot(delta,delta))
    if not math.isfinite(length):raise DomainExit('Unrepresentable drift')
    for source in model.sources:
        offset=np.array(source.position_m)-start
        fraction=min(1.,max(0.,float(np.dot(offset,delta))/length)) if length else 0.
        if math.hypot(*(offset-fraction*delta))<=source.exclusion_radius_m:
            raise DomainExit('Drift reaches excluded source '+source.id)

def boris_step(model,phase,charge_C,mass_kg,dt_s,*,electric_acting=True,magnetic_acting=True):
    if not isinstance(phase,Phase):raise ValueError('Explicit synchronized phase required')
    charge=scalar(charge_C);mass=scalar(mass_kg);dt=scalar(dt_s)
    if mass<=0 or dt<=0:raise ValueError('Positive mass and timestep required')
    if type(electric_acting) is not bool or type(magnetic_acting) is not bool:raise ValueError('Explicit physical controls required')
    end_time=phase.time_s+dt
    if not math.isfinite(end_time) or end_time<=phase.time_s:raise DomainExit('Unrepresentable time advance')
    x=np.array(phase.position_m);v=np.array(phase.velocity_m_s);mid=x+.5*dt*v
    _segment_in_domain(model,x,mid)
    reading=model.evaluate(mid)
    if not reading['valid']:raise DomainExit('Midpoint outside field domain')
    E=np.array(reading['electric_field_V_m']) if electric_acting else np.zeros(3)
    B=np.array(reading['magnetic_field_T']) if magnetic_acting else np.zeros(3)
    half=.5*dt*(charge/mass)
    t=half*B
    if not np.isfinite(t).all() or math.hypot(*t)>.05:raise DomainExit('Gyro angle exceeds0.1 radians per step')
    minus=v+half*E
    s=2*t/(1+float(np.dot(t,t)))
    plus=minus+np.cross(minus+np.cross(minus,t),s)
    updated_velocity=plus+half*E
    updated_position=mid+.5*dt*updated_velocity
    if not np.isfinite([mid,minus,plus,updated_velocity,updated_position]).all():raise DomainExit('Unrepresentable SI trial')
    for velocity in (minus,plus,updated_velocity):
        if math.hypot(*velocity)>SPEED_LIMIT_M_S:raise DomainExit('Trial exceeds nonrelativistic velocity limit')
    _segment_in_domain(model,mid,updated_position)
    # Endpoints may be outside while the two drift segments cross an exclusion.
    # Both segments were checked, so no source can be silently crossed.
    new_phase=Phase(tuple(updated_position),tuple(updated_velocity),end_time)
    electric_work=float(charge*np.dot(E,updated_position-x))
    delta_K=.5*mass*float(np.dot(updated_velocity,updated_velocity)-np.dot(v,v))
    if not math.isfinite(electric_work) or not math.isfinite(delta_K):raise DomainExit('Unrepresentable energy diagnostic')
    return new_phase,{'electric_work_J':electric_work,'kinetic_change_J':delta_K,
        'sample_position_m':mid.tolist(),'sample_time_s':phase.time_s+.5*dt,
        'velocity_convention':'position and velocity synchronized at full-step time',
        'electric_acting':electric_acting,'magnetic_acting':magnetic_acting}
