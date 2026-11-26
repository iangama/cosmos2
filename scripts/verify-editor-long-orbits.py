"""100-period IAS15 editor orbits against independent CSPICE Kepler propagation."""
from pathlib import Path
import json,math,sys,tempfile
import numpy as np
import spiceypy as spice
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from session import Session
from physics import PHYSICAL_SCALE as U
from orbital_diagnostics import integrals
results=[]
with tempfile.TemporaryDirectory() as temp:
 for eccentricity in (0.,.6):
  m1,m2=.7,.3;mu=m1+m2;a=1.;period=2*math.pi*math.sqrt(a**3/mu);elements=[a*(1-eccentricity),eccentricity,.37,.49,.18,.27,0.,mu]
  relative=np.array(spice.conics(elements,0));initial=[]
  for name,mass,factor in [('Primary',m1,-m2/mu),('Companion',m2,m1/mu)]:initial.append({'name':name,'mass':mass,'position':(relative[:3]*factor).tolist(),'velocity':(relative[3:]*factor).tolist()})
  s=Session(Path(temp)/str(eccentricity),2);s._new_population(initial);maxpos=maxenergy=maxmomentum=maxangular=0.
  baseline=s.sim.copy();baseline.integrator.epsilon=1e-12;maxrefine=0.
  for t in np.linspace(0,100*period,201):
   s.sim.integrate(float(t));baseline.integrate(float(t));expected=np.array(spice.conics(elements,float(t)))
   bodies=s.state()['bodies'];actual=np.array([bodies[1][k][i]-bodies[0][k][i] for k in ['position','velocity'] for i in range(3)]);strict=np.array([getattr(baseline.particles[1],k)-getattr(baseline.particles[0],k) for k in ['x','y','z','vx','vy','vz']])
   maxpos=max(maxpos,float(np.linalg.norm(actual[:3]-expected[:3]))/a);maxrefine=max(maxrefine,float(np.linalg.norm(actual[:3]-strict[:3]))/a);c=s.state()['conservation'];maxenergy=max(maxenergy,s.state()['energy_error']);maxmomentum=max(maxmomentum,c['momentum_error_normalized']);maxangular=max(maxangular,c['angular_momentum_error_normalized'])
  assert maxpos<=1e-5 and maxenergy<=1e-8 and maxmomentum<=1e-10 and maxangular<=1e-10,(maxpos,maxenergy,maxmomentum,maxangular)
  s.save();frozen=s.state();s.sim.integrate(s.sim.t+.1);s.load();assert s.state()['bodies']==frozen['bodies'] and s.state()['conservation']==frozen['conservation']
  results.append({'eccentricity':eccentricity,'periods':100,'samples':201,'mass_ratio_m2_m1':m2/m1,'CSPICE_position_difference_over_a_max':maxpos,'position_difference_m_max':maxpos*a*U['length_unit_m'],'IAS15_epsilon1e_12_refinement_difference_over_a_max':maxrefine,'energy_relative_error_max':maxenergy,'momentum_normalized_error_max':maxmomentum,'angular_momentum_normalized_error_max':maxangular,'checkpoint_after100_periods_exact':True})
report={'oracle':'CSPICE conics; independent Kepler propagation in tilted inertial axes','IAS15_epsilon':1e-9,'cases':results,'scientific_generation':s.state()['scientific_generation']}
(ROOT/'evidence/editor-long-orbits-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
