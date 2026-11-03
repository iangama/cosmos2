"""Vector J2 versus preserved scalar derivation, field derivatives and 128-body reaction."""
from pathlib import Path
import hashlib,json,math,sys,tempfile,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/('app' if '--installed' in sys.argv else 'output/c211-j2-vector')
sys.path[:0]=[str(SOURCE),str(ROOT/'output/c211-j2-vector'),str(ROOT/'app')]
from j2_field import correction,corrections
from scalar_reference import correction as reference
from session import Session
from physics import PHYSICAL_SCALE as U
import gravity_harmonics as harmonics
rng=np.random.default_rng(613492)
maxima={'potential_relative':0.,'g_relative':0.,'T_relative':0.,'gradient_relative':0.,'tensor_gradient_relative':0.}
for case in range(20):
 axis=rng.normal(size=3).tolist();points=rng.normal(size=(128,3));points*=rng.uniform(2e8,1e12,size=(128,1))/np.linalg.norm(points,axis=1)[:,None]
 GM=float(rng.uniform(1e14,1e20));R=1e8;j2=float(rng.uniform(-.01,.01));phi,g,T=corrections(GM,R,j2,axis,points,tensor=True)
 for i,x in enumerate(points):
  ref=reference(GM,R,j2,axis,x.tolist());values=[ref['potential_J_kg'],ref['acceleration_m_s2'],ref['tidal_tensor_s_2']]
  for key,a,b in zip(('potential_relative','g_relative','T_relative'),(phi[i],g[i],T[i]),values):
   # Scale by the model amplitude, avoiding false relative failures at true zeros.
   scale={'potential_relative':GM*abs(j2)*R**2/np.linalg.norm(x)**3,'g_relative':GM*abs(j2)*R**2/np.linalg.norm(x)**4,'T_relative':GM*abs(j2)*R**2/np.linalg.norm(x)**5}[key]
   error=float(np.linalg.norm(np.asarray(a)-np.asarray(b)))/scale;maxima[key]=max(maxima[key],error)
  if i==0:
   h=np.linalg.norm(x)*1e-5;df=np.empty(3);dg=np.empty((3,3))
   for k in range(3):
    delta=np.eye(3)[k]*h;a=correction(GM,R,j2,axis,(x+delta).tolist());b=correction(GM,R,j2,axis,(x-delta).tolist())
    df[k]=-(a['potential_J_kg']-b['potential_J_kg'])/(2*h);dg[:,k]=(np.asarray(a['acceleration_m_s2'])-b['acceleration_m_s2'])/(2*h)
   maxima['gradient_relative']=max(maxima['gradient_relative'],float(np.linalg.norm(df-g[i])/np.linalg.norm(g[i])))
   maxima['tensor_gradient_relative']=max(maxima['tensor_gradient_relative'],float(np.linalg.norm(dg-T[i])/np.linalg.norm(T[i])))
assert max(maxima[k] for k in ('potential_relative','g_relative','T_relative'))<2e-13,maxima
assert maxima['gradient_relative']<2e-8 and maxima['tensor_gradient_relative']<2e-8,maxima
rejected=0
for points in ([[0,0,0]],[[1e7,0,0]],[[float('nan'),0,0]],[],[[1e18,0,0]]):
 try:corrections(1e20,1e8,.002,[0,0,1],points)
 except ValueError:rejected+=1
 else:raise AssertionError('Invalid batch accepted')
with tempfile.TemporaryDirectory() as tmp:
 s=Session(Path(tmp),128);bs=s.state()['bodies']
 for i in range(4):
  radius=min(1e8,.1*U['length_unit_m']*min(math.dist(bs[i]['position'],b['position']) for b in bs if b['id']!=bs[i]['id']))
  s.set_j2({'system_id':s.system_id,'edit_token':s.edit_token,'revision':s.revision,'expected_time':s.sim.t,'frame':s.contract()['frame'],'body':bs[i]['id'],'parameters':{'j2':.002,'radius_eq_m':radius,'axis':[.3,-.4,.5],'provenance':'Synthetic vector validation'}})
 a,energy=harmonics.terms(s._physical_bodies());mass=np.asarray([p.m for p in s.sim.particles]);residual=np.sum(mass[:,None]*a,axis=0)
 recoil=float(np.linalg.norm(residual)/np.sum(np.linalg.norm(mass[:,None]*a,axis=1)));assert recoil<1e-14,recoil
 began=time.perf_counter()
 for _ in range(12):s.integrate(s.sim.t+1/30)
 elapsed=time.perf_counter()-began;state=s.state();assert state['energy_error']<1e-10 and state['conservation']['J2_axial_angular']['normalized_error']<1e-10
report={'status':'passed','source':str(SOURCE.relative_to(ROOT)),'hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (SOURCE/'j2_field.py',SOURCE/'gravity_harmonics.py',Path(__file__))},'points':2560,'maxima':maxima,'invalid_batches_rejected':rejected,'128_mass_four_source_recoil':recoil,'diagnostic_12_updates_wall_s':elapsed,'diagnostic_scope':'Isolated timing only; not native rate/frame acceptance','owner_pointer_sha256':hashlib.sha256((ROOT/'user/sessions/latest.json').read_bytes()).hexdigest()}
(ROOT/'evidence/j2-vector-kernel-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
