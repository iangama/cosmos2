"""Isolated coupled cloud driver: mirror, transaction, roles and exact future."""
from pathlib import Path
import copy,hashlib,json,math,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'output/c211-test-particles-staging'))
from cloud_driver import Driver,digest,source_phase
import numpy as np
import rebound
began=time.perf_counter()
def mirror(mass=1.,position=(0,0,0),velocity=(0,0,0)):
 s=rebound.Simulation();s.G=1.;s.integrator='ias15';s.integrator.epsilon=1e-9;s.integrator.adaptive_mode='INDIVIDUAL';s.add(m=mass,x=position[0],y=position[1],z=position[2],vx=velocity[0],vy=velocity[1],vz=velocity[2]);return s
m=mirror();original=m.__reduce__()[1][0];d=Driver(m,'source:central',{'count':10000});assert m.__reduce__()[1][0]==original and d.sim.N==10001 and d.sim.N_active==1
radius=np.linspace(1.,4.,10000);angle=(np.arange(10000)*math.pi*(3.-math.sqrt(5.)))%(2*math.pi);worst=0.
for target in (2*math.pi,20*math.pi):
 d.advance(target);assert source_phase(d.sim)==source_phase(m) and d.sim.t==m.t
 expected=np.column_stack((radius*np.cos(angle+target/radius**1.5),radius*np.sin(angle+target/radius**1.5),np.zeros(10000)))
 worst=max(worst,float(np.max(np.linalg.norm(d.positions()-expected,axis=1)/radius)))
assert worst<2e-10,worst
metadata,binary=d.checkpoint();n=mirror();n=rebound.Simulation(m.__reduce__()[1][0]);e=Driver.restore(n,'source:central',metadata,binary);assert np.array_equal(e.positions(),d.positions())
for target in (m.t+.01,m.t+.1,m.t+1.):
 d.advance(target);e.advance(target);assert np.array_equal(d.positions(),e.positions()) and source_phase(m)==source_phase(n)
metadata,binary=d.checkpoint();frozen=d.sim.__reduce__()[1][0];mirror_frozen=m.__reduce__()[1][0];refused=0
for changes in ({'model':'other'},{'source_id':'other'},{'configuration':{'count':True}},{'configuration':{'count':10001}},{'epoch':True},{'confirmed_time':True},{'confirmed_source':[True,0,0,0,0,0,0]},{'initial_source':[2.,0,0,0,0,0,0]},{'initial_source':[1.,1,0,0,0,0,0]},{'confirmed_time':m.t+1},{'extra':'x'}):
 bad=copy.deepcopy(metadata);bad.update(changes);bad['sha256']=digest({k:v for k,v in bad.items() if k!='sha256'})
 try:Driver.restore(m,'source:central',bad,binary)
 except ValueError:refused+=1
 else:raise AssertionError(changes)
 assert d.sim.__reduce__()[1][0]==frozen and m.__reduce__()[1][0]==mirror_frozen
for mutation in ('N_active','testparticle_type','mass','epsilon','gravity_ignore','time','nan'):
 sim=rebound.Simulation(binary)
 if mutation=='N_active':sim.N_active=sim.N
 elif mutation=='testparticle_type':sim.testparticle_type=1
 elif mutation=='mass':sim.particles[10000].m=1e-8
 elif mutation=='epsilon':sim.integrator.epsilon=1e-8
 elif mutation=='gravity_ignore':sim.gravity_ignore=1
 elif mutation=='time':sim.t+=1
 elif mutation=='nan':sim.particles[10000].x=float('nan')
 bad_binary=sim.__reduce__()[1][0];bad=copy.deepcopy(metadata);bad['binary_sha256']=hashlib.sha256(bad_binary).hexdigest();bad['sha256']=digest({k:v for k,v in bad.items() if k!='sha256'})
 try:Driver.restore(m,'source:central',bad,bad_binary)
 except ValueError:refused+=1
 else:raise AssertionError(mutation)
 assert d.sim.__reduce__()[1][0]==frozen and m.__reduce__()[1][0]==mirror_frozen
# A failed trial, including a bad active/passive partition, never commits phase.
def corrupt(pointer):pointer.contents.N_active=2;pointer.contents.stop()
try:d.advance(m.t+.1,heartbeat=corrupt)
except ValueError:refused+=1
else:raise AssertionError('Bad trial committed')
assert d.sim.__reduce__()[1][0]==frozen and m.__reduce__()[1][0]==mirror_frozen
# Nonzero source mass, translation and Galilean boost preserve relative Kepler motion.
other=mirror(.2,(3.,-2.,.4),(.001,.002,-.003));q=Driver(other,'source:boost',{'count':257});q.advance(.8)
r=1.+3*np.arange(257)/256;theta=(np.arange(257)*math.pi*(3-math.sqrt(5)))%(2*math.pi)+.8*np.sqrt(.2/r**3)
expected=np.array([3.,-2.,.4])+.8*np.array([.001,.002,-.003])+np.column_stack((r*np.cos(theta),r*np.sin(theta),np.zeros(257)))
boost_error=float(np.max(np.abs(q.positions()-expected)));assert boost_error<1e-11,boost_error
# A heartbeat yield confirms a partial valid phase and resumes normally.
yield_at=q.sim.t+.01
def stop(pointer):
 if pointer.contents.t>=yield_at:pointer.contents.stop()
q.advance(q.sim.t+5,heartbeat=stop);assert yield_at<=q.sim.t<yield_at+5 and source_phase(q.sim)==source_phase(other)
report={'status':'isolated_joint_cloud_driver_verified_not_installed','active_sources':1,'test_particles':10000,'mirror_never_independently_integrated':True,'analytic_Kepler_max_relative_position_error':worst,'three_future_targets_exact':True,'sealed_metadata_binary_and_invalid_trial_refused':refused,'translated_boosted_mass_p2_max_phase_error':boost_error,'heartbeat_partial_confirmed_and_resumable':True,'checkpoint_binary_bytes':len(binary),'elapsed_s':time.perf_counter()-began,'scope':'Candidate driver only; no Session/worker/native live cloud/performance acceptance.'}
(ROOT/'evidence/cloud-driver-prototype-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
