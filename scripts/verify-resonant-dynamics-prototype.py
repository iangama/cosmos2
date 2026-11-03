"""Isolated three-active-body resonant/control trajectories; no installed UI."""
from pathlib import Path
import hashlib,json,math,sys,time
import numpy as np
import rebound
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'output/c211-resonances-staging'),str(ROOT/'app')]
from resonant_angles import instantaneous,circular_coverage

IDS=['synthetic-star','inner-planet','outer-planet'];PERIOD=2*math.pi/math.sqrt(1.001)

def initial(ratio=2.,epsilon=1e-9):
    sim=rebound.Simulation();sim.G=1.;sim.integrator='ias15';sim.integrator.epsilon=epsilon
    sim.add(m=1.)
    ain=((1.00001/1.001)/ratio**2)**(1/3)
    sim.add(primary=sim.particles[0],m=1e-5,a=ain,e=.1,M=0.,pomega=0.)
    sim.add(primary=sim.particles[0],m=.001,a=1.,e=.01,M=0.,pomega=0.)
    sim.move_to_com();return sim

def bodies(sim):return [{'id':i,'mass':p.m,'position':[p.x,p.y,p.z],'velocity':[p.vx,p.vy,p.vz]} for i,p in zip(IDS,sim.particles)]

def run(ratio,epsilon=1e-9):
    sim=initial(ratio,epsilon);energy=sim.energy();angular=np.asarray(sim.angular_momentum());E=L=0.;samples=[]
    for target in np.linspace(0.,500*PERIOD,20001):
        sim.integrate(float(target))
        data=instantaneous(bodies(sim),*IDS,2,[0.,0.,1.],[1.,0.,0.])
        angle=data['critical_angles'][0]['angle_rad'];assert angle is not None
        E=max(E,abs(sim.energy()/energy-1));L=max(L,float(np.linalg.norm(np.asarray(sim.angular_momentum())-angular)/np.linalg.norm(angular)))
        samples.append([float(target),angle,data['outer_to_inner_period_ratio'],data['inner']['eccentricity']])
    series=np.array(samples);unwrapped=np.unwrap(series[:,1]);differences=np.diff(unwrapped)
    assert max(abs(differences))<.2 # explicitly dense for this measured synthetic trajectory
    coverage=circular_coverage(series[::5,1].tolist())
    # Direction reversals include fast forced terms. They are not a count
    # of slow libration periods or evidence of permanent capture.
    step=np.diff(unwrapped[::10]);sign=np.sign(step);turns=int(np.count_nonzero(sign[1:]*sign[:-1]<0))
    return {'ratio_initial':ratio,'epsilon':epsilon,'periods':500,'samples':len(samples),'maximum_phase_increment_rad':float(max(abs(differences))),'unwrapped_span_rad':float(np.ptp(unwrapped)),'net_critical_angle_turns':float((unwrapped[-1]-unwrapped[0])/(2*math.pi)),'sampled_direction_reversals':turns,'energy_relative_error':E,'angular_relative_error':L,'circular_coverage':coverage,'final_phase':[[getattr(p,k) for k in ('x','y','z','vx','vy','vz')] for p in sim.particles]},samples

began=time.perf_counter();results=[]
for ratio in (2.,1.8):
    result,samples=run(ratio);results.append(result)
    (ROOT/f'output/c211-resonances-staging/dynamics-{ratio}.json').write_text(json.dumps({'model':'Three active Newtonian masses; synthetic dimensionless initial conditions','initial_mass_canonical':[1.,1e-5,.001],'samples_columns':['time_model','theta_inner_rad','period_ratio','inner_eccentricity'],'samples':samples,'summary':result},indent=2)+'\n')
    print(json.dumps(result),flush=True)
assert results[0]['unwrapped_span_rad']<math.pi,results[0]
assert results[1]['unwrapped_span_rad']>50*math.pi,results[1]
assert max(r['energy_relative_error'] for r in results)<1e-10
assert max(r['angular_relative_error'] for r in results)<1e-10
report={'status':'isolated_three_active_body_libration_and_circulation_verified_not_installed','trajectories':results,'elapsed_s':time.perf_counter()-began,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),ROOT/'output/c211-resonances-staging/resonant_angles.py')},'scope':'Dense sampled synthetic finite trajectories. No permanent-capture claim; tighter solver/oracle convergence, Session/history/checkpoint/worker/native/UI still pending.'}
(ROOT/'evidence/resonant-dynamics-prototype-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='trajectories'},indent=2),flush=True)
