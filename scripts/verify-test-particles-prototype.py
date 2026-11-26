"""Isolated10k massless science and archive proof; no product/performance acceptance."""
from pathlib import Path
import hashlib,json,math,sys,tempfile,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'output/c211-test-particles-staging'))
from test_particle_cloud import make
import numpy as np
import rebound
began=time.perf_counter();s=make();assert s.N==10001 and s.N_active==1 and s.testparticle_type==0 and all(p.m==0 for p in list(s.particles)[1:])
radius=np.linspace(1.,4.,10000);angle=(np.arange(10000)*math.pi*(3.-math.sqrt(5.)))%(2*math.pi)
worst_position=worst_velocity=worst_specific_energy=worst_specific_L=0.
for target in (2*math.pi,10*math.pi,20*math.pi):
 s.integrate(target);p=np.empty((10001,3));v=np.empty_like(p);s.serialize_particle_data(xyz=p,vxvyvz=v)
 phi=angle+target/radius**1.5;expected=np.column_stack((radius*np.cos(phi),radius*np.sin(phi),np.zeros(10000)))
 ev=np.column_stack((-np.sin(phi)/np.sqrt(radius),np.cos(phi)/np.sqrt(radius),np.zeros(10000)))
 worst_position=max(worst_position,float(np.max(np.linalg.norm(p[1:]-expected,axis=1)/radius)))
 worst_velocity=max(worst_velocity,float(np.max(np.linalg.norm(v[1:]-ev,axis=1)*np.sqrt(radius))))
 energy=.5*np.sum(v[1:]**2,axis=1)-1./np.linalg.norm(p[1:],axis=1)
 worst_specific_energy=max(worst_specific_energy,float(np.max(np.abs(energy+1/(2*radius))*2*radius)))
 worst_specific_L=max(worst_specific_L,float(np.max(np.abs(np.cross(p[1:],v[1:])[:,2]-np.sqrt(radius))/np.sqrt(radius))))
 assert np.array_equal(p[0],np.zeros(3)) and np.array_equal(v[0],np.zeros(3))
assert worst_position<2e-10 and worst_velocity<2e-10 and worst_specific_energy<2e-12 and worst_specific_L<2e-12
with tempfile.TemporaryDirectory(prefix='cosmos2-cloud-') as temp:
 path=Path(temp)/'cloud.bin';s.save_to_file(str(path));t=rebound.Simulation(str(path));assert t.N_active==1 and t.testparticle_type==0
 def phase(sim):
  p=np.empty((sim.N,3));v=np.empty_like(p);sim.serialize_particle_data(xyz=p,vxvyvz=v);return p,v
 assert all(np.array_equal(a,b) for a,b in zip(phase(s),phase(t)))
 for goal in (s.t+.01,s.t+.1):
  s.integrate(goal);t.integrate(goal);assert all(np.array_equal(a,b) for a,b in zip(phase(s),phase(t)))
 binary_sha=hashlib.sha256(path.read_bytes()).hexdigest()
# Two active sources and an extra close massless neighbour: no source recoil
# or test-test force. Finite integration differences are numerical tolerances.
def restricted(extra):
 q=rebound.Simulation();q.integrator='ias15';q.integrator.epsilon=1e-11;q.add(m=1);q.add(m=.001,x=1.,vy=math.sqrt(1.001));q.move_to_com()
 if extra:q.add(m=0.,x=2.,vy=.7);q.add(m=0.,x=2.+1e-9,vy=.7)
 q.N_active=2;q.testparticle_type=0;return q
base=restricted(False);cloud=restricted(True);single=restricted(False);single.add(m=0.,x=2.,vy=.7)
for q in (base,cloud,single):q.integrate(2.)
active_error=max(abs(getattr(base.particles[i],k)-getattr(cloud.particles[i],k)) for i in (0,1) for k in ('x','y','z','vx','vy','vz'))
test_error=max(abs(getattr(single.particles[2],k)-getattr(cloud.particles[2],k)) for k in ('x','y','z','vx','vy','vz'))
assert active_error<1e-12 and test_error<1e-12,(active_error,test_error)
report={'status':'isolated_10k_massless_prototype_verified_not_installed','rebound':rebound.__version__,'active_sources':1,'test_particles':10000,'mass_exactly_zero':True,'N_active':1,'testparticle_type':0,'analytic_Kepler_targets':[2*math.pi,10*math.pi,20*math.pi],'max_relative_position_error':worst_position,'max_scaled_velocity_error':worst_velocity,'max_relative_specific_energy_error':worst_specific_energy,'max_relative_specific_angular_momentum_error':worst_specific_L,'central_source_position_velocity_exact_zero':True,'two_source_no_recoil_phase_difference':active_error,'close_massless_neighbour_phase_difference':test_error,'binary_sha256':binary_sha,'checkpoint_and_two_future_targets_exact':True,'elapsed_s':time.perf_counter()-began,'scope':'Isolated science only. No Session/worker/native renderer/10k formal performance acceptance.'}
(ROOT/'evidence/test-particles-prototype-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
