"""Exact old/new fixtures, independent fields, failure recovery and EM0.2 migration."""
from dataclasses import asdict
from pathlib import Path
import hashlib
import importlib.util
import itertools
import json
import math
import subprocess
import sys
import tempfile
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[1];NEW=ROOT/'output/c212-em-v03-staging';OLD=ROOT/'output/c212-em-product/em';sys.path.insert(0,str(NEW))
from em_mutual import System,Phase
from em_fields import K_E,SPEED_LIMIT_M_S
from em_experiment import Experiment,canonical,generation
from em_migrate import migrate_v02,LEGACY_02_GENERATION
spec=importlib.util.spec_from_file_location('em_mutual_reference_02',OLD/'em_mutual.py');legacy=importlib.util.module_from_spec(spec);sys.modules[spec.name]=legacy;spec.loader.exec_module(legacy)
owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes()
for name,sha in LEGACY_02_GENERATION['files_sha256'].items():assert hashlib.sha256((OLD/name).read_bytes()).hexdigest()==sha
for name in ('em_fields.py','em_particles.py','constants.json'):assert (OLD/name).read_bytes()==(NEW/name).read_bytes()
rng=np.random.default_rng(204217);fixtures=[];exact_steps=0;max_force_error=0.
for population in (1,2,8,32,128):
    for trial in range(8):
        x=tuple(map(tuple,rng.uniform(-6,6,size=(population,3))));v=tuple(map(tuple,rng.normal(0,.02,size=(population,3))))
        q=tuple(rng.uniform(-1e-7,1e-7,population));m=tuple(rng.uniform(.5,2,population));r=(.003,)*population;ids=tuple(map(str,range(population)))
        system=System(ids,q,m,r);reference=legacy.System(ids,q,m,r);phase=Phase(x,v);old_phase=legacy.Phase(x,v)
        f,u=system.force_potential(x);old_f,old_u=reference.force_potential(x)
        assert f.dtype==np.float64 and f.tobytes()==old_f.tobytes() and u==old_u
        # An independent long-double pair loop checks reactions and the full
        # signed configuration without copying the vectorized reduction.
        independent=np.zeros((population,3),dtype=np.longdouble)
        for i,j in itertools.combinations(range(population),2):
            delta=np.array(x[i],dtype=np.longdouble)-np.array(x[j],dtype=np.longdouble)
            radius=np.sqrt(np.sum(delta*delta));pair=np.longdouble(K_E)*np.longdouble(q[i])*np.longdouble(q[j])*delta/radius**3
            independent[i]+=pair;independent[j]-=pair
        scale=max(float(np.max(abs(independent))),1e-300);error=float(np.max(abs(f.astype(np.longdouble)-independent)))/scale;max_force_error=max(max_force_error,error);assert error<2e-14
        f[:]=1e99;assert system.force_potential(x)[0].tobytes()==old_f.tobytes()
        for step in range(32):
            acting=step%7!=0;phase=system.step(phase,.002,acting=acting);old_phase=reference.step(old_phase,.002,acting=acting)
            assert canonical(asdict(phase))==canonical(asdict(old_phase));exact_steps+=1
        assert system.diagnostics(phase)==reference.diagnostics(old_phase)
        fixtures.append({'population':population,'case':trial,'bit_exact_force_and_32_steps':True})

q=math.sqrt(1/K_E);system=System(('a','b'),(q,-q),(1,1),(.1,.1));reference=legacy.System(('a','b'),(q,-q),(1,1),(.1,.1))
x=((-1.,0.,0.),(1.,0.,0.));v=((10.,0.,0.),(-10.,0.,0.));phase=Phase(x,v);old_phase=legacy.Phase(x,v)
for i in range(10):
    before=canonical(asdict(phase))
    for model,p in ((system,phase),(reference,old_phase)):
        try:model.step(p,.2)
        except ValueError:pass
        else:raise AssertionError('Excluded pair crossing accepted')
    assert canonical(asdict(phase))==before
    good=system.step(phase,.001);old_good=reference.step(old_phase,.001);assert canonical(asdict(good))==canonical(asdict(old_good))
    # Do not move the starting phase: repeat a failed trial to exercise reuse.
for speed in (np.nextafter(SPEED_LIMIT_M_S,0),SPEED_LIMIT_M_S):
    a=Phase(((0.,-0.,0.),),((speed,0.,-0.),));b=legacy.Phase(((0.,-0.,0.),),((speed,0.,-0.),))
    aa=System(('single',),(0.,),(1.,),(.01,)).step(a,.001,acting=False);bb=legacy.System(('single',),(0.,),(1.,),(.01,)).step(b,.001,acting=False)
    assert canonical(asdict(aa))==canonical(asdict(bb))
# Check the optimized three-component sums over widely separated magnitudes.
from em_mutual import _row_dot3,_row_norm3
wide=rng.normal(size=(10000,3))*np.power(10.,rng.uniform(-140,140,size=(10000,1)))
other=rng.normal(size=(10000,3))*np.power(10.,rng.uniform(-140,140,size=(10000,1)))
assert _row_norm3(wide).tobytes()==np.linalg.norm(wide,axis=1).tobytes()
assert _row_dot3(wide,other).tobytes()==np.sum(wide*other,axis=1).tobytes()
# Both generations must refuse finite pair forces whose summed potential
# overflows; lazy energy evaluation must not weaken the scientific domain.
overflow_x=tuple(itertools.islice(itertools.product((0.,1.,2.,3.,4.,5.),repeat=3),128))
overflow_q=math.sqrt(1e306/K_E)
for mod in (legacy,sys.modules['em_mutual']):
    model=mod.System(tuple(map(str,range(128))),(overflow_q,)*128,(1e308,)*128,(.01,)*128)
    p=mod.Phase(overflow_x,((0.,0.,0.),)*128)
    try:model.step(p,.001)
    except (ValueError,ArithmeticError):pass
    else:raise AssertionError('Summed potential overflow accepted')
rejected=[]
for name,args in [('boolean vector',(((True,0,0),),((0,0,0),))),('nonfinite',(((float('nan'),0,0),),((0,0,0),))),('speed cap',(((0,0,0),),((np.nextafter(SPEED_LIMIT_M_S,float('inf')),0,0),)))]:
    for cls in (Phase,legacy.Phase):
        try:cls(*args)
        except ValueError:pass
        else:raise AssertionError(name)
    rejected.append(name)

with tempfile.TemporaryDirectory(prefix='cosmos2-em-v03-') as temp:
    temp=Path(temp);migrations=[]
    for preset in ('coulomb','dipole'):
        source=temp/(preset+'-02.json');destination=temp/(preset+'-03.json')
        code='import sys,json;sys.path.insert(0,sys.argv[1]);from em_presets import create;ex=create(sys.argv[3]);ex.advance(123);ex.save(sys.argv[2]);ex.advance(777);print(json.dumps(ex.payload(),sort_keys=True))'
        child=subprocess.run([sys.executable,'-c',code,str(OLD),str(source),preset],check=True,capture_output=True,text=True,encoding='utf-8')
        original_checkpoint=source.read_bytes();old_record=json.loads(original_checkpoint)
        try:Experiment.load(source)
        except ValueError:pass
        else:raise AssertionError('Implicit0.2 migration accepted')
        ex=migrate_v02(source,destination);assert source.read_bytes()==original_checkpoint
        assert json.loads(canonical(ex.payload()))==old_record['payload']
        restored=Experiment.load(destination);assert canonical(restored.editor)==canonical(ex.editor)
        ex.advance(777);restored.advance(777)
        assert canonical(ex.payload())==canonical(restored.payload())
        assert json.loads(canonical(ex.payload()))==json.loads(child.stdout)
        assert ex.editor['migration']['generation']==LEGACY_02_GENERATION
        migrations.append({'preset':preset,'original_preserved':True,'exact_future_vs_legacy_process_steps':777,'exact_new_save_future_steps':777})

# Uninstrumented timings are isolated from GUI/IPC and cannot approve native rate.
positions=tuple(itertools.islice(itertools.product((-4,-2,0,2,4),repeat=3),125))+((-6,0,0),(6,0,0),(0,6,0));charge=.01*math.sqrt(1/K_E)
timings={}
for label,mod in [('old02',legacy),('new03',sys.modules['em_mutual'])]:
    model=mod.System(tuple(map(str,range(128))),tuple(charge*(-1)**k for k in range(128)),(1.,)*128,(.01,)*128);p=mod.Phase(positions,((0.,0.,0.),)*128)
    began=time.perf_counter()
    for i in range(1000):p=model.step(p,.001)
    timings[label]=time.perf_counter()-began
assert owner.read_bytes()==original
report={'status':'EM0_3_optimized_kernel_exact_legacy_fixtures_migration_and_independent_force_verified',
        'fixtures':len(fixtures),'bit_exact_steps':exact_steps,'max_relative_force_error_vs_longdouble_pairs':max_force_error,
        'failed_crossings_then_safe_trials':10,'strict_public_refusals':rejected,'migrations':migrations,
        'isolated_1000_step_timings_s':timings,'isolated_speedup':timings['old02']/timings['new03'],'owner_pointer_preserved':True,
        'scientific_generation':generation(),'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (*NEW.glob('*.py'),Path(__file__))},
        'scope':'Isolated EM0.3 kernel/checkpoint proof, not native/worker/profile acceptance. Forty signed fixtures and migration fixtures are bit exact; not a proof of identical rounding for every possible input.'}
(ROOT/'evidence/em-v03-kernel-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('scientific_generation','source_sha256')},indent=2))
