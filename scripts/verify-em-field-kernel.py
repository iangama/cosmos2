"""Independent static EM field references and physical invariances; isolated only."""
from pathlib import Path
from decimal import Decimal,localcontext
import hashlib
import itertools
import json
import math
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/c212-em-staging'
sys.path.insert(0,str(STAGE))
from em_fields import Model,Source,lorentz,EPSILON_0,MU_0,C,K_E
rng=np.random.default_rng(181026)
directions=rng.normal(size=(1024,3));directions/=np.linalg.norm(directions,axis=1)[:,None]
directions=np.vstack((np.eye(3),-np.eye(3),directions))
with localcontext() as ctx:
    ctx.prec=50
    reference_k=float(1/(4*Decimal('3.1415926535897932384626433832795028841971693993751')*Decimal('8.8541878188e-12')))
assert abs(K_E/reference_k-1)<3e-16
assert abs(EPSILON_0*MU_0*C*C-1)<2e-10
worst=0.;checks=0
for center,sign in itertools.product(((0.,0.,0.),(3.,-2.,7.)),(-1,1)):
    model=Model((Source('q',center,.01,sign*2e-8),))
    for d in directions:
        r=model.evaluate((np.array(center)+2*d).tolist());g=np.array(r['electric_field_V_m'])
        expected=sign*reference_k*2e-8/4*d
        error=np.linalg.norm(g-expected)/np.linalg.norm(expected);worst=max(worst,float(error))
        assert error<1e-13 and np.dot(g,d)*sign>0
        assert abs(r['electric_potential_V']/(sign*reference_k*2e-8/2)-1)<1e-14
        far=model.evaluate((np.array(center)+4*d).tolist())
        assert abs(math.hypot(*far['electric_field_V_m'])/math.hypot(*g)-.25)<1e-14
        checks+=1

sources=(Source('a',(0,0,0),.01,2e-8,(1,2,3)),Source('b',(-1,2,.5),.01,-3e-8,(-4,2,1)),Source('c',(2,-1,1),.01,1e-8,(3,-1,2)))
model=Model(sources,(3,-4,2),(.3,.1,-.2));point=np.array([3.4,2.7,-1.8])
base=model.evaluate(point);E=np.array(base['electric_field_V_m']);B=np.array(base['magnetic_field_T'])
gradient_errors=[];divergence_errors=[];nonuniform=Model(sources)
for h in (.01,.005,.0025):
    grad=[];div=0.
    for k in range(3):
        offset=np.eye(3)[k]*h;lo=model.evaluate(point-offset);hi=model.evaluate(point+offset)
        grad.append(-(hi['electric_potential_V']-lo['electric_potential_V'])/(2*h))
        blo=nonuniform.evaluate(point-offset);bhi=nonuniform.evaluate(point+offset)
        div+=(bhi['magnetic_field_T'][k]-blo['magnetic_field_T'][k])/(2*h)
    gradient_errors.append(float(np.linalg.norm(np.array(grad)-E)/base['electric_scale_V_m']))
    # Remove uniform B from the normalization: it has exactly zero derivative.
    scale=sum(np.linalg.norm(Model((s,)).evaluate(point)['magnetic_field_T']) for s in sources)/np.linalg.norm(point)
    divergence_errors.append(float(abs(div)/scale))
assert gradient_errors[-1]<1e-6 and gradient_errors[-1]<gradient_errors[0]/10
assert divergence_errors[-1]<1e-5 and divergence_errors[-1]<divergence_errors[0]/10,divergence_errors

rotation_error=0.
for _ in range(24):
    rotation,_=np.linalg.qr(rng.normal(size=(3,3)))
    if np.linalg.det(rotation)<0:rotation[:,0]*=-1
    shift=rng.normal(size=3)
    moved=tuple(Source(s.id,tuple(rotation@np.array(s.position_m)+shift),s.exclusion_radius_m,s.charge_C,tuple(rotation@np.array(s.magnetic_moment_A_m2))) for s in sources)
    other=Model(moved,tuple(rotation@np.array(model.uniform_E_V_m)),tuple(rotation@np.array(model.uniform_B_T))).evaluate(rotation@point+shift)
    for name,ref,scale in [('electric_field_V_m',E,base['electric_scale_V_m']),('magnetic_field_T',B,base['magnetic_scale_T'])]:
        error=float(np.linalg.norm(np.array(other[name])-rotation@ref)/scale)
        rotation_error=max(rotation_error,error);assert error<1e-13

dipole=Model((Source('m',(0,0,0),.01,0,(0,0,4)),))
axis=dipole.evaluate((0,0,2))['magnetic_field_T'];equator=dipole.evaluate((2,0,0))['magnetic_field_T']
assert np.allclose(axis,[0,0,MU_0/(4*math.pi)],rtol=1e-14,atol=0)
assert np.allclose(equator,[0,0,-MU_0/(8*math.pi)],rtol=1e-14,atol=0)
cancel=Model((Source('left',(-1,0,0),.01,1e-8),Source('right',(1,0,0),.01,1e-8))).evaluate((0,0,0))
assert cancel['electric_field_V_m']==[0,0,0] and cancel['electric_scale_V_m']>0
reverse=Model(tuple(reversed(sources)),model.uniform_E_V_m,model.uniform_B_T).evaluate(point)
assert reverse['electric_field_V_m']==base['electric_field_V_m'] and reverse['magnetic_field_T']==base['magnetic_field_T']

v=[3000,4000,5000];controls=[];power_error=0.
for electric,magnetic in itertools.product((False,True),repeat=2):
    r=lorentz(model,point,v,-2e-8,3e-5,electric_acting=electric,magnetic_acting=magnetic)
    assert r['reference']==base
    expected=(-2e-8*E if electric else np.zeros(3))+(-2e-8*np.cross(v,B) if magnetic else np.zeros(3))
    assert np.allclose(r['force_N'],expected,rtol=1e-14,atol=0)
    assert np.allclose(r['acceleration_m_s2'],expected/3e-5,rtol=1e-14,atol=0)
    scale=math.hypot(*r['magnetic_force_N'])*math.hypot(*v)
    error=abs(r['magnetic_power_W'])/scale if scale else abs(r['magnetic_power_W'])
    power_error=max(power_error,error);assert error<1e-14
    controls.append({'electric_acting':electric,'magnetic_acting':magnetic,'reference_unchanged':True})

assert not dipole.evaluate((0,0,0))['valid'] and not dipole.evaluate((.01,0,0))['valid']
assert dipole.evaluate((.01000001,0,0))['valid']
assert not lorentz(dipole,(0,0,0),v,1,1)['valid']
rejected=0
bad=[lambda:Source('x',(0,0,0),0),lambda:Source('x',(0,0,float('nan')),1),lambda:Source('x',(0,0,0),1,True),
     lambda:Model((sources[0],sources[0])),lambda:Model(tuple(Source(str(i),(0,0,0),1) for i in range(129))),
     lambda:Model(uniform_B_T=(float('inf'),0,0)),lambda:lorentz(model,point,v,1,0),
     lambda:lorentz(model,point,(.02*C,0,0),1,1),lambda:lorentz(model,point,v,1,1,electric_acting=1)]
for call in bad:
    try:call()
    except ValueError:rejected+=1
    else:raise AssertionError('Invalid scientific domain accepted')
report={'status':'isolated_static_EM_kernel_verified_not_installed','charge_direction_checks':checks,
    'maximum_relative_charge_field_error':worst,'electric_potential_gradient_refinement_errors':gradient_errors,
    'magnetic_divergence_refinement_errors':divergence_errors,'rotation_translation_relative_error':rotation_error,
    'dipole_axis_equator_verified':True,'cancellation_retains_nonzero_error_scale':True,'source_order_invariant':True,
    'electric_magnetic_physical_controls':controls,'maximum_normalized_magnetic_power':power_error,
    'exclusion_boundary_and_interior_unavailable':True,'invalid_inputs_refused':rejected,
    'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (STAGE/'em_fields.py',STAGE/'constants.json',Path(__file__))},
    'scope':'Static fixed-source SI fields and force only. No integrator, source reaction, Coulomb mutual dynamics, worker, persistence, body catalogue or native/UI acceptance.'}
(ROOT/'evidence/em-field-kernel-check.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps(report,indent=2,allow_nan=False))
