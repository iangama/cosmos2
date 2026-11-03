"""Isolated planar osculating-angle comparisons; no dynamic resonance claim."""
from pathlib import Path
import copy,hashlib,json,math,sys
import numpy as np
import rebound
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'output/c211-resonances-staging'),str(ROOT/'app')]
from resonant_angles import elements,instantaneous,circular_coverage
from physics import PHYSICAL_SCALE as U

def delta(a,b):return abs(math.remainder(a-b,2*math.pi))
primary={'id':'star','mass':1.,'position':[2.,-3.,.5],'velocity':[.1,-.04,.2]}
errors={'mean_longitude_rad':0.,'periapsis_rad':0.,'semimajor_relative':0.,'eccentricity':0.};count=0
rng=np.random.default_rng(712644)
for e in (0.,1e-10,1e-5,.1,.4,.8):
    for _ in range(40):
        a=float(rng.uniform(.5,3.));M=float(rng.uniform(0.,2*math.pi));peri=float(rng.uniform(0.,2*math.pi));mass=1e-5
        sim=rebound.Simulation();sim.add(m=primary['mass'],x=2.,y=-3.,z=.5,vx=.1,vy=-.04,vz=.2)
        sim.add(primary=sim.particles[0],m=mass,a=a,e=e,M=M,pomega=peri)
        p=sim.particles[1];body={'id':'planet','mass':mass,'position':[p.x,p.y,p.z],'velocity':[p.vx,p.vy,p.vz]}
        actual=elements(primary,body,[0.,0.,1.],[1.,0.,0.]);reference=p.orbit(primary=sim.particles[0])
        errors['mean_longitude_rad']=max(errors['mean_longitude_rad'],delta(actual['mean_longitude_rad'],reference.l))
        errors['semimajor_relative']=max(errors['semimajor_relative'],abs(actual['semimajor_axis_m']/U['length_unit_m']/reference.a-1))
        errors['eccentricity']=max(errors['eccentricity'],abs(actual['eccentricity']-reference.e))
        if e>=1e-5:errors['periapsis_rad']=max(errors['periapsis_rad'],delta(actual['longitude_periapsis_rad'],reference.pomega))
        else:assert actual['longitude_periapsis_rad'] is None
        count+=1
assert errors['mean_longitude_rad']<1e-10 and errors['semimajor_relative']<1e-12 and errors['eccentricity']<1e-12 and errors['periapsis_rad']<1e-9,errors

# Independent Cartesian Kepler construction, without REBOUND's element builder.
def kepler(body_id,a,e,M,peri,mass):
    E=M
    for _ in range(24):E-=(E-e*math.sin(E)-M)/(1-e*math.cos(E))
    c,s=math.cos(E),math.sin(E);n=math.sqrt((1.+mass)/a**3)
    r=np.array([a*(c-e),a*math.sqrt(1-e*e)*s,0.]);v=np.array([-a*n*s,a*n*math.sqrt(1-e*e)*c,0.])/(1-e*c)
    rotation=Rotation.from_rotvec([0.,0.,peri]).as_matrix()
    return {'id':body_id,'mass':mass,'position':(rotation@r+primary['position']).tolist(),'velocity':(rotation@v+primary['velocity']).tolist()}

max_phase=0.;model=None
for t in np.linspace(0.,20*math.pi,301):
    inner=kepler('inner',1.,.1,2*t+.4,.3,1e-5)
    outer=kepler('outer',(4*(1+2e-5)/(1+1e-5))**(1/3),.2,t+.2,.3,2e-5)
    model=instantaneous([primary,inner,outer],'star','inner','outer',2,[0.,0.,1.],[1.,0.,0.])
    # M_inner=2*M_outer and both apsides=.3: 2λouter−λinner−varpi=0.
    max_phase=max(max_phase,delta(model['critical_angles'][0]['angle_rad'],0.))
    assert abs(model['outer_to_inner_period_ratio']-2)<1e-12 and model['classification'] is None
assert max_phase<1e-12,max_phase

# Covariance includes the selected inertial plane/reference. A reference-axis
# rotation alone cancels from the critical-angle combination as well.
original=[primary,inner,outer];angles=[x['angle_rad'] for x in model['critical_angles']];rotation_error=0.
for _ in range(40):
    matrix=Rotation.random(random_state=rng).as_matrix();changed=copy.deepcopy(original)
    translation=rng.normal(size=3);boost=rng.normal(size=3)
    for b in changed:
        b['position']=(matrix@np.asarray(b['position'])+translation).tolist();b['velocity']=(matrix@np.asarray(b['velocity'])+boost).tolist()
    new=instantaneous(changed,'star','inner','outer',2,(matrix@np.array([0.,0.,1.])).tolist(),(matrix@np.array([1.,0.,0.])).tolist())
    rotation_error=max(rotation_error,*[delta(x['angle_rad'],a) for x,a in zip(new['critical_angles'],angles)])
assert rotation_error<1e-11,rotation_error
ring=circular_coverage([2*math.pi*i/100 for i in range(100)]);constant=circular_coverage([.3]*100)
assert ring['classification'] is None and ring['circular_mean_rad'] is None and abs(ring['minimum_occupied_arc_rad']-2*math.pi*.99)<1e-14
assert constant['classification'] is None and constant['minimum_occupied_arc_rad']==0.
guards=[]
for label,change in [('circular periapsis',None),('radial',lambda b:b[1].__setitem__('velocity',primary['velocity'])),('retrograde',lambda b:b[1].__setitem__('velocity',(2*np.array(primary['velocity'])-np.array(b[1]['velocity'])).tolist()))]:
    if change is None:
        b=kepler('circle',1.,0.,.3,0.,1e-5);assert elements(primary,b,[0.,0.,1.],[1.,0.,0.])['longitude_periapsis_rad'] is None;guards.append(label);continue
    b=copy.deepcopy(original);change(b)
    try:instantaneous(b,'star','inner','outer',2,[0.,0.,1.],[1.,0.,0.])
    except ValueError:guards.append(label)
    else:raise AssertionError('Invalid orbital domain accepted: '+label)
report={'status':'isolated_osculating_angles_verified_not_installed','REBOUND_comparison_cases':count,'maximum_errors':errors,'independent_Kepler_2to1_angle_error_rad':max_phase,'rotation_translation_boost_angle_error_rad':rotation_error,'circular_coverage_never_declares_resonance':True,'domains_with_explicit_gaps':guards,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),ROOT/'output/c211-resonances-staging/resonant_angles.py')},'scope':'No mutually interacting resonant fixture, dynamics/libration classifier, Session, history, checkpoint, worker, native/UI or performance acceptance'}
(ROOT/'evidence/resonant-angles-prototype-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
