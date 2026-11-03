"""Read-only proposals, guard failures, integral baselines and migration semantics."""
from pathlib import Path
import copy,hashlib,json,math,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from session import Session
from physics import PHYSICAL_SCALE as U
from body_registry import digest
from atlas import states
from atlas_import import prepare,experiment_subset

def guard(s,body,primary):return {'system_id':s.system_id,'edit_token':s.edit_token,'revision':s.revision,'expected_time':s.sim.t,'frame':s.contract()['frame'],'body':body,'primary':primary}
results=[];invalid=0;corrupt=0
with tempfile.TemporaryDirectory() as temp:
 for imported,count in [(False,2),(False,32),(False,128),(True,2)]:
  s=Session(Path(temp)/str(imported)/str(count),count)
  if imported:s.import_atlas(prepare(experiment_subset(states(utc='2026-10-11T12:00:00'))))
  s.sim.integrate(.1);body=s.state()['bodies'][1];request=guard(s,body['id'],s.registry[0]['id']);proposal={'mass_kg':body['mass']*U['mass_unit_kg']*1.2,'position_m':[v*U['length_unit_m'] for v in body['position']],'velocity_m_s':[v*U['velocity_unit_m_s']*1.4 for v in body['velocity']]};request['proposed']=proposal
  s.save();pointer=(s.directory/'latest.json').read_bytes();frozen=copy.deepcopy(s.state());before_file=s.directory/'before.bin';s.sim.save_to_file(str(before_file));report=s.orbit(request);after_file=s.directory/'after.bin';s.sim.save_to_file(str(after_file))
  assert s.state()==frozen and (s.directory/'latest.json').read_bytes()==pointer and before_file.read_bytes()==after_file.read_bytes()
  for field,value in [('body','missing'),('primary','missing'),('primary',body['id']),('system_id','0'*32),('edit_token','0'*32),('revision',s.revision-1),('expected_time',s.sim.t+1),('frame','SSB'),('proposed',{}),('proposed',{'mass_kg':1,'position_m':[0,0,0],'velocity_m_s':[0,0,0]})]:
   bad=copy.deepcopy(request);bad[field]=value
   try:s.orbit(bad)
   except ValueError:invalid+=1
   else:raise AssertionError((field,value))
   assert s.state()==frozen
  s.set_body({**guard(s,body['id'],s.registry[0]['id']),**proposal});actual=s.orbit(guard(s,body['id'],s.registry[0]['id']))
  assert actual['before']==report['after'] and actual['before_escape']==report['after_escape']
  current=s.state()['conservation'];assert current['momentum_error_normalized']==0 and current['angular_momentum_error_normalized']==0 and current['SI']['barycenter_drift_norm_m']==0
  reference=copy.deepcopy(s.conservation_reference);s.sim.integrate(.2);s.set_attributes({**guard(s,body['id'],s.registry[0]['id']),'radius_m':1e6,'angular_velocity_rad_s':[.001,0,0]});assert s.conservation_reference==reference
  s.save();saved=copy.deepcopy(s.state());s.load();assert s.conservation_reference==reference and s.state()['conservation']==saved['conservation']
  path=s.directory/'latest.json';manifest=json.loads(path.read_text())
  changes=[lambda m:m['conservation_reference'].update(time=s.sim.t+1),lambda m:m['conservation_reference'].update(total_mass=-1),lambda m:m['conservation_reference']['momentum'].__setitem__(0,1),lambda m:m['conservation_reference']['active_ids'].reverse(),lambda m:m['conservation_reference'].update(energy_reference_time=-1),lambda m:m.pop('conservation_reference'),lambda m:m.update(saved_generation=[])]
  for change in changes:
   bad=copy.deepcopy(manifest);change(bad);bad['manifest_sha256']=digest({k:v for k,v in bad.items() if k!='manifest_sha256'});path.write_text(json.dumps(bad));before=copy.deepcopy(s.state())
   try:s.load()
   except ValueError:corrupt+=1
   else:raise AssertionError('Invalid conservation checkpoint accepted')
   assert s.state()==before
  # Generation3.1 preserves its energy baseline and declares a fresh momentum reference.
  old=copy.deepcopy(manifest);old['saved_generation']['model_version']='3.1.0';old.pop('conservation_reference');old['saved_generation']['code_sha256'].pop('app/orbital_diagnostics.py');old['manifest_sha256']=digest({k:v for k,v in old.items() if k!='manifest_sha256'});path.write_text(json.dumps(old));energy=s.initial_energy;s.load();assert s.initial_energy==energy and s.conservation_reference['policy']=='legacy_checkpoint_new_momentum_reference' and s.conservation_reference['energy_reference_time'] is None and s.conservation_reference['time']==s.sim.t
  results.append({'atlas_copy':imported,'count':len(s.registry),'preview_read_only_binary_and_checkpoint_exact':True,'proposal_matches_applied_diagnostic_exactly':True,'physical_intervention_resets_integral_reference':True,'kinematic_edit_preserves_reference':True,'checkpoint_reference_exact':True,'generation3_1_migration_explicit':True})
 # Free translation of a one-body system follows COM drift, with no artificial recenter.
 s=Session(Path(temp)/'one',2);s.new_system({**guard(s,s.registry[0]['id'],s.registry[1]['id']),'name':'Free body','mass_kg':U['mass_unit_kg'],'position_m':[0,0,0],'velocity_m_s':[1,2,3]});s.sim.integrate(.5);one=s.state()['conservation'];assert one['SI']['barycenter_drift_norm_m']<1e-9 and math.dist(one['SI']['barycenter_m'],[v*.5*U['time_unit_s'] for v in [1,2,3]])<1e-9
report={'models':results,'invalid_read_only_requests_without_mutation':invalid,'corrupt_reference_checkpoints_without_mutation':corrupt,'one_body_COM_expected_motion':True,'scope':'Snapshot pair previews and translational conservation, no N-body extrapolation/escape guarantee.'}
(ROOT/'evidence/session-orbits-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
