"""Verify exact continuation and reject corrupted, incompatible or invalid EM states."""
from pathlib import Path
import hashlib
import json
import math
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/c212-em-staging';sys.path.insert(0,str(STAGE))
from em_fields import Model,Source,K_E
from em_particles import Phase as TestPhase,DomainExit
from em_mutual import System,Phase as MutualPhase
from em_experiment import Experiment,canonical,MAX_CHECKPOINT_BYTES

owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes();results=[];rejected=[]
q=math.sqrt(1/K_E)
with tempfile.TemporaryDirectory(prefix='cosmos2-em-checkpoint-') as folder:
    path=Path(folder)/'em.json'
    experiments=[Experiment('test_particle',Model((Source('fixed',(0,0,0),.01,-1e-9),),uniform_B_T=(0,0,.01)),TestPhase((2,0,0),(0,.6,.1)),.002,{'electric_acting':True,'magnetic_acting':True},charge_C=.1,mass_kg=1),
        Experiment('mutual_electrostatic',System(('a','b'),(q,-q),(1,1),(.01,.01)),MutualPhase(((-1,0,0),(1,0,0)),((0,-.5,0),(0,.5,0))),.002,{'acting':True})]
    for experiment in experiments:
        experiment.advance(123);experiment.save(path);restored=Experiment.load(path)
        assert restored.payload()==experiment.payload()
        experiment.advance(777);restored.advance(777)
        assert restored.payload()==experiment.payload()
        results.append({'mode':experiment.mode,'save_after_steps':123,'exact_future_steps':777,'phase_and_configuration_equal':True})
    valid=json.loads(path.read_bytes())
    def refuse(name,record=None,raw=None,seal=True):
        if raw is None:
            if seal:
                body={k:v for k,v in record.items() if k!='sha256'};record['sha256']=hashlib.sha256(canonical(body)).hexdigest()
            raw=canonical(record)
        path.write_bytes(raw)
        try:Experiment.load(path)
        except (ValueError,TypeError,OverflowError):rejected.append(name)
        else:raise AssertionError('Invalid checkpoint accepted: '+name)
    def copy():return json.loads(json.dumps(valid))
    r=copy();r['payload']['dt_s']=.01;refuse('altered bytes',r,seal=False)
    r=copy();r['schema']=True;refuse('boolean schema',r)
    r=copy();r['generation']['version']='other';refuse('generation mismatch',r)
    r=copy();r['payload']['phase']['velocity_m_s'][0]=[1e9,0,0];refuse('relativistic phase',r)
    r=copy();r['payload']['system']['ids'][1]='a';refuse('duplicate charge ID',r)
    r=copy();r['payload']['system']['mass_kg'][0]=0;refuse('zero mass',r)
    r=copy();r['payload']['system']['exclusion_radius_m'][0]=-1;refuse('negative exclusion',r)
    r=copy();r['payload']['phase']['position_m'][1]=r['payload']['phase']['position_m'][0];refuse('coincident active charges',r)
    r=copy();r['payload']['controls']['magnetic_acting']=True;refuse('unsupported mutual magnetic term',r)
    r=copy();r['payload']['dt_s']=-1;refuse('negative timestep',r)
    r=copy();r['payload']['unexpected']=1;refuse('unknown mode payload field',r)
    refuse('duplicate JSON key',raw=b'{"schema":1,"schema":1}')
    refuse('nonfinite JSON',raw=b'{"schema":NaN}')
    refuse('size bound',raw=b' '*(MAX_CHECKPOINT_BYTES+1))

    # Partial batches commit only successful steps and stop at the last valid
    # physical time. Checkpointing that phase preserves the same domain stop.
    obstacle=Model((Source('excluded',(0,0,0),.1),))
    run=Experiment('test_particle',obstacle,TestPhase((-1,0,0),(1,0,0)),.2,{'electric_acting':False,'magnetic_acting':False},charge_C=0,mass_kg=1)
    try:run.advance(10)
    except DomainExit:pass
    else:raise AssertionError('Expected domain stop')
    assert abs(run.phase.time_s-.8)<1e-14 and run.phase.position_m[0]<-.1
    run.save(path);again=Experiment.load(path);before=again.payload()
    try:again.advance()
    except DomainExit:pass
    else:raise AssertionError('Restored phase crossed excluded domain')
    assert again.payload()==before
    assert not list(Path(folder).glob('*.tmp'))
assert owner.read_bytes()==original
report={'status':'isolated_EM_checkpoint_and_exact_future_verified_not_installed','exact_continuations':results,
    'invalid_checkpoints_refused':rejected,'domain_exit_keeps_last_valid_phase_and_reproduces_after_restore':True,
    'temporary_files_cleaned':True,'owner_pointer_preserved':True,
    'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (STAGE/'em_experiment.py',STAGE/'em_fields.py',STAGE/'em_particles.py',STAGE/'em_mutual.py',STAGE/'constants.json',Path(__file__))},
    'scope':'Prototype EM schema2 exact science continuation and structural rejection. No gravitational Session conversion, GUI or real-time performance acceptance.'}
(ROOT/'evidence/em-checkpoint-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
