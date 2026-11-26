"""Sealed, versioned SI cloud state; no gravity-session compatibility."""
from dataclasses import asdict
from pathlib import Path
import hashlib
import json
import os
import tempfile
import numpy as np
from cloud_core import System,Phase,VERSION
from cloud_fields import evaluate
from em_fields import Model,Source,scalar

FILES=('cloud_core.py','cloud_fields.py','em_fields.py','em_particles.py','constants.json','cloud_checkpoint.py','cloud_native.py','cloud_kernel.cpp','CMakeLists.txt','cosmos2_em_cloud.dll','build-receipt.json')
MAX_BYTES=2_000_000
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def generation():
    base=Path(__file__).resolve().parent
    return {'model':VERSION,'files_sha256':{n:hashlib.sha256((base/n).read_bytes()).hexdigest() for n in FILES}}
def controls(value):
    if not isinstance(value,dict) or set(value)!={'electric_acting','magnetic_acting'} or any(type(v) is not bool for v in value.values()):raise ValueError('Explicit independent EM controls required')
    return value.copy()
def timestep(value):
    dt=scalar(value)
    if dt<=0:raise ValueError('Positive SI timestep required')
    return dt
def record(system,phase,dt_s,acting):
    if not isinstance(system,System) or not isinstance(phase,Phase) or system.count!=phase.count:raise ValueError('Matching cloud state required')
    evaluate(system.model,phase.positions(),potential=False)
    body={'schema':1,'generation':generation(),'count':phase.count,'model':asdict(system.model),'dt_s':timestep(dt_s),'controls':controls(acting),
          'phase':{'time_s':phase.time_s,'position_f64le_hex':phase._x.hex(),'velocity_f64le_hex':phase._v.hex()},
          'particles':{'charge_f64le_hex':system._q.hex(),'mass_f64le_hex':system._m.hex()}}
    return {**body,'sha256':hashlib.sha256(canonical(body)).hexdigest()}
def save(path,system,phase,dt_s,acting):
    data=canonical(record(system,phase,dt_s,acting));path=Path(path)
    if len(data)>MAX_BYTES:raise ValueError('Cloud checkpoint exceeds size limit')
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(dir=path.parent,prefix=path.name+'.',suffix='.tmp')
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path)
    finally:Path(temp).unlink(missing_ok=True)
def unique(pairs):
    d={}
    for k,v in pairs:
        if k in d:raise ValueError('Duplicate checkpoint key')
        d[k]=v
    return d
def load(path):
    with Path(path).open('rb') as stream:data=stream.read(MAX_BYTES+1)
    if len(data)>MAX_BYTES:raise ValueError('Cloud checkpoint exceeds size limit')
    r=json.loads(data,object_pairs_hook=unique,parse_constant=lambda v:(_ for _ in ()).throw(ValueError('Nonfinite checkpoint constant')))
    if not isinstance(r,dict) or set(r)!={'schema','generation','count','model','dt_s','controls','phase','particles','sha256'} or type(r['schema']) is not int or r['schema']!=1:raise ValueError('Unknown cloud checkpoint schema')
    seal=r.pop('sha256')
    if seal!=hashlib.sha256(canonical(r)).hexdigest() or r['generation']!=generation():raise ValueError('Cloud checkpoint seal/generation mismatch; explicit migration required')
    n=r['count']
    if type(n) is not int or not 1<=n<=10000:raise ValueError('Cloud population outside1..10000')
    p=r['phase'];particles=r['particles'];model=r['model']
    if not isinstance(p,dict) or set(p)!={'time_s','position_f64le_hex','velocity_f64le_hex'} or not isinstance(particles,dict) or set(particles)!={'charge_f64le_hex','mass_f64le_hex'}:raise ValueError('Unknown cloud buffers')
    if not isinstance(model,dict) or set(model)!={'sources','uniform_E_V_m','uniform_B_T'} or not isinstance(model['sources'],list) or len(model['sources'])>128:raise ValueError('Unknown prescribed source model')
    def decode(value,width):
        if type(value) is not str or len(value)!=n*width*16 or any(c not in '0123456789abcdef' for c in value):raise ValueError('Invalid canonical f64 buffer')
        return np.frombuffer(bytes.fromhex(value),dtype='<f8').reshape((n,3) if width==3 else (n,))
    source=Model(tuple(Source(**s) for s in model['sources']),model['uniform_E_V_m'],model['uniform_B_T'])
    system=System(source,decode(particles['charge_f64le_hex'],1),decode(particles['mass_f64le_hex'],1))
    phase=Phase(decode(p['position_f64le_hex'],3),decode(p['velocity_f64le_hex'],3),p['time_s'])
    evaluate(system.model,phase.positions(),potential=False)
    return system,phase,timestep(r['dt_s']),controls(r['controls'])
