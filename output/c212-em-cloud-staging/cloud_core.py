"""Immutable synchronized Boris cloud,1..10000 prescribed-field test particles.

Each particle has q/m but no reaction on sources or on other test particles.
No plasma self-fields, gravity, radiation, induction or atomic interpretation.
"""
from dataclasses import dataclass
import math
import numpy as np
from em_fields import scalar,SPEED_LIMIT_M_S
from em_particles import DomainExit
from cloud_fields import MAX_COUNT,POSITION_LIMIT_M,positions,model_domain,evaluate,drift_domain,dot3

VERSION='SI_prescribed_EM_test_cloud_boris_v1'
def immutable(a):return np.frombuffer(np.ascontiguousarray(a,dtype='<f8').tobytes(),dtype='<f8').reshape(a.shape)
def numeric(raw,dimensions):
    if not isinstance(raw,np.ndarray):
        if not isinstance(raw,(tuple,list)) or not 1<=len(raw)<=MAX_COUNT:raise ValueError('Bounded numeric cloud population required')
        values=raw
        if dimensions==2:
            if any(not isinstance(row,(tuple,list,np.ndarray)) or len(row)!=3 for row in raw):raise ValueError('Three components per cloud particle required')
            values=[v for row in raw for v in row]
        if any(isinstance(v,(bool,np.bool_)) for v in values):raise ValueError('Boolean cloud scalars forbidden')
    a=np.asarray(raw)
    if a.dtype.kind not in 'fiu' or a.ndim!=dimensions or not 1<=len(a)<=MAX_COUNT or dimensions==2 and a.shape[1]!=3:raise ValueError('Explicit bounded numeric arrays required')
    a=np.asarray(a,dtype=float)
    if not np.isfinite(a).all():raise ValueError('Finite cloud scalars required')
    return a
def speed_domain(v):
    norms=np.sqrt(dot3(v,v));near=abs(norms-SPEED_LIMIT_M_S)<=1e-12*SPEED_LIMIT_M_S
    if np.any(norms[~near]>SPEED_LIMIT_M_S) or any(math.hypot(*row)>SPEED_LIMIT_M_S for row in v[near]):raise DomainExit('Cloud trial exceeds0.01c')

@dataclass(frozen=True,init=False)
class Phase:
    _x:bytes
    _v:bytes
    count:int
    time_s:float
    def __init__(self,position_m,velocity_m_s,time_s=0.):
        x=numeric(position_m,2);v=numeric(velocity_m_s,2);t=scalar(time_s)
        if x.shape!=v.shape or t<0:raise ValueError('Matching synchronized cloud phase and nonnegative time required')
        positions(x);speed_domain(v);self._store(x,v,t)
    def _store(self,x,v,t):
        object.__setattr__(self,'_x',np.ascontiguousarray(x,dtype='<f8').tobytes());object.__setattr__(self,'_v',np.ascontiguousarray(v,dtype='<f8').tobytes());object.__setattr__(self,'count',len(x));object.__setattr__(self,'time_s',t)
    @classmethod
    def _internal(cls,x,v,t):
        phase=object.__new__(cls);phase._store(x,v,t);return phase
    def positions(self):return np.frombuffer(self._x,dtype='<f8').reshape(self.count,3)
    def velocities(self):return np.frombuffer(self._v,dtype='<f8').reshape(self.count,3)
    def point(self,index):
        if type(index) is not int or not 0<=index<self.count:raise ValueError('Cloud index outside population')
        return {'index':index,'position_m':self.positions()[index].tolist(),'velocity_m_s':self.velocities()[index].tolist(),'time_s':self.time_s}

@dataclass(frozen=True,init=False)
class System:
    model:object
    _q:bytes
    _m:bytes
    count:int
    def __init__(self,model,charge_C,mass_kg):
        model_domain(model);q=numeric(charge_C,1);m=numeric(mass_kg,1)
        if q.shape!=m.shape or np.any(m<=0):raise ValueError('One finite charge and positive mass per test particle required')
        object.__setattr__(self,'model',model);object.__setattr__(self,'_q',q.astype('<f8').tobytes());object.__setattr__(self,'_m',m.astype('<f8').tobytes());object.__setattr__(self,'count',len(q))
    @classmethod
    def uniform(cls,model,count,charge_C,mass_kg):
        if type(count) is not int or not 1<=count<=MAX_COUNT:raise ValueError('Cloud count1..10000 required')
        return cls(model,np.full(count,scalar(charge_C)),np.full(count,scalar(mass_kg)))
    def charges(self):return np.frombuffer(self._q,dtype='<f8')
    def masses(self):return np.frombuffer(self._m,dtype='<f8')
    def step(self,phase,dt_s,*,electric_acting=True,magnetic_acting=True):
        if not isinstance(phase,Phase) or phase.count!=self.count:raise ValueError('Matching synchronized cloud phase required')
        if type(electric_acting) is not bool or type(magnetic_acting) is not bool:raise ValueError('Explicit electric/magnetic acting controls required')
        dt=scalar(dt_s);end=phase.time_s+dt
        if dt<=0 or not math.isfinite(end) or end<=phase.time_s:raise DomainExit('Invalid or unrepresentable cloud time advance')
        x=phase.positions();v=phase.velocities();q=self.charges();m=self.masses()
        with np.errstate(all='ignore'):mid=x+.5*dt*v
        positions(mid);drift_domain(self.model,x,mid);E,B,_=evaluate(self.model,mid,potential=False)
        if not electric_acting:E=np.zeros_like(E)
        if not magnetic_acting:B=np.zeros_like(B)
        with np.errstate(all='ignore'):
            half=.5*dt*(q/m);t=half[:,None]*B
            if not np.isfinite(t).all() or np.any(np.sqrt(dot3(t,t))>.05):raise DomainExit('Cloud gyro angle exceeds0.1rad per step')
            minus=v+half[:,None]*E;s=2*t/(1+dot3(t,t))[:,None]
            plus=minus+np.cross(minus+np.cross(minus,t),s);updated=plus+half[:,None]*E;proposed=mid+.5*dt*updated
        if not all(np.isfinite(a).all() for a in (minus,plus,updated,proposed)):raise DomainExit('Unrepresentable SI cloud trial')
        for trial in (minus,plus,updated):speed_domain(trial)
        positions(proposed);drift_domain(self.model,mid,proposed)
        with np.errstate(all='ignore'):
            work=q*dot3(E,proposed-x);delta=.5*m*(dot3(updated,updated)-dot3(v,v))
        if not np.isfinite(work).all() or not np.isfinite(delta).all():raise DomainExit('Unrepresentable per-particle work/energy')
        return Phase._internal(proposed,updated,end),{'electric_work_J':immutable(work),'kinetic_change_J':immutable(delta),
                'sample_time_s':phase.time_s+.5*dt,'velocity_convention':'position and velocity synchronized at full-step time',
                'electric_acting':electric_acting,'magnetic_acting':magnetic_acting}
    def diagnostics(self,phase):
        if not isinstance(phase,Phase) or phase.count!=self.count:raise ValueError('Matching cloud phase required')
        v=phase.velocities();energy=.5*self.masses()*dot3(v,v)
        if not np.isfinite(energy).all():raise DomainExit('Unrepresentable cloud kinetic energy')
        return {'kinetic_energy_J':math.fsum(energy.tolist()),'moving_charge_C':math.fsum(self.charges().tolist()),
                'count':self.count,'time_s':phase.time_s,'backreaction':False,'test_test_interaction':False,
                'scope':'Test matter only in static prescribed fields; fixed-source reservoirs and field energy excluded.'}
