"""Independent analytic/gradient probes and binary-exact read-only session queries."""
from pathlib import Path
import copy,json,math,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from gravity_field import evaluate
from session import Session
from physics import PHYSICAL_SCALE as U
from atlas import states
from atlas_import import prepare,experiment_subset
from body_registry import digest
GM=U['nominal_GM_unit_m3_s2'];L=U['length_unit_m']
body={'id':'a','mass':1.,'position':[0.,0.,0.]};one=evaluate([body],[2e9,0,0]);assert math.isclose(one['acceleration_m_s2'][0],-GM/(2e9)**2,rel_tol=3e-16) and one['acceleration_m_s2'][1:]==[0,0] and math.isclose(one['potential_J_kg'],-GM/2e9,rel_tol=3e-16)
symmetric=[{**body,'position':[-1.,0,0]},{**body,'id':'b','position':[1.,0,0]}];assert evaluate(symmetric,[0,0,0])['acceleration_m_s2']==[0,0,0]
results=[];invalid=0;maxgradient=0.;maxtranslation=0.
with tempfile.TemporaryDirectory() as temp:
 for kind,count in [('fixture',2),('fixture',32),('fixture',128),('atlas',2)]:
  s=Session(Path(temp)/kind/str(count),count)
  if kind=='atlas':s.import_atlas(prepare(experiment_subset(states(utc='2026-10-11T12:00:00'))))
  s.sim.integrate(.05);s.save();before=copy.deepcopy(s.state());pointer=(s.directory/'latest.json').read_bytes();s.sim.save_to_file(str(s.directory/'before.bin'))
  request={'system_id':s.system_id,'edit_token':s.edit_token,'revision':s.revision,'expected_time':s.sim.t,'frame':s.contract()['frame'],'position_m':[1.7e10,-9e9,3e9]};sample=s.probe(request);bodies=s._bodies(s.sim,s.registry)
  assert sample['time']==s.sim.t and len(sample['sources'])==len(bodies) and sample['scientific_generation']==before['scientific_generation']
  finite=[];h=10000.
  for k in range(3):
   plus=request['position_m'].copy();minus=plus.copy();plus[k]+=h;minus[k]-=h;finite.append(-(evaluate(bodies,plus)['potential_J_kg']-evaluate(bodies,minus)['potential_J_kg'])/(2*h))
  err=math.dist(finite,sample['acceleration_m_s2'])/sample['acceleration_norm_m_s2'];gradient_error=err;maxgradient=max(maxgradient,err);assert err<2e-8,err
  shift=[100.,-20.,30.];moved=[{**b,'position':[v+shift[k] for k,v in enumerate(b['position'])]} for b in bodies];r=evaluate(moved,[v+shift[k]*L for k,v in enumerate(request['position_m'])]);err=math.dist(r['acceleration_m_s2'],sample['acceleration_m_s2'])/sample['acceleration_norm_m_s2'];maxtranslation=max(maxtranslation,err);assert err<2e-13
  for field,value in [('system_id','bad'),('edit_token','bad'),('revision',-1),('expected_time',s.sim.t+1),('frame','SSB'),('position_m',None),('position_m',[0,0]),('position_m',[True,0,0]),('position_m',[math.nan,0,0]),('position_m',[math.inf,0,0]),('position_m',[2e17,0,0]),('position_m',[v*L for v in bodies[0]['position']])]:
   bad={**request,field:value}
   try:s.probe(bad)
   except ValueError:invalid+=1
   else:raise AssertionError((field,value))
   assert s.state()==before
  s.sim.save_to_file(str(s.directory/'after.bin'));assert (s.directory/'before.bin').read_bytes()==(s.directory/'after.bin').read_bytes() and (s.directory/'latest.json').read_bytes()==pointer and s.state()==before
  # Version3.3 checkpoints retain their attributes and conservation reference.
  old=json.loads(pointer);old['saved_generation']['model_version']='3.3.0';old['saved_generation']['code_sha256'].pop('app/gravity_field.py');old['manifest_sha256']=digest({k:v for k,v in old.items() if k!='manifest_sha256'});(s.directory/'latest.json').write_text(json.dumps(old));s.load();assert s.state()['bodies']==before['bodies'] and s.state()['conservation']==before['conservation']
  results.append({'kind':kind,'count':len(bodies),'read_only_binary_checkpoint_and_state_exact':True,'legacy3_3_attributes_and_reference_preserved':True,'potential_gradient_relative_error':gradient_error})
report={'models':results,'invalid_requests_rejected_without_mutation':invalid,'single_mass_analytic_and_symmetric_cancellation':True,'max_potential_gradient_relative_difference':maxgradient,'max_common_translation_relative_difference':maxtranslation,'no_softening_or_test_mass_backreaction':True}
(ROOT/'evidence/gravity-probe-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
