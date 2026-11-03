"""Independent SI intervention balances, zero energy and atomic failure/checkpoint."""
from pathlib import Path
import copy,json,math,sys,tempfile
import numpy as np
from scipy.integrate import solve_ivp
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from session import Session
from physics import PHYSICAL_SCALE as u
from atlas import states
from atlas_import import prepare,experiment_subset
results=[];rejected=0
def request(s,b):return {'body':b['id'],'system_id':s.system_id,'edit_token':s.edit_token,'expected_time':s.sim.t,'revision':s.revision,'frame':s.state()['contract']['frame'],'mass_kg':b['mass']*u['mass_unit_kg'],'position_m':[x*u['length_unit_m'] for x in b['position']],'velocity_m_s':[x*u['velocity_unit_m_s'] for x in b['velocity']]}
for imported in [False,True]:
 with tempfile.TemporaryDirectory() as folder:
  s=Session(folder,2)
  if imported:s.import_atlas(prepare(experiment_subset(states(utc='2026-10-11T12:00:00'))))
  original=copy.deepcopy(s.atlas_initial);before=s.state();r=request(s,before['bodies'][1]);r['mass_kg']*=1.2;r['position_m'][0]+=1e8;r['velocity_m_s'][1]+=1000
  oldp=np.array([b['position'] for b in before['bodies']]);oldv=np.array([b['velocity'] for b in before['bodies']]);oldm=np.array([b['mass'] for b in before['bodies']])
  e0=s.sim.energy();event=s.set_body(r);after=s.state();m=np.array([b['mass'] for b in after['bodies']]);p=np.array([b['position'] for b in after['bodies']]);v=np.array([b['velocity'] for b in after['bodies']])
  delta_p=np.sum(m[:,None]*v-oldm[:,None]*oldv,axis=0);delta_l=np.sum(m[:,None]*np.cross(p,v)-oldm[:,None]*np.cross(oldp,oldv),axis=0)
  assert np.allclose(delta_p,event['external_momentum_delta'],rtol=1e-11,atol=1e-20);assert np.allclose(delta_l,event['external_angular_momentum_delta'],rtol=1e-11,atol=1e-20)
  assert event['external_energy_delta']==s.sim.energy()-e0 and s.atlas_initial==original
  assert np.allclose(p[1]*u['length_unit_m'],r['position_m'],atol=.001,rtol=1e-14)
  for kind in ['stale','frame','nan','infinity','bool','shape','mass','position_limit','speed_limit','coincident','unknown']:
   bad=request(s,after['bodies'][1])
   if kind=='stale':bad['revision']-=1
   elif kind=='frame':bad['frame']='SSB/J2000'
   elif kind=='nan':bad['position_m'][0]=float('nan')
   elif kind=='infinity':bad['velocity_m_s'][0]=float('inf')
   elif kind=='bool':bad['mass_kg']=True
   elif kind=='shape':bad['position_m']=[1,2]
   elif kind=='mass':bad['mass_kg']=-1
   elif kind=='position_limit':bad['position_m']=[1e18,0,0]
   elif kind=='speed_limit':bad['velocity_m_s']=[1e8,0,0]
   elif kind=='coincident':bad['position_m']=[x*u['length_unit_m'] for x in after['bodies'][0]['position']]
   else:bad['body']='sol:naif:699'
   frozen=copy.deepcopy(s.state())
   try:s.set_body(bad)
   except ValueError:rejected+=1
   else:raise AssertionError(kind)
   assert s.state()==frozen
  s.save();s.sim.integrate(s.sim.t+.001);s.load();assert s.state()['bodies']==after['bodies'] and s.state()['interventions']==after['interventions'] and s.atlas_initial==original
  n=len(m)
  def equations(t,y):
   positions=y[:3*n].reshape(n,3);velocities=y[3*n:].reshape(n,3);acceleration=np.zeros((n,3))
   for i in range(n):
    for j in range(n):
     if i!=j:
      delta=positions[j]-positions[i];acceleration[i]+=m[j]*delta/np.linalg.norm(delta)**3
   return np.concatenate((velocities.ravel(),acceleration.ravel()))
  # Evolving the edited in-memory IAS15 clone checks stale force-cache invalidation.
  reference=solve_ivp(equations,[0,.1],np.concatenate((p.ravel(),v.ravel())),method='DOP853',rtol=2e-13,atol=2e-15,max_step=.005)
  assert reference.success;s.sim.integrate(s.sim.t+.1)
  evolved=np.array([b['position'] for b in s.state()['bodies']]);difference=float(np.max(np.abs(evolved-reference.y[:3*n,-1].reshape(n,3)))*u['length_unit_m'])
  assert difference<.01,difference
  results.append({'imported_atlas':imported,'SI_roundtrip':True,'independent_P_L':True,'checkpoint_exact':True,'post_edit_DOP853_max_component_difference_m':difference})
# Exact binary fractions create a real E=0 reference; it must remain saveable.
with tempfile.TemporaryDirectory() as folder:
 s=Session(folder,2)
 for i in [0,1]:
  b=s.state()['bodies'][i];r=request(s,b);r.update(mass_kg=u['mass_unit_kg'],position_m=[(-1 if i==0 else 1)*u['length_unit_m'],0,0],velocity_m_s=[0,.5*u['velocity_unit_m_s'],(.5 if i==0 else -.5)*u['velocity_unit_m_s']]);s.set_body(r)
 assert s.initial_energy==0,s.initial_energy
 assert s.state()['energy_error'] is None and s.state()['energy_error_absolute']==0
 s.save();s.sim.integrate(.01);s.load();assert s.initial_energy==0 and s.state()['energy_error'] is None
report={'cases':results,'invalid_without_mutation':rejected,'zero_energy_relative_unknown_absolute_available_save_load':True,'scope':'First C2-06 slice: existing point masses, SI mass/phase editor; no creation/radius/spin acceptance.'}
(ROOT/'evidence/body-editor-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
