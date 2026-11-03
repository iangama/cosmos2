"""Candidate passive orbital instruments: exact solver, history and archives."""
from pathlib import Path
import copy,hashlib,json,math,sys,tempfile,time
ROOT=Path(__file__).resolve().parents[1];INSTALLED='--installed' in sys.argv
SOURCE=ROOT/('app' if INSTALLED else 'output/c211-resonances-product/app')
sys.path.insert(0,str(SOURCE))
from session import Session
from body_registry import digest
from material_driver import phase
import orbital_instruments as tools

def guard(s):return {'system_id':s.system_id,'edit_token':s.edit_token,'revision':s.revision,'expected_time':s.sim.t,'frame':s.contract()['frame'],'orbital_revision':s.orbital_instruments['revision']}
def configure(s,**parameters):return s.configure_orbital_instruments({**guard(s),**parameters})
began=time.perf_counter();cases=[];rejected=corrupted=0
with tempfile.TemporaryDirectory(prefix='cosmos2-resonance-session-') as folder:
    for preset in ('resonant2','circulating18'):
        directory=Path(folder)/preset;s=Session(directory,2);s.load_resonant_experiment({**guard(s),'preset':preset})
        assert s.sim.N==3 and s.revision==0 and not s.interventions and str(s.sim.integrator)=='ias15' and not bool(s.sim._additional_forces)
        definition=copy.deepcopy(s.orbital_instruments['definition']);binary=s.sim.__reduce__()[1][0];baseline=s.initial_energy;reference=copy.deepcopy(s.conservation_reference)
        read=s.sample_orbital_instruments(guard(s));assert read['available']
        ratio=2. if preset=='resonant2' else 1.8
        assert abs(read['result']['outer_to_inner_period_ratio']-ratio)<1e-12
        configure(s,operation='align_plane',definition=definition)
        configure(s,operation='capture',recording=True,cadence_wall_s=.25)
        assert not s.instruments['probes'] # orbital capture is independent of gravity probes
        s.sample_orbital_instruments(guard(s));s.orbital_curves(guard(s));s.orbital_export(guard(s))
        assert s.sim.__reduce__()[1][0]==binary and s.initial_energy==baseline and s.conservation_reference==reference
        control=s.sim.copy()
        for i in range(140):
            target=(i+1)*.1;s.integrate(target);control.integrate(target)
            assert s.collect_orbital_history(s.state(),i*.25)
            assert not s.collect_orbital_history(s.state(),i*.25)
            assert phase(s.sim)==phase(control)
        h=s.orbital_instruments;assert len(h['samples'])==128 and h['dropped']==12 and h['next_sequence']==140
        tools.validate(h,s.issued_ids,s.sim.t,s.system_id,s.revision,s.contract()['frame'])
        saved_h=copy.deepcopy(h);before=s.sim.__reduce__()[1][0]
        record=s.orbital_point({**guard(s),'sequence':h['dropped']})
        assert record==h['samples'][0]
        s.save();manifest=json.loads((directory/'latest.json').read_text())
        assert s.sim.__reduce__()[1][0]==before
        restored=Session(directory,2);restored.load()
        assert restored.orbital_instruments==h and phase(restored.sim)==phase(s.sim)
        for target in (14.1,15.,17.):
            s.integrate(target);restored.integrate(target)
            assert phase(s.sim)==phase(restored.sim)
        frozen=s.sim.__reduce__()[1][0];old_h=copy.deepcopy(s.orbital_instruments)
        for change in ({'orbital_revision':True},{'orbital_revision':-1},{'revision':-1},{'expected_time':-1.},{'system_id':'0'*32},{'frame':'other'}):
            try:s.configure_orbital_instruments({**guard(s),**change,'operation':'definition','definition':definition})
            except (ValueError,TypeError):rejected+=1
            else:raise AssertionError('Old orbital form accepted')
            assert s.sim.__reduce__()[1][0]==frozen and s.orbital_instruments==old_h
        for key,value in [('j',True),('j',1),('j',10),('primary_id',definition['inner_id']),('outer_id','missing'),('plane_normal',[0.,0.,0.]),('plane_reference',[0.,0.,1.])]:
            try:configure(s,operation='definition',definition={**definition,key:value})
            except (ValueError,TypeError):rejected+=1
            else:raise AssertionError('Invalid orbital definition accepted: '+key)
            assert s.sim.__reduce__()[1][0]==frozen and s.orbital_instruments==old_h
        mutations=['missing','definition','event','sequence','sample_angle','sample_ratio','source_GM','source_position','sample_time','frame','active_ids','SI_order','cadence','record_config','generation','false_gap']
        for mutation in mutations:
            bad=copy.deepcopy(manifest);cfg=bad['orbital_instruments'];row=cfg['samples'][0];reading=row['reading']
            if mutation=='missing':bad.pop('orbital_instruments')
            elif mutation=='definition':cfg['definition']['j']=3
            elif mutation=='event':cfg['events'][0]['definition']['outer_id']=definition['primary_id']
            elif mutation=='sequence':row['sequence']+=1
            elif mutation=='sample_angle':reading['result']['critical_angles'][0]['angle_rad']+=.001
            elif mutation=='sample_ratio':reading['result']['outer_to_inner_period_ratio']+=.001
            elif mutation=='source_GM':reading['selected_phase_si'][1]['GM_m3_s2']*=2
            elif mutation=='source_position':reading['selected_phase_si'][1]['position_m'][0]+=1e6
            elif mutation=='sample_time':reading['time']=1e10
            elif mutation=='frame':reading['frame']='other'
            elif mutation=='active_ids':reading['active_ids'][1]=reading['active_ids'][0]
            elif mutation=='SI_order':reading['selected_phase_si'].reverse()
            elif mutation=='cadence':row['cadence_wall_s']=5.
            elif mutation=='record_config':reading['configuration_revision']=0
            elif mutation=='generation':reading['scientific_generation']['model_version']='3.10.0'
            elif mutation=='false_gap':row['break_before']=['invented']
            bad['manifest_sha256']=digest({k:v for k,v in bad.items() if k!='manifest_sha256'})
            (directory/'latest.json').write_text(json.dumps(bad))
            try:s.load()
            except (ValueError,TypeError,KeyError):corrupted+=1
            else:raise AssertionError('Resealed orbital corruption accepted: '+mutation)
            assert s.sim.__reduce__()[1][0]==frozen and s.orbital_instruments==old_h
        (directory/'latest.json').write_text(json.dumps(manifest))
        pointer=(directory/'latest.json').read_bytes()
        first=s.create_branch({**guard(s),'name':'Ângulos originais'})
        configure(s,operation='definition',definition={**definition,'j':3})
        s.integrate(18.);assert s.collect_orbital_history(s.state(),100.)
        assert s.orbital_instruments['samples'][-1]['break_before']
        second=s.create_branch({**guard(s),'name':'Razão diferente'})
        comparison=s.compare_branches({**guard(s),'first_id':first['id'],'second_id':second['id']})
        assert comparison['orbital_definition_changed'] and not comparison['same_physical_instant']
        assert comparison['first_orbital_curves']['samples'][-1]['time_s']!=comparison['second_orbital_curves']['samples'][-1]['time_s']
        assert (directory/'latest.json').read_bytes()==pointer
        s.load_branch({**guard(s),'branch_id':first['id']});assert s.orbital_instruments==old_h
        # A definition retains a removed identity and becomes unavailable,
        # even after another new body is appended in the same particle slot.
        removed=definition['outer_id'];s.remove_body({**guard(s),'body':removed})
        s.integrate(s.sim.t+.1);s.collect_orbital_history(s.state(),101.)
        assert not s.orbital_instruments['samples'][-1]['reading']['available']
        s.create_body({**guard(s),'name':'Substituto','mass_kg':1e20,'position_m':[2e9,0.,0.],'velocity_m_s':[0.,1e4,0.]})
        s.integrate(s.sim.t+.1);s.collect_orbital_history(s.state(),102.)
        assert not s.orbital_instruments['samples'][-1]['reading']['available']
        s.save();restored.load();assert restored.orbital_instruments==s.orbital_instruments
        configure(s,operation='clear');assert not s.orbital_instruments['samples'] and s.orbital_instruments['next_sequence']==0
        s.restart_seed();assert s.sim.N==3 and s.sim.t==0. and s.orbital_instruments['definition'] is not None and not s.orbital_instruments['recording']
        cases.append({'preset':preset,'read_config_record_queries_preserve_same_integrator_binary':True,'recording_vs_control_REBOUND_exact':True,'128_record_ring_and_original_point':True,'save_load_continuation_exact':True,'branch_definitions_original_times_and_owner_pointer_preserved':True,'removed_identity_is_gap_not_reassigned':True})
report={'status':'installed_orbital_instruments_session_verified' if INSTALLED else 'candidate_orbital_instruments_session_verified_not_installed','cases':cases,'invalid_or_stale_commands_rejected':rejected,'sealed_corruptions_rejected_atomically':corrupted,'elapsed_s':time.perf_counter()-began,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.glob('*.py')},'scope':'Read-only orbital measurements; no added resonance force, automatic libration classifier or permanent capture assertion; worker/native/performance separate'}
(ROOT/('evidence/resonance-session-installed-check.json' if INSTALLED else 'evidence/resonance-session-prototype-check.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'},indent=2),flush=True)
