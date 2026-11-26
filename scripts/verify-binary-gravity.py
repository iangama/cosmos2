"""Independent inertial N-body comparison and differential-field checks."""
from pathlib import Path
import itertools
import json
import math
import sys
import numpy as np
import rebound

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from binary_gravity import field,lagrange_points,source_positions,integrate
from forces import evaluate,normalize

baseline=evaluate({'scenario':'binary'})['result'];mu=baseline['binary']['mu']
phases=np.array(baseline['phase_rad']);position=np.array(baseline['positions'])
velocity=np.array(baseline['velocities_rotating'])
sim=rebound.Simulation();sim.G=1;sim.integrator='ias15';sim.integrator.epsilon=1e-11
sim.add(m=1-mu,x=-mu,vy=-mu);sim.add(m=mu,x=1-mu,vy=1-mu)
sim.add(m=0,x=position[0,0],y=position[0,1],z=position[0,2],
        vx=velocity[0,0]-position[0,1],vy=velocity[0,1]+position[0,0],vz=velocity[0,2]);sim.N_active=2
independent=[]
for tau in phases:
    sim.integrate(tau);p=list(sim.particles)[2];independent.append([p.x,p.y,p.z])
inertial_error=float(np.max(np.abs(np.array(independent)-baseline['inertial_positions'])))
assert inertial_error<1e-8,inertial_error
assert baseline['binary']['jacobi_relative_error']<1e-8
p=np.array([.4,1.2,.3]);g,potential,tide,parts=field(p,mu);h=1e-5
gradient=np.array([(field(p+np.eye(3)[i]*h,mu)[1]-field(p-np.eye(3)[i]*h,mu)[1])/(2*h) for i in range(3)])
numerical=np.column_stack([(field(p+np.eye(3)[i]*h,mu)[0]-field(p-np.eye(3)[i]*h,mu)[0])/(2*h) for i in range(3)])
assert np.max(np.abs(gradient+g))<1e-9
assert np.max(np.abs(tide-numerical))<1e-9
assert abs(np.trace(tide))<1e-14
assert np.max(np.abs(g-parts.sum(axis=0)))<1e-15
for point in lagrange_points(mu):
    q=np.array(point['position']);assert np.linalg.norm(field(q,mu)[0]+[q[0],q[1],0])<1e-10
l4=np.array([.5-mu,math.sqrt(3)/2,0,0,0,0])
solution=integrate(l4,mu,4*math.pi)
assert np.max(np.abs(solution.y.T-l4))<1e-8
for first,second in itertools.product((False,True),repeat=2):
    request={'scenario':'binary','controls':{'gravity':{'effects':{'primary_attraction':first,'secondary_attraction':second}}}}
    result=evaluate(request)['result']
    assert result['reference']==baseline['reference']
    request['controls']['gravity']['visible']=False
    assert evaluate(request)['result']==result
    assert result['binary']['jacobi_relative_error']<1e-8
    if not(first or second):
        expected=position[0]+phases[:,None]*[velocity[0,0]-position[0,1],velocity[0,1]+position[0,0],velocity[0,2]]
        assert np.max(np.abs(np.array(result['inertial_positions'])-expected))<1e-8
off=evaluate({'scenario':'binary','controls':{'gravity':{'acting':False}}})['result']
assert off['binary']['gates']==[False,False] and off['reference']==baseline['reference']
heavy=evaluate({'scenario':'binary','parameters':{'primary_solar':2}})['result']
assert heavy['positions']==baseline['positions']
assert math.isclose(heavy['reference']['binary_period_s']*math.sqrt(2),baseline['reference']['binary_period_s'],rel_tol=1e-14)
assert math.isclose(heavy['reference']['probe']['potential_m2_s2'],baseline['reference']['probe']['potential_m2_s2']*2,rel_tol=1e-14)
close=integrate([1-mu+.025,0,0,-.2,0,0],mu,1)
assert close.t[-1]<1 and close.t_events[0].size==1
try:evaluate({'scenario':'binary','parameters':{'probe_x':1-mu,'probe_y':0,'probe_z':0}})
except ValueError:pass
else:raise AssertionError('Accepted a probe at a singular source')
json.dumps(baseline,allow_nan=False)
report={'inertial_rebound_max_position_error_separation':inertial_error,
        'jacobi_relative_error':baseline['binary']['jacobi_relative_error'],
        'potential_gradient_error':float(np.max(np.abs(gradient+g))),
        'tidal_gradient_error':float(np.max(np.abs(tide-numerical))),
        'vacuum_tidal_trace':float(np.trace(tide)),'lagrange_equilibria':5,
        'l4_equilibrium':True,'force_combinations':4,'all_off_ballistic_inertial':True,
        'reference_and_visibility_independent':True,'physical_mass_scaling':True,
        'exclusion_terminates_without_collision_claim':True,
        'scope':'Spatial circular restricted problem, no general N-body/GR/collision acceptance'}
(ROOT/'evidence/binary-gravity-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
