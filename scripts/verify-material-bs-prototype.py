"""Joint material BS, independent RHS oracle, exact resume and safe failure."""
from pathlib import Path
import copy,hashlib,json,math,sys,time
import numpy as np
import rebound
from scipy.integrate import solve_ivp
ROOT=Path(__file__).resolve().parents[1]
INSTALLED='--installed' in sys.argv
SOURCE=ROOT/('app' if INSTALLED else 'output/c211-tides-staging')
sys.path[:0]=[str(SOURCE),str(ROOT/'app')]
from material_driver import Driver,phase,digest
from physics import PHYSICAL_SCALE as U
from equilibrium_tide import G

M=m=1e25;R=1e7;k=.3;a=1e8;I=.33*M*R*R
n=math.sqrt(G*(M+m)/a**3);period=2*math.pi/n/U['time_unit_s']
ids=['material-source','point-companion']
cfg={'radius_m':R,'love_k2':k,'time_lag_s':.003/n,'inertia_kg_m2':I,'spin_rad_s':(np.array([.25,.1,1.4])*n).tolist(),'provenance':'Synthetic joint-solver verification, not observed planet'}

def initial(boost=False):
    sim=rebound.Simulation();sim.G=1.;sim.integrator='ias15';sim.integrator.epsilon=1e-9
    sim.add(m=M/U['mass_unit_kg'],x=-.4*a/U['length_unit_m'],vy=-.5*math.sqrt(1.2/.8)*a*n/U['velocity_unit_m_s'])
    sim.add(m=m/U['mass_unit_kg'],x=.4*a/U['length_unit_m'],vy=.5*math.sqrt(1.2/.8)*a*n/U['velocity_unit_m_s'])
    if boost:
        for p in sim.particles:p.x+=2.;p.y-=1.;p.vx+=.01;p.vz-=.02
    return sim

def normalized(driver):
    y=driver.values()
    return np.r_[y[:3]*driver.length/a,y[3:6]*driver.length/driver.time/a/n,y[6:9]/driver.time/n,y[9]*driver.energy/(G*M*m/a)]

def independent_rhs(t,y):
    # Cartesian CTL equations derived directly from the selected potential-Love
    # convention. This oracle never calls the candidate material/force kernel.
    x=y[:3]*a;v=y[3:6]*a*n;omega=y[6:9]*n
    distance=float(np.linalg.norm(x));rv=float(x@v);u=v-np.cross(omega,x)
    C=3*G*k*m*m*R**5
    elastic=-C*x/distance**8
    damping=-C*cfg['time_lag_s']/distance**10*(2*x*rv+distance**2*u)
    acceleration=-y[:3]/np.linalg.norm(y[:3])**3+(elastic+damping)*(1/M+1/m)/(a*n*n)
    spin=-np.cross(x,damping)/I/(n*n)
    heat=C*cfg['time_lag_s']/distance**10*(2*rv**2+distance**2*float(u@u))/(G*M*m/a*n)
    return np.r_[y[3:6],acceleration,spin,heat]

began=time.perf_counter();driver=Driver(initial(),ids,ids[0],cfg)
y0=normalized(driver);reference=driver.balances();maxE=maxL=0.;last_heat=0.
for target in np.linspace(0.,20*period,201)[1:]:
    driver=driver.advance(float(target));b=driver.balances()
    maxE=max(maxE,abs(b['energy_plus_heat_J']-reference['energy_plus_heat_J'])/abs(reference['energy_plus_heat_J']))
    maxL=max(maxL,float(np.linalg.norm(np.array(b['orbital_plus_spin_angular_momentum_kg_m2_s'])-reference['orbital_plus_spin_angular_momentum_kg_m2_s'])/np.linalg.norm(reference['orbital_plus_spin_angular_momentum_kg_m2_s'])))
    assert b['dissipated_heat_J']>=last_heat;last_heat=b['dissipated_heat_J']
assert maxE<1e-9 and maxL<1e-9,(maxE,maxL)
assert last_heat/(G*M*m/a)>1e-9
print(json.dumps({'joint_BS_energy_relative_error':maxE,'joint_BS_angular_relative_error':maxL,'elapsed_s':time.perf_counter()-began}),flush=True)
oracle=solve_ivp(independent_rhs,(0.,40*math.pi),y0,method='DOP853',rtol=1e-12,atol=1e-14,max_step=2*math.pi/120)
assert oracle.success
error=float(np.linalg.norm(normalized(driver)-oracle.y[:,-1]));assert error<2e-8,error

# A serialized ODE vector plus the native BS archive is required. REBOUND's
# archive alone omits user ODEs. Rebind the known callback and prove exact future
# phase, spin, heat, dt and serialized BS policy at multiple requested epochs.
value=driver.checkpoint();mirror=driver.sim.copy();before=driver.checkpoint()
restored=Driver.restore(mirror,copy.deepcopy(value));exact=[]
assert restored.values().tolist()==driver.values().tolist()
assert driver.checkpoint()==before # observational checkpoint
for target in [20.13*period,21*period,22.75*period]:
    driver=driver.advance(target);restored=restored.advance(target)
    assert driver.values().tolist()==restored.values().tolist()
    assert phase(driver.sim)==phase(restored.sim) and driver.sim.t==restored.sim.t
    assert driver.engine.dt==restored.engine.dt
    exact.append(target)

rejects=[]
def reject(label,change):
    v=copy.deepcopy(value);change(v);v['sha256']=digest({k:x for k,x in v.items() if k!='sha256'})
    current=phase(mirror);t=mirror.t
    try:Driver.restore(mirror,v)
    except (ValueError,TypeError,KeyError):rejects.append(label)
    else:raise AssertionError('Corrupted material state accepted: '+label)
    assert phase(mirror)==current and mirror.t==t

reject('negative heat',lambda v:v['coordinates'].__setitem__(9,-1.))
reject('coordinates versus mirror',lambda v:v['coordinates'].__setitem__(0,v['coordinates'][0]+.01))
reject('engine time versus phase',lambda v:v.__setitem__('epoch',v['epoch']+.1))
reject('center position versus phase',lambda v:v['center'].__setitem__(0,1.))
reject('center velocity versus phase',lambda v:v['center_velocity'].__setitem__(0,1.))
reject('mass',lambda v:v['masses_kg'].__setitem__(0,M*1.1))
reject('scale',lambda v:v.__setitem__('time_s',v['time_s']*2))
reject('reference heat',lambda v:v['reference'].__setitem__('dissipated_heat_J',1.))
reject('binary checksum',lambda v:v.__setitem__('binary_sha256','0'*64))
reject('mirror time',lambda v:v.__setitem__('confirmed_time',v['confirmed_time']+1.))

boosted=Driver(initial(True),ids,ids[0],cfg);boosted=boosted.advance(2*period)
plain=Driver(initial(),ids,ids[0],cfg);plain=plain.advance(2*period)
boost_error=float(np.linalg.norm(normalized(boosted)-normalized(plain)));assert boost_error<1e-10,boost_error

# A nonphysical trial must leave the original confirmed driver unchanged.
bad=copy.deepcopy(cfg);bad['spin_rad_s']=[1e6,0.,0.]
try:Driver(initial(),ids,ids[0],bad)
except ValueError:rejects.append('invalid initial spin')
else:raise AssertionError('Fast material spin accepted')
fall=initial();fall.particles[0].vy=fall.particles[1].vy=0.
falling=Driver(fall,ids,ids[0],cfg);old=falling.checkpoint()
try:falling.advance(period)
except ValueError:rejects.append('domain boundary during joint trial')
else:raise AssertionError('Exterior-domain crossing accepted')
assert falling.checkpoint()==old

report={'status':'installed_joint_BS_verified' if INSTALLED else 'isolated_joint_BS_verified_not_installed','policy':driver.__class__.__module__,'periods':20,'energy_plus_heat_relative_error':maxE,'orbital_plus_spin_angular_relative_error':maxL,'joint_BS_vs_independent_DOP853_normalized_final_error':error,'heat_over_energy_unit':last_heat/(G*M*m/a),'exact_resume_future_targets':exact,'translation_boost_error':boost_error,'rejected_corruptions_and_domains':rejects,'serialized_material_bytes':len(json.dumps(value)),'elapsed_s':time.perf_counter()-began,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),SOURCE/'material_driver.py',SOURCE/'equilibrium_tide.py')},'scope':'No installed Session/worker/UI/surface/performance acceptance'}
(ROOT/('evidence/tides-bs-installed-check.json' if INSTALLED else 'evidence/tides-bs-prototype-check.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
