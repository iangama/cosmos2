"""Independent mechanical balances, atomic refusals, edited future and pinned migration."""
from copy import deepcopy
from pathlib import Path
import hashlib
import itertools
import json
import math
import subprocess
import sys
import tarfile
import tempfile

ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/c212-em-staging';sys.path.insert(0,str(STAGE))
from em_experiment import Experiment,canonical,generation
from em_editor import apply_intervention,apply_visual,diagnostics,validate_editor,MAX_INTERVENTIONS
from em_presets import create
from em_fields import K_E,MU_0
from em_migrate import migrate_legacy,LEGACY_GENERATION

owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes();cases=[];rejections=[];balances=[]
def wire(value):return json.loads(canonical(value))
def signature(ex):return canonical({'science':ex.payload(),'editor':ex.editor})
def independent(ex):
    p=wire(ex.payload());phase=p['phase'];mutual=p['mode']=='mutual_electrostatic'
    if mutual:
        charges=p['system']['charge_C'];masses=p['system']['mass_kg'];xs=phase['position_m'];vs=phase['velocity_m_s']
        potential=sum(K_E*charges[i]*charges[j]/math.dist(xs[i],xs[j]) for i,j in itertools.combinations(range(len(xs)),2)) if p['controls']['acting'] else 0.
        fixed=[]
    else:
        charges=[p['particle']['charge_C']];masses=[p['particle']['mass_kg']];xs=[phase['position_m']];vs=[phase['velocity_m_s']]
        sources=p['model']['sources'];x=xs[0]
        phi=sum(K_E*s['charge_C']/math.dist(x,s['position_m']) for s in sources)-sum(a*b for a,b in zip(p['model']['uniform_E_V_m'],x))
        potential=charges[0]*phi if p['controls']['electric_acting'] else 0.;fixed=[s['charge_C'] for s in sources]
    momenta=[[m*v for v in velocity] for m,velocity in zip(masses,vs)]
    P=[sum(p[k] for p in momenta) for k in range(3)]
    L=[sum(x[(k+1)%3]*p[(k+2)%3]-x[(k+2)%3]*p[(k+1)%3] for x,p in zip(xs,momenta)) for k in range(3)]
    K=sum(.5*m*sum(v*v for v in velocity) for m,velocity in zip(masses,vs))
    return {'mechanical_energy_J':K+potential,'total_charge_C':sum(charges+fixed),'momentum_kg_m_s':P,'angular_momentum_kg_m2_s':L}
def close(a,b):
    if isinstance(a,list):
        for x,y in zip(a,b):close(x,y)
    else:assert math.isclose(a,b,rel_tol=2e-13,abs_tol=1e-14),(a,b)
def edit(ex,request):
    old=signature(ex);before=independent(ex);trial=apply_intervention(ex,request);assert signature(ex)==old
    after=independent(trial);event=trial.editor['interventions'][-1]
    for key in before:
        close(event['diagnostics_before'][key],before[key]);close(event['diagnostics_after'][key],after[key])
        delta=[y-x for x,y in zip(before[key],after[key])] if isinstance(before[key],list) else after[key]-before[key]
        close(event['delta'][key],delta)
    assert trial.phase.time_s==ex.phase.time_s and trial.editor['reference']['diagnostics']==diagnostics(trial)
    balances.append({'operation':request['operation'],'delta':event['delta']});return trial
def refuse(ex,name,request=None,visual=None):
    old=signature(ex)
    try:apply_visual(ex,visual) if visual is not None else apply_intervention(ex,request)
    except (ValueError,TypeError,KeyError,OverflowError):pass
    else:raise AssertionError('Invalid edit accepted: '+name)
    assert signature(ex)==old;rejections.append(name)

ex=create('crossed');ex.advance(123);phase=ex.payload()['phase']
for source in (
    {'id':'plus','position_m':[-2,1,.5],'exclusion_radius_m':.1,'charge_C':1e-9,'magnetic_moment_A_m2':[0,0,0]},
    {'id':'minus','position_m':[2,-1,1],'exclusion_radius_m':.1,'charge_C':-2e-9,'magnetic_moment_A_m2':[0,0,0]}):
    ex=edit(ex,{'operation':'create_source','source':source})
point=[4,3,2];reading=ex.model.evaluate(point)
expected=list(ex.model.uniform_E_V_m)
for s in ex.model.sources:
    d=[a-b for a,b in zip(point,s.position_m)];r=math.sqrt(sum(v*v for v in d))
    expected=[a+K_E*s.charge_C*v/r**3 for a,v in zip(expected,d)]
close(reading['electric_field_V_m'],expected)
ex=edit(ex,{'operation':'update_source','id':'plus','changes':{'position_m':[-1,1,2],'charge_C':-3e-9}})
assert ex.payload()['phase']==phase and ex.model.evaluate(point)!=reading
ex=edit(ex,{'operation':'set_background','changes':{'uniform_E_V_m':[.3,-.1,.2],'uniform_B_T':[.1,.2,.7]}})
assert ex.payload()['phase']==phase
apply_visual(ex,{'selected_id':'plus'});old_reference=deepcopy(ex.editor['reference'])
for E,B in itertools.product((False,True),repeat=2):
    ex=edit(ex,{'operation':'set_controls','controls':{'electric_acting':E,'magnetic_acting':B}})
    for visible_e,visible_b in itertools.product((False,True),repeat=2):
        physics=canonical(ex.payload());ref=deepcopy(ex.editor['reference']);history=deepcopy(ex.editor['interventions'])
        apply_visual(ex,{'electric_visible':visible_e,'magnetic_visible':visible_b})
        assert canonical(ex.payload())==physics and ex.editor['reference']==ref and ex.editor['interventions']==history
assert ex.payload()['phase']==phase
ex=edit(ex,{'operation':'remove_source','id':'plus'});assert ex.editor['visual']['selected_id'] is None
cases.append('asymmetric signed sources, fields, x/v/t preservation and 16 acting/visibility combinations')

dip=create('dipole');point=[3,2,-4];before=dip.model.evaluate(point)
dip=edit(dip,{'operation':'update_source','id':'synthetic-dipole','changes':{'position_m':[.1,-.2,.3],'magnetic_moment_A_m2':[3e5,1e5,-2e5]}})
s=dip.model.sources[0];r=[a-b for a,b in zip(point,s.position_m)];length=math.sqrt(sum(v*v for v in r));dot=sum(a*b for a,b in zip(s.magnetic_moment_A_m2,r))
expected=[MU_0/(4*math.pi)*(3*dot*v/length**5-m/length**3) for v,m in zip(r,s.magnetic_moment_A_m2)]
close(dip.model.evaluate(point)['magnetic_field_T'],expected);assert before!=dip.model.evaluate(point)
cases.append('translated and rotated dipole agrees with independent 3D expression')

mutual=create('coulomb');mutual.advance(123)
mutual=edit(mutual,{'operation':'update_body','id':'positive','changes':{'mass_kg':1.3,'charge_C':mutual.model.charge_C[0]*1.2,'position_m':[-1,.2,.1],'velocity_m_s':[.1,-.2,.3]}})
body={'id':'third','charge_C':1e-7,'mass_kg':2.,'exclusion_radius_m':.03,'position_m':[4,2,-1],'velocity_m_s':[.2,-.3,.4]}
mutual=edit(mutual,{'operation':'create_body','body':body});apply_visual(mutual,{'selected_id':'third'})
mutual=edit(mutual,{'operation':'set_controls','controls':{'acting':False}})
assert diagnostics(mutual)['potential_energy_J']==0
mutual=edit(mutual,{'operation':'set_controls','controls':{'acting':True}})
mutual=edit(mutual,{'operation':'remove_body','id':'third'});assert mutual.editor['visual']['selected_id'] is None
ex=edit(ex,{'operation':'update_test_particle','changes':{'mass_kg':2.,'charge_C':.008,'position_m':[.2,.3,.4],'velocity_m_s':[.5,.1,-.2]}})
cases.append('active charge create/update/remove and mass/charge/phase deltas, disabled potential convention')

bad=[('unsupported regime',{'operation':'create_body','body':body}),('unknown operation',{'operation':'teleport'}),
 ('duplicate identity',{'operation':'create_source','source':wire(ex.payload())['model']['sources'][0]}),
 ('edit identity',{'operation':'update_source','id':'minus','changes':{'id':'renamed'}}),
 ('unknown source',{'operation':'remove_source','id':'missing'}),
 ('zero exclusion',{'operation':'update_source','id':'minus','changes':{'exclusion_radius_m':0}}),
 ('source covers particle',{'operation':'update_source','id':'minus','changes':{'position_m':list(ex.phase.position_m)}}),
 ('nonfinite field',{'operation':'set_background','changes':{'uniform_E_V_m':[float('nan'),0,0]}}),
 ('gyro domain',{'operation':'set_background','changes':{'uniform_B_T':[1e9,0,0]}}),
 ('boolean scalar',{'operation':'update_test_particle','changes':{'mass_kg':True}}),
 ('nonpositive mass',{'operation':'update_test_particle','changes':{'mass_kg':0}}),
 ('relativistic velocity',{'operation':'update_test_particle','changes':{'velocity_m_s':[1e9,0,0]}}),
 ('unknown patch',{'operation':'set_background','changes':{'gravity':True}}),
 ('empty patch',{'operation':'set_background','changes':{}}),
 ('unexpected command field',{'operation':'remove_source','id':'minus','surprise':1}),
 ('unchanged physics',{'operation':'set_controls','controls':dict(ex.controls)})]
for name,request in bad:refuse(ex,name,request)
for name,changes in [('invalid selection',{'selected_id':'missing'}),('invalid visual type',{'electric_visible':1}),('invalid camera',{'elevation_rad':5}),('unknown visual property',{'time_s':1})]:refuse(ex,name,visual=changes)
for name,request in [
 ('mutual zero mass',{'operation':'update_body','id':'positive','changes':{'mass_kg':0}}),
 ('mutual pair overlap',{'operation':'update_body','id':'positive','changes':{'position_m':list(mutual.phase.position_m[1])}}),
 ('mutual B forbidden',{'operation':'set_background','changes':{'uniform_B_T':[0,0,1]}}),
 ('duplicate active ID',{'operation':'create_body','body':body|{'id':'positive'}})]:refuse(mutual,name,request)
single=edit(create('coulomb'),{'operation':'remove_body','id':'negative'})
refuse(single,'minimum population',{'operation':'remove_body','id':'positive'})

with tempfile.TemporaryDirectory(prefix='cosmos2-em-editor-') as folder:
    folder=Path(folder);future=[];migrations=[]
    for name,experiment in [('prescribed',ex),('mutual',mutual)]:
        apply_visual(experiment,{'electric_visible':False,'magnetic_visible':True,'azimuth_rad':.9,'map_radius_m':4.,'map_cut_z_m':.3})
        path=folder/(name+'.json');experiment.save(path);restored=Experiment.load(path)
        assert signature(restored)==signature(experiment)
        experiment.advance(777);restored.advance(777);assert signature(restored)==signature(experiment)
        future.append({'mode':name,'edited_checkpoint_and_history_exact':True,'exact_future_steps':777})
    archive=ROOT/'evidence/em-prototype-0_1-frozen-20261018.tar.gz'
    assert hashlib.sha256(archive.read_bytes()).hexdigest()=='3f6850d7de7895071155e2e372014fd49556f570f9aff5a8945f32dbcf1b8314'
    legacy=folder/'legacy';legacy.mkdir()
    with tarfile.open(archive) as tar:
        for name in LEGACY_GENERATION['files_sha256']:
            raw=tar.extractfile('output/c212-em-staging/'+name).read()
            assert hashlib.sha256(raw).hexdigest()==LEGACY_GENERATION['files_sha256'][name]
            (legacy/name).write_bytes(raw)
    for name in ('helix','coulomb'):
        source=ROOT/'evidence/em-legacy-0_1-checkpoints'/(name+'.json');raw=source.read_bytes()
        try:Experiment.load(source)
        except ValueError:pass
        else:raise AssertionError('Implicit schema1 migration accepted')
        destination=folder/(name+'-migrated.json');migrated=migrate_legacy(source,destination)
        assert source.read_bytes()==raw and migrated.payload()==Experiment.load(destination).payload()
        saved=json.loads(raw);assert wire(migrated.payload())==saved['payload']
        code='from em_experiment import Experiment; import json,sys; ex=Experiment.load(sys.argv[1]); ex.advance(777); print(json.dumps(ex.payload(),sort_keys=True))'
        result=subprocess.run([sys.executable,'-c',code,str(source)],cwd=legacy,capture_output=True,text=True,encoding='utf-8',check=True)
        migrated.advance(777);assert wire(migrated.payload())==json.loads(result.stdout)
        try:migrate_legacy(source,destination)
        except ValueError:pass
        else:raise AssertionError('Overwriting migration accepted')
        migrations.append({'mode':name,'original_sha256':hashlib.sha256(raw).hexdigest(),'legacy_process_future_exact_steps':777})
    corrupt=deepcopy(json.loads((folder/'prescribed.json').read_bytes()));corrupt['editor']['interventions'][-1]['delta']['mechanical_energy_J']+=1
    corrupt['sha256']=hashlib.sha256(canonical({k:v for k,v in corrupt.items() if k!='sha256'})).hexdigest()
    path=folder/'bad-history.json';path.write_bytes(canonical(corrupt))
    try:Experiment.load(path)
    except ValueError:rejections.append('resealed inconsistent intervention delta')
    else:raise AssertionError('Inconsistent history accepted')

bounded=create('electric')
for i in range(MAX_INTERVENTIONS+6):
    bounded=apply_intervention(bounded,{'operation':'set_background','changes':{'uniform_E_V_m':[.2+i*.001,0,0]}})
assert len(bounded.editor['interventions'])==64 and bounded.editor['dropped_interventions']==6
validate_editor(bounded,bounded.editor)
assert owner.read_bytes()==original
report={'status':'isolated_EM_0_2_editor_mechanical_balances_future_and_explicit_migration_verified',
        'cases':cases,'independent_balance_interventions':len(balances),'balance_examples':balances,
        'atomic_refusals':rejections,'edited_futures':future,'explicit_legacy_migrations':migrations,
        'history_bound':64,'dropped_history_count_explicit':6,'owner_pointer_preserved':True,
        'scientific_generation':generation(),'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (STAGE/'em_editor.py',STAGE/'em_migrate.py',STAGE/'em_experiment.py',Path(__file__))},
        'scope':'Local model and checkpoint proof only; no GUI/native scene, rate or frame acceptance. Delta is mechanical matter energy, excluding fixed-source reservoirs, field energy and induction.'}
(ROOT/'evidence/em-editor-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='balance_examples'},indent=2))
