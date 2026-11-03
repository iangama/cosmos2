"""Candidate Session recording: phase/integrator equality and atomic saves."""
from pathlib import Path
import copy
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
from atlas import states
from atlas_import import prepare,experiment_subset


def guard(s):
    return {'system_id':s.system_id,'edit_token':s.edit_token,'revision':s.revision,'expected_time':s.sim.t,
            'frame':s.contract()['frame'],'instruments_revision':s.instruments['revision'],'history_revision':s.instrument_history['revision']}


def physical(s):
    state=copy.deepcopy(s.state());state.pop('instrument_history');return state


cases=[];rejected=0;corrupt=0;warning_cases=[]
with tempfile.TemporaryDirectory() as tmp:
    for kind in ('fixture','atlas','single'):
        case_warnings=[]
        warnings.showwarning=lambda message,category,filename,lineno,file=None,line=None:case_warnings.append({'message':str(message),'category':category.__name__,'file':Path(filename).name,'line':lineno})
        warnings.simplefilter('always')
        s=Session(Path(tmp)/kind,32)
        if kind=='atlas':s.import_atlas(prepare(experiment_subset(states(utc='2026-10-11T12:00:00'))))
        if kind=='single':s.new_system({**guard(s),'name':'Isolada','mass_kg':1e25,'position_m':[0,0,0],'velocity_m_s':[0,0,0]})
        for point in ([1.7e10,-9e9,3e9],[1.7e10+1e6,-9e9,3e9]):
            s.configure_instruments({**guard(s),'operation':'create','definition':{'mode':'fixed','name':'Teste','position_m':point}})
        baseline=physical(s);control=s.sim.copy();s.save();pointer=(s.directory/'latest.json').read_bytes()
        s.configure_history({**guard(s),'recording':True,'cadence_wall_s':.25})
        assert physical(s)==baseline
        for i in range(12):
            t=(i+1)*.01;s.sim.integrate(t);control.integrate(t)
            frozen=physical(s)
            s.sim.save_to_file(str(s.directory/'before-reading.bin'))
            assert s.collect_history(s.state(),10+i*.3)
            assert physical(s)==frozen and not s.collect_history(s.state(),10+i*.3+.01)
            s.sim.save_to_file(str(s.directory/'after-reading.bin'))
            assert (s.directory/'before-reading.bin').read_bytes()==(s.directory/'after-reading.bin').read_bytes()
        s.sim.save_to_file(str(s.directory/'recorded.bin'));control.save_to_file(str(s.directory/'control.bin'))
        # Independent copies allocate particle-name pointers at different addresses;
        # REBOUND's own comparison handles those allocations. The stronger exact
        # binary check above compares the same integrator before/after each reading.
        assert s.sim==control
        assert (s.directory/'latest.json').read_bytes()==pointer
        data=s.history_curves(guard(s));sequence=data['samples'][4]['sequence']
        assert s.history_point({**guard(s),'sequence':sequence})==s.instrument_history['samples'][4]
        frozen=copy.deepcopy(s.state())
        for key,value in [('system_id','old'),('edit_token','old'),('revision',-1),('expected_time',s.sim.t+1),
                          ('frame','wrong'),('instruments_revision',-1),('history_revision',True),('history_revision',0)]:
            try:s.configure_history({**guard(s),key:value,'recording':False,'cadence_wall_s':1.})
            except ValueError:rejected+=1
            else:raise AssertionError('Old recorder request accepted')
            assert s.state()==frozen
        expected=copy.deepcopy(s.instrument_history);s.save();path=s.directory/'latest.json';manifest=json.loads(path.read_text())
        manifest['saved_generation']['model_version']='3.7.0'
        manifest['manifest_sha256']=digest({k:v for k,v in manifest.items() if k!='manifest_sha256'})
        path.write_text(json.dumps(manifest));s.load()
        assert s.instrument_history==expected and s._history_last_wall is None
        assert s.state()['bodies']==frozen['bodies'] and s.state()['conservation']==frozen['conservation']
        for mutation in (lambda m:m.pop('instrument_history'),lambda m:m.pop('field_layers'),lambda m:m.pop('instruments'),
                         lambda m:m['instrument_history']['samples'][0]['reading']['readings'][0].update(potential_J_kg=0.),
                         lambda m:m['instrument_history']['samples'][0]['integrals'].update(energy_J=1.),
                         lambda m:m['instrument_history']['samples'][0]['reading'].update(time=99.),
                         lambda m:m['instrument_history'].update(next_sequence=0)):
            bad=copy.deepcopy(manifest);mutation(bad);bad['manifest_sha256']=digest({k:v for k,v in bad.items() if k!='manifest_sha256'})
            path.write_text(json.dumps(bad));before=copy.deepcopy(s.state())
            try:s.load()
            except ValueError:corrupt+=1
            else:raise AssertionError('Resealed history corruption installed')
            assert s.state()==before
        legacy=copy.deepcopy(manifest);legacy.pop('instrument_history');legacy['saved_generation']['model_version']='3.6.0';legacy['manifest_sha256']=digest({k:v for k,v in legacy.items() if k!='manifest_sha256'})
        path.write_text(json.dumps(legacy));s.load();assert s.instrument_history['samples']==[] and not s.instrument_history['recording']
        path.write_text(json.dumps(manifest));s.load();s.restart_seed();assert s.instrument_history['samples']==[] and not s.instrument_history['recording']
        warning_cases.extend({'kind':kind,**w} for w in case_warnings)
        cases.append({'kind':kind,'recording_vs_control_REBOUND_equal':True,'own_integrator_binary_before_after_reading_exact':True,'sampling_cadence_does_not_change_integrator_targets':True,
                      'checkpoint_history_and_phase_exact':True,'legacy3_6_empty_explicit':True,'selected_original_record_exact':True})
assert not warning_cases,warning_cases
report={'status':'installed_verified' if INSTALLED else 'candidate_session_verified_not_promoted3_7','models':cases,'old_guards_rejected_atomically':rejected,
        'resealed_corrupt_or_missing_blocks_rejected_atomically':corrupt,'warning_cases':warning_cases}
report['generation']=s.state()['scientific_generation']['model_version']
(ROOT/(f'evidence/history-session-installed-{s.state()["scientific_generation"]["model_version"]}-check.json' if INSTALLED else 'evidence/history-session-prototype-check.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
