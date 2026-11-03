"""Live Session preset semantics, conservation, edits and sealed initial populations."""
from pathlib import Path
import copy,json,math,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from session import Session
from body_registry import digest
from gravity_experiments import catalog

def guard(s):return {'system_id':s.system_id,'edit_token':s.edit_token,'revision':s.revision,'expected_time':s.sim.t,'frame':s.contract()['frame']}
def advance(s,target):
 while s.sim.t<target:s.sim.integrate(min(target,s.sim.t+10/30))
results=[];corrupt=0
with tempfile.TemporaryDirectory() as temp:
 for model in catalog()['models']:
  s=Session(Path(temp)/model['id']);s.load_experiment({**guard(s),'scenario_id':model['id']});seed=copy.deepcopy(s.seed);original=s.state();ids=[b['id'] for b in s.registry]
  assert all(b['origin']=={'kind':'user_model'} and 'reference_id' not in b for b in original['bodies']) and original['experiment']['definition']['construction']['observational_source'] is None
  assert len(s.registry)==len(model['initial']) and not original['experiment']['conditions_edited']
  samples=[];saved=None
  for target in model['verification_times_model']:
   advance(s,target);state=s.state();e=state['experiment'];c=state['conservation'];assert state['energy_error']<1e-8 and c['momentum_error_normalized']<1e-8 and c['angular_momentum_error_normalized']<1e-8
   if model['id']=='flyby':assert e['status']=='isolated_flyby' and e['analysis']['outward']
   else:
    assert e['status']=='hierarchical_outgoing' and e['analysis']['matches_selected_model_outcome'] and e['analysis']['separation_over_binary_a']>30
    assert (e['analysis']['initial_incoming_cluster_energy_canonical']>0)==(model['id']=='capture')
   samples.append({'time':target,'status':e['status'],'energy_relative_error':state['energy_error'],'momentum_normalized_error':c['momentum_error_normalized'],'angular_momentum_normalized_error':c['angular_momentum_error_normalized'],'COM_drift_m':c['SI']['barycenter_drift_norm_m']})
   if saved is None:s.save();saved=copy.deepcopy(state)
  expected=s.state()['bodies'];s.load();assert s.state()['bodies']==saved['bodies'];advance(s,model['horizon_model_time']);assert s.state()['bodies']==expected
  s.save();path=s.directory/'latest.json';manifest=json.loads(path.read_text())
  changes=[lambda m:m['seed']['initial'][0].update(mass=-1),lambda m:m['seed']['scenario'].update(expected_pair_indices=[0,0]),lambda m:m['seed']['scenario']['construction'].update(observational_source='fakeJPL'),lambda m:m['seed']['scenario'].update(catalog_sha256='bad'),lambda m:m['seed']['initial'][0].update(name='renamed')]
  for change in changes:
   bad=copy.deepcopy(manifest);change(bad);bad['fixture_sha256']=digest(bad['seed']);bad['manifest_sha256']=digest({k:v for k,v in bad.items() if k!='manifest_sha256'});path.write_text(json.dumps(bad));before=copy.deepcopy(s.state())
   try:s.load()
   except ValueError:corrupt+=1
   else:raise AssertionError('Invalid preset checkpoint accepted')
   assert s.state()==before
  path.write_text(json.dumps(manifest));s.load();s.set_attributes({**guard(s),'body':ids[0],'radius_m':None,'angular_velocity_rad_s':[0,0,.01]});assert not s.state()['experiment']['conditions_edited']
  s.set_mass(ids[0],s.sim.particles[0].m*1.1);assert s.state()['experiment']['conditions_edited'];s.remove_body({**guard(s),'body':ids[1]});assert s.state()['experiment']['status']=='modified_population';s.save();s.load();assert s.state()['experiment']['status']=='modified_population'
  old=s.system_id;s.restart_seed();assert s.system_id!=old and s.seed==seed and [b['mass'] for b in s.state()['bodies']]==[b['mass'] for b in original['bodies']] and not s.state()['experiment']['conditions_edited']
  results.append({'model':model['id'],'samples':samples,'checkpoint_continuation_exact':True,'initial_population_and_definition_preserved':True,'physical_edits_mark_modified':True,'kinematic_edits_do_not_mark_physics_modified':True,'deleted_ID_not_reassigned_in_analysis':True,'restart_recovers_seed':True})
report={'models':results,'corrupt_or_forged_model_checkpoints_without_mutation':corrupt,'scope':'Three local finite Newtonian models, not observed systems; independent DOP853 check is separate.'}
(ROOT/'evidence/gravity-experiments-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
