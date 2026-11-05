"""IS4 synchronized drift/Boris/drift in static SI E/B and gravity.

Adapted from preserved C2-12 em_particles.py; body-domain adapter and science
validation are separate. No neutral-center feedback or implicit clock coupling.

Positions AND velocities describe the same full-step time. No hidden half-step
velocity is exported. A failed trial never mutates the caller's last valid phase.
"""
from dataclasses import dataclass
import math
import numpy as np
from is4_values import scalar,vector,SPEED_LIMIT_M_S

class DomainExit(ValueError):
    pass

@dataclass(frozen=True)
class Phase:
    position_m: tuple
    velocity_m_s: tuple
    time_s: float=0.
    position_origin_m: tuple|None=None
    position_offset_m: tuple|None=None

    def __post_init__(self):
        position=vector(self.position_m)
        if self.position_origin_m is None and self.position_offset_m is None:
            origin,offset=position,(0.,0.,0.)
        elif self.position_origin_m is None or self.position_offset_m is None:
            raise ValueError('Position origin and displacement must be provided together')
        else:
            origin,offset=vector(self.position_origin_m),vector(self.position_offset_m)
            if tuple(math.fsum([origin[k],offset[k]]) for k in range(3))!=position:
                raise ValueError('Absolute position and origin/displacement differ')
        object.__setattr__(self,'position_m',position)
        object.__setattr__(self,'position_origin_m',origin)
        object.__setattr__(self,'position_offset_m',offset)
        object.__setattr__(self,'velocity_m_s',vector(self.velocity_m_s))
        value=scalar(self.time_s)
        if value<0:raise ValueError('Nonnegative model time required')
        if math.hypot(*self.velocity_m_s)>SPEED_LIMIT_M_S:raise DomainExit('Velocity exceeds0.01c')
        object.__setattr__(self,'time_s',value)

def _segment_in_domain(model,start,end):
    if model.segment_in_domain(start.tolist(),end.tolist()) is not True:
        raise DomainExit('Drift leaves declared field/gravity domain')

def boris_step(model,phase,charge_C,mass_kg,dt_s,*,electric_acting=True,magnetic_acting=True,gravity_acting=True):
    if not isinstance(phase,Phase):raise ValueError('Explicit synchronized phase required')
    charge=scalar(charge_C);mass=scalar(mass_kg);dt=scalar(dt_s)
    if mass<=0 or dt<=0:raise ValueError('Positive mass and timestep required')
    if any(type(flag) is not bool for flag in [electric_acting,magnetic_acting,gravity_acting]):raise ValueError('Explicit physical controls required')
    end_time=phase.time_s+dt
    if not math.isfinite(end_time) or end_time<=phase.time_s:raise DomainExit('Unrepresentable time advance')
    x=np.array(phase.position_m);v=np.array(phase.velocity_m_s)
    origin=phase.position_origin_m;offset=np.array(phase.position_offset_m)
    mid_offset=offset+.5*dt*v
    mid=np.array([math.fsum([origin[k],float(mid_offset[k])]) for k in range(3)])
    _segment_in_domain(model,x,mid)
    reading=model.evaluate(mid.tolist())
    if reading.get('valid') is not True:raise DomainExit('Midpoint outside field domain')
    E=np.array(vector(reading['electric_field_V_m'])) if electric_acting else np.zeros(3)
    B=np.array(vector(reading['magnetic_field_T'])) if magnetic_acting else np.zeros(3)
    g=np.array(vector(reading['gravity_m_s2'])) if gravity_acting else np.zeros(3)
    half=.5*dt*(charge/mass)
    t=half*B
    if not np.isfinite(t).all() or math.hypot(*t)>.05:raise DomainExit('Gyro angle exceeds0.1 radians per step')
    kick=half*E+.5*dt*g
    minus=v+kick
    s=2*t/(1+float(np.dot(t,t)))
    plus=minus+np.cross(minus+np.cross(minus,t),s)
    updated_velocity=plus+kick
    updated_offset=mid_offset+.5*dt*updated_velocity
    updated_position=np.array([math.fsum([origin[k],float(updated_offset[k])]) for k in range(3)])
    if not np.isfinite([mid,minus,plus,updated_velocity,updated_position]).all():raise DomainExit('Unrepresentable SI trial')
    for velocity in (minus,plus,updated_velocity):
        if math.hypot(*velocity)>SPEED_LIMIT_M_S:raise DomainExit('Trial exceeds nonrelativistic velocity limit')
    _segment_in_domain(model,mid,updated_position)
    # Endpoints may be outside while the two drift segments cross an exclusion.
    # Both segments were checked, so no source can be silently crossed.
    new_phase=Phase(tuple(float(v) for v in updated_position),tuple(float(v) for v in updated_velocity),end_time,
        position_origin_m=origin,position_offset_m=tuple(float(v) for v in updated_offset))
    # Integrate work along the two kinematic drift segments. Subtracting
    # planet-scale absolute positions loses their small displacement.
    drift_displacement=.5*dt*(v+updated_velocity)
    electric_work=float(charge*np.dot(E,drift_displacement))
    gravity_work=float(mass*np.dot(g,drift_displacement))
    delta_K=.5*mass*float(np.dot(updated_velocity-v,updated_velocity+v))
    if any(not math.isfinite(v) for v in [electric_work,gravity_work,delta_K]):raise DomainExit('Unrepresentable energy diagnostic')
    return new_phase,{'electric_work_J':electric_work,'gravity_work_J':gravity_work,'kinetic_change_J':delta_K,
        'sample_position_m':mid.tolist(),'sample_time_s':phase.time_s+.5*dt,
        'work_displacement_m':drift_displacement.tolist(),
        'absolute_position_roundoff_m':((updated_position-x)-drift_displacement).tolist(),
        'velocity_convention':'position and velocity synchronized at full-step time',
        'electric_acting':electric_acting,'magnetic_acting':magnetic_acting,'gravity_acting':gravity_acting}
