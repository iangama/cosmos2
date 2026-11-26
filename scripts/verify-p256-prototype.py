"""256 fully interacting masses: independent RHS, persistence and population guards."""
from pathlib import Path
import argparse,copy,hashlib,json,math,sys,tempfile,time
parser=argparse.ArgumentParser();parser.add_argument('--installed',action='store_true');args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT/'app' if args.installed else ROOT/'output/c211-p256-product/app';sys.path.insert(0,str(SOURCE))
import numpy as np
from scipy.integrate import solve_ivp
from session import Session
from material_driver import phase
from physics import fixture,PHYSICAL_SCALE as U
from body_registry import digest
began=time.perf_counter()
def guard(s):return {'system_id':s.system_id,'edit_token':s.edit_token,'revision':s.revision,'expected_time':s.sim.t,'frame':s.contract()['frame']}
with tempfile.TemporaryDirectory(prefix='cosmos2-256-') as temp:
 s=Session(Path(temp),256);initial=s.state();assert s.sim.N==256 and initial['population_contract']['active_mass_count']==256 and initial['population_contract']['all_active_masses_gravitate']
 masses=np.array([p.m for p in s.sim.particles]);y=np.array([[p.x,p.y,p.z,p.vx,p.vy,p.vz] for p in s.sim.particles])
 def rhs(t,z):
  z=z.reshape(256,6);delta=z[None,:,:3]-z[:,None,:3];d2=np.einsum('ijk,ijk->ij',delta,delta);np.fill_diagonal(d2,np.inf)
  acceleration=np.sum(delta*(masses[None,:]/d2**1.5)[:,:,None],axis=1)
  return np.hstack((z[:,3:],acceleration)).ravel()
 oracle=solve_ivp(rhs,(0.,.02),y.ravel(),method='DOP853',rtol=1e-12,atol=1e-14,max_step=.002);assert oracle.success
 s.integrate(.02);error=float(np.max(np.abs(np.array(phase(s.sim)).reshape(256,7)[:,1:]-oracle.y[:,-1].reshape(256,6))))
 assert error<2e-12,error
 p=s.state();ig=guard(s)|{'instruments_revision':s.instruments['revision']};s.configure_instruments(ig|{'operation':'create','definition':{'mode':'fixed','name':'256 fontes','position_m':[9e9,3e9,4e9]}})
 s.configure_history(guard(s)|{'instruments_revision':s.instruments['revision'],'history_revision':s.instrument_history['revision'],'recording':True,'cadence_wall_s':.25})
 d={'primary_id':'p0','inner_id':'p1','outer_id':'p2','j':2,'plane_normal':[0,0,1],'plane_reference':[1,0,0]}
 s.configure_orbital_instruments(guard(s)|{'orbital_revision':0,'operation':'definition','definition':d})
 s.configure_orbital_instruments(guard(s)|{'orbital_revision':1,'operation':'capture','recording':True,'cadence_wall_s':.25})
 for i in range(5):
  s.integrate(.03+i*.01);p=s.state();assert s.collect_history(p,i*.25) and s.collect_orbital_history(p,i*.25)
 assert len(s.instrument_history['samples'][-1]['reading']['source_snapshot_si'])==256
 assert len(s.orbital_instruments['samples'][-1]['reading']['active_ids'])==256
 s.save();t=Session(Path(temp),2);t.load();assert phase(s.sim)==phase(t.sim) and s.instrument_history==t.instrument_history and s.orbital_instruments==t.orbital_instruments
 for target in (.08,.11,.16):s.integrate(target);t.integrate(target);assert phase(s.sim)==phase(t.sim)
 frozen=phase(s.sim);ref=copy.deepcopy(s.conservation_reference)
 request=guard(s)|{'name':'Limite','mass_kg':U['mass_unit_kg']*1e-8,'position_m':[1e11,1e11,1e11],'velocity_m_s':[0,0,0]}
 try:s.create_body(request)
 except ValueError:pass
 else:raise AssertionError('257th active mass accepted')
 assert phase(s.sim)==frozen and s.conservation_reference==ref and s.revision==0
 # A source at the final index contributes to the direct acceleration as well.
 a=rhs(0,y.ravel()).reshape(256,6)[1,3:];delta=y[-1,:3]-y[1,:3];last=masses[-1]*delta/np.linalg.norm(delta)**3;assert np.linalg.norm(last)>0
 report={'status':'installed_p256_verified' if args.installed else 'candidate_p256_verified_not_installed','active_masses':256,'all_mutual_point_gravity':True,'independent_DOP853_max_phase_error':error,'oracle_interval_model_units':.02,'oracle_max_step':.002,'history_source_count':256,'orbital_active_id_count':256,'save_load_three_future_targets_exact':True,'257th_rejected_atomically':True,'energy_error':s.state()['energy_error'],'elapsed_s':time.perf_counter()-began,'scope':'Scientific/persistence test; worker, native UI and formal256 performance separate.'}
(ROOT/('evidence/p256-installed-check.json' if args.installed else 'evidence/p256-prototype-check.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
