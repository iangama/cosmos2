"""Exact sealed cloud restart, source identity and resealed-domain refusals."""
from pathlib import Path
import hashlib,json,sys,tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/c212-em-cloud-checkpoint-staging';sys.path.insert(0,str(STAGE))
from cloud_checkpoint import save,load,canonical,generation
from cloud_core import System,Phase
from em_fields import Model,Source
cases=[];refusals=[]
with tempfile.TemporaryDirectory() as tmp:
    path=Path(tmp)/'cloud.json'
    for n,steps in ((1,777),(128,777),(10000,64)):
        i=np.arange(n);x=np.column_stack((np.sin(i),np.cos(i),np.ones(n)*5));v=x*.01
        model=Model((Source('p',(0,0,0),.1,1e-9),),(.1,0,0),(0,0,.5)) if n<10000 else Model(uniform_B_T=(0,0,.5))
        system=System(model,np.where(i%2,1.,-1.),np.ones(n));phase=Phase(x,v);dt=.002;acting={'electric_acting':True,'magnetic_acting':True}
        for _ in range(13):phase,_=system.step(phase,dt,**acting)
        save(path,system,phase,dt,acting);s,p,d,a=load(path)
        assert (system._q,system._m,phase._x,phase._v,phase.time_s,dt,acting)==(s._q,s._m,p._x,p._v,p.time_s,d,a)
        for _ in range(steps):
            phase,work=system.step(phase,dt,**acting);p,w=s.step(p,d,**a)
            assert (phase._x,phase._v,phase.time_s)==(p._x,p._v,p.time_s)
            assert work['electric_work_J'].tobytes()==w['electric_work_J'].tobytes() and work['kinetic_change_J'].tobytes()==w['kinetic_change_J'].tobytes()
        cases.append({'count':n,'exact_future_collective_steps':steps})
    original=json.loads(path.read_bytes())
    for name in ('schema','generation','count','buffer','nonfinite','speed','mass','controls','dt','source','exclusion','extra'):
        r=json.loads(json.dumps(original))
        if name=='schema':r['schema']=True
        elif name=='generation':r['generation']['model']='gravity'
        elif name=='count':r['count']=True
        elif name=='buffer':r['phase']['position_f64le_hex']='00'
        elif name=='nonfinite':r['phase']['position_f64le_hex']=np.array([float('nan')],dtype='<f8').tobytes().hex()+r['phase']['position_f64le_hex'][16:]
        elif name=='speed':r['phase']['velocity_f64le_hex']=np.array([1e9],dtype='<f8').tobytes().hex()+r['phase']['velocity_f64le_hex'][16:]
        elif name=='mass':r['particles']['mass_f64le_hex']='0000000000000000'+r['particles']['mass_f64le_hex'][16:]
        elif name=='controls':r['controls']['electric_acting']=1
        elif name=='dt':r['dt_s']=False
        elif name=='source':r['model']['sources']=[{'id':'bad'}]
        elif name=='exclusion':
            r['model']['sources']=[{'id':'excluded','position_m':[0,0,0],'exclusion_radius_m':.1,'charge_C':0,'magnetic_moment_A_m2':[0,0,0]}]
            r['phase']['position_f64le_hex']='0'*48+r['phase']['position_f64le_hex'][48:]
        elif name=='extra':r['gravity']=True
        r.pop('sha256');r['sha256']=hashlib.sha256(canonical(r)).hexdigest();path.write_bytes(canonical(r))
        try:load(path)
        except (ValueError,ArithmeticError,TypeError):refusals.append(name)
        else:raise AssertionError(name)
    path.write_bytes(b'{"schema":1,"schema":1}')
    try:load(path)
    except ValueError:refusals.append('duplicate_key')
    else:raise AssertionError('duplicate key')
report={'status':'isolated_cloud_checkpoint_exact_buffers_future_and_resealed_domain_refusals_verified','cases':cases,'refusals':refusals,'scientific_generation':generation(),'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (*STAGE.glob('*.py'),STAGE/'constants.json',Path(__file__))},'scope':'Isolated schema1 cloud checkpoint. No worker/UI/native transport or implicit gravity checkpoint compatibility.'}
(ROOT/'evidence/em-cloud-checkpoint-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('scientific_generation','source_sha256')},indent=2))
