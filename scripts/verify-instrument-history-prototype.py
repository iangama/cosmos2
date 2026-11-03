"""Candidate history/comparison math, independently of installed3.6 runtime."""
from pathlib import Path
import copy
import importlib.util
import json
import math
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
INSTALLED='--installed' in sys.argv
SOURCE=ROOT/('app' if INSTALLED else 'output/c211-history-staging')
sys.path.insert(0,str(ROOT/'app'))
from session import Session
from physics import PHYSICAL_SCALE as U


def module(name):
    spec=importlib.util.spec_from_file_location(name,SOURCE/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


history=module('instrument_history');comparison=module('probe_comparison')


def guard(s):
    return {'system_id':s.system_id,'edit_token':s.edit_token,'revision':s.revision,'expected_time':s.sim.t,
            'frame':s.contract()['frame'],'instruments_revision':s.instruments['revision']}


with tempfile.TemporaryDirectory() as tmp:
    s=Session(tmp,2)
    for x in (2e9,2.001e9):
        s.configure_instruments({**guard(s),'operation':'create','definition':{'name':'Ponto'+str(x),'mode':'fixed','position_m':[x,1e8,0.]}})
    reading=s.sample_instruments(guard(s));ids=[r['id'] for r in reading['readings']]
    result=comparison.compare(reading,*ids)
    assert result['distance_m']==1e6 and result['same_included_sources']
    assert result['linear_tidal_residual_norm_m_s2']/result['delta_acceleration_norm_m_s2']<.001
    assert abs(math.fsum(result['first_tidal_eigenvalues_s_2']))<1e-14*math.hypot(*result['first_tidal_eigenvalues_s_2'])
    # Different exclusions are explicit; T·dx is never represented as their model.
    changed=copy.deepcopy(reading);changed['readings'][1]['excluded_source_ids']=[s.registry[0]['id']]
    mismatch=comparison.compare(changed,*ids)
    assert not mismatch['same_included_sources'] and mismatch['linear_tidal_prediction_m_s2'] is None
    baseline=copy.deepcopy(s.state());s.sim.save_to_file(str(Path(tmp)/'before.bin'))
    value=history.configure(history.empty(),{'recording':True,'cadence_wall_s':.25})
    value=history.append(value,s.instruments,s.state(),0.)
    assert s.state()==baseline
    s.sim.save_to_file(str(Path(tmp)/'after.bin'))
    assert (Path(tmp)/'before.bin').read_bytes()==(Path(tmp)/'after.bin').read_bytes()
    for i in range(1,131):
        s.sim.integrate(i*.001)
        value=history.append(value,s.instruments,s.state(),.25 if i!=7 else 1.)
    assert len(value['samples'])==128 and value['dropped']==3 and value['next_sequence']==131
    assert value['samples'][4]['break_before']==['cadence_gap']
    validated=history.validate(value,s.issued_ids,s.sim.t,s.system_id,s.revision,s.instruments['revision'],s.contract()['frame'])
    assert validated==value and validated is not value
    assert len(json.dumps(history.curves(value)))<128000
    rejected=0
    for mutation in (lambda v:v.update(recording=1),lambda v:v.update(cadence_wall_s=.01),lambda v:v.update(dropped=1),
                     lambda v:v['samples'][0]['reading'].update(time=s.sim.t+1),
                     lambda v:v['samples'][0]['reading']['readings'][0].update(acceleration_norm_m_s2=0.),
                     lambda v:v['samples'][0]['reading']['readings'][0]['tidal_tensor_s_2'][0].__setitem__(0,1.),
                     lambda v:v['samples'][0]['integrals'].update(energy_J=1.),
                     lambda v:v['samples'][0]['reading']['source_snapshot_si'][0].update(id='not-issued')):
        bad=copy.deepcopy(value);mutation(bad)
        try:history.validate(bad,s.issued_ids,s.sim.t,s.system_id,s.revision,s.instruments['revision'],s.contract()['frame'])
        except ValueError:rejected+=1
        else:raise AssertionError('Invalid history installed')
    # Missing follow source is a stored gap, not a zero or interpolated measurement.
    s.configure_instruments({**guard(s),'operation':'create','definition':{'name':'Seguida','mode':'follow','body_id':s.registry[1]['id'],'offset_m':[1e6,0,0],'exclude_followed_source':True}})
    target=s.registry[1]['id'];s.remove_body({**guard(s),'body':target})
    value=history.append(value,s.instruments,s.state(),.25)
    assert not value['samples'][-1]['reading']['readings'][2]['available']
    assert 'state_or_instrument_definition_changed' in value['samples'][-1]['break_before']
    assert history.validate(value,s.issued_ids,s.sim.t,s.system_id,s.revision,s.instruments['revision'],s.contract()['frame'])==value
report={'status':'installed_verified' if INSTALLED else 'verified_candidate_math_only_not_installed','bounded_samples':128,'oldest_discarded_explicitly':4,
        'physical_state_and_binary_unchanged_by_recording':True,'historical_g_and_T_recomputed_from_SI_sources':True,
        'historical_integrals_recomputed_from_SI_phase':True,'corruptions_rejected':rejected,
        'different_source_exclusions_disable_tidal_prediction':True,'missing_source_and_cadence_gaps_explicit':True,
        'curves_payload_bytes':len(json.dumps(history.curves(value)).encode()),
        'nearby_probe_linear_tidal_relative_residual':result['linear_tidal_residual_norm_m_s2']/result['delta_acceleration_norm_m_s2']}
report['generation']=s.state()['scientific_generation']['model_version']
(ROOT/(f'evidence/instrument-history-installed-{s.state()["scientific_generation"]["model_version"]}-check.json' if INSTALLED else 'evidence/instrument-history-prototype-check.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
