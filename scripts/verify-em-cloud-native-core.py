"""Native helper: independent fields, scalar Boris, analytic orbits and10000 timing."""
from pathlib import Path
import hashlib
import json
import math
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/c212-em-cloud-native-staging';sys.path.insert(0,str(STAGE))
from cloud_core import System,Phase,VERSION
from cloud_fields import evaluate
from em_fields import Model,Source,K_E,MU_0,SPEED_LIMIT_M_S
from em_particles import Phase as ScalarPhase,boris_step,DomainExit
for name in ('em_fields.py','em_particles.py','constants.json'):assert (STAGE/name).read_bytes()==(ROOT/'output/c212-em-v04-product/em'/name).read_bytes()
rng=np.random.default_rng(191026);x=rng.normal(size=(64,3))*3+[0,0,5]
model=Model((Source('p',(-1,.3,0),.02,1e-9,(1e4,0,2e4)),Source('n',(1,-.5,.4),.03,-.7e-9,(0,2e4,0))),(.1,.2,-.1),(.3,-.2,.5))
E,B,phi=evaluate(model,x);field_errors=[]
for i,p in enumerate(x):
    reading=model.evaluate(p);assert reading['valid']
    ee=float(np.linalg.norm(E[i]-reading['electric_field_V_m']))/reading['electric_scale_V_m'];be=float(np.linalg.norm(B[i]-reading['magnetic_field_T']))/reading['magnetic_scale_T']
    assert ee<1e-13 and be<1e-13 and math.isclose(phi[i],reading['electric_potential_V'],abs_tol=1e-13,rel_tol=1e-13)
    # Separate long-double loop, with a different arithmetic grouping.
    point=np.array(p,dtype=np.longdouble);e=np.array(model.uniform_E_V_m,dtype=np.longdouble);b=np.array(model.uniform_B_T,dtype=np.longdouble)
    for s in model.sources:
        d=point-np.array(s.position_m,dtype=np.longdouble);r=np.sqrt(np.sum(d*d));moment=np.array(s.magnetic_moment_A_m2,dtype=np.longdouble)
        e+=np.longdouble(K_E)*s.charge_C*d/r**3
        b+=np.longdouble(MU_0)/(4*np.longdouble(math.pi))*(3*d*np.dot(d,moment)/r**5-moment/r**3)
    le=float(np.linalg.norm(E[i].astype(np.longdouble)-e))/reading['electric_scale_V_m'];lb=float(np.linalg.norm(B[i].astype(np.longdouble)-b))/reading['magnetic_scale_T']
    assert le<1e-13 and lb<1e-13;field_errors.append(max(ee,be,le,lb))
v=rng.normal(size=(16,3))*.1;q=rng.uniform(-1,1,16);m=rng.uniform(.5,2,16);system=System(model,q,m);scalar_max=0.;scalar_steps=0
for acting_e in (False,True):
    for acting_b in (False,True):
        p=Phase(x[:16],v);refs=[ScalarPhase(tuple(a),tuple(b)) for a,b in zip(x[:16],v)]
        for step in range(16):
            p,d=system.step(p,.002,electric_acting=acting_e,magnetic_acting=acting_b)
            for i in range(16):
                refs[i],sd=boris_step(model,refs[i],float(q[i]),float(m[i]),.002,electric_acting=acting_e,magnetic_acting=acting_b);scalar_steps+=1
                error=max(np.max(abs(p.positions()[i]-refs[i].position_m)),np.max(abs(p.velocities()[i]-refs[i].velocity_m_s)));scalar_max=max(scalar_max,float(error))
                assert error<2e-13 and math.isclose(d['electric_work_J'][i],sd['electric_work_J'],abs_tol=1e-14)

period=2*math.pi;closure=[];energy=[]
for steps in (1000,2000,4000):
    sysB=System.uniform(Model(uniform_B_T=(0,0,1)),1,1,1);p=Phase([[0,0,0]],[[1,0,.3]]);k0=sysB.diagnostics(p)['kinetic_energy_J'];worst=0.
    for i in range(10*steps):
        p,_=sysB.step(p,period/steps)
        if i%50==0:worst=max(worst,abs(sysB.diagnostics(p)['kinetic_energy_J']-k0)/k0)
    t=p.time_s;analytic=np.array([math.sin(t),math.cos(t)-1,.3*t]);closure.append(float(np.linalg.norm(p.positions()[0]-analytic)));energy.append(worst)
assert closure[0]/closure[1]>3.8 and closure[1]/closure[2]>3.8 and closure[-1]<1e-3 and max(energy)<1e-10,(closure,energy)
# Uniform E is independently analytic and its discrete work balances matter KE.
sysE=System(Model(uniform_E_V_m=(.2,-.1,.3)),q,m);initial=Phase(x[:16],v);p=initial;work=np.zeros(16)
for _ in range(500):p,d=sysE.step(p,.002);work+=d['electric_work_J']
acc=q[:,None]/m[:,None]*np.array([.2,-.1,.3]);t=p.time_s
e_position=float(np.max(abs(p.positions()-(x[:16]+v*t+.5*acc*t*t))));e_velocity=float(np.max(abs(p.velocities()-(v+acc*t))))
dk=.5*m*(np.sum(p.velocities()**2,axis=1)-np.sum(v*v,axis=1));work_error=float(np.max(abs(work-dk)))
assert max(e_position,e_velocity,work_error)<1e-10
# E×B mean drift is independent of q sign; ten full physical gyro periods.
cross=System.uniform(Model(uniform_E_V_m=(.2,0,0),uniform_B_T=(0,0,1)),1,1,1);p=Phase([[0,0,0]],[[1,0,.3]])
for _ in range(20000):p,_=cross.step(p,period/2000)
drift=p.positions()[0,:2]/p.time_s;drift_error=float(np.linalg.norm(drift-[0,-.2])/.2);assert drift_error<1e-3

obstacle=System.uniform(Model((Source('excluded',(0,0,0),.1,0.),)),2,1,1)
initial=Phase([[-1,0,0],[-1,2,0]],[[4,0,0],[4,0,0]]);before=(initial._x,initial._v,initial.time_s)
for _ in range(5):
    try:obstacle.step(initial,1)
    except DomainExit as error:assert 'excluded' in str(error)
    else:raise AssertionError('Cloud tunneled through source exclusion')
    assert (initial._x,initial._v,initial.time_s)==before
    safe,_=obstacle.step(initial,.001);assert safe.time_s==.001
tiny=System.uniform(Model((Source('tiny',(0,0,0),1e-310,0.),)),1,1,1)
try:tiny.step(Phase([[-1e-300,0,0]],[[4e-300,0,0]]),1)
except DomainExit:pass
else:raise AssertionError('Underflow-scale drift crossed source')
raw=np.array([[1.,2.,3.]]);p=Phase(raw,[[0,0,0]]);raw[:]=0;assert p.positions().tolist()==[[1.,2.,3.]]
for array in (p.positions(),p.velocities(),System.uniform(Model(),1,1,1).charges()):
    try:array.setflags(write=True)
    except ValueError:pass
    else:raise AssertionError('Public cloud arrays can be modified')
refusals=0
for action in (lambda:Phase([[True,0,0]],[[0,0,0]]),lambda:Phase([[0,0,0]],[[2*SPEED_LIMIT_M_S,0,0]]),
               lambda:Phase([[1e18,0,0]],[[0,0,0]]),lambda:System.uniform(Model(),10001,1,1),lambda:System(Model(),[1],[0]),
               lambda:sysE.step(initial,True),lambda:System.uniform(Model(),1,1,1).step(Phase([[0,0,0]],[[0,0,0]],1e30),.001),
               lambda:cross.step(Phase([[0,0,0]],[[1,0,0]]),1),lambda:cross.step(Phase([[0,0,0]],[[1,0,0]]),.001,electric_acting=1)):
    try:action()
    except (ValueError,ArithmeticError):refusals+=1
    else:raise AssertionError('Invalid cloud trial accepted')

# The timing includes immutable phase buffers and per-particle work diagnostics.
n=10000;i=np.arange(n);angle=i*math.pi*(3-math.sqrt(5));r=1+2*i/(n-1)
xx=np.column_stack((r*np.cos(angle),r*np.sin(angle),.1*np.sin(2*angle)));vv=np.column_stack((-np.sin(angle),np.cos(angle),.1*np.cos(angle)))
charges=np.where(i%2,1.,-1.);many=System(Model(uniform_E_V_m=(.2,0,0),uniform_B_T=(0,0,1)),charges,np.ones(n));p=Phase(xx,vv);work=np.zeros(n)
began=time.perf_counter()
for _ in range(500):p,d=many.step(p,.002);work+=d['electric_work_J']
wall=time.perf_counter()-began;analytic_error=0.
for k in (0,1234,9999):
    omega=charges[k];t=p.time_s;u=vv[k]-[0,-.2,0];s=math.sin(omega*t);c=math.cos(omega*t)
    expected=xx[k]+[(u[0]*s+u[1]*(1-c))/omega,(u[0]*(c-1)+u[1]*s)/omega-.2*t,u[2]*t]
    analytic_error=max(analytic_error,float(np.max(abs(p.positions()[k]-expected))))
assert analytic_error<1e-5
report={'status':'isolated_batched_prescribed_EM_cloud_scientific_references_verified_not_native_acceptance',
        'model':VERSION,'field_reference_points':64,'field_normalized_error_max':max(field_errors),'scalar_Boris_comparison_steps':scalar_steps,'scalar_Boris_max_phase_component_error':scalar_max,
        'B_uniform_periods':10,'steps_per_period':[1000,2000,4000],'B_uniform_refinement_position_errors_m':closure,'B_uniform_relative_energy_error_max':max(energy),
        'E_uniform_position_error_m':e_position,'E_uniform_velocity_error_m_s':e_velocity,'E_work_balance_absolute_error_J':work_error,'crossed_field_mean_drift_relative_error':drift_error,
        'exclusion_failures_then_safe_trials':5,'tiny_underflow_scale_crossing_refused':True,'public_buffers_immutable':True,'invalid_inputs_refused':refusals,
        'cloud10000':{'steps':500,'dt_s':.002,'elapsed_wall_s':wall,'elapsed_model_s':p.time_s,'isolated_model_s_per_wall_s':p.time_s/wall,'analytic_selected_particle_max_component_error_m':analytic_error},
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (*STAGE.glob('*.py'),STAGE/'constants.json',STAGE/'cloud_kernel.cpp',STAGE/'CMakeLists.txt',STAGE/'build-receipt.json',STAGE/'cosmos2_em_cloud.dll',Path(__file__))},
        'scope':'CPU scientific prototype only. Static prescribed sources, no reaction/test-test forces, plasma/PIC or gravity.10000 isolated timing is not native frame/worker/pause/checkpoint or combined128-source performance acceptance.'}
(ROOT/'evidence/em-cloud-native-helper-e-core-check.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'},indent=2))
