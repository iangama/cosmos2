"""Local initial-condition search; candidates are measured models, not observed systems."""
from pathlib import Path
import itertools,json,math,sys,time
import rebound
ROOT=Path(__file__).resolve().parents[1]

def seed(phase,impact,speed):
 s=rebound.Simulation();s.G=1;s.integrator='ias15';s.integrator.epsilon=1e-11;s.exit_min_distance=1e-8
 c,t=math.cos(phase),math.sin(phase)
 s.add(m=.8,x=-.2*c,y=-.2*t,vx=.2*t,vy=-.2*c)
 s.add(m=.2,x=.8*c,y=.8*t,vx=-.8*t,vy=.8*c)
 s.add(m=.4,x=-12,y=impact,vx=speed);s.move_to_com();return s

def phase(s):return [{'mass':p.m,'position':[p.x,p.y,p.z],'velocity':[p.vx,p.vy,p.vz]} for p in s.particles]
def assess(s):
 pairs=[]
 for i,j in [(0,1),(0,2),(1,2)]:
  p,q=s.particles[i],s.particles[j];r=math.dist(p.xyz,q.xyz);v=math.dist(p.vxyz,q.vxyz);energy=.5*v*v-(p.m+q.m)/r
  if energy<0:
   a=-(p.m+q.m)/(2*energy);pairs.append((a,i,j))
 if not pairs:return None
 a,i,j=min(pairs);k=next(k for k in range(3) if k not in (i,j));p,q,esc=[s.particles[x] for x in (i,j,k)];m=p.m+q.m
 center=[(p.m*x+q.m*y)/m for x,y in zip(p.xyz,q.xyz)];velocity=[(p.m*x+q.m*y)/m for x,y in zip(p.vxyz,q.vxyz)];r=[x-y for x,y in zip(esc.xyz,center)];v=[x-y for x,y in zip(esc.vxyz,velocity)];distance=math.hypot(*r);outerenergy=.5*sum(x*x for x in v)-(m+esc.m)/distance;radial=sum(x*y for x,y in zip(r,v))/distance
 return {'pair':[i,j],'escaper':k,'binary_a':a,'outer_specific_energy':outerenergy,'outer_separation':distance,'separation_over_a':distance/a,'outward':radial>0}
found={};attempts=0
for speed,impact,phi in itertools.product([.6,.25],[.3,.7,1.1,1.5,2.,-1.],[(i+.2)*math.pi/5 for i in range(10)]):
 s=seed(phi,impact,speed);initial=phase(s);energy=s.energy();began=time.perf_counter();aborted=False
 def heartbeat(p):
  global aborted
  if time.perf_counter()-began>.3:aborted=True;p.contents.stop()
 s.heartbeat=heartbeat
 try:s.integrate(80)
 except (rebound.Encounter,rebound.GenericError):continue
 if aborted:continue
 first=assess(s)
 if not first or not first['outward'] or first['outer_specific_energy']<=0 or first['separation_over_a']<30:continue
 s.integrate(120)
 if aborted:continue
 final=assess(s);attempts+=1
 if not final or final['pair']!=first['pair'] or final['escaper']!=first['escaper'] or final['outer_specific_energy']<=0 or not final['outward']:continue
 kind='capture' if speed==.6 and final['pair']==[0,2] else 'ejection' if speed==.25 else None
 if kind and kind not in found:
  found[kind]={'parameters':{'phase_rad':phi,'impact_canonical':impact,'incoming_speed_canonical':speed},'initial':initial,'initial_energy':energy,'at80':first,'at120':final,'final_energy_relative_drift':abs((s.energy()-energy)/energy)};print(json.dumps({kind:found[kind]}),flush=True)
 if len(found)==2:break
report={'scope':'Local selected Newtonian point-mass models; not observational systems or universal outcomes. Full independent verification required before catalog.','candidates':found,'qualified_attempts':attempts}
(ROOT/'output/gravity-experiment-search.json').write_text(json.dumps(report,indent=2)+'\n');assert len(found)==2,report
