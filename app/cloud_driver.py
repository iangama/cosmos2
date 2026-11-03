"""One IAS15 state for one active source and a passive cloud; confirmed mirror only.

Isolated candidate, not installed. Circular synthetic annulus; no J2/material,
no test-test gravity, no mass or source editing while this driver is bound.
"""
import copy,hashlib,json,math
import numpy as np
import rebound
from pathlib import Path
_ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
_U=json.loads((_ROOT/'data/science/canonical-units.json').read_text())
_POSITION_LIMIT=1e17/_U['length_unit_m'];_VELOCITY_LIMIT=1e7/math.sqrt(_U['nominal_GM_unit_m3_s2']/_U['length_unit_m'])
VERSION='massless_central_ias15_v1';MAX_COUNT=10000

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def source_phase(sim):
 p=sim.particles[0];return [getattr(p,k) for k in ('m','x','y','z','vx','vy','vz')]
def settings(value):
 if not isinstance(value,dict) or set(value)!={'count'} or type(value['count']) is not int or not 1<=value['count']<=MAX_COUNT:raise ValueError('Cloud count1..10000 required')
 return copy.deepcopy(value)
def _plain(sim):
 if sim.G!=1. or sim.N_var!=0 or sim._N_odes!=0 or str(sim.integrator)!='ias15' or sim.integrator.epsilon!=1e-9 or str(sim.gravity)!='basic' or sim.softening!=0 or str(sim.collision)!='none' or sim.gravity_ignore!=0 or sim.force_is_velocity_dependent!=0 or bool(sim._additional_forces) or bool(sim._pre_timestep_modifications) or bool(sim._post_timestep_modifications) or bool(sim._heartbeat):raise ValueError('Unmodified point-gravity IAS15 required')
 if not math.isfinite(sim.t) or sim.t<0:raise ValueError('Invalid cloud time')

class Driver:
 def __init__(self,mirror,source_id,configuration):
  self._validate_mirror(mirror)
  if not isinstance(source_id,str) or not 1<=len(source_id)<=100:raise ValueError('Explicit stable source identity required')
  self.configuration=settings(configuration);self.source_id=source_id;self.mirror=mirror;self.epoch=mirror.t;self.initial_source=source_phase(mirror)
  self.sim=rebound.Simulation();self.sim.G=1.;self.sim.integrator='ias15';self.sim.integrator.epsilon=1e-9;self.sim.t=mirror.t
  # Initial proposal for the immutable annulus (r_min=1); IAS15 still adapts.
  # A tiny proposal is restored by REBOUND on early exact-finish exits and
  # otherwise repeatedly starves the40ms worker budget before it can grow.
  self.sim.dt=min(.1,.1/math.sqrt(self.initial_source[0]))
  self.sim.add(**dict(zip(('m','x','y','z','vx','vy','vz'),self.initial_source)))
  mass=self.initial_source[0];center=np.array(self.initial_source[1:4]);boost=np.array(self.initial_source[4:7]);count=self.configuration['count']
  for i in range(count):
   radius=1.+3.*i/max(1,count-1);angle=(i*math.pi*(3.-math.sqrt(5.)))%(2.*math.pi);speed=math.sqrt(mass/radius)
   r=center+radius*np.array([math.cos(angle),math.sin(angle),0.]);v=boost+speed*np.array([-math.sin(angle),math.cos(angle),0.])
   self.sim.add(m=0.,x=r[0],y=r[1],z=r[2],vx=v[0],vy=v[1],vz=v[2])
  self.sim.N_active=1;self.sim.testparticle_type=0
  # REBOUND's all-pair close-distance condition would be quadratic in the cloud.
  # This immutable circular preset uses a linear source-distance domain check.
  self.sim.exit_min_distance=0.;self._confirmed_source=source_phase(mirror);self._confirmed_time=mirror.t;self.check()

 @staticmethod
 def _validate_mirror(sim):
  _plain(sim)
  if sim.N!=1 or sim.N_active not in (1,2**64-1) or not 1e-12<=sim.particles[0].m<=100:raise ValueError('Exactly one active source mirror required')
  if not all(math.isfinite(v) for v in source_phase(sim)):raise ValueError('Nonfinite source mirror')

 def _arrays(self,sim=None):
  sim=self.sim if sim is None else sim;m=np.empty(sim.N);r=np.empty((sim.N,3));v=np.empty_like(r);sim.serialize_particle_data(m=m,xyz=r,vxvyvz=v);return m,r,v

 def _domain(self,sim):
  m,r,v=self._arrays(sim)
  if not np.isfinite(m).all() or not np.isfinite(r).all() or not np.isfinite(v).all() or m[0]!=self.initial_source[0] or np.any(m[1:]!=0.):raise ValueError('Cloud masses/phase outside contract')
  if np.max(np.linalg.norm(r,axis=1))>_POSITION_LIMIT or np.max(np.linalg.norm(v,axis=1))>_VELOCITY_LIMIT:raise ValueError('Cloud phase outside canonical/SI domain')
  if np.min(np.linalg.norm(r[1:]-r[0],axis=1))<1e-12:raise ValueError('Cloud crossed source point-domain boundary')
  return r,v

 def _check_engine(self,sim):
  _plain(sim)
  if sim.N!=1+self.configuration['count'] or sim.N_active!=1 or sim.testparticle_type!=0 or sim.integrator.adaptive_mode!='PRS23' or sim.exit_min_distance!=0.:raise ValueError('Cloud active/passive partition invalid')
  self._domain(sim)
  expected=np.array(self.initial_source[1:4])+(sim.t-self.epoch)*np.array(self.initial_source[4:7])
  if not np.allclose(np.array(source_phase(sim)[1:4]),expected,rtol=1e-12,atol=1e-13):raise ValueError('Source inertial motion inconsistent with activation')

 def check(self):
  self._validate_mirror(self.mirror);self._check_engine(self.sim)
  if self.mirror.t!=self._confirmed_time or self.sim.t!=self._confirmed_time or source_phase(self.mirror)!=self._confirmed_source or source_phase(self.sim)!=self._confirmed_source:raise ValueError('Cloud no longer matches its confirmed source mirror')

 def advance(self,target,heartbeat=None):
  self.check()
  if type(target) not in (int,float) or not math.isfinite(target) or target<self.sim.t:raise ValueError('Cloud target must be finite and forward')
  trial=rebound.Simulation(self.sim.__reduce__()[1][0]);failure=[]
  def monitor(pointer):
   try:
    self._domain(trial)
    if heartbeat is not None:heartbeat(pointer)
   except Exception as error:failure.append(str(error));pointer.contents.stop()
  trial.heartbeat=monitor
  try:trial.integrate(target)
  finally:trial.heartbeat=0
  if failure:raise ValueError('Cloud trial refused: '+failure[0])
  self._check_engine(trial)
  current=source_phase(trial)
  self.sim=trial
  p=self.mirror.particles[0]
  for key,v in zip(('x','y','z','vx','vy','vz'),current[1:]):setattr(p,key,v)
  self.mirror.t=trial.t;self._confirmed_source=current;self._confirmed_time=trial.t
  self.check()

 def public(self):
  return {'model':VERSION,'source_id':self.source_id,'active_sources':1,'test_particles':self.configuration['count'],'test_particle_mass':0.,'backreaction':False,'mutual_test_gravity':False,'confirmed_time':self._confirmed_time,'epoch':self.epoch,'integrator':'IAS15 joint source and massless particles','epsilon':1e-9,'preset':'synthetic circular annulus1..4 canonical distance units','observational_source':None}

 def positions(self):
  self.check();r=np.empty((self.sim.N,3));self.sim.serialize_particle_data(xyz=r);return r[1:]

 def point(self,index):
  self.check()
  if type(index) is not int or not 0<=index<self.configuration['count']:raise ValueError('Particle index outside cloud')
  p=self.sim.particles[index+1];s=self.sim.particles[0];r=np.array([p.x-s.x,p.y-s.y,p.z-s.z]);v=np.array([p.vx-s.vx,p.vy-s.vy,p.vz-s.vz])
  return {'index':index,'id':'tp:'+str(index),'role':'massless_test_particle','mass':0.,'time':self.sim.t,'source_id':self.source_id,'position':[p.x,p.y,p.z],'velocity':[p.vx,p.vy,p.vz],'specific_energy':float(.5*np.dot(v,v)-s.m/np.linalg.norm(r)),'specific_angular_momentum':np.cross(r,v).tolist(),'units':'canonical; caller must bind explicit physical scales/frame'}

 def checkpoint(self):
  self.check();binary=self.sim.__reduce__()[1][0]
  metadata={'schema':1,'model':VERSION,'rebound':rebound.__version__,'source_id':self.source_id,'configuration':self.configuration,'epoch':self.epoch,'initial_source':self.initial_source,'confirmed_time':self._confirmed_time,'confirmed_source':self._confirmed_source,'binary_sha256':hashlib.sha256(binary).hexdigest()}
  metadata['sha256']=digest(metadata);return copy.deepcopy(metadata),binary

 @classmethod
 def restore(cls,mirror,source_id,metadata,binary):
  cls._validate_mirror(mirror)
  required={'schema','model','rebound','source_id','configuration','epoch','initial_source','confirmed_time','confirmed_source','binary_sha256','sha256'}
  if not isinstance(metadata,dict) or set(metadata)!=required or type(metadata['schema']) is not int or metadata['schema']!=1 or metadata['model']!=VERSION or metadata['rebound']!=rebound.__version__ or metadata['sha256']!=digest({k:v for k,v in metadata.items() if k!='sha256'}):raise ValueError('Cloud checkpoint seal/model invalid')
  if metadata['source_id']!=source_id or not isinstance(binary,bytes) or not 1<=len(binary)<=100_000_000 or hashlib.sha256(binary).hexdigest()!=metadata['binary_sha256']:raise ValueError('Cloud binary/source identity mismatch')
  confirmed=metadata['confirmed_source']
  if not isinstance(confirmed,list) or len(confirmed)!=7 or any(type(v) not in (int,float) or not math.isfinite(v) for v in confirmed):raise ValueError('Invalid confirmed source phase')
  if type(metadata['confirmed_time']) not in (int,float) or not math.isfinite(metadata['confirmed_time']):raise ValueError('Invalid confirmed time')
  initial=metadata['initial_source']
  if not isinstance(initial,list) or len(initial)!=7 or any(type(v) not in (int,float) or not math.isfinite(v) for v in initial) or not 1e-12<=initial[0]<=100:raise ValueError('Invalid cloud activation source')
  if type(metadata['epoch']) not in (int,float) or not math.isfinite(metadata['epoch']) or not 0<=metadata['epoch']<=mirror.t:raise ValueError('Invalid cloud activation time')
  if metadata['confirmed_source']!=source_phase(mirror) or metadata['confirmed_time']!=mirror.t:raise ValueError('Cloud checkpoint differs from confirmed mirror')
  result=object.__new__(cls);result.mirror=mirror;result.source_id=source_id;result.configuration=settings(metadata['configuration']);result.epoch=metadata['epoch'];result.initial_source=copy.deepcopy(initial);result._confirmed_source=copy.deepcopy(metadata['confirmed_source']);result._confirmed_time=metadata['confirmed_time'];result.sim=rebound.Simulation(binary);result.check();return result
