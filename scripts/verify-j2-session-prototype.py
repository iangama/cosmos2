"""Candidate product J2 across editing, instruments, archives and validation."""
from pathlib import Path
import copy
import hashlib
import json
import math
import sys
import tempfile
import warnings

ROOT=Path(__file__).resolve().parents[1]
INSTALLED='--installed' in sys.argv
SOURCE=ROOT/('app' if INSTALLED else 'output/c211-j2-product')
sys.path[:0]=[str(SOURCE),str(ROOT/'app')]
from session import Session
from body_registry import digest
from atlas import states
from atlas_import import prepare,experiment_subset
from physics import PHYSICAL_SCALE as U
import gravity_harmonics
import gravity_field


def guard(s):return {'system_id':s.system_id,'edit_token':s.edit_token,'revision':s.revision,
                     'expected_time':s.sim.t,'frame':s.contract()['frame']}


def signature(s):
    return copy.deepcopy({k:v for k,v in s.state().items() if k not in ('branches',)})


cases=[];rejected=0;corruptions=0
with warnings.catch_warnings(record=True) as emitted:
    warnings.simplefilter('always')
    with tempfile.TemporaryDirectory() as tmp:
        for kind in ('fixture2','fixture32','atlas','single'):
            folder=Path(tmp)/kind;s=Session(folder,2 if kind=='fixture2' else 32)
            if kind=='atlas':s.import_atlas(prepare(experiment_subset(states(utc='2026-10-11T12:00:00'))))
            if kind=='single':s.new_system({**guard(s),'name':'Isolada','mass_kg':1e25,'position_m':[0.,0.,0.],'velocity_m_s':[1000.,-500.,0.]})
            source=s.registry[1 if kind=='atlas' else 0]['id']
            params={'j2':.002,'radius_eq_m':6e6 if kind in ('atlas','single') else 1e8,
                    'axis':[.3,-.4,.5],'provenance':'Modelo sintético para verificação; não parâmetro observado'}
            s.save();owner=(folder/'latest.json').read_bytes();before=signature(s)
            old=guard(s);event=s.set_j2({**guard(s),'body':source,'parameters':params})
            after=signature(s)
            assert after['bodies'][0]['position']==before['bodies'][0]['position'] and after['time']==before['time']
            assert event['external_energy_delta']==s.initial_energy-before['conservation']['current']['energy']
            assert s.gravity_effects[source]['provenance']==params['provenance'] and s.contract()['gravity']=='monopoles_plus_exterior_J2'
            assert s.state()['conservation']['angular_momentum_error_normalized'] is None
            assert (folder/'latest.json').read_bytes()==owner
            for i in range(2):
                s.configure_instruments({**guard(s),'instruments_revision':s.instruments['revision'],'operation':'create',
                    'definition':{'mode':'fixed','name':'J2 '+str(i),'position_m':[1.7e10+i*1e6,-9e9,3e9]}})
            s.configure_history({**guard(s),'instruments_revision':s.instruments['revision'],
                'history_revision':s.instrument_history['revision'],'recording':True,'cadence_wall_s':.25})
            for i in range(8):
                s.integrate((i+1)*.003)
                frozen=signature(s);a=folder/'before-query.bin';b=folder/'after-query.bin';s.sim.save_to_file(str(a))
                p=[1.7e10,-9e9,3e9]
                probe=s.probe({**guard(s),'position_m':p})
                reading=s.sample_instruments({**guard(s),'instruments_revision':s.instruments['revision']})
                assert probe['acceleration_m_s2']==reading['readings'][0]['acceleration_m_s2']
                assert probe['tidal_tensor_s_2']==reading['readings'][0]['tidal_tensor_s_2']
                assert signature(s)==frozen
                s.sim.save_to_file(str(b));assert a.read_bytes()==b.read_bytes();a.unlink();b.unlink()
                assert s.collect_history(s.state(),10+i*.3)
            assert all(any('j2' in row for row in record['reading']['source_snapshot_si']) for record in s.instrument_history['samples'])
            energy_error=s.state()['energy_error'];assert energy_error is None or energy_error<1e-10
            s.save();baseline=json.loads((folder/'latest.json').read_text());phase=signature(s)
            restored=Session(folder,2);restored.load()
            assert restored.sim==s.sim and restored.gravity_effects==s.gravity_effects
            assert restored.instrument_history==s.instrument_history and restored.conservation_reference==s.conservation_reference
            assert restored.edit_token!=s.edit_token
            for obj in (s,restored):obj.integrate(.037)
            assert restored.sim==s.sim and restored.state()['bodies']==s.state()['bodies']
            # Archives compare distinct J2 assumptions at original physical times.
            s.save();main_pointer=(folder/'latest.json').read_bytes()
            a=s.create_branch({**guard(s),'name':'Com J2'})
            active_phase=signature(s)
            s.set_j2({**guard(s),'body':source,'parameters':None})
            b=s.create_branch({**guard(s),'name':'Monopolo'})
            plain=signature(s)
            comparison=s.compare_branches({**guard(s),'first_id':a['id'],'second_id':b['id']})
            assert comparison['gravity_definition_changed'] and comparison['same_physical_instant']
            assert comparison['first_gravity_effects'] and not comparison['second_gravity_effects']
            assert signature(s)==plain and (folder/'latest.json').read_bytes()==main_pointer
            s.load_branch({**guard(s),'branch_id':a['id']})
            assert s.gravity_effects and s.state()['instrument_history']==active_phase['instrument_history']
            assert s.state()['bodies']==active_phase['bodies'] and s.state()['conservation']==active_phase['conservation']
            assert (folder/'latest.json').read_bytes()==main_pointer
            # Old request identities and malformed material/source assumptions.
            frozen=signature(s)
            for request in ({**old,'body':source,'parameters':params},
                            {**guard(s),'body':'removed','parameters':params},
                            *[{**guard(s),'body':source,'parameters':{**params,key:value}} for key,value in
                              [('j2',True),('j2',float('nan')),('j2',.11),('radius_eq_m',0.),
                               ('radius_eq_m',1e13),('axis',[0.,0.,0.]),('provenance','')]]):
                try:s.set_j2(request)
                except (ValueError,TypeError):rejected+=1
                else:raise AssertionError('Invalid or stale J2 request accepted')
                assert signature(s)==frozen
            if kind!='single':
                try:s.remove_body({**guard(s),'body':source})
                except ValueError:rejected+=1
                else:raise AssertionError('J2 source removed without explicit deactivation')
                assert signature(s)==frozen
            s.save();pointer=folder/'latest.json';baseline=json.loads(pointer.read_text())
            for mutation in ('missing_effects','changed_effects','wrong_old','wrong_new','removed_source','old_generation'):
                bad=copy.deepcopy(baseline)
                if mutation=='missing_effects':bad.pop('gravity_effects')
                elif mutation=='changed_effects':bad['gravity_effects'][source]['j2']*=2
                elif mutation=='wrong_old':bad['interventions'][0]['old_j2']=params
                elif mutation=='wrong_new':bad['interventions'][0]['new_j2']['j2']*=2
                elif mutation=='removed_source':bad['gravity_effects']['removed']=bad['gravity_effects'].pop(source)
                elif mutation=='old_generation':bad['saved_generation']['model_version']='3.8.0'
                bad['manifest_sha256']=digest({k:v for k,v in bad.items() if k!='manifest_sha256'})
                pointer.write_text(json.dumps(bad))
                try:s.load()
                except (ValueError,TypeError,KeyError):corruptions+=1
                else:raise AssertionError('Corrupt J2 history accepted: '+mutation)
                assert signature(s)==frozen
            pointer.write_text(json.dumps(baseline))
            # Edits rebind callbacks and include the quadrupole in energy deltas.
            p=s.state()['bodies'][0];before=s._energy();event=s.set_mass(p['id'],p['mass']*1.01)
            assert event['external_energy_delta']==s._energy()-before
            assert s.gravity_effects and bool(s.sim._additional_forces)
            s.integrate(s.sim.t+.001);s.save()
            s.restart_seed();assert not s.gravity_effects and not bool(s.sim._additional_forces)
            cases.append({'kind':kind,'field_probe_tensor_force_kernel':True,'readonly_queries_preserve_full_binary':True,
                          'energy_reference_intervention_and_rebind':True,'history_keeps_J2_provenance':True,
                          'checkpoint_exact_phase_and_cache_continuation':True,'branch_J2_vs_monopole_comparison_restore':True,
                          'relative_energy_error':energy_error})
    assert not emitted,[str(w.message) for w in emitted]
report={'status':'installed_J2_session_verified' if INSTALLED else 'candidate_J2_session_verified_not_installed',
        'cases':cases,'invalid_or_stale_requests_rejected':rejected,'sealed_corruptions_rejected_atomically':corruptions,
        'unhandled_warnings':len(emitted),'scope':'Exterior fixed-axis J2 only; native/UI/performance/material acceptance separate'}
(ROOT/('evidence/j2-session-installed-check.json' if INSTALLED else 'evidence/j2-session-prototype-check.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
