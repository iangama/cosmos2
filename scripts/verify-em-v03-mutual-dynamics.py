"""Electrostatic pair reactions, elliptic orbit, convergence and128-source invariants."""
from pathlib import Path
import hashlib
import json
import math
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/c212-em-v03-staging';sys.path.insert(0,str(STAGE))
from em_fields import K_E,SPEED_LIMIT_M_S
from em_particles import DomainExit
from em_mutual import System,Phase

q=math.sqrt(1/K_E)
system=System(('positive','negative'),(q,-q),(1,1),(.01,.01))
ecc=.4;radius=1-ecc;speed=.5*math.sqrt((1+ecc)/(1-ecc));period=4*math.pi
initial=Phase(((-radius,0,0),(radius,0,0)),((0,-speed,0),(0,speed,0)))
baseline=system.diagnostics(initial);errors=[];energy_errors=[];momentum_errors=[]
for steps in (1000,2000,4000):
    phase=initial;worst=0.;p_error=0.
    for index in range(10*steps):
        phase=system.step(phase,period/steps)
        if index%50==0 or index+1==10*steps:
            d=system.diagnostics(phase)
            worst=max(worst,abs(d['energy_J']-baseline['energy_J'])/baseline['energy_scale_J'])
            p_error=max(p_error,math.hypot(*d['momentum_kg_m_s']))
    error=float(np.linalg.norm(np.array(phase.position_m)-np.array(initial.position_m)))
    errors.append(error);energy_errors.append(worst);momentum_errors.append(p_error)
assert errors[0]/errors[1]>3.8 and errors[1]/errors[2]>3.8,errors
assert energy_errors[-1]<=1e-6 and max(momentum_errors)<=1e-10,energy_errors

# Exact force/potential special values and finite-difference consistency.
force,U=system.force_potential(initial.position_m)
assert abs(U+1/(2*radius))<1e-14 and np.allclose(force[0],-force[1],rtol=0,atol=0)
assert abs(force[0,0]-1/(2*radius)**2)<1e-14
point=np.array(initial.position_m);gradient=[]
for h in (1e-3,5e-4,2.5e-4):
    moved=point.copy();moved[0,0]+=h;_,up=system.force_potential(moved)
    moved[0,0]-=2*h;_,down=system.force_potential(moved)
    gradient.append(abs(-(up-down)/(2*h)-force[0,0])/abs(force[0,0]))
assert gradient[-1]<1e-6 and gradient[0]/gradient[-1]>10

# A nonsymmetric population of128 checks pair cancellation/torque as well
# as consistency between the force kernel and the reference field evaluator.
rng=np.random.default_rng(181026);positions=rng.normal(size=(128,3))*10
charges=rng.normal(size=128)*q;masses=rng.uniform(.3,3,128)
many=System(tuple(map(str,range(128))),tuple(charges),tuple(masses),tuple([1e-5]*128))
phase=Phase(tuple(map(tuple,positions)),tuple(map(tuple,rng.normal(size=(128,3))*.01)))
forces,potential=many.force_potential(positions);force_scale=sum(np.linalg.norm(f) for f in forces)
momentum_residual=float(np.linalg.norm(np.sum(forces,axis=0))/force_scale)
torque_residual=float(np.linalg.norm(np.sum(np.cross(positions,forces),axis=0))/sum(np.linalg.norm(x)*np.linalg.norm(f) for x,f in zip(positions,forces)))
assert momentum_residual<1e-14 and torque_residual<1e-14
field_error=0.
for i in range(128):
    reading=many.field_snapshot(phase,str(i)).evaluate(positions[i]);assert reading['valid']
    expected=charges[i]*np.array(reading['electric_field_V_m'])
    error=float(np.linalg.norm(forces[i]-expected)/(abs(charges[i])*reading['electric_scale_V_m']))
    field_error=max(field_error,error);assert error<1e-12

off=many.step(phase,.01,acting=False)
assert np.allclose(off.position_m,positions+.01*np.array(phase.velocity_m_s),rtol=0,atol=1e-14)
assert off.velocity_m_s==phase.velocity_m_s
assert many.field_snapshot(phase).evaluate((100,100,100))['electric_scale_V_m']>0

obstacle=System(('a','b'),(0,0),(1,1),(.1,.1))
old=Phase(((-1,0,0),(1,0,0)),((4,0,0),(-4,0,0)))
try:obstacle.step(old,1)
except DomainExit:pass
else:raise AssertionError('Pair tunneled through exclusion')
assert old.position_m==((-1.,0.,0.),(1.,0.,0.))
rejected=0
for call in (lambda:System(('a','a'),(1,1),(1,1),(.1,.1)),lambda:System(('a',),(1,),(0,),(.1,)),
    lambda:system.step(initial,0),lambda:system.step(initial,.01,acting=0),
    lambda:system.force_potential(((0,0,0),(0,0,0))),lambda:Phase(((0,0,0),),((2*SPEED_LIMIT_M_S,0,0),))):
    try:call()
    except ValueError:rejected+=1
    else:raise AssertionError('Invalid mutual domain accepted')
report={'status':'isolated_mutual_Coulomb_dynamics_verified_not_installed','elliptic_periods':10,
    'eccentricity':ecc,'steps_per_period':[1000,2000,4000],'elliptic_closure_refinement_errors_m':errors,
    'max_energy_errors_over_initial_K_plus_abs_U':energy_errors,'max_momentum_error_kg_m_s':max(momentum_errors),
    'potential_gradient_refinement_errors':gradient,'population128_net_force_normalized':momentum_residual,
    'population128_net_torque_normalized':torque_residual,'all128_forces_vs_reference_field_relative_error':field_error,
    'acting_off_ballistic_reference_preserved':True,'pair_crossing_refused_without_mutation':True,'invalid_inputs_refused':rejected,
    'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (STAGE/'em_fields.py',STAGE/'em_particles.py',STAGE/'em_mutual.py',STAGE/'constants.json',Path(__file__))},
    'scope':'Instantaneous nonrelativistic electrostatics only, CPU prototype.128 force evaluations are not acceptance of128 real-time evolving charges. No magnetic self-fields, worker, persistence or UI.'}
(ROOT/'evidence/em-v03-mutual-dynamics-check.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps(report,indent=2,allow_nan=False))
