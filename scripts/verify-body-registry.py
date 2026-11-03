"""Topology transactions against independent balances, integration and sealed restores."""
from pathlib import Path
import copy,hashlib,json,math,sys,tempfile
import numpy as np
from scipy.integrate import solve_ivp
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from session import Session
from physics import PHYSICAL_SCALE as U
from body_registry import digest
from atlas import states
from atlas_import import prepare,experiment_subset,generation as atlas_generation

def guard(s):return {'system_id':s.system_id,'edit_token':s.edit_token,'revision':s.revision,'expected_time':s.sim.t,'frame':s.contract()['frame']}
def addition(s,name='Acentos: órbita "Lua" \\ teste'):
 b=s.state()['bodies'][-1]
 return {**guard(s),'name':name,'mass_kg':1e23,'position_m':[b['position'][0]*1e9+2e9,b['position'][1]*1e9+3e9,b['position'][2]*1e9+1e9],'velocity_m_s':[127.,-31.,55.]}
def frozen(s):return copy.deepcopy(s.state())
def reject(s,method,request):
 before=frozen(s)
 try:getattr(s,method)(request)
 except (ValueError,TypeError):pass
 else:raise AssertionError(('Accepted invalid',method,request))
 assert s.state()==before

def totals(state):
 bodies=state['bodies'];m=[b['mass'] for b in bodies];r=np.array([b['position'] for b in bodies]);v=np.array([b['velocity'] for b in bodies])
 energy=math.fsum(.5*b['mass']*math.fsum(x*x for x in b['velocity']) for b in bodies)-math.fsum(m[i]*m[j]/math.dist(r[i],r[j]) for i in range(len(m)) for j in range(i))
 return energy,np.array([math.fsum(m[i]*v[i,k] for i in range(len(m))) for k in range(3)]),np.array([math.fsum(m[i]*np.cross(r[i],v[i])[k] for i in range(len(m))) for k in range(3)]),math.fsum(m)
def balance(before,after,event):
 a,b=totals(before),totals(after)
 for key,index in [('external_energy_delta',0),('external_momentum_delta',1),('external_angular_momentum_delta',2),('external_mass_delta',3)]:
  difference=np.asarray(b[index])-np.asarray(a[index]);scale=max(float(np.max(np.abs(a[index]))),float(np.max(np.abs(b[index]))),1e-30)
  assert np.max(np.abs(difference-np.asarray(event[key])))<=2e-13*scale,(key,difference,event[key])
 assert event['external_mass_delta_kg']==event['external_mass_delta']*U['mass_unit_kg']
 assert event['external_energy_delta_J']==event['external_energy_delta']*U['mass_unit_kg']*U['velocity_unit_m_s']**2 or math.isclose(event['external_energy_delta_J'],event['external_energy_delta']*U['mass_unit_kg']*U['velocity_unit_m_s']**2,rel_tol=1e-15)

def independent(s):
 state=s.state();n=len(state['bodies']);m=np.array([b['mass'] for b in state['bodies']]);r=np.array([b['position'] for b in state['bodies']]);v=np.array([b['velocity'] for b in state['bodies']]);t=s.sim.t
 def rhs(_,y):
  r=y[:3*n].reshape(n,3);v=y[3*n:].reshape(n,3);a=np.zeros((n,3))
  for i in range(n):
   for j in range(n):
    if i!=j:
     d=r[j]-r[i];a[i]+=m[j]*d/np.linalg.norm(d)**3
  return np.concatenate((v.ravel(),a.ravel()))
 answer=solve_ivp(rhs,[t,t+.03],np.concatenate((r.ravel(),v.ravel())),method='DOP853',rtol=2e-13,atol=2e-15,max_step=.002)
 assert answer.success;s.sim.integrate(t+.03);actual=np.array([b['position'] for b in s.state()['bodies']]);error=float(np.max(abs(actual-answer.y[:3*n,-1].reshape(n,3)))*1e9);assert error<.01,error
 return error

results=[];invalid=0;corrupt=0
with tempfile.TemporaryDirectory() as tmp:
 for kind,count in [('fixture',32),('fixture128',128),('atlas',2),('user',2)]:
  folder=Path(tmp)/kind;s=Session(folder,count)
  if kind=='atlas':s.import_atlas(prepare(experiment_subset(states(utc='2026-10-11T12:00:00'))))
  if kind=='user':s.new_system({**guard(s),'name':'Inicial "único"','mass_kg':U['mass_unit_kg'],'position_m':[0,0,0],'velocity_m_s':[0,0,0]});assert s.initial_energy==0 and s.contract()['epoch'] is None
  original=copy.deepcopy(s.atlas_initial);start=frozen(s)
  if kind=='user':
   reject(s,'remove_body',{**guard(s),'body':s.registry[0]['id']});invalid+=1
   event=s.create_body(addition(s));balance(start,s.state(),event);start=frozen(s)
  index=len(s.registry)//2;removed=s.registry[index]['id'];survivors=[b for i,b in enumerate(start['bodies']) if i!=index]
  event=s.remove_body({**guard(s),'body':removed});after=frozen(s);balance(start,after,event)
  assert after['bodies']==survivors and after['time']==start['time'];assert removed in s.issued_ids
  stable={b['id']:(b['scene_node'],b['label_node']) for b in after['bodies']}
  event=s.create_body(addition(s));created=event['body'];after_add=frozen(s);balance(after,after_add,event)
  assert created!=removed and created not in stable and created.startswith('exp:'+s.system_id+':body:')
  assert all((b['scene_node'],b['label_node'])==stable[b['id']] for b in after_add['bodies'][:-1]);assert 'reference_id' not in after_add['bodies'][-1]
  assert s.atlas_initial==original and len(after_add['bodies'])==len(start['bodies'])
  for field,value in [('system_id','0'*32),('edit_token','0'*32),('revision',s.revision-1),('expected_time',s.sim.t+1),('frame','J2000'),('name','\ninvalid'),('name','x'*81),('mass_kg',True),('position_m',[0,0]),('velocity_m_s',[float('inf'),0,0])]:
   request=addition(s);request[field]=value;reject(s,'create_body',request);invalid+=1
  request=addition(s);request['position_m']=[v*1e9 for v in s.state()['bodies'][0]['position']];reject(s,'create_body',request);invalid+=1
  reject(s,'remove_body',{**guard(s),'body':removed});invalid+=1
  if count==128:reject(s,'create_body',addition(s));invalid+=1
  saved_state=frozen(s);stale=addition(s);s.save();manifest_file=folder/'latest.json';manifest=json.loads(manifest_file.read_text())
  s.sim.integrate(s.sim.t+.001);s.load();assert s.state()['bodies']==saved_state['bodies'] and s.atlas_initial==original and s.interventions==saved_state['interventions']
  reject(s,'create_body',stale);invalid+=1
  reopened=Session(folder,2);reopened.load();assert reopened.state()['bodies']==s.state()['bodies'] and reopened.issued_ids==s.issued_ids and reopened.seed==s.seed
  changes=[lambda m:m['registry'][0].update(id='p999'),lambda m:m['registry'][0].update(name='renamed without event'),lambda m:m.update(body_count=0),lambda m:m['issued_ids'].append(m['issued_ids'][0]),lambda m:m.update(topology_revision=0),lambda m:m['registry'][-1].update(reference_id='sol:naif:399'),lambda m:m['interventions'][-1].update(body=removed),lambda m:m['registry'].reverse(),lambda m:m['seed'].update(kind='not-a-model')]
  for change in changes:
   bad=copy.deepcopy(manifest);change(bad);bad['manifest_sha256']=digest({k:v for k,v in bad.items() if k!='manifest_sha256'});manifest_file.write_text(json.dumps(bad));before=frozen(s)
   try:s.load()
   except ValueError:corrupt+=1
   else:raise AssertionError(('Resealed corruption accepted',kind,bad))
   assert s.state()==before
  bad=copy.deepcopy(manifest);bad['registry'][0]['name']='wrong seal';manifest_file.write_text(json.dumps(bad));before=frozen(s)
  try:s.load()
  except ValueError:corrupt+=1
  else:raise AssertionError('Metadata seal ignored')
  assert s.state()==before;manifest_file.write_text(json.dumps(manifest))
  error=independent(s) if kind in ('atlas','user') else None
  sid=s.system_id;s.restart_seed();assert s.system_id!=sid and s.revision==0 and len(s.registry)==(3 if kind=='atlas' else 1 if kind=='user' else count) and s.atlas_initial==original
  results.append({'model':kind,'stable_survivors':True,'no_reused_ID':True,'independent_mass_E_P_L':True,'exact_checkpoint_reopen':True,'initial_source_preserved':True,'DOP853_post_topology_max_component_m':error,'restart_original_seed':True})
 # Actual old schemas, followed by conversion to3. Neither loader uses current row indices as IDs.
 legacy=[]
 for schema in (1,2):
  folder=Path(tmp)/('legacy'+str(schema));s=Session(folder,2)
  if schema==2:s.import_atlas(prepare(experiment_subset(states(utc='2026-10-11T12:00:00'))))
  s.set_mass(s.registry[0]['id'],1.2);s.save();path=folder/'latest.json';m=json.loads(path.read_text());m['schema']=schema
  for key in ('system_id','registry','issued_ids','seed','topology_revision'):m.pop(key)
  for event in m['interventions']:event.pop('system_id',None)
  if schema==1:
   for key in ('manifest_sha256','saved_generation','body_count'):m.pop(key)
  else:
   m['saved_generation']=atlas_generation();m['manifest_sha256']=digest({k:v for k,v in m.items() if k!='manifest_sha256'})
  path.write_text(json.dumps(m));expected=s.state()['bodies'];s.reset(32);s.load();assert s.state()['bodies']==expected
  s.save();s.load();assert s.state()['bodies']==expected;legacy.append(schema)
report={'models':results,'invalid_without_mutation':invalid,'corrupt_or_incoherent_checkpoints_without_mutation':corrupt,'legacy_schemas_converted_to3':legacy,'scope':'Second C2-06 slice: 1–128 active point masses; creation/removal/stable registry. Radius/spin/orbit previews still pending.'}
(ROOT/'evidence/body-registry-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
