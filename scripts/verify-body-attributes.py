"""Uncoupled radius/spin, independent rotations, continuity and checkpoint provenance."""
from pathlib import Path
import copy,json,math,sys,tempfile
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from session import Session
from physics import PHYSICAL_SCALE as U
from body_registry import digest
import body_attributes as A
from atlas import states
from atlas_import import prepare,experiment_subset

def guard(s,body):return {'system_id':s.system_id,'edit_token':s.edit_token,'revision':s.revision,'expected_time':s.sim.t,'frame':s.contract()['frame'],'body':body}
def phase(s):return [(p.m,p.x,p.y,p.z,p.vx,p.vy,p.vz) for p in s.sim.particles]
def rotation(q):return Rotation.from_quat([*q[1:],q[0]]).as_matrix()
results=[];invalid=0;corrupt=0;worst=0.
with tempfile.TemporaryDirectory() as temp:
 for imported in (False,True):
  folder=Path(temp)/str(imported);s=Session(folder,2)
  if imported:s.import_atlas(prepare(experiment_subset(states(utc='2026-10-11T12:00:00'))))
  target=s.registry[1]['id'];original=copy.deepcopy(s.atlas_initial);default=s.body_attributes[target]
  if imported:
   axes=original['bodies'][1]['shape_reference']['radii_m'];assert math.isclose(default['radius_m']**3,math.prod(axes),rel_tol=1e-14) and default['radius_origin']['kind']=='reference_volume_equivalent_sphere'
  else:assert default['radius_m'] is None
  assert default['angular_velocity_rad_s'] is None
  s.sim.integrate(.2);reference=s.sim.copy();before=phase(s);baseline=s.initial_energy;simulation=s.sim
  omega=[.0001,-.0002,.0003];s.set_attributes({**guard(s,target),'radius_m':1e7,'angular_velocity_rad_s':omega});attr=copy.deepcopy(s.body_attributes[target])
  assert phase(s)==before and s.sim is simulation and s.initial_energy==baseline
  for elapsed_si in (0.,.01,12.,100.,1e4,1e6):
   t=attr['orientation_epoch_model_time']+elapsed_si/U['time_unit_s'];q=A.orientation(attr,t);actual=rotation(q);expected=Rotation.from_rotvec(np.array(omega)*elapsed_si).as_matrix();error=float(np.max(abs(actual-expected)));worst=max(worst,error)
   assert error<1e-12,(elapsed_si,error);assert np.max(abs(actual.T@actual-np.eye(3)))<1e-14 and abs(np.linalg.det(actual)-1)<1e-14
  s.sim.integrate(.201);reference.integrate(.201);assert np.max(abs(np.array(phase(s))-phase(type('S',(),{'sim':reference})())))<1e-14
  q0=A.orientation(s.body_attributes[target],s.sim.t);s.set_attributes({**guard(s,target),'radius_m':2e7,'angular_velocity_rad_s':[-.0002,.0001,.00005]});q1=A.orientation(s.body_attributes[target],s.sim.t);assert np.max(abs(np.array(q0)-q1))<1e-14
  s.set_attributes({**guard(s,target),'radius_m':0.,'angular_velocity_rad_s':[0.,0.,0.]});assert s.body_attributes[target]['radius_m']==0 and s.body_attributes[target]['angular_velocity_rad_s']==[0,0,0]
  s.set_attributes({**guard(s,target),'radius_m':None,'angular_velocity_rad_s':None});assert s.body_attributes[target]['angular_velocity_rad_s'] is None
  for field,value in [('radius_m',True),('radius_m',-1),('radius_m',1e13),('radius_m',float('nan')),('angular_velocity_rad_s',[0,0]),('angular_velocity_rad_s',[True,0,0]),('angular_velocity_rad_s',[1e4,0,0]),('angular_velocity_rad_s',[float('inf'),0,0]),('radius_m','1'),('revision',s.revision-1),('edit_token','0'*32),('expected_time',s.sim.t+1),('body','p999')]:
   request={**guard(s,target),'radius_m':1e7,'angular_velocity_rad_s':[.001,0,0]};request[field]=value;before=copy.deepcopy(s.state())
   try:s.set_attributes(request)
   except ValueError:invalid+=1
   else:raise AssertionError((field,value))
   assert s.state()==before
  for request in [{**guard(s,target),'radius_m':1e10,'angular_velocity_rad_s':[.001,0,0]},{**guard(s,target),'radius_m':1}]:
   before=copy.deepcopy(s.state())
   try:s.set_attributes(request)
   except ValueError:invalid+=1
   else:raise AssertionError(request)
   assert s.state()==before
  # Deleted attributes remain in the intervention, and cannot migrate to a survivor.
  removed=copy.deepcopy(s.body_attributes[target]);s.remove_body(guard(s,target));assert s.interventions[-1]['removed_attributes']==removed and target not in s.body_attributes
  survivor=s.registry[0]['id'];s.set_attributes({**guard(s,survivor),'radius_m':1e6,'angular_velocity_rad_s':[0,0,.002]})
  s.save();saved=copy.deepcopy(s.state());saved_baseline=s.initial_energy;path=folder/'latest.json';manifest=json.loads(path.read_text());s.load();assert s.state()['bodies']==saved['bodies'] and s.initial_energy==saved_baseline
  reopened=Session(folder);reopened.load();assert reopened.body_attributes==s.body_attributes and reopened.atlas_initial==original
  changes=[lambda m:m['body_attributes'][survivor].update(radius_m=-1),lambda m:m['body_attributes'][survivor].update(orientation_epoch_model_time=100),lambda m:m['body_attributes'][survivor]['orientation_reference_wxyz'].__setitem__(0,2),lambda m:m['body_attributes'][survivor].update(radius_origin={'kind':'observed'}),lambda m:m['interventions'][-1]['new_attributes'].update(radius_m=2e6),lambda m:m['interventions'][-2]['removed_attributes'].update(radius_m=4),lambda m:m.pop('body_attributes')]
  for change in changes:
   bad=copy.deepcopy(manifest);change(bad);bad['manifest_sha256']=digest({k:v for k,v in bad.items() if k!='manifest_sha256'});path.write_text(json.dumps(bad));before=copy.deepcopy(s.state())
   try:s.load()
   except ValueError:corrupt+=1
   else:raise AssertionError('Attribute/history corruption accepted')
   assert s.state()==before
  path.write_text(json.dumps(manifest));assert s.atlas_initial==original
  results.append({'atlas_copy':imported,'reference_radius_or_unknown_explicit':True,'spin_null_distinct_from_zero':True,'phase_integrator_and_energy_baseline_untouched':True,'orientation_continuous_on_edit':True,'deleted_attributes_preserved_in_history':True,'checkpoint_exact_and_reopen':True,'source_unchanged':True})
 # Honest migration of a generation3.0 checkpoint has no attribute history/table.
 s=Session(Path(temp)/'old',2);s.save();path=s.directory/'latest.json';m=json.loads(path.read_text());m.pop('body_attributes');m['saved_generation']['model_version']='3.0.0';m['saved_generation']['code_sha256'].pop('app/body_attributes.py');m['manifest_sha256']=digest({k:v for k,v in m.items() if k!='manifest_sha256'});path.write_text(json.dumps(m));s.load();assert s.state()['restoration']['status']=='changed_generation' and all(a['radius_m'] is None for a in s.body_attributes.values());s.save();s.load()
report={'cases':results,'independent_Scipy_rotation_matrix_max_difference':worst,'invalid_without_mutation':invalid,'corrupt_attribute_checkpoints_without_mutation':corrupt,'generation3_0_migrates_to3_1':True,'scope':'Geometric radius/kinematic spin, no torques/J2/contact/internal-energy model; translational conservation remains separate.'}
(ROOT/'evidence/body-attributes-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
