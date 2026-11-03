"""Analytic Lorentz trajectories and independent DOP853 for nonuniform fields."""
from pathlib import Path
import hashlib
import itertools
import json
import math
import sys
import numpy as np
from scipy.integrate import solve_ivp

ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/c212-em-staging';sys.path.insert(0,str(STAGE))
from em_fields import Model,Source,K_E,lorentz,SPEED_LIMIT_M_S
from em_particles import Phase,boris_step,DomainExit

def run(model,phase,charge,mass,dt,steps,**controls):
    energy=[];work=0.;initial=phase
    for _ in range(steps):
        phase,diagnostic=boris_step(model,phase,charge,mass,dt,**controls)
        work+=diagnostic['electric_work_J'];energy.append(.5*mass*math.hypot(*phase.velocity_m_s)**2)
    return phase,energy,work

# Both charge signs, arbitrary E direction: exact constant acceleration at
# synchronized output times. Ballistic case is the same initial phase.
electric=Model(uniform_E_V_m=(.3,-.5,.8));initial=Phase((1,2,3),(3,-2,1))
uniform_E_error=0.
for sign in (-1,1):
    end,energy,work=run(electric,initial,sign,2,.003,500)
    t=1.5;a=sign*np.array(electric.uniform_E_V_m)/2
    expected=np.array(initial.position_m)+t*np.array(initial.velocity_m_s)+.5*a*t*t
    uniform_E_error=max(uniform_E_error,float(np.linalg.norm(np.array(end.position_m)-expected)))
    assert np.linalg.norm(np.array(end.position_m)-expected)<1e-11
    assert np.linalg.norm(np.array(end.velocity_m_s)-(np.array(initial.velocity_m_s)+t*a))<1e-11
    assert abs((energy[-1]-.5*2*math.hypot(*initial.velocity_m_s)**2)-work)<1e-10

# Ten full gyro periods, with observations at quarter-periods to avoid a
# closure-only check. The same analytic solution covers E x B drift.
refinements={};max_energy_drift=0.;crossed_drift_error=0.
for electric_x in (0.,.2):
    model=Model(uniform_E_V_m=(electric_x,0,0),uniform_B_T=(0,0,1))
    errors=[]
    for samples in (500,1000,2000):
        dt=2*math.pi/samples;phase=Phase((0,0,0),(1,0,.3));worst=0.;max_K=0.;work=0.
        for i in range(10*samples):
            phase,d=boris_step(model,phase,1,1,dt);work+=d['electric_work_J']
            K=.5*math.hypot(*phase.velocity_m_s)**2;max_K=max(max_K,abs(K-.545))
            if (i+1)%(samples//4)==0 or i+1==10*samples:
                t=(i+1)*dt
                expected=np.array([math.sin(t)+electric_x*(1-math.cos(t)),math.cos(t)-1+electric_x*math.sin(t)-electric_x*t,.3*t])
                expected_v=np.array([math.cos(t)+electric_x*math.sin(t),-math.sin(t)+electric_x*math.cos(t)-electric_x,.3])
                worst=max(worst,float(np.linalg.norm(np.array(phase.position_m)-expected)),float(np.linalg.norm(np.array(phase.velocity_m_s)-expected_v)))
        errors.append(worst)
        if electric_x==0:
            max_energy_drift=max(max_energy_drift,max_K/.545);assert max_K/.545<1e-10
        else:
            assert abs((K-.545)-work)<1e-10
            crossed_drift_error=abs(phase.position_m[1]/(10*2*math.pi)+electric_x)/electric_x
    assert errors[-1]<1e-3 and errors[0]/errors[1]>3.9 and errors[1]/errors[2]>3.9
    refinements[str(electric_x)]=errors
assert crossed_drift_error<1e-3

# Nonuniform field: independent adaptive high-order integration of the ODE.
# This fixture tests coupled E and B, not just the uniform closed form.
model=Model((Source('q',(0,0,0),.1,-1e-9,(0,0,.3)),),uniform_B_T=(0,0,.02))
initial=Phase((2,0,.3),(0,.6,.1));duration=4.
def derivative(t,y):
    # Independent expressions for the fixed fixture; does not call Model or lorentz.
    x=y[:3];v=y[3:];r=np.linalg.norm(x);n=x/r
    from em_fields import MU_0
    E=K_E*(-1e-9)*x/r**3;moment=np.array([0,0,.3])
    B=np.array([0,0,.02])+MU_0/(4*math.pi)*(3*n*np.dot(moment,n)-moment)/r**3
    return np.concatenate((v,.1*(E+np.cross(v,B))))
reference=solve_ivp(derivative,(0,duration),[*initial.position_m,*initial.velocity_m_s],method='DOP853',rtol=2e-12,atol=2e-13)
assert reference.success
nonuniform_errors=[]
for steps in (200,400,800):
    phase,_,_=run(model,initial,.1,1,duration/steps,steps)
    error=float(np.linalg.norm(np.array([*phase.position_m,*phase.velocity_m_s])-reference.y[:,-1]));nonuniform_errors.append(error)
assert nonuniform_errors[-1]<1e-5 and nonuniform_errors[0]/nonuniform_errors[1]>3.8 and nonuniform_errors[1]/nonuniform_errors[2]>3.8

controls=[]
model=Model(uniform_E_V_m=(.1,0,0),uniform_B_T=(0,0,1));phase=Phase((0,0,0),(1,0,0))
for electric,magnetic in itertools.product((False,True),repeat=2):
    end,_,_=run(model,phase,1,1,.001,100,electric_acting=electric,magnetic_acting=magnetic)
    if not electric and not magnetic:assert np.linalg.norm(np.array(end.position_m)-[.1,0,0])<1e-14 and end.velocity_m_s==phase.velocity_m_s
    controls.append({'electric':electric,'magnetic':magnetic,'final_position_m':end.position_m})

# A drift that enters and exits an exclusion during one trial is rejected,
# despite all proposed endpoints lying outside the forbidden sphere.
obstacle=Model((Source('excluded',(0,0,0),.1),));old=Phase((-1,0,0),(4,0,0))
try:boris_step(obstacle,old,0,1,1)
except DomainExit:pass
else:raise AssertionError('Tunneled through excluded source')
assert old==Phase((-1,0,0),(4,0,0))
rejected=0
for call in (lambda:boris_step(model,phase,1,1,0),lambda:boris_step(model,phase,1,0,.01),
    lambda:boris_step(model,phase,1,1,1),lambda:Phase((0,0,0),(2*SPEED_LIMIT_M_S,0,0))):
    try:call()
    except ValueError:rejected+=1
    else:raise AssertionError('Unsupported trial accepted')
report={'status':'isolated_synchronized_Boris_dynamics_verified_not_installed',
    'uniform_E_max_position_error_m':uniform_E_error,'ten_period_uniform_refinement_errors_m_and_m_s':refinements,
    'pure_B_max_relative_energy_drift':max_energy_drift,'crossed_fields_mean_drift_relative_error':crossed_drift_error,
    'nonuniform_vs_independent_DOP853_refinement_errors':nonuniform_errors,'physical_controls':controls,
    'source_exclusion_crossing_refused_without_state_mutation':True,'invalid_trials_refused':rejected,
    'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (STAGE/'em_fields.py',STAGE/'em_particles.py',STAGE/'constants.json',Path(__file__))},
    'scope':'Single nonrelativistic test particle in fixed SI fields; synchronized phase, fixed dt, CPU fixtures only. No worker/checkpoint/native/UI/population performance acceptance.'}
(ROOT/'evidence/em-particle-dynamics-check.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps(report,indent=2,allow_nan=False))
