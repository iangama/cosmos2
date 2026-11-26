"""Candidate material Session: fields/history/branches/checkpoints and guards."""
from pathlib import Path
import copy,hashlib,json,math,sys,tempfile,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
INSTALLED='--installed' in sys.argv
SOURCE=ROOT/('app' if INSTALLED else 'output/c211-tides-product/app')
sys.path.insert(0,str(SOURCE))
from session import Session
from physics import PHYSICAL_SCALE as U
from body_registry import digest
from material_driver import phase
import gravity_field
import orbital_diagnostics
import material_tides

M=m=1e25;R=1e7;a=1e8;n=math.sqrt(U['G_m3_kg_s2']*(M+m)/a**3)
period=2*math.pi/n/U['time_unit_s']
cfg={'radius_m':R,'love_k2':.3,'time_lag_s':.003/n,'inertia_kg_m2':.33*M*R*R,'spin_rad_s':(np.array([.25,.1,1.4])*n).tolist(),'provenance':'Synthetic material Session test; no observed interior'}

def identity(s):return {'system_id':s.system_id,'edit_token':s.edit_token,'revision':s.revision,'expected_time':s.sim.t,'frame':s.contract()['frame']}
def fixture(s):
    v=.5*math.sqrt(1.2/.8)*a*n/U['velocity_unit_m_s']
    s._new_population([{'name':'Material sintético','mass':M/U['mass_unit_kg'],'position':[-.4*a/U['length_unit_m'],0.,0.],'velocity':[0.,-v,0.]},{'name':'Companheiro pontual','mass':m/U['mass_unit_kg'],'position':[.4*a/U['length_unit_m'],0.,0.],'velocity':[0.,v,0.]}])

began=time.perf_counter();guards=[];corruptions=[]
with tempfile.TemporaryDirectory(prefix='cosmos2-material-session-') as folder:
    s=Session(folder,2);fixture(s);source,companion=[b['id'] for b in s.registry]
    s.set_tides({**identity(s),'body':source,'parameters':cfg})
    assert s.state()['integrator']=='BS joint orbit/spin/heat'
    assert s._tides is not None and not s.gravity_effects
    s.configure_instruments({**identity(s),'instruments_revision':0,'operation':'create','definition':{'name':'Companheiro','mode':'follow','body_id':companion,'offset_m':[0.,0.,0.],'exclude_followed_source':True}})
    s.configure_history({**identity(s),'instruments_revision':s.instruments['revision'],'history_revision':0,'recording':True,'cadence_wall_s':.25})
    frozen=s._tides.checkpoint();mirror=s.sim.__reduce__()[1][0]
    read=s.sample_instruments({**identity(s),'instruments_revision':s.instruments['revision']})
    b=s._physical_bodies();p=b[1];point=[v*U['length_unit_m'] for v in p['position']]
    field=gravity_field.evaluate([b[0]],point)
    assert read['readings'][0]['acceleration_m_s2']==field['acceleration_m_s2']
    monopole=gravity_field.evaluate([{k:v for k,v in b[0].items() if k!='tide'}],point)
    delta=np.array(field['acceleration_m_s2'])-monopole['acceleration_m_s2']
    expected=np.array(s._tides.material()['force_on_companion_N'])/m
    assert np.linalg.norm(delta-expected)<1e-10*np.linalg.norm(expected)
    assert s._tides.checkpoint()==frozen and s.sim.__reduce__()[1][0]==mirror
    orbit=s.orbit({**identity(s),'body':companion,'primary':source})
    assert orbit['before']['perturbation_relative_acceleration_ratio']>0 and 'material tide' in orbit['before']['model']
    for i,target in enumerate(np.linspace(0.,4*period,17)[1:]):
        s.integrate(float(target));state=s.state();s.collect_history(state,float(i))
        assert state['energy_error']<1e-9 and state['conservation']['angular_momentum_error_normalized']<1e-9
    assert len(s.instrument_history['samples'])==16
    s.save();saved=json.loads((Path(folder)/'latest.json').read_text());expected_state=s.state();checkpoint=s._tides.checkpoint()
    t=Session(folder,2);t.load()
    assert t._tides.values().tolist()==s._tides.values().tolist() and phase(t.sim)==phase(s.sim)
    assert t.instrument_history==s.instrument_history
    for target in [4.1*period,4.5*period]:
        s.integrate(target);t.integrate(target)
        assert phase(s.sim)==phase(t.sim) and s._tides.values().tolist()==t._tides.values().tolist()

    def rejected(label,operation):
        before=s._tides.checkpoint();rev=s.revision;hist=copy.deepcopy(s.instrument_history)
        try:operation()
        except (ValueError,TypeError,KeyError):guards.append(label)
        else:raise AssertionError('Guard accepted: '+label)
        assert s._tides.checkpoint()==before and s.revision==rev and s.instrument_history==hist
    rejected('old revision',lambda:s.set_tides({**identity(s),'revision':s.revision-1,'body':source,'parameters':None}))
    rejected('unknown source',lambda:s.set_tides({**identity(s),'body':'other','parameters':None}))
    rejected('wrong source disable',lambda:s.set_tides({**identity(s),'body':companion,'parameters':None}))
    rejected('in-place material reconfiguration',lambda:s.set_tides({**identity(s),'body':source,'parameters':cfg}))
    rejected('mass edit',lambda:s.set_mass(source,2*M/U['mass_unit_kg']))
    rejected('topology edit',lambda:s.remove_body({**identity(s),'body':companion}))
    rejected('prescribed J2',lambda:s.set_j2({**identity(s),'body':source,'parameters':{'j2':.001,'radius_eq_m':R,'axis':[0.,0.,1.],'provenance':'Synthetic'}}))
    old=saved
    def corrupt(label,change):
        value=copy.deepcopy(old);change(value);value['manifest_sha256']=digest({k:v for k,v in value.items() if k!='manifest_sha256'})
        (Path(folder)/'latest.json').write_text(json.dumps(value))
        before=s._tides.checkpoint();rev=s.revision
        try:s.load()
        except (ValueError,TypeError,KeyError):corruptions.append(label)
        else:raise AssertionError('Corruption accepted: '+label)
        assert s._tides.checkpoint()==before and s.revision==rev
    corrupt('missing material declaration',lambda v:v.pop('material_tides'))
    corrupt('material silently disabled',lambda v:v.__setitem__('material_tides',None))
    corrupt('activation history removed',lambda v:v['interventions'][0].__setitem__('new_material_origin',None))
    corrupt('contract',lambda v:v['contract'].__setitem__('integrator','IAS15'))
    corrupt('historical quadrupole',lambda v:v['instrument_history']['samples'][0]['reading']['source_snapshot_si'][0]['tide']['quadrupole_stf_kg_m2'][0].__setitem__(0,1e40))
    corrupt('historical heat',lambda v:v['instrument_history']['samples'][0]['reading']['source_snapshot_si'][0]['tide'].__setitem__('dissipated_heat_J',-1.))
    (Path(folder)/'latest.json').write_text(json.dumps(old))

    # Archives retain the joint state without replacing the main checkpoint.
    pointer=(Path(folder)/'latest.json').read_bytes()
    first=s.create_branch({**identity(s),'name':'Com maré'})
    s.set_tides({**identity(s),'body':source,'parameters':None})
    assert s._tides is None and s.state()['integrator']=='IAS15'
    second=s.create_branch({**identity(s),'name':'Pontual'})
    assert (Path(folder)/'latest.json').read_bytes()==pointer

    plain=Session(Path(folder)/'invalid-initial',2);fixture(plain);identifier=plain.registry[0]['id']
    for key,bad in [('radius_m',0.),('radius_m',1e20),('love_k2',0.),('love_k2',1.6),('time_lag_s',-1.),('time_lag_s',1e12),('inertia_kg_m2',1e60),('inertia_kg_m2',0.),('spin_rad_s',[1.,0.,0.]),('spin_rad_s',[0.,False,0.]),('provenance',''),('provenance','control\ntext')]:
        before=phase(plain.sim);binary=plain.sim.__reduce__()[1][0];rev=plain.revision
        try:plain.set_tides({**identity(plain),'body':identifier,'parameters':{**cfg,key:bad}})
        except (ValueError,TypeError):guards.append('invalid '+key+' '+str(bad))
        else:raise AssertionError('Invalid initial material accepted: '+key)
        assert phase(plain.sim)==before and plain.sim.__reduce__()[1][0]==binary and plain.revision==rev and plain._tides is None
    for key,bad in [('system_id','0'*32),('edit_token','0'*32),('expected_time',1.),('frame','other')]:
        try:plain.set_tides({**identity(plain),key:bad,'body':identifier,'parameters':cfg})
        except ValueError:guards.append('old '+key)
        else:raise AssertionError('Wrong material identity accepted')
    plain.reset(32)
    try:plain.set_tides({**identity(plain),'body':plain.registry[0]['id'],'parameters':cfg})
    except ValueError:guards.append('more than two active masses')
    else:raise AssertionError('Many-body material accepted')
    catalog=s._branches().public()['branches'];assert len(catalog)==2
    comparison=s.compare_branches({**identity(s),'first_id':catalog[0]['id'],'second_id':catalog[1]['id']})
    assert comparison['material_definition_changed'] and comparison['same_physical_instant']
    s.load_branch({**identity(s),'branch_id':catalog[0]['id']})
    assert s._tides is not None
    s.restart_seed();assert s._tides is None and s.sim.t==0.
    s.load_tidal_experiment(identity(s));assert s._tides is not None and s.revision==1
    s.integrate(period);s.save();u=Session(folder,2);u.load();assert u._tides.values().tolist()==s._tides.values().tolist()
    # Disabling material permits later topology/phase edits. Old material
    # origins belong to the historical active population, not the final one.
    source=s._tides.source_id;companion=s._tides.ids[1-s._tides.index]
    s.set_tides({**identity(s),'body':source,'parameters':None})
    s.remove_body({**identity(s),'body':companion});s.save();u.load();assert u._tides is None and u.sim.N==1

    # A point-mass checkpoint loaded over an active material session must clear
    # all material ownership. The archive itself stays byte-identical.
    pointer=(Path(folder)/'latest.json').read_bytes()
    s.load_tidal_experiment(identity(s));s.load();assert s._tides is None and s.sim.N==1
    assert (Path(folder)/'latest.json').read_bytes()==pointer

report={'status':'installed_material_session_verified' if INSTALLED else 'candidate_session_verified_not_installed','history_samples':16,'same_evaluator_active_force_and_probe':True,'exact_joint_resume':True,'main_checkpoint_pointer_preserved_by_branches':True,'rejected_commands':guards,'sealed_corruptions_rejected_without_mutation':corruptions,'elapsed_s':time.perf_counter()-began,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.glob('*.py')}}
(ROOT/('evidence/tides-session-installed-check.json' if INSTALLED else 'evidence/tides-session-prototype-check.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'},indent=2),flush=True)
