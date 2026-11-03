"""Candidate joint relative orbit/spin/heat BS solver, with a REBOUND phase mirror.

The ten material coordinates live in ONE user ODE. IAS15 is never advanced
while this driver owns the two-body phase. The separate particle simulation
is only a confirmed phase mirror for the existing instruments and scene.
Nothing in this prototype is imported by the installed application.
"""
import base64
import copy
import ctypes
import hashlib
import json
import math
import warnings

import numpy as np
import rebound

from equilibrium_tide import G,response,frozen_field
from physics import PHYSICAL_SCALE as U

POLICY='Two active bodies; one deformable sphere and one point companion. Joint relative orbit, material spin and heat in one REBOUND BS ODE; analytic inertial center of mass. IAS15 particle state is a confirmed mirror only. No J2, rotational bulge, surface displacement, thermal radius or extra gravitating bodies.'
EPS=1e-13
VERSION='isolated-material-bs-v1'


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def phase(sim):
    return [[getattr(p,k) for k in ('m','x','y','z','vx','vy','vz')] for p in sim.particles]


def parameters(value):
    keys={'radius_m','love_k2','time_lag_s','inertia_kg_m2','spin_rad_s','provenance'}
    if not isinstance(value,dict) or set(value)!=keys:raise ValueError('Explicit material radius, potential Love k2, lag, inertia, spin and provenance required')
    for k in keys-{'spin_rad_s','provenance'}:
        if type(value[k]) not in (int,float) or not math.isfinite(value[k]):raise ValueError('Finite material parameters required')
    s=value['spin_rad_s']
    if not isinstance(s,list) or len(s)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in s):raise ValueError('Finite material spin required')
    text=value['provenance']
    if not isinstance(text,str) or not 1<=len(text.strip())<=240 or any(ord(c)<32 for c in text):raise ValueError('Material provenance required')
    if not .001<=value['radius_m']<=1e12 or not 0<value['love_k2']<=1.5 or not 0<=value['time_lag_s']<=1e12 or value['inertia_kg_m2']<=0:raise ValueError('Material parameters outside candidate bounds')
    return copy.deepcopy(value)


def strict(action):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always');result=action()
    if caught:raise ValueError('Unexpected material solver warning: '+'; '.join(str(w.message) for w in caught))
    return result


class Driver:
    def __init__(self,sim,ids,source_id,configuration):
        self._validate_mirror(sim)
        if not isinstance(ids,list) or len(ids)!=2 or len(set(ids))!=2 or source_id not in ids or any(not isinstance(x,str) for x in ids):raise ValueError('Two distinct active identities required')
        self.sim=sim;self.ids=list(ids);self.source_id=source_id;self.index=ids.index(source_id)
        self.configuration=parameters(configuration)
        self.masses=[p.m*U['mass_unit_kg'] for p in sim.particles]
        self.M=self.masses[self.index];self.m=self.masses[1-self.index]
        self.epoch=sim.t
        p,q=sim.particles[self.index],sim.particles[1-self.index]
        r=np.array([q.x-p.x,q.y-p.y,q.z-p.z])*U['length_unit_m']
        v=np.array([q.vx-p.vx,q.vy-p.vy,q.vz-p.vz])*U['velocity_unit_m_s']
        self.length=math.hypot(*r);self.time=math.sqrt(self.length**3/(G*(self.M+self.m)))
        self.energy=self.M*self.m/(self.M+self.m)*self.length**2/self.time**2
        fraction=self.m/(self.M+self.m)
        self.center=[getattr(p,k)+fraction*(getattr(q,k)-getattr(p,k)) for k in ('x','y','z')]
        self.center_velocity=[getattr(p,k)+fraction*(getattr(q,k)-getattr(p,k)) for k in ('vx','vy','vz')]
        y=np.r_[r/self.length,v*self.time/self.length,np.array(configuration['spin_rad_s'])*self.time,0.]
        self.engine=rebound.Simulation();self.engine.integrator='bs'
        self.engine.integrator.eps_abs=EPS;self.engine.integrator.eps_rel=EPS;self.engine.dt=.001
        self.error=None;self._attach(y);self.rhs(y)
        self._confirmed_phase=phase(sim);self._confirmed_time=sim.t
        self.initial_phase=phase(sim)
        self.reference=self.balances()

    @staticmethod
    def _validate_mirror(sim):
        if sim.N!=2 or sim.N_active not in (2,2**64-1) or sim.N_var!=0 or sim.G!=1. or str(sim.gravity)!='basic' or str(sim.collision)!='none' or sim.softening!=0 or str(sim.integrator)!='ias15' or sim.integrator.epsilon!=1e-9 or sim.integrator.adaptive_mode!='PRS23':raise ValueError('Two active point-mass mirror with the fixed base contract required')
        if any(bool(getattr(sim,k)) for k in ('_additional_forces','_pre_timestep_modifications','_post_timestep_modifications','_heartbeat')):raise ValueError('Unknown callback on the material phase mirror')
        if not math.isfinite(sim.t) or sim.t<0 or any(not all(math.isfinite(x) for x in row) or row[0]<=0 for row in phase(sim)):raise ValueError('Invalid material mirror phase')

    def values(self):return np.array([self.ode.y[i] for i in range(10)])

    def material(self,y=None):
        y=self.values() if y is None else y;c=self.configuration
        return response(self.M,self.m,c['radius_m'],c['love_k2'],c['time_lag_s'],c['inertia_kg_m2'],(y[6:9]/self.time).tolist(),(y[:3]*self.length).tolist(),(y[3:6]*self.length/self.time).tolist())

    def rhs(self,y):
        d=self.material(y);r=y[:3]
        acceleration=-r/math.hypot(*r)**3+np.array(d['force_on_companion_N'])*(1/self.M+1/self.m)*self.time**2/self.length
        derivative=np.r_[y[3:6],acceleration,np.array(d['spin_derivative_rad_s2'])*self.time**2,d['heat_power_W']*self.time/self.energy]
        if not np.isfinite(derivative).all():raise ValueError('Nonfinite joint material derivative')
        return derivative

    def _attach(self,y):
        self.ode=self.engine.create_ode(length=10,needs_nbody=False)
        def derivatives(pointer,out,coordinates,t):
            if self.error:
                for i in range(10):out[i]=0.
                self.engine.stop();return
            try:
                dy=self.rhs(np.array([coordinates[i] for i in range(10)]))
                for i,v in enumerate(dy):out[i]=v
            except Exception as error:
                self.error=str(error)
                for i in range(10):out[i]=0.
                self.engine.stop()
        self.ode.derivatives=derivatives
        self._callback_address=ctypes.cast(self.ode._derivatives,ctypes.c_void_p).value
        for i,v in enumerate(y):self.ode.y[i]=v

    def check(self):
        self._validate_mirror(self.sim)
        if self.error:raise ValueError('Material trial rejected: '+self.error)
        if phase(self.sim)!=self._confirmed_phase or self.sim.t!=self._confirmed_time:raise ValueError('Material mirror changed without joint integration')
        e=self.engine
        if rebound.__version__!='5.2.2' or e.N!=0 or e.G!=1. or str(e.integrator)!='bs' or e.integrator.eps_abs!=EPS or e.integrator.eps_rel!=EPS or e.integrator.min_dt!=0 or e.integrator.max_dt!=0 or self.ode.length!=10 or self.ode.needs_nbody!=0 or ctypes.cast(self.ode._derivatives,ctypes.c_void_p).value!=self._callback_address:raise ValueError('Material solver contract changed')
        if e._N_odes not in (1,2) or ctypes.addressof(e._odes[0].contents)!=ctypes.addressof(self.ode) or e._N_odes==2 and (e._odes[1].contents.length!=0 or e._odes[1].contents.needs_nbody!=0):raise ValueError('Unexpected material ODE population')
        if any(bool(getattr(e,k)) for k in ('_additional_forces','_pre_timestep_modifications','_post_timestep_modifications','_heartbeat')) or e.N_var!=0 or str(e.gravity)!='basic' or str(e.collision)!='none' or e.softening!=0:raise ValueError('Unexpected material engine callback/physics')
        if [p.m*U['mass_unit_kg'] for p in self.sim.particles]!=self.masses:raise ValueError('Material masses changed without intervention')
        if not np.isfinite(self.values()).all() or self.values()[9]<0:raise ValueError('Invalid material coordinates or heat')
        self.material()

    def _advance_unchecked(self,target,heartbeat=None):
        if type(target) not in (int,float) or not math.isfinite(target) or target<self.sim.t:raise ValueError('Finite forward material target required')
        if target==self.sim.t:return
        old_heat=self.values()[9]
        try:
            self.engine.heartbeat=(lambda p:heartbeat(p) if heartbeat else None) if heartbeat else 0
            strict(lambda:self.engine.integrate((target-self.epoch)*U['time_unit_s']/self.time))
        finally:self.engine.heartbeat=0
        if self.error:raise ValueError('Material domain boundary: '+self.error)
        y=self.values();self.material(y)
        if y[9]<old_heat:raise ValueError('Material heat decreased')
        elapsed=self.engine.t*self.time/U['time_unit_s'];confirmed=self.epoch+elapsed
        # REBOUND may stop at a heartbeat boundary before the requested target.
        # Publish its actual confirmed epoch; never label it as the target.
        self.sim.t=target if self.engine.t==(target-self.epoch)*U['time_unit_s']/self.time else confirmed
        center=np.array(self.center)+(self.sim.t-self.epoch)*np.array(self.center_velocity)
        r=y[:3]*self.length/U['length_unit_m'];v=y[3:6]*self.length/self.time/U['velocity_unit_m_s']
        f=self.m/(self.M+self.m)
        for index,sign in ((self.index,-f),(1-self.index,1-f)):
            particle=self.sim.particles[index]
            for key,value in zip(('x','y','z'),center+sign*r):setattr(particle,key,value)
            for key,value in zip(('vx','vy','vz'),np.array(self.center_velocity)+sign*v):setattr(particle,key,value)
        self._confirmed_phase=phase(self.sim);self._confirmed_time=self.sim.t
        self.check()

    def advance(self,target,heartbeat=None):
        """Return an accepted trial; a domain error cannot mutate this driver."""
        self.check();trial=self.clone();trial._advance_unchecked(target,heartbeat);return trial

    def balances(self):
        y=self.values();d=self.material(y);I=self.configuration['inertia_kg_m2']
        mechanical=self.energy*(.5*float(y[3:6]@y[3:6])-1/math.hypot(*y[:3]))+d['effective_induced_energy_J']+.5*I*float(y[6:9]@y[6:9])/self.time**2
        heat=y[9]*self.energy
        angular=self.M*self.m/(self.M+self.m)*self.length**2/self.time*np.cross(y[:3],y[3:6])+I*y[6:9]/self.time
        return {'mechanical_energy_J':float(mechanical),'dissipated_heat_J':float(heat),'energy_plus_heat_J':float(mechanical+heat),'orbital_plus_spin_angular_momentum_kg_m2_s':angular.tolist()}

    def field(self,point_m):
        d=self.material();p=self.sim.particles[self.index]
        displacement=[point_m[i]-getattr(p,k)*U['length_unit_m'] for i,k in enumerate(('x','y','z'))]
        return frozen_field(d['quadrupole_stf_kg_m2'],self.configuration['radius_m'],displacement)

    def checkpoint(self):
        self.check();binary=strict(lambda:self.engine.__reduce__()[1][0])
        value={'schema':1,'model':VERSION,'rebound':rebound.__version__,'ids':self.ids,'source_id':self.source_id,'configuration':self.configuration,'masses_kg':self.masses,'epoch':self.epoch,'initial_phase':self.initial_phase,'length_m':self.length,'time_s':self.time,'energy_J':self.energy,'center':self.center,'center_velocity':self.center_velocity,'coordinates':self.values().tolist(),'confirmed_time':self.sim.t,'confirmed_phase':phase(self.sim),'reference':self.reference,'binary_b64':base64.b64encode(binary).decode(),'binary_sha256':hashlib.sha256(binary).hexdigest()}
        value['sha256']=digest(value);return copy.deepcopy(value)

    @classmethod
    def restore(cls,sim,value):
        cls._validate_mirror(sim)
        if not isinstance(value,dict) or value.get('sha256')!=digest({k:v for k,v in value.items() if k!='sha256'}):raise ValueError('Material checkpoint seal mismatch')
        if value.get('schema')!=1 or value.get('model')!=VERSION or value.get('rebound')!=rebound.__version__:raise ValueError('Unsupported material checkpoint')
        initial=value['initial_phase']
        if not isinstance(initial,list) or len(initial)!=2 or any(not isinstance(row,list) or len(row)!=7 or any(type(x) not in (int,float) or not math.isfinite(x) for x in row) or row[0]<=0 for row in initial):raise ValueError('Invalid initial material phase')
        seed=rebound.Simulation();seed.G=1.;seed.integrator='ias15';seed.integrator.epsilon=1e-9;seed.t=value['epoch']
        for row in initial:seed.add(**dict(zip(('m','x','y','z','vx','vy','vz'),row)))
        candidate=cls(seed,value['ids'],value['source_id'],value['configuration'])
        origin=candidate.checkpoint()
        for key in ('masses_kg','epoch','initial_phase','length_m','time_s','energy_J','center','center_velocity','reference'):
            if value[key]!=origin[key]:raise ValueError('Material origin does not reproduce its scales/reference: '+key)
        candidate.sim=sim;candidate._confirmed_phase=phase(sim);candidate._confirmed_time=sim.t
        if value['masses_kg']!=candidate.masses or value['confirmed_time']!=sim.t or value['confirmed_phase']!=phase(sim):raise ValueError('Material checkpoint does not match phase')
        for key in ('epoch','length_m','time_s','energy_J'):
            v=value[key]
            if type(v) not in (int,float) or not math.isfinite(v) or (v<0 if key=='epoch' else v<=0):raise ValueError('Invalid material scale/epoch')
        if value['epoch']>sim.t:raise ValueError('Material epoch in future')
        candidate.epoch=value['epoch'];candidate.length=value['length_m'];candidate.time=value['time_s'];candidate.energy=value['energy_J']
        expected_time=math.sqrt(candidate.length**3/(G*(candidate.M+candidate.m)))
        expected_energy=candidate.M*candidate.m/(candidate.M+candidate.m)*candidate.length**2/candidate.time**2
        if candidate.time!=expected_time or candidate.energy!=expected_energy:raise ValueError('Inconsistent material scales')
        for key in ('center','center_velocity'):
            v=value[key]
            if not isinstance(v,list) or len(v)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in v):raise ValueError('Invalid material center of mass')
            setattr(candidate,key,list(v))
        y=value['coordinates']
        if not isinstance(y,list) or len(y)!=10 or any(type(x) not in (int,float) or not math.isfinite(x) for x in y) or y[9]<0:raise ValueError('Invalid saved material coordinates')
        if not isinstance(value['binary_b64'],str) or len(value['binary_b64'])>100000:raise ValueError('Invalid material binary length')
        binary=base64.b64decode(value['binary_b64'],validate=True)
        if hashlib.sha256(binary).hexdigest()!=value['binary_sha256']:raise ValueError('Material binary checksum mismatch')
        engine=strict(lambda:rebound.Simulation(binary))
        if engine._N_odes!=0 or engine.N!=0 or engine.t<0 or not math.isfinite(engine.t) or not math.isfinite(engine.dt) or engine.dt<=0:raise ValueError('Invalid saved material engine')
        candidate.engine=engine;candidate._attach(y);candidate.reference=copy.deepcopy(value['reference'])
        candidate.check()
        # Check the independent mirror against the joint coordinates. The
        # activation phase can differ by a few ulps after barycentric algebra.
        expected_epoch=candidate.epoch+engine.t*candidate.time/U['time_unit_s']
        if abs(expected_epoch-sim.t)>32*math.ulp(max(1.,sim.t)):raise ValueError('Material engine time differs from confirmed epoch')
        p,q=sim.particles[candidate.index],sim.particles[1-candidate.index]
        relative=np.array([getattr(q,k)-getattr(p,k) for k in ('x','y','z','vx','vy','vz')])
        expected=np.r_[np.array(y[:3])*candidate.length/U['length_unit_m'],np.array(y[3:6])*candidate.length/candidate.time/U['velocity_unit_m_s']]
        center=np.array(candidate.center)+(sim.t-candidate.epoch)*np.array(candidate.center_velocity)
        f=candidate.m/(candidate.M+candidate.m)
        actual_center=np.array([getattr(p,k)+f*(getattr(q,k)-getattr(p,k)) for k in ('x','y','z')])
        actual_velocity=np.array([getattr(p,k)+f*(getattr(q,k)-getattr(p,k)) for k in ('vx','vy','vz')])
        if not np.allclose(relative,expected,rtol=1e-13,atol=1e-18) or not np.allclose(actual_center,center,rtol=1e-13,atol=1e-15) or not np.allclose(actual_velocity,candidate.center_velocity,rtol=1e-13,atol=1e-15):raise ValueError('Material coordinates/center differ from mirror')
        reference=candidate.reference
        if not isinstance(reference,dict) or set(reference)!=set(candidate.balances()) or any(type(reference[k]) not in (int,float) or not math.isfinite(reference[k]) for k in ('mechanical_energy_J','dissipated_heat_J','energy_plus_heat_J')) or reference['dissipated_heat_J']!=0:raise ValueError('Invalid material conservation reference')
        angular=reference['orbital_plus_spin_angular_momentum_kg_m2_s']
        if not isinstance(angular,list) or len(angular)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in angular):raise ValueError('Invalid material angular reference')
        return candidate

    def clone(self):return self.restore(strict(self.sim.copy),self.checkpoint())
