"""Joint cloud Session: Kepler oracle, atomic archive, source roles and immutable branches."""
from pathlib import Path
import copy
import hashlib
import json
import math
import sys
import tempfile
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/('app' if '--installed' in sys.argv else 'output/c211-cloud-product/app')
sys.path.insert(0,str(SOURCE))
from session import Session
from body_registry import digest
from physics import PHYSICAL_SCALE as U

def guard(s):
    return {'system_id':s.system_id,'edit_token':s.edit_token,'revision':s.revision,
            'expected_time':s.sim.t,'frame':s.contract()['frame']}

def phase(s):
    return (s.sim.__reduce__()[1][0],None if s._cloud is None else s._cloud.driver.sim.__reduce__()[1][0],
            s.system_id,s.edit_token,s.revision,copy.deepcopy(s.interventions),copy.deepcopy(s.instrument_history))

def exact_joint_phase(a,b):
    assert a._cloud.driver.sim.t==b._cloud.driver.sim.t
    for x,y in zip(a._cloud.driver._arrays(),b._cloud.driver._arrays()):
        assert np.array_equal(x,y)

began=time.perf_counter();refused=[];corruptions=[]
with tempfile.TemporaryDirectory(prefix='cosmos2-cloud-session-') as folder:
    s=Session(folder,2)
    s.load_cloud_experiment({**guard(s),'parameters':{'count':10000}})
    source=s.registry[0]['id'];cloud_id=s._cloud.id
    assert s.sim.N==1 and s._cloud.driver.sim.N==10001
    initial=s.state()
    assert len(initial['bodies'])==1 and initial['population_contract']['active_mass_count']==1
    assert initial['test_particle_cloud']['test_particles']==10000
    assert not initial['population_contract']['test_particles_are_field_sources']
    assert len(json.dumps(initial))<40000,'Public state must not embed the12MB IAS15 sidecar or10k phases'
    radius=np.linspace(1.,4.,10000)
    angle=(np.arange(10000)*math.pi*(3-math.sqrt(5)))%(2*math.pi)
    worst=0.
    for target in (2*math.pi,20*math.pi):
        s.integrate(target)
        theta=angle+target/radius**1.5
        expected=np.column_stack((radius*np.cos(theta),radius*np.sin(theta),np.zeros(10000)))
        worst=max(worst,float(np.max(np.linalg.norm(s._cloud.driver.positions()-expected,axis=1)/radius)))
        assert s._phase(s.sim.particles[0])=={'mass':1.,'position':[0.,0.,0.],'velocity':[0.,0.,0.]}
    assert worst<2e-10,worst
    frozen=phase(s)
    point=s.cloud_point({**guard(s),'cloud_id':cloud_id,'index':9999})
    assert point['id']=='tp:'+cloud_id+':9999' and point['mass_kg']==0. and point['source_id']==source
    assert math.isclose(point['specific_energy_J_kg'],-.5/4*U['velocity_unit_m_s']**2,rel_tol=2e-10)
    assert phase(s)==frozen
    s.configure_instruments({**guard(s),'instruments_revision':0,'operation':'create',
        'definition':{'mode':'fixed','name':'Campo da fonte','position_m':[2e9,0.,0.]}})
    read=s.sample_instruments({**guard(s),'instruments_revision':s.instruments['revision']})
    assert read['source_ids']==[source]
    assert np.allclose(read['readings'][0]['acceleration_m_s2'],[-U['nominal_GM_unit_m3_s2']/4e18,0.,0.],rtol=1e-14,atol=0.)
    s.configure_history({**guard(s),'instruments_revision':s.instruments['revision'],'history_revision':0,'recording':True,'cadence_wall_s':.25})
    s.collect_history(s.state(),1.)
    s.save();pointer=Path(folder)/'latest.json';saved=pointer.read_bytes();manifest=json.loads(saved)
    binary=Path(folder)/manifest['test_particle_cloud']['binary']
    assert binary.stat().st_size>10_000_000
    t=Session(folder,2);t.load()
    assert t._cloud.id==cloud_id and t.edit_token!=s.edit_token
    exact_joint_phase(s,t)
    assert t.instrument_history==s.instrument_history
    for target in (s.sim.t+.01,s.sim.t+.1,s.sim.t+1.):
        s.integrate(target);t.integrate(target)
        exact_joint_phase(s,t)
        assert t._phase(t.sim.particles[0])==s._phase(s.sim.particles[0])

    def reject(label,operation):
        before=phase(s)
        try:operation()
        except (ValueError,TypeError,KeyError):refused.append(label)
        else:raise AssertionError('Accepted invalid cloud operation: '+label)
        assert phase(s)==before,label
    reject('mass edit',lambda:s.set_mass(source,.2))
    reject('phase edit',lambda:s.set_body({**guard(s),'body':source,'GM_m3_s2':U['nominal_GM_unit_m3_s2'],'position_m':[0.,0.,0.],'velocity_m_s':[1.,0.,0.]}))
    reject('topology edit',lambda:s.create_body({**guard(s),'name':'Extra','GM_m3_s2':1e12,'position_m':[2e9,0.,0.],'velocity_m_s':[0.,0.,0.]}))
    reject('J2',lambda:s.set_j2({**guard(s),'body':source,'parameters':{'j2':.001,'radius_eq_m':1e6,'axis':[0.,0.,1.],'provenance':'test'}}))
    reject('material',lambda:s.set_tides({**guard(s),'body':source,'parameters':{}}))
    reject('reconfigure active',lambda:s.set_cloud({**guard(s),'parameters':{'count':128}}))
    for key,value in [('system_id','0'*32),('edit_token','0'*32),('revision',0),('expected_time',0.),('frame','other')]:
        reject('stale '+key,lambda k=key,v=value:s.set_cloud({**guard(s),k:v,'parameters':None}))
    for index in (True,-1,10000,1.2,None):
        reject('invalid particle '+str(index),lambda i=index:s.cloud_point({**guard(s),'cloud_id':cloud_id,'index':i}))
    reject('old cloud identity',lambda:s.cloud_point({**guard(s),'cloud_id':'0'*32,'index':0}))

    def corrupt(label,change):
        value=copy.deepcopy(manifest);change(value)
        value['manifest_sha256']=digest({k:v for k,v in value.items() if k!='manifest_sha256'})
        pointer.write_text(json.dumps(value))
        before=phase(s)
        try:s.load()
        except (ValueError,TypeError,KeyError,OSError):corruptions.append(label)
        else:raise AssertionError('Accepted cloud checkpoint corruption: '+label)
        assert phase(s)==before,label
    corrupt('missing cloud',lambda v:v.pop('test_particle_cloud'))
    corrupt('silently disabled',lambda v:v.__setitem__('test_particle_cloud',None))
    corrupt('cloud identity',lambda v:v['test_particle_cloud'].__setitem__('cloud_id','0'*32))
    corrupt('binary path traversal',lambda v:v['test_particle_cloud'].__setitem__('binary','../other.bin'))
    corrupt('extra descriptor',lambda v:v['test_particle_cloud'].__setitem__('extra',0))
    corrupt('count',lambda v:v['test_particle_cloud']['driver']['configuration'].__setitem__('count',9999))
    corrupt('source',lambda v:v['test_particle_cloud']['driver'].__setitem__('source_id','other'))
    corrupt('time',lambda v:v['test_particle_cloud']['driver'].__setitem__('confirmed_time',0.))
    corrupt('activation absent',lambda v:v['interventions'][0].__setitem__('new_cloud_origin',None))
    corrupt('activation time',lambda v:v['interventions'][0].__setitem__('time',1.))
    corrupt('injected source energy',lambda v:v['interventions'][0].__setitem__('external_energy_delta',1.))
    corrupt('contract',lambda v:v['contract'].__setitem__('test_particle_model','other'))
    corrupt('old generation declaring cloud',lambda v:v['saved_generation'].__setitem__('model_version','3.12.0'))
    raw=binary.read_bytes();binary.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
    pointer.write_bytes(saved);before=phase(s)
    try:s.load()
    except ValueError:corruptions.append('binary corruption')
    else:raise AssertionError('Accepted corrupted joint IAS15 binary')
    assert phase(s)==before;binary.write_bytes(raw)
    first=s.create_branch({**guard(s),'name':'Com dez mil partículas'})
    s.set_cloud({**guard(s),'parameters':None})
    assert s._cloud is None and s.sim.integrator.adaptive_mode=='INDIVIDUAL'
    second=s.create_branch({**guard(s),'name':'Só fonte'})
    assert pointer.read_bytes()==saved
    comparison=s.compare_branches({**guard(s),'first_id':first['id'],'second_id':second['id']})
    assert comparison['test_cloud_definition_changed'] and comparison['same_physical_instant']
    s.load_branch({**guard(s),'branch_id':first['id']});assert s._cloud.id==cloud_id
    s.restart_seed();assert s._cloud is not None and s._cloud.id!=cloud_id and s.sim.t==0.
    reject('old individual ID after restart',lambda:s.cloud_point({**guard(s),'cloud_id':cloud_id,'index':0}))
    s.set_cloud({**guard(s),'parameters':None});s.integrate(1.);s.set_mass(s.registry[0]['id'],.2);s.save();t.load();assert t._cloud is None
    s.load_cloud_experiment({**guard(s),'parameters':{'count':128}});s.load();assert s._cloud is None
    s.reset(256);assert s._cloud is None and s.sim.N==256
    for count in (False,0,10001,3.5):
        reject('invalid count '+str(count),lambda n=count:s.load_cloud_experiment({**guard(s),'parameters':{'count':n}}))

report={'status':'joint_cloud_session_verified_not_installed','test_particles':10000,'active_sources':1,
    'analytic_Kepler_max_relative_position_error':worst,'source_mirror_never_independently_advanced':True,
    'source_only_field_readings_and_history':True,'individual_selection_SI_and_identity':True,
    'three_joint_IAS15_future_states_exact':True,'guards_refused':refused,'corruptions_refused_atomically':corruptions,
    'branches_retain_joint_state_and_compare_definitions':True,'restart_new_particle_namespace':True,
    'plain_load_reset_clear_cloud':True,'checkpoint_binary_bytes':len(raw),'elapsed_s':time.perf_counter()-began,
    'scope':'Isolated Session candidate; worker, live native transport/selection and10k performance still pending.'}
(ROOT/'evidence/cloud-session-prototype-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
