"""Isolated Love/CTL normalization, frozen field, work/heat and orbital averages."""
from pathlib import Path
import hashlib,json,math,sys
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'output/c211-tides-staging'))
from equilibrium_tide import G,response,frozen_field
M,m,R,k=1e25,1e22,3e6,.3
I=.33*M*R*R;a=1e8;mu=G*(M+m);n=math.sqrt(mu/a**3);tau=1e-4/n
omega=np.array([.3*n,-.2*n,1.4*n]);r=np.array([a,.2*a,.1*a]);v=np.array([-.2,1.,.15])*math.sqrt(mu/a)
def call(r=r,v=v,omega=omega,tau=tau):return response(M,m,R,k,tau,I,omega.tolist(),r.tolist(),v.tolist())
d=call();F=np.array(d['force_on_companion_N']);Fd=np.array(d['dissipative_force_N']);torque=np.array(d['spin_torque_N_m']);Q=np.array(d['quadrupole_stf_kg_m2']);field=frozen_field(Q,R,r.tolist())
field_force=float(np.linalg.norm(m*np.array(field['acceleration_m_s2'])-F)/np.linalg.norm(F));assert field_force<1e-13,field_force
balance=float(abs(np.dot(Fd,v)+np.dot(torque,omega)+d['heat_power_W'])/d['heat_power_W']);assert balance<1e-13,balance
# Total force includes a much larger radial term. Normalize its cancellation
# by |r||F|, the operands' scale, rather than the small lag torque residual.
torque_balance=float(np.linalg.norm(np.cross(r,F)+torque)/(np.linalg.norm(r)*np.linalg.norm(F)))
assert d['heat_power_W']>0 and torque_balance<1e-14
h=math.hypot(*r)*1e-5;numeric_g=np.empty(3);numeric_T=np.empty((3,3));elastic_gradient=np.empty(3)
for j in range(3):
 delta=np.eye(3)[j]*h;plus=frozen_field(Q,R,(r+delta).tolist());minus=frozen_field(Q,R,(r-delta).tolist())
 numeric_g[j]=-(plus['potential_J_kg']-minus['potential_J_kg'])/(2*h)
 numeric_T[:,j]=(np.array(plus['acceleration_m_s2'])-minus['acceleration_m_s2'])/(2*h)
 elastic_gradient[j]=-(call(r=r+delta,tau=0.)['effective_induced_energy_J']-call(r=r-delta,tau=0.)['effective_induced_energy_J'])/(2*h)
gradient=float(np.linalg.norm(numeric_g-field['acceleration_m_s2'])/np.linalg.norm(field['acceleration_m_s2']))
tensor=float(np.linalg.norm(numeric_T-field['tidal_tensor_s_2'])/np.linalg.norm(field['tidal_tensor_s_2']))
elastic=float(np.linalg.norm(elastic_gradient-d['elastic_force_N'])/np.linalg.norm(d['elastic_force_N']))
assert max(gradient,tensor,elastic)<1e-8,(gradient,tensor,elastic)
rot=Rotation.from_rotvec([.3,-.7,.2]).as_matrix();rd=call(r=rot@r,v=rot@v,omega=rot@omega)
rotation=float(np.linalg.norm(rd['force_on_companion_N']-rot@F)/np.linalg.norm(F));assert rotation<1e-13
assert math.isclose(rd['heat_power_W'],d['heat_power_W'],rel_tol=1e-13)
zero=call(tau=0.);assert zero['heat_power_W']==0 and not np.any(zero['spin_torque_N_m'])
circular=call(r=np.array([a,0.,0.]),v=np.array([0.,n*a,0.]),omega=np.array([0.,0.,n]));assert circular['heat_power_W']==0
# Kepler averages are independent analytical references from Leconte2010.
# Four periapsis orientations perform the apsidal average used there for obliquity.
x,w=np.polynomial.legendre.leggauss(256);f=(x+1)*math.pi;weights=w*math.pi
averages=[]
for e in (.1,.3,.6):
 obliquity=.4;spin=1.2*n;om=np.array([spin*math.sin(obliquity),0.,spin*math.cos(obliquity)])
 heating=work=spindot=precession=0.
 for anomaly,weight in zip(f,weights):
  radius=a*(1-e*e)/(1+e*math.cos(anomaly));dt=(1-e*e)**1.5/(1+e*math.cos(anomaly))**2/(2*math.pi)
  r0=radius*np.array([math.cos(anomaly),math.sin(anomaly),0.]);v0=math.sqrt(mu/(a*(1-e*e)))*np.array([-math.sin(anomaly),e+math.cos(anomaly),0.])
  for psi in (0.,math.pi/4,math.pi/2,3*math.pi/4):
   transform=Rotation.from_rotvec([0.,0.,psi]).as_matrix();rr=transform@r0;vv=transform@v0;d=call(r=rr,v=vv,omega=om)
   heating+=d['heat_power_W']*weight*dt/4;work+=np.dot(d['dissipative_force_N'],vv)*weight*dt/4
   spindot+=np.dot(d['spin_torque_N_m'],om/spin)*weight*dt/4
  radial=-3*G*k*m*m*R**5/radius**7*(1/M+1/m)
  precession+=-math.sqrt(1-e*e)/(n*a*e)*radial*math.cos(anomaly)*weight*dt
 N=(1+7.5*e**2+45/8*e**4+5/16*e**6)/(1-e*e)**6
 Na=(1+15.5*e**2+255/8*e**4+185/16*e**6+25/64*e**8)/(1-e*e)**7.5
 O=(1+3*e**2+3/8*e**4)/(1-e*e)**4.5;K=1.5*G*k*m*m*R**5*tau/a**6*n*n;c=math.cos(obliquity)
 expected=[2*K*(Na-2*N*c*spin/n+(1+c*c)/2*O*(spin/n)**2),2*K*(N*c*spin/n-Na),-K/n*((1+c*c)*O*spin/n-2*c*N)]
 actual=[heating,work,spindot];errors=[abs(a-b)/abs(b) for a,b in zip(actual,expected)];assert max(errors)<1e-10,(e,errors)
 # RagozzineWolf2009 potential-Love static apsidal rate, finite companion mass.
 analytic=7.5*k*n*(m/M)*(R/a)**5*(1+1.5*e*e+.125*e**4)/(1-e*e)**5
 error=abs(precession-analytic)/analytic;assert error<1e-10,error
 averages.append({'e':e,'Leconte_heat_work_spin_relative_errors':errors,'RagozzineWolf_precession_relative_error':error})
rejected=0
for changes in ({'radius_m':0.},{'love_k2':True},{'tau_s':-1.},{'inertia_kg_m2':0.},{'spin_rad_s':[1.,0.,0.]},{'displacement_m':[R/2,0.,0.]}):
 params=dict(source_mass_kg=M,companion_mass_kg=m,radius_m=R,love_k2=k,tau_s=tau,inertia_kg_m2=I,spin_rad_s=omega.tolist(),displacement_m=r.tolist(),relative_velocity_m_s=v.tolist());params.update(changes)
 try:response(**params)
 except ValueError:rejected+=1
 else:raise AssertionError('Invalid candidate domain accepted')
report={'status':'isolated_kernel_verified_not_installed','field_equals_pair_force_relative_error':field_force,'mechanical_work_plus_heat_relative_residual':balance,'gradient_relative_error':gradient,'tensor_gradient_relative_error':tensor,'effective_energy_gradient_relative_error':elastic,'rotation_relative_error':rotation,'zero_lag_no_heat_or_torque':True,'circular_sync_no_heat':True,'orbital_averages':averages,'invalid_domains_rejected':rejected,'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'output/c211-tides-staging/equilibrium_tide.py',Path(__file__),ROOT/'output/c211-tides-staging/reference.json')},'scope':'One deformable isotropic body plus point companion, first order time lag; no time integration, checkpoint, material surface, worker or native acceptance'}
(ROOT/'evidence/tides-kernel-prototype-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
