"""Isolated joint orbit/spin/heat convergence; does not change product solver."""
from pathlib import Path
import hashlib,json,math,sys,time
import numpy as np
from scipy.integrate import solve_ivp
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'output/c211-tides-staging'))
from equilibrium_tide import G,response
M=m=1e25;R=1e7;k=.3;a=1e8;I=.33*M*R**2;n=math.sqrt(G*(M+m)/a**3);tau=.003/n
Eunit=G*M*m/a;reduced=M*m/(M+m);Lunit=reduced*a*a*n
initial=np.array([.8,0.,0.,0.,math.sqrt(1.2/.8),0.,.25,.1,1.4,0.])

def material(y):return response(M,m,R,k,tau,I,(y[6:9]*n).tolist(),(y[:3]*a).tolist(),(y[3:6]*a*n).tolist())
def rhs(t,y):
 d=material(y);r=y[:3];acc=-r/np.linalg.norm(r)**3+np.array(d['force_on_companion_N'])*(1/M+1/m)/(a*n*n)
 return np.r_[y[3:6],acc,np.array(d['spin_derivative_rad_s2'])/(n*n),d['heat_power_W']/(Eunit*n)]
def balances(y):
 d=material(y);E=.5*np.dot(y[3:6],y[3:6])-1/np.linalg.norm(y[:3])+d['effective_induced_energy_J']/Eunit+.5*I*n*n*np.dot(y[6:9],y[6:9])/Eunit+y[9]
 L=np.cross(y[:3],y[3:6])+I*n/Lunit*y[6:9]
 return E,L
end=20*2*math.pi;times=np.linspace(0,end,401);results=[];began=time.perf_counter()
for method,tol in (('DOP853',1e-9),('DOP853',1e-12),('Radau',1e-11)):
 result=solve_ivp(rhs,(0,end),initial,method=method,rtol=tol,atol=tol*.01,max_step=2*math.pi/60,t_eval=times)
 assert result.success,result.message
 E0,L0=balances(initial);energy=angular=0.
 for y in result.y.T:
  E,L=balances(y);energy=max(energy,abs(E-E0)/abs(E0));angular=max(angular,float(np.linalg.norm(L-L0)/np.linalg.norm(L0)))
 assert energy<1e-7 and angular<1e-8,(method,tol,energy,angular)
 assert result.y[9,-1]>1e-9 and np.min(np.diff(result.y[9]))>=0
 assert energy<.01*result.y[9,-1],(method,energy,result.y[9,-1])
 results.append({'method':method,'rtol':tol,'energy_plus_heat_relative_error':energy,'orbital_plus_spin_angular_relative_error':angular,'heat_over_energy_unit':float(result.y[9,-1]),'final':result.y[:,-1].tolist(),'evaluations':result.nfev})
reference=np.array(results[-1]['final']);errors=[float(np.linalg.norm(np.array(r['final'])-reference)) for r in results[:2]]
assert max(errors)<1e-6 and errors[1]<errors[0],errors
# The observed transfer is larger than numerical conservation errors.
spin_change=float(np.linalg.norm(reference[6:9]-initial[6:9]));assert spin_change>1e-4
report={'status':'isolated_joint_dynamics_verified_not_installed','model':'One deformable body and point companion; orbit/spin/heat advanced together by each integrator','periods':20,'solvers':results,'DOP853_vs_Radau_final_state_norm_errors':errors,'spin_change_over_mean_motion':spin_change,'elapsed_s':time.perf_counter()-began,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),ROOT/'output/c211-tides-staging/equilibrium_tide.py')},'scope':'Same previously verified force kernel, independent integration methods; no REBOUND coupling/cache/checkpoint/native/material-surface acceptance'}
(ROOT/'evidence/tides-dynamics-prototype-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
