"""Restore and evolve SI cloud checkpoints in a fresh Python process."""
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/c212-em-cloud-checkpoint-staging';sys.path.insert(0,str(STAGE))
from cloud_checkpoint import save,load,generation
from cloud_core import System,Phase
from em_fields import Model,Source
def future(path,steps):
    s,p,dt,acting=load(path);digest=hashlib.sha256()
    for _ in range(steps):
        p,d=s.step(p,dt,**acting)
        for v in (p._x,p._v,d['electric_work_J'].tobytes(),d['kinetic_change_J'].tobytes()):digest.update(v)
    return {'all_steps_sha256':digest.hexdigest(),'final_time_s':p.time_s,'generation':generation()}
if len(sys.argv)>1:print(json.dumps(future(Path(sys.argv[1]),int(sys.argv[2]))))
else:
    results=[]
    with tempfile.TemporaryDirectory() as tmp:
        for n,steps in ((128,777),(10000,64)):
            i=np.arange(n);x=np.column_stack((np.sin(i),np.cos(i),np.ones(n)*5));v=x*.01
            model=Model((Source('dipole',(0,0,0),.1,1e-9,(1e4,0,2e4)),),(.1,0,0),(0,0,.5)) if n<10000 else Model(uniform_B_T=(0,0,.5))
            s=System(model,np.where(i%2,1.,-1.),np.ones(n));p=Phase(x,v);dt=.002;acting={'electric_acting':True,'magnetic_acting':True}
            for _ in range(17):p,_=s.step(p,dt,**acting)
            path=Path(tmp)/f'{n}.json';save(path,s,p,dt,acting);before=path.read_bytes();reference=future(path,steps)
            child=subprocess.run([sys.executable,str(Path(__file__).resolve()),str(path),str(steps)],check=True,capture_output=True,text=True,encoding='utf-8');assert reference==json.loads(child.stdout) and path.read_bytes()==before
            results.append({'count':n,'exact_future_steps_in_fresh_process':steps,'checkpoint_preserved':True,'future':reference})
    report={'status':'isolated_cloud_checkpoint_fresh_process_future_exact','cases':results,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (*STAGE.glob('*.py'),STAGE/'constants.json',Path(__file__))},'scope':'Fresh Python checkpoint restore only, not an operational worker, native transport, UI or native throughput acceptance.'}
    (ROOT/'evidence/em-cloud-checkpoint-process-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'cases':len(results)}))
