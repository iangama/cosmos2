"""Semantically valid binaries with incompatible force/solver settings must refuse load."""
from pathlib import Path
import copy,hashlib,json,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from session import Session
from body_registry import digest
cases=[]
with tempfile.TemporaryDirectory() as temp:
 s=Session(temp);s.save();path=Path(temp)/'latest.json';manifest=json.loads(path.read_text());binary=Path(temp)/manifest['binary'];original=binary.read_bytes()
 for name,change in [('inactive_masses',lambda sim:setattr(sim,'N_active',1)),('softening',lambda sim:setattr(sim,'softening',.01)),('gravity_disabled',lambda sim:setattr(sim,'gravity','none')),('different_integrator',lambda sim:setattr(sim,'integrator','whfast')),('different_tolerance',lambda sim:setattr(sim.integrator,'epsilon',1e-4)),('collisions',lambda sim:setattr(sim,'collision','direct')),('different_G',lambda sim:setattr(sim,'G',2))]:
  changed=s.sim.copy();change(changed);binary.unlink();changed.save_to_file(str(binary));bad=copy.deepcopy(manifest);bad['sha256']=hashlib.sha256(binary.read_bytes()).hexdigest();bad['manifest_sha256']=digest({k:v for k,v in bad.items() if k!='manifest_sha256'});path.write_text(json.dumps(bad));before=copy.deepcopy(s.state())
  try:s.load()
  except ValueError:cases.append(name)
  else:raise AssertionError(name)
  assert s.state()==before
 binary.write_bytes(original);path.write_text(json.dumps(manifest));s.load();assert s.state()['population_contract']['active_mass_count']==32 and s.state()['population_contract']['all_active_masses_gravitate']
report={'incompatible_binaries_rejected_without_mutation':cases,'checksum_resealed_does_not_override_solver_contract':True,'all32_masses_gravitate':True}
(ROOT/'evidence/solver-contract-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
