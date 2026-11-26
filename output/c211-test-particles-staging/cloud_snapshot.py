"""Bounded confirmed cloud packet, independent of the installed native bridge."""
import hashlib,json,math,os,struct,uuid
from pathlib import Path
import numpy as np
MAGIC=b'C2CLD001';MAX_COUNT=10000;MAX_METADATA=32768;FRAME='initial_central_source_inertial'
HEADER=struct.Struct('<8sI')

def _identity(value):
 if not isinstance(value,str) or len(value)!=32 or any(c not in '0123456789abcdef' for c in value):raise ValueError('Cloud identity must be32 lowercase hex digits')
 return value

def validate_solver(sim):
 if sim.N_active!=1 or sim.N_var!=0 or sim.testparticle_type!=0 or sim.N<2 or sim.N>MAX_COUNT+1 or sim.G!=1. or str(sim.gravity)!='basic' or str(sim.integrator)!='ias15' or sim.integrator.epsilon!=1e-9 or sim.softening!=0 or str(sim.collision)!='none' or bool(sim._additional_forces):raise ValueError('Isolated central-source cloud contract required')
 masses=np.empty(sim.N,dtype=np.float64);xyz=np.empty((sim.N,3),dtype=np.float64);velocity=np.empty_like(xyz)
 sim.serialize_particle_data(m=masses,xyz=xyz,vxvyvz=velocity)
 if not math.isfinite(sim.t) or sim.t<0 or masses[0]!=1. or np.any(masses[1:]!=0):raise ValueError('Central unit mass and exactly zero cloud masses required')
 if np.any(xyz[0]!=0) or np.any(velocity[0]!=0):raise ValueError('Central source must remain stationary in this fixed frame')
 if not np.isfinite(xyz).all() or not np.isfinite(velocity).all():raise ValueError('Nonfinite cloud phase')
 return xyz

def encode(sim,system_id,edit_token,sequence,length_unit_m,time_unit_s):
 xyz=validate_solver(sim)
 _identity(system_id);_identity(edit_token)
 if type(sequence) is not int or not 0<=sequence<2**63:raise ValueError('Invalid confirmed sequence')
 for value in (length_unit_m,time_unit_s):
  if type(value) not in (int,float) or not math.isfinite(value) or value<=0:raise ValueError('Positive finite physical scales required')
 xyz=xyz[1:]*length_unit_m
 if not np.isfinite(xyz).all() or np.max(np.linalg.norm(xyz,axis=1))>1e17:raise ValueError('Cloud positions outside SI domain')
 payload=xyz.astype('<f8',copy=False).tobytes()
 metadata={'schema':1,'model':'isolated_massless_central_source_v1','system_id':system_id,'edit_token':edit_token,'sequence':sequence,'time_model':sim.t,'time_s':sim.t*time_unit_s,'time_unit_s':time_unit_s,'length_unit_m':length_unit_m,'frame':FRAME,'count':sim.N-1,'active_source_count':1,'particle_ids':'tp:index0..count-1; fixed for this system','positions':'SI_m_float64_little_endian_xyz','payload_sha256':hashlib.sha256(payload).hexdigest()}
 header=json.dumps(metadata,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii');assert len(header)<=MAX_METADATA
 return HEADER.pack(MAGIC,len(header))+header+payload

def decode(packet,system_id,edit_token,minimum_sequence=0):
 if not isinstance(packet,bytes) or len(packet)<HEADER.size or len(packet)>HEADER.size+MAX_METADATA+MAX_COUNT*24:raise ValueError('Cloud packet size invalid')
 magic,size=HEADER.unpack_from(packet)
 if magic!=MAGIC or not 0<size<=MAX_METADATA or len(packet)<HEADER.size+size:raise ValueError('Cloud packet header invalid')
 try:m=json.loads(packet[HEADER.size:HEADER.size+size])
 except (ValueError,UnicodeError) as error:raise ValueError('Invalid cloud metadata') from error
 required={'schema','model','system_id','edit_token','sequence','time_model','time_s','time_unit_s','length_unit_m','frame','count','active_source_count','particle_ids','positions','payload_sha256'}
 if not isinstance(m,dict) or set(m)!=required or type(m['schema']) is not int or m['schema']!=1 or m['model']!='isolated_massless_central_source_v1':raise ValueError('Cloud schema/model invalid')
 if _identity(m['system_id'])!=_identity(system_id) or _identity(m['edit_token'])!=_identity(edit_token):raise ValueError('Stale cloud system or edit token')
 if m['frame']!=FRAME or m['active_source_count']!=1 or type(m['active_source_count']) is not int or m['positions']!='SI_m_float64_little_endian_xyz' or m['particle_ids']!='tp:index0..count-1; fixed for this system':raise ValueError('Cloud coordinate/identity contract invalid')
 if type(m['sequence']) is not int or not minimum_sequence<=m['sequence']<2**63 or type(m['count']) is not int or not 1<=m['count']<=MAX_COUNT:raise ValueError('Cloud sequence/count invalid')
 for key in ('time_model','time_s','time_unit_s','length_unit_m'):
  if type(m[key]) not in (int,float) or not math.isfinite(m[key]) or m[key]<0 or (key in ('time_unit_s','length_unit_m') and m[key]==0):raise ValueError('Cloud time/scale invalid')
 if m['time_s']!=m['time_model']*m['time_unit_s']:raise ValueError('Inconsistent physical time')
 payload=packet[HEADER.size+size:]
 if len(payload)!=m['count']*24 or hashlib.sha256(payload).hexdigest()!=m['payload_sha256']:raise ValueError('Cloud payload size/digest invalid')
 xyz=np.frombuffer(payload,dtype='<f8').reshape(m['count'],3)
 if not np.isfinite(xyz).all() or np.max(np.linalg.norm(xyz,axis=1))>1e17:raise ValueError('Cloud payload outside position domain')
 return m,xyz

def publish(path,packet):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
 try:
  with temporary.open('xb') as stream:stream.write(packet);stream.flush();os.fsync(stream.fileno())
  os.replace(temporary,path)
 finally:temporary.unlink(missing_ok=True)
