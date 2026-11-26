"""Candidate one-mass domain: edits/topology/migration and inertial reference."""
from pathlib import Path
import copy
import hashlib
import json
import sys
import tempfile
import warnings

ROOT=Path(__file__).resolve().parents[1]
INSTALLED='--installed' in sys.argv
SOURCE=ROOT/('app' if INSTALLED else 'output/c211-history-staging')
sys.path.insert(0,str(ROOT/'app'));sys.path.insert(0,str(SOURCE))
from session import Session
from body_registry import digest
from physics import PHYSICAL_SCALE as U


def guard(s):
    return {'system_id':s.system_id,'edit_token':s.edit_token,'revision':s.revision,'expected_time':s.sim.t,'frame':s.contract()['frame']}


def inertial(s,delta):
    body=s._bodies(s.sim,s.registry)[0];initial_t=s.sim.t
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        for i in range(1,31):s.sim.integrate(initial_t+delta*i/30)
    expected=[body['position'][k]+body['velocity'][k]*delta for k in range(3)]
    after=s._bodies(s.sim,s.registry)[0]
    error=max(abs(a-b)*U['length_unit_m'] for a,b in zip(after['position'],expected))
    assert error<1e-4 and after['velocity']==body['velocity'] and not caught
    assert s.sim.integrator.adaptive_mode=='INDIVIDUAL' and s.sim.integrator.iterations_max_exceeded==0
    return error


with tempfile.TemporaryDirectory() as temp:
    s=Session(temp,32);s.new_system({**guard(s),'name':'Inercial','mass_kg':1e25,'position_m':[3e9,-2e9,7e9],'velocity_m_s':[1200.,-3400.,500.]})
    error=inertial(s,1.)
    s.set_mass(s.registry[0]['id'],.01);error=max(error,inertial(s,.2))
    state=s.state();b=state['bodies'][0]
    s.set_body({**guard(s),'body':b['id'],'mass_kg':2e25,'position_m':[v*U['length_unit_m'] for v in b['position']], 'velocity_m_s':[800.,-200.,1700.]})
    error=max(error,inertial(s,.3));s.save();state=s.state();s.load()
    assert s.state()['bodies']==state['bodies'] and s.sim.integrator.adaptive_mode=='INDIVIDUAL'
    # An old3.6 numerical criterion is migrated with the full physical phase,
    # reference, attributes and SI origin preserved and an explicit receipt.
    s.save();path=s.directory/'latest.json';manifest=json.loads(path.read_text());original=copy.deepcopy(s.state())
    legacy_sim=s.sim.copy();legacy_sim.integrator.adaptive_mode='PRS23';binary=s.directory/manifest['binary'];legacy_sim.save_to_file(str(binary))
    manifest['sha256']=hashlib.sha256(binary.read_bytes()).hexdigest();manifest['saved_generation']['model_version']='3.6.0';manifest.pop('instrument_history')
    manifest['manifest_sha256']=digest({k:v for k,v in manifest.items() if k!='manifest_sha256'});path.write_text(json.dumps(manifest));s.load()
    assert s.state()['bodies']==original['bodies'] and s.state()['conservation']==original['conservation']
    assert s.restoration['numerical_migration']=={'domain':'one active point mass; zero external force','saved_ias15_adaptive_mode':'PRS23','current_ias15_adaptive_mode':'INDIVIDUAL','physical_phase_preserved':True}
    error=max(error,inertial(s,.2));s.save();manifest=json.loads(path.read_text());manifest['saved_generation']['model_version']='3.7.0'
    # Declaring new3.7 while carrying the old single-body criterion is rejected
    # before replacement; a recomputed seal cannot legalize a changed contract.
    legacy_sim=s.sim.copy();legacy_sim.integrator.adaptive_mode='PRS23';binary=s.directory/manifest['binary'];legacy_sim.save_to_file(str(binary));manifest['sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
    manifest['manifest_sha256']=digest({k:v for k,v in manifest.items() if k!='manifest_sha256'});path.write_text(json.dumps(manifest));before=copy.deepcopy(s.state())
    try:s.load()
    except ValueError:pass
    else:raise AssertionError('Wrong new-generation single-body criterion installed')
    assert s.state()==before
    # Add/remove returns to the correct multi/single domain without changing
    # the numerical criterion for the128-mass profile.
    event=s.create_body({**guard(s),'name':'Segunda','mass_kg':1e22,'position_m':[1.3e10,8e9,-4e9],'velocity_m_s':[0.,700.,0.]})
    assert s.sim.integrator.adaptive_mode=='PRS23'
    s.remove_body({**guard(s),'body':event['body']});assert s.sim.integrator.adaptive_mode=='INDIVIDUAL'
    error=max(error,inertial(s,.2))
    s.reset(128);assert s.sim.integrator.adaptive_mode=='PRS23'
report={'status':'installed_verified' if INSTALLED else 'candidate_single_body_policy_verified_not_installed','max_inertial_position_difference_m':error,
        'velocity_exact_no_warnings':True,'mass_phase_topology_edits_choose_correct_domain':True,
        'legacy3_6_numeric_migration_preserves_phase_and_reference':True,'wrong3_7_numeric_mode_rejected_atomically':True,
        'PRS23_for128_unchanged':True}
report['generation']=s.state()['scientific_generation']['model_version']
(ROOT/(f'evidence/single-body-session-installed-{s.state()["scientific_generation"]["model_version"]}-check.json' if INSTALLED else 'evidence/single-body-session-check.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
