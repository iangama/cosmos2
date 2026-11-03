"""Vector conics against CSPICE, REBOUND and conserved two-body integration."""
from pathlib import Path
import json,math,sys
import numpy as np
import rebound,spiceypy as spice
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from orbital_diagnostics import pair,integrals
from physics import PHYSICAL_SCALE as U
results=[];worst_a=0.;worst_e=0.;worst_curve=0.;worst_energy=0.
for name,e,a,inc in [('circular',0,2,0),('inclined',.3,2,.7),('retrograde',.2,3,2.8),('eccentric',.95,10,.3),('hyperbolic',1.5,-2,.8)]:
 s=rebound.Simulation();s.G=1;s.integrator='ias15';s.add(m=.7);s.add(m=.3,a=a,e=e,inc=inc,Omega=.4,omega=.6,f=.5);s.move_to_com()
 def bodies():return [{'id':str(i),'mass':p.m,'position':[p.x,p.y,p.z],'velocity':[p.vx,p.vy,p.vz]} for i,p in enumerate(s.particles)]
 b=bodies();d=pair(b,'1','0');r=np.array(b[1]['position'])-b[0]['position'];v=np.array(b[1]['velocity'])-b[0]['velocity'];mu=1.
 elements=spice.oscelt(np.concatenate((r*U['length_unit_m']/1000,v*U['velocity_unit_m_s']/1000)),0,U['nominal_GM_unit_m3_s2']/1e9)
 actual_a=d['semimajor_axis_m']/U['length_unit_m'];ae=abs(actual_a-a)/abs(a);ee=abs(d['eccentricity']-elements[1]);worst_a=max(worst_a,ae);worst_e=max(worst_e,ee);assert ae<1e-12 and ee<1e-12,(name,ae,ee)
 assert math.isclose(d['mu_m3_s2'],U['nominal_GM_unit_m3_s2']) and math.isclose(d['escape_speed_pair_m_s'],math.sqrt(2/np.linalg.norm(r))*U['velocity_unit_m_s'])
 curve=[np.array(p)-b[0]['position'] for segment in d['preview']['segments_model_units'] for p in segment];assert curve
 nearest=min(float(np.linalg.norm(x-r)) for x in curve);worst_curve=max(worst_curve,nearest*U['length_unit_m']);assert nearest<1e-12
 # Every displayed point satisfies the focus equation and lies in the orbital plane.
 h=np.cross(r,v);ev=np.array(d['eccentricity_vector']);p=d['parameter_m']/U['length_unit_m']
 for x in curve:
  radius=np.linalg.norm(x);assert abs(np.dot(x,h))<1e-12*radius*np.linalg.norm(h);assert abs(radius*(1+np.dot(ev,x/radius))-p)<1e-11*max(p,1)
 old=integrals(b,0);s.integrate(.5);new=integrals(bodies(),s.t);err=abs((new['energy']-old['energy'])/old['energy']);worst_energy=max(worst_energy,err);assert err<1e-12 and np.max(abs(np.array(new['momentum'])-old['momentum']))<1e-14 and np.max(abs(np.array(new['angular_momentum'])-old['angular_momentum']))<1e-13
 if e==0:assert not d['periapsis_direction_defined'] and not d['ascending_node_defined']
 results.append({'case':name,'classification':d['classification'],'semimajor_relative_difference':ae,'eccentricity_CSPICE_difference':ee,'closed':d['preview']['closed'],'clipped':d['preview']['clipped'],'energy_relative_drift':err})
# Near parabola and radial states retain direct observables without inventing unstable angles.
base=[{'id':'a','mass':.7,'position':[0,0,0],'velocity':[0,0,0]},{'id':'b','mass':.3,'position':[1,0,0],'velocity':[0,math.sqrt(2),0]}]
d=pair(base,'b','a');assert d['classification']=='near_parabolic' and d['semimajor_axis_m'] is None and d['period_s'] is None and not d['preview']['closed']
base[1]['velocity']=[.1,0,0];d=pair(base,'b','a');assert d['classification']=='radial_degenerate' and d['inclination_rad'] is None and not d['preview']['segments_model_units']
# Galilean transformation changes the COM, preserving relative pair conic.
base[1]['velocity']=[0,1,0];old=pair(base,'b','a');shift=np.array([3.,-4.,2.]);boost=np.array([.2,-.3,.4]);changed=[dict(b,position=(np.array(b['position'])+shift).tolist(),velocity=(np.array(b['velocity'])+boost).tolist()) for b in base];new=pair(changed,'b','a');assert abs(old['eccentricity']-new['eccentricity'])<1e-14
before=integrals(base,0);after=integrals(changed,0);assert np.max(abs(np.array(after['barycenter'])-before['barycenter']-shift))<1e-14
for ids in [('a','a'),('missing','a')]:
 try:pair(base,*ids)
 except ValueError:pass
 else:raise AssertionError(ids)
report={'cases':results,'maximum_semimajor_relative_difference':worst_a,'maximum_eccentricity_CSPICE_difference':worst_e,'maximum_curve_current_point_difference_m':worst_curve,'maximum_two_body_energy_relative_drift':worst_energy,'comparable_masses_mu_includes_both':True,'near_parabola_and_radial_degeneracy_explicit':True,'Galilean_invariance':True,'scope':'Instantaneous pair conic/translation integrals; no long-term N-body/JPL prediction.'}
(ROOT/'evidence/orbital-diagnostics-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
