"""Independent dipole formulas, operator ledger, mirror and integration checks."""
from pathlib import Path
import copy
import itertools
import json
import math
import sys
import time

import numpy as np
from scipy.constants import elementary_charge as e, proton_mass as m
from scipy.integrate import solve_ivp

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from forces import evaluate,normalize
from dipole import field,basis,integrate,RADIUS_M as R,GM_EARTH

started=time.perf_counter()
p=normalize({'scenario':'dipole'})['parameters']
baseline=evaluate({'scenario':'dipole'})
result=baseline['result'];read=result['particle_readings']
axis=np.array([0.,0.,1.]);eq=p['B_equator_uT']*1e-6
# Independent spherical components: B_r=2C cos(theta)/r^3,
# B_theta=C sin(theta)/r^3, then project into fixed Cartesian axes.
def spherical_field(x):
    x=np.asarray(x);radius=np.linalg.norm(x);theta=math.acos(x[2]/radius);phi=math.atan2(x[1],x[0])
    radial=np.array([math.sin(theta)*math.cos(phi),math.sin(theta)*math.sin(phi),math.cos(theta)])
    polar=np.array([math.cos(theta)*math.cos(phi),math.cos(theta)*math.sin(phi),-math.sin(theta)])
    return eq/radius**3*(2*math.cos(theta)*radial+math.sin(theta)*polar)
field_errors=[];gradient_errors=[]
for point in ([4,0,0],[0,0,3],[2,-1,1],[1.5,.2,-2],[0,0,-6]):
    x=np.array(point,dtype=float);b=field(x,eq,axis);ref=spherical_field(x)
    error=np.linalg.norm(b-ref)/np.linalg.norm(ref);assert error<1e-14;field_errors.append(error)
    h=1e-4;unit=np.eye(3)
    jac=np.column_stack([(field(x+h*d,eq,axis)-field(x-h*d,eq,axis))/(2*h) for d in unit])
    scale=np.linalg.norm(b)/np.linalg.norm(x)
    curl=np.array([jac[2,1]-jac[1,2],jac[0,2]-jac[2,0],jac[1,0]-jac[0,1]])
    error=max(abs(np.trace(jac)),np.linalg.norm(curl))/scale;assert error<1e-7;gradient_errors.append(error)
    assert np.allclose(field(2*x,eq,axis),b/8,rtol=1e-14,atol=1e-22)
e1,e2,tilted=basis(37);rotation=np.column_stack((e1,e2,tilted))
assert np.allclose(field(rotation@np.array([2.,1.,3.]),eq,tilted),rotation@field([2,1,3],eq,axis),rtol=1e-14)
for line in result['dipole']['field_lines']:
    a=np.array(line);tangent=a[2:]-a[:-2];b=field(a[1:-1],eq,axis)
    error=np.linalg.norm(np.cross(tangent,b),axis=1)/(np.linalg.norm(tangent,axis=1)*np.linalg.norm(b,axis=1))
    assert np.max(error)<.002  # finite chord vs exact tangent

cases=[]
for magnetic,gravitational in itertools.product((False,True),repeat=2):
    controls={'electromagnetic':{'acting':magnetic},'gravity':{'acting':gravitational}}
    r=evaluate({'scenario':'dipole','controls':controls})['result'];v=np.array(r['particle_readings']['velocity_m_s'])
    b=np.array(r['particle_readings']['magnetic_field_T']);x=np.array(r['positions'])*R
    fm=e*np.cross(v,b)*magnetic;fg=-m*GM_EARTH*x/np.linalg.norm(x,axis=1)[:,None]**3*gravitational
    assert np.allclose(fm,r['particle_readings']['magnetic_force_N'],rtol=1e-13,atol=1e-32)
    assert np.allclose(fg,r['particle_readings']['gravity_force_N'],rtol=1e-13,atol=1e-36)
    power=np.sum(fm*v,axis=1);scale=np.linalg.norm(fm,axis=1)*np.linalg.norm(v,axis=1)
    assert np.max(np.abs(power)/np.maximum(scale,1e-100))<1e-15
    assert r['dipole']['energy_residual']<1e-7
    assert r['reference']==result['reference'] and r['field']==[{**f,'applied_vector':(np.array(f['vector'])*(magnetic if f['force']=='electromagnetic' else gravitational)).tolist()} for f in result['field']]
    if not magnetic and not gravitational:
        expected=x[0]+np.array(r['time_s'])[:,None]*v[0]
        assert np.max(np.linalg.norm(x-expected,axis=1))/R<1e-12
        assert r['dipole']['status']=='outer_boundary'
        assert abs(np.linalg.norm(x[-1])/R-10)<1e-12
    cases.append({'magnetic':magnetic,'gravity':gravitational,'energy_error':r['dipole']['energy_residual'],'status':r['dipole']['status']})
for force,effect in [('gravity','orbital_acceleration'),('electromagnetic','magnetic_deflection')]:
    master=evaluate({'scenario':'dipole','controls':{force:{'acting':False}}})
    effect_off=evaluate({'scenario':'dipole','controls':{force:{'effects':{effect:False}}}})
    assert master['result']==effect_off['result'] and master['physics_sha256']==effect_off['physics_sha256']
hidden=evaluate({'scenario':'dipole','controls':{'gravity':{'visible':False},'electromagnetic':{'visible':False}}})
assert hidden['result']==result and hidden['physics_sha256']==baseline['physics_sha256']

# Mirror location compared to the independent adiabatic relation, without
# fitting the Lorentz trajectory to it. Full gyro-motion remains in the solver.
x=np.array(result['positions']);latitude=np.degrees(np.arcsin(x[:,2]/np.linalg.norm(x,axis=1)))
mirror_error=abs(np.max(np.abs(latitude))-result['reference']['adiabatic_mirror_latitude_deg'])
assert result['dipole']['parallel_reversals']>=1 and mirror_error<.2
refined=integrate(p,rtol=2e-12)
position_refinement=float(np.max(np.linalg.norm(refined['states'][:,:3]-x,axis=1)))
assert position_refinement<1e-6

# Independent RK45, spherical B and SI variables over the first five seconds.
v0=np.array(read['velocity_m_s'][0]);initial=np.concatenate((x[0]*R,v0))
def rhs(t,state):
    pos,vel=state[:3],state[3:];b=spherical_field(pos/R)
    return np.concatenate((vel,e/m*np.cross(vel,b)-GM_EARTH*pos/np.linalg.norm(pos)**3))
times=np.linspace(0,5,61)
ref=solve_ivp(rhs,[0,5],initial,method='RK45',rtol=2e-11,atol=[1e-5]*3+[1e-6]*3,t_eval=times)
assert ref.success
short=integrate({**p,'duration_s':5})
# Compare at the exact 241 exported times subset: every4th state is1/12s.
rk_error=float(np.max(np.linalg.norm(ref.y[:3].T/R-short['states'][::4,:3],axis=1)))
assert rk_error<1e-6

# Local uniform-field limit improves as spatial/time extent contracts.
local_errors=[]
for duration in (.002,.001):
    run=integrate({**p,'duration_s':duration},gravitational=False)
    omega=-e*eq/(m*p['initial_radius_R']**3);vperp=v0[1];vz=v0[2]
    t=run['times'];exact=np.column_stack((p['initial_radius_R']+vperp*(1-np.cos(omega*t))/(omega*R),vperp*np.sin(omega*t)/(omega*R),vz*t/R))
    error=float(np.max(np.linalg.norm(run['states'][:,:3]-exact,axis=1)));assert error<1e-8;local_errors.append(error)
assert local_errors[1]<local_errors[0]/5

boundary=integrate({**p,'initial_radius_R':2.5,'pitch_deg':5,'B_equator_uT':5,'duration_s':10})
assert boundary['status']=='inner_boundary' and abs(np.linalg.norm(boundary['states'][-1,:3])-1)<1e-10
try:integrate({**p,'initial_radius_R':2.5,'B_equator_uT':40,'duration_s':50,'pitch_deg':15})
except ValueError:budget_rejected=True
else:raise AssertionError('Expected explicit gyro budget refusal')
assert json.loads(json.dumps(baseline,allow_nan=False))==baseline
report={'model_id':baseline['scientific_contract']['model_id'],'scientific_contract':baseline['scientific_contract'],
        'field_relative_error_max':max(field_errors),'div_curl_normalized_error_max':max(gradient_errors),
        'operator_cases':cases,'master_and_effect_equivalent':True,'visibility_preserves_physics':True,
        'mirror_latitude_error_deg':mirror_error,'dop853_refinement_position_R':position_refinement,
        'independent_rk45_position_R':rk_error,'local_uniform_errors_R':local_errors,
        'inner_outer_boundaries':True,'budget_refusal':budget_rejected,'trace_samples':result['dipole']['trace_samples'],
        'elapsed_s':time.perf_counter()-started,'scope':'prescribed ideal dipole, classical test particle; adiabatic comparison, not IGRF/plasma model'}
(ROOT/'evidence/dipole-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='scientific_contract'},indent=2))
