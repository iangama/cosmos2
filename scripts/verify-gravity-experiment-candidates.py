"""Independent ODE and convergence for locally selected point-mass experiences."""
from pathlib import Path
import json,math,sys,time
import numpy as np
from scipy.integrate import solve_ivp
import rebound
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from physics import PHYSICAL_SCALE as UNITS
source=json.loads((ROOT/'output/gravity-experiment-search.json').read_text());scale=.01
models={}
for key,value in source['candidates'].items():
 models[key]={'initial':[{**b,'mass':b['mass']*scale**3,'position':[x*scale for x in b['position']],'velocity':[x*scale for x in b['velocity']]} for b in value['initial']],'horizon':120,'source_parameters':value['parameters']}
s=rebound.Simulation();s.G=1;s.add(m=.8);s.add(m=.2,a=-2,e=1.6,f=-1.7,inc=.3);s.move_to_com();models['flyby']={'initial':[{'mass':p.m*scale**3,'position':[x*scale for x in p.xyz],'velocity':[x*scale for x in p.vxyz]} for p in s.particles],'horizon':20,'source_parameters':{'a':-2,'eccentricity':1.6,'true_anomaly':-1.7,'inclination':.3}}
def simulation(model,epsilon):
 s=rebound.Simulation();s.G=1;s.integrator='ias15';s.integrator.epsilon=epsilon;s.exit_min_distance=1e-12
 for b in model['initial']:
  r,v=b['position'],b['velocity'];s.add(m=b['mass'],x=r[0],y=r[1],z=r[2],vx=v[0],vy=v[1],vz=v[2])
 return s
reports=[]
for kind,model in models.items():
 masses=np.array([b['mass'] for b in model['initial']]);n=len(masses);r=np.array([b['position'] for b in model['initial']]);v=np.array([b['velocity'] for b in model['initial']]);initial=np.concatenate((r.ravel(),v.ravel()));times=[model['horizon']*2/3,model['horizon']]
 def rhs(t,y):
  r=y[:3*n].reshape(n,3);v=y[3*n:].reshape(n,3);a=np.zeros((n,3))
  for i in range(n):
   for j in range(n):
    if i!=j:
     d=r[j]-r[i];a[i]+=masses[j]*d/np.linalg.norm(d)**3
  return np.concatenate((v.ravel(),a.ravel()))
 reference=solve_ivp(rhs,[0,model['horizon']],initial,method='DOP853',rtol=2e-13,atol=2e-17,max_step=.03,dense_output=True);assert reference.success
 minsep=min(float(np.min(np.linalg.norm(reference.y[3*i:3*i+3]-reference.y[3*j:3*j+3],axis=0))) for i in range(n) for j in range(i));peak=float(np.max(np.linalg.norm(reference.y[3*n:].reshape(n,3,-1),axis=1)))*UNITS['velocity_unit_m_s']
 variants=[]
 for epsilon in [1e-9,1e-12]:
  s=simulation(model,epsilon);baseline=s.energy();records=[]
  for t in times:
   s.integrate(t);actual=np.array([p.xyz for p in s.particles]);expected=reference.sol(t)[:3*n].reshape(n,3);difference=float(np.max(abs(actual-expected)))*1e9
   pairs=[]
   for i in range(n):
    for j in range(i):
     p,q=s.particles[i],s.particles[j];mu=p.m+q.m;distance=math.dist(p.xyz,q.xyz);energy=.5*math.dist(p.vxyz,q.vxyz)**2-mu/distance
     if energy<0:pairs.append((-mu/(2*energy),j,i))
   record={'time':t,'independent_position_max_component_difference_m':difference,'energy_relative_drift':abs((s.energy()-baseline)/baseline)}
   if kind=='flyby':assert not pairs;record['positive_pair_energy']=True
   else:
    a,i,j=min(pairs);k=next(k for k in range(n) if k not in [i,j]);p,q,e=[s.particles[x] for x in [i,j,k]];m=p.m+q.m;center=(p.m*np.array(p.xyz)+q.m*np.array(q.xyz))/m;velocity=(p.m*np.array(p.vxyz)+q.m*np.array(q.vxyz))/m;dr=np.array(e.xyz)-center;dv=np.array(e.vxyz)-velocity;outer=.5*float(dv@dv)-(m+e.m)/np.linalg.norm(dr);ratio=np.linalg.norm(dr)/a
    assert [i,j]==([0,2] if kind=='capture' else [0,1]) and outer>0 and float(dr@dv)>0 and ratio>30
    record.update(pair=[i,j],escaper=k,outer_specific_energy_canonical=outer,binary_a_canonical=a,separation_over_a=float(ratio))
   assert difference<1e5 and record['energy_relative_drift']<1e-8,(kind,epsilon,record);records.append(record)
  variants.append({'epsilon':epsilon,'samples':records})
 assert minsep>1e-10 and peak<1e7,(kind,minsep,peak)
 reports.append({'model':kind,'minimum_accepted_ODE_separation_m':minsep*1e9,'peak_accepted_ODE_speed_m_s':peak,'variants':variants,'ODE_steps':len(reference.t)})
 print(json.dumps(reports[-1]),flush=True)
report={'models':reports,'scaling':{'length':scale,'mass':scale**3,'velocity':scale,'time':1.},'scope':'Local Newtonian point-mass initial conditions; no observed bodies. Finite two-epoch hierarchy/escape evidence, not eternal capture.'}
(ROOT/'evidence/gravity-experiment-candidates-check.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'output/gravity-experiment-candidates.json').write_text(json.dumps({'models':models,'scaling':report['scaling']},indent=2)+'\n')
