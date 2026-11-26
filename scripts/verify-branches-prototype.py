"""Candidate immutable branches; run separately from native frame measurement."""
from pathlib import Path
import copy
import hashlib
import json
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
INSTALLED='--installed' in sys.argv
SOURCE=ROOT/('app' if INSTALLED else 'output/c211-branches-staging')
sys.path.insert(0,str(ROOT/'app'));sys.path.insert(0,str(SOURCE))
from session import Session
from branch_store import Store
from body_registry import digest
from atlas import states
from atlas_import import prepare,experiment_subset
from physics import PHYSICAL_SCALE as U

def guard(s):
    return {'system_id':s.system_id,'edit_token':s.edit_token,'revision':s.revision,'expected_time':s.sim.t,'frame':s.contract()['frame']}

def physical(s):
    value=copy.deepcopy(s.state());value.pop('branches',None);return value

def bytes_digest(folder):
    return {str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}

cases=[];rejected=0
with tempfile.TemporaryDirectory() as temp:
    for kind in ('fixture2','fixture32','atlas','single'):
        folder=Path(temp)/kind;s=Session(folder,2 if kind=='fixture2' else 32)
        if kind=='atlas':s.import_atlas(prepare(experiment_subset(states(utc='2026-10-11T12:00:00'))))
        if kind=='single':s.new_system({**guard(s),'name':'Inercial','mass_kg':1e25,'position_m':[0.,0.,0.],'velocity_m_s':[1000.,-500.,0.]})
        for i in range(2):s.configure_instruments({**guard(s),'instruments_revision':s.instruments['revision'],'operation':'create',
            'definition':{'name':'Ramo '+str(i),'mode':'fixed','position_m':[1.7e10+i*1e6,-9e9,3e9]}})
        s.configure_history({**guard(s),'instruments_revision':s.instruments['revision'],'history_revision':s.instrument_history['revision'],
            'recording':True,'cadence_wall_s':.25})
        for i in range(8):s.sim.integrate(.001*(i+1));s.collect_history(s.state(),10+i*.3)
        s.save();owner_pointer=(folder/'latest.json').read_bytes();before=physical(s);control=s.sim.copy()
        store=s._branches()
        s.sim.save_to_file(str(folder/'before.bin'))
        a=store.create(s,{**guard(s),'name':'Base "A" \\'})
        assert physical(s)==before and s.sim==control and (folder/'latest.json').read_bytes()==owner_pointer
        s.sim.save_to_file(str(folder/'after.bin'))
        assert (folder/'before.bin').read_bytes()==(folder/'after.bin').read_bytes()
        archive_before=bytes_digest(folder/'branches')
        old_mass=s.sim.particles[0].m;s.set_mass(s.registry[0]['id'],old_mass*1.01)
        b=store.create(s,{**guard(s),'name':'Massa aumentada'})
        assert b['parent_id']==a['id'] and b['parent_sha256']==a['record_sha256']
        frozen=physical(s);s.sim.save_to_file(str(folder/'before-compare.bin'))
        compared=store.compare(s,{**guard(s),'first_id':a['id'],'second_id':b['id']})
        assert compared['same_physical_instant'] and physical(s)==frozen
        assert compared['body_differences'][0]['delta_position_m']==[0.,0.,0.]
        assert compared['body_differences'][0]['delta_mass_kg']==(old_mass*1.01-old_mass)*U['mass_unit_kg']
        assert compared['first_curves']==compared['second_curves'] and len(compared['first_curves']['samples'])==8
        s.sim.save_to_file(str(folder/'after-compare.bin'))
        assert (folder/'before-compare.bin').read_bytes()==(folder/'after-compare.bin').read_bytes()
        assert all(bytes_digest(folder/'branches')[p]==v for p,v in archive_before.items())
        store.load(s,{**guard(s),'branch_id':a['id']})
        assert s.state()['bodies']==before['bodies'] and s.sim.t==before['time'] and s.state()['conservation']==before['conservation']
        assert s.instrument_history['samples'] and s.state()['instruments']==before['instruments'] and s.sim==control
        assert s.edit_token!=before['edit_token'] and (folder/'latest.json').read_bytes()==owner_pointer
        # Reusing a pre-switch editor request cannot overwrite the restored branch.
        frozen=physical(s)
        try:store.create(s,{**guard(s),'edit_token':before['edit_token'],'name':'Antigo'})
        except ValueError:rejected+=1
        else:raise AssertionError('Old pre-switch command accepted')
        assert physical(s)==frozen
        s.sim.integrate(s.sim.t+.01);s.collect_history(s.state(),30.)
        later=store.create(s,{**guard(s),'name':'Outro instante'})
        unequal=store.compare(s,{**guard(s),'first_id':a['id'],'second_id':later['id']})
        assert not unequal['same_physical_instant'] and all('delta_position_m' not in r for r in unequal['body_differences'])
        assert unequal['first_curves']['samples'][-1]['time_s']<unequal['second_curves']['samples'][-1]['time_s']
        reopened=Store(folder/'branches');assert len(reopened.records)==3
        frozen=physical(s)
        for identifier in ('../../latest','branch:'+'0'*32,True):
            try:reopened.load(s,{**guard(s),'branch_id':identifier})
            except ValueError:rejected+=1
            else:raise AssertionError('Invalid branch identity accepted')
            assert physical(s)==frozen
        a_folder=folder/'branches'/a['id'].split(':')[1]
        binary=a_folder/json.loads((a_folder/'latest.json').read_text())['binary'];data=binary.read_bytes();binary.write_bytes(data+b'corrupt')
        try:reopened.load(s,{**guard(s),'branch_id':a['id']})
        except ValueError:rejected+=1
        else:raise AssertionError('Corrupt branch binary installed')
        assert physical(s)==frozen;binary.write_bytes(data)
        receipt_path=a_folder/'branch.json';receipt=receipt_path.read_bytes();bad=json.loads(receipt);bad['time']+=.001
        bad['record_sha256']=digest({k:v for k,v in bad.items() if k!='record_sha256'});receipt_path.write_text(json.dumps(bad))
        # This creates an otherwise intact standalone catalog with a falsely
        # resealed receipt time. The physical archive must reject it pre-install.
        standalone=Path(temp)/(kind+'-false-time');standalone.mkdir()
        import shutil
        shutil.copytree(a_folder,standalone/a_folder.name)
        false_store=Store(standalone)
        try:false_store.load(s,{**guard(s),'branch_id':a['id']})
        except ValueError:rejected+=1
        else:raise AssertionError('False receipt time replaced physical session')
        assert physical(s)==frozen;receipt_path.write_bytes(receipt)
        assert (folder/'latest.json').read_bytes()==owner_pointer
        cases.append({'kind':kind,'immutable_fork_integrator_phase_and_owner_pointer_preserved':True,
            'same_origin_named_parent_lineage_and_reopen':True,'equal_time_SI_endpoint_differences':True,
            'different_times_never_subtracted_or_interpolated':True,'comparison_own_integrator_binary_exact':True,
            'restore_phase_reference_history_definitions_exact':True,'corrupt_binary_false_time_and_stale_commands_atomic':True})
report={'status':'installed3_8_branch_archives_verified' if INSTALLED else 'candidate_branch_archives_verified_not_installed','cases':cases,'rejected_without_mutation':rejected,
    'scope':'Immutable archive/restore/compare core only; no installed UI or native branch acceptance'}
(ROOT/('evidence/branches-installed-check.json' if INSTALLED else 'evidence/branches-prototype-check.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
