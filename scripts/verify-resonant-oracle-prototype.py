"""Independent Newtonian 3-body RHS and IAS15 convergence for angle fixture."""
from pathlib import Path
import hashlib,json,math,sys,time
import numpy as np
import rebound
from scipy.integrate import solve_ivp
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'output/c211-resonances-staging'),str(ROOT/'app')]
from resonant_angles import instantaneous

MASSES=np.array([1.,1e-5,.001]);IDS=['star','inner','outer']
P=2*math.pi/math.sqrt(1.001);END=20*P

def initial(epsilon):
    s=rebound.Simulation();s.G=1.;s.integrator='ias15';s.integrator.epsilon=epsilon
    s.add(m=1.);s.add(primary=s.particles[0],m=1e-5,a=((1.00001/1.001)/4)**(1/3),e=.1,M=0.,pomega=0.)
    s.add(primary=s.particles[0],m=.001,a=1.,e=.01,M=0.,pomega=0.);s.move_to_com();return s
def phase(s):return np.array([[getattr(p,k) for k in ('x','y','z','vx','vy','vz')] for p in s.particles]).ravel()
def rhs(t,y):
    state=y.reshape(3,6);acc=np.zeros((3,3))
    for i in range(3):
        for j in range(i):
            d=state[j,:3]-state[i,:3];distance=math.sqrt(float(d@d));force=d/distance**3
            acc[i]+=MASSES[j]*force;acc[j]-=MASSES[i]*force
    return np.column_stack((state[:,3:],acc)).ravel()
def angle(y):
    state=y.reshape(3,6);bodies=[{'id':i,'mass':float(m),'position':row[:3].tolist(),'velocity':row[3:].tolist()} for i,m,row in zip(IDS,MASSES,state)]
    return instantaneous(bodies,*IDS,2,[0.,0.,1.],[1.,0.,0.])['critical_angles'][0]['angle_rad']
began=time.perf_counter();y0=phase(initial(1e-9));oracles=[]
for tol,parts in [(1e-12,60),(2.3e-14,120),(2.3e-14,240)]:
    result=solve_ivp(rhs,(0.,END),y0,method='DOP853',rtol=tol,atol=tol*.01,max_step=P/parts)
    assert result.success;oracles.append(result.y[:,-1])
refinements=[float(np.linalg.norm(b-a)) for a,b in zip(oracles,oracles[1:])];refinement=refinements[-1];errors=[];angle_errors=[]
for epsilon in [1e-9,1e-12]:
    s=initial(epsilon);s.integrate(END);y=phase(s)
    errors.append(float(np.linalg.norm(y-oracles[-1])))
    angle_errors.append(abs(math.remainder(angle(y)-angle(oracles[-1]),2*math.pi)))
assert refinement<1e-8 and max(errors)<1e-8 and max(angle_errors)<1e-8,(refinement,errors,angle_errors)
assert refinements[1]<refinements[0],refinements
# At the float64 floor, two tolerance settings need not order monotonically.
assert errors[1]<errors[0] or max(errors)<max(1e-10,5*refinement),errors
report={'status':'isolated_three_active_body_oracle_verified_not_installed','outer_periods':20,'DOP853_60_120_240_steps_per_outer_period_state_refinements':refinements,'IAS15_vs_refined_DOP853_state_norm_errors':errors,'critical_angle_errors_rad':angle_errors,'all_three_masses_gravitate':True,'elapsed_s':time.perf_counter()-began,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),ROOT/'output/c211-resonances-staging/resonant_angles.py')},'scope':'Independent RHS/solver over20periods. Does not independently validate500periods or install resonance instruments/classifier.'}
(ROOT/'evidence/resonant-oracle-prototype-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
