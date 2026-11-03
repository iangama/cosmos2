"""Compare complete cloud trajectories in separate, source-pinned processes."""
from pathlib import Path
import hashlib
import json
import struct
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
STAGES=(ROOT/'output/c212-em-cloud-staging',ROOT/'output/c212-em-cloud-v02-staging')

def child(stage,case):
    import numpy as np
    sys.path.insert(0,str(stage))
    import cloud_core
    import cloud_fields
    from em_fields import Model,Source,SPEED_LIMIT_M_S
    assert Path(cloud_core.__file__).resolve().parent==stage.resolve()
    assert Path(cloud_fields.__file__).resolve().parent==stage.resolve()
    n,steps,source_case,electric,magnetic=case
    rng=np.random.default_rng(191027+n)
    x=rng.normal(size=(n,3))*.3+[0,0,5]
    v=rng.normal(size=(n,3))*.1
    q=rng.uniform(-1,1,n);m=rng.uniform(.5,2,n)
    sources=(Source('p',(-1,.3,0),.02,1e-9,(1e4,0,2e4)),Source('n',(1,-.5,.4),.03,-.7e-9,(0,2e4,0))) if source_case else ()
    model=Model(sources,(.1,.2,-.1),(.3,-.2,.5))
    system=cloud_core.System(model,q,m);phase=cloud_core.Phase(x,v)
    trajectory=hashlib.sha256();fields=hashlib.sha256()
    for a in cloud_fields.evaluate(model,x):fields.update(a.tobytes())
    for _ in range(steps):
        phase,d=system.step(phase,.002,electric_acting=electric,magnetic_acting=magnetic)
        for data in (phase._x,phase._v,struct.pack('<d',phase.time_s),d['electric_work_J'].tobytes(),d['kinetic_change_J'].tobytes(),struct.pack('<d',d['sample_time_s'])):trajectory.update(data)
    # Compare admission on both sides of the conservative L-infinity bound
    # and of the actual Euclidean speed cap, including mixed populations.
    admission=[]
    for scale in (.1,1/np.sqrt(3)*(1-2e-12),1/np.sqrt(3),np.nextafter(1.,0.),1.,np.nextafter(1.,2.),1.01,1e100):
        for direction in ((1.,0.,0.),(1.,1.,1.),(.6,.8,0.)):
            trial=np.array(direction)*scale*SPEED_LIMIT_M_S
            try:cloud_core.Phase([[0.,0.,0.],[1.,0.,0.]],[[0.,0.,0.],trial.tolist()])
            except (ValueError,ArithmeticError):admission.append(False)
            else:admission.append(True)
    return {'case':case,'all_step_phase_work_time_sha256':trajectory.hexdigest(),'field_bytes_sha256':fields.hexdigest(),
            'admission':admission,'final_time_s':phase.time_s,'version':cloud_core.VERSION}

if len(sys.argv)>1:
    print(json.dumps(child(Path(sys.argv[1]),json.loads(sys.argv[2])),allow_nan=False))
else:
    cases=[];total=0
    for n,steps in ((1,777),(16,777),(128,777),(10000,64)):
        for source_case in ((False,True) if n<10000 else (False,)):
            for electric,magnetic in ((False,False),(True,False),(False,True),(True,True)):
                case=[n,steps,source_case,electric,magnetic];results=[]
                for stage in STAGES:
                    run=subprocess.run([sys.executable,str(Path(__file__).resolve()),str(stage),json.dumps(case)],check=True,capture_output=True,text=True,encoding='utf-8')
                    results.append(json.loads(run.stdout))
                assert results[0].pop('version')=='SI_prescribed_EM_test_cloud_boris_v1'
                assert results[1].pop('version')=='SI_prescribed_EM_test_cloud_boris_v2'
                assert results[0]==results[1],case
                cases.append(results[0]);total+=steps
    paths=[p for stage in STAGES for p in (*stage.glob('*.py'),stage/'constants.json')]+[Path(__file__)]
    report={'status':'cloud_v1_v2_separate_process_all_step_phase_fields_work_time_and_speed_admission_bit_exact',
            'cases':cases,'complete_collective_steps_compared':total,'admission_trials_per_case':24,
            'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
            'scope':'Finite listed fixtures only; no checkpoint compatibility, native throughput or universal rounding equivalence claim.'}
    (ROOT/'evidence/em-cloud-v02-future-check.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':report['status'],'cases':len(cases),'complete_collective_steps_compared':total},indent=2))
