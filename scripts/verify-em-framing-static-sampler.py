"""Static helper vs original scalar fields, real fences and original2s slice."""
from pathlib import Path
from copy import deepcopy
import argparse
import hashlib
import json
import math
import os
import random
import sys
ROOT=Path(__file__).resolve().parents[1];I=ROOT/'output/c212-em-framing-product'
sys.path.insert(0,str(I/'app'));sys.path.insert(0,str(I/'em'));os.environ['PYTHONUTF8']='1'
from em_static_sampler import StaticSampler
from em_fields import Model,Source
from em_particles import Phase
from em_experiment import Experiment,generation
from em_slice import sample_slice
import em_laboratory
parser=argparse.ArgumentParser();parser.add_argument('--label',default='release1');args=parser.parse_args();assert args.label.isalnum()
dest=ROOT/f'evidence/em-framing-static-sampler-{args.label}-check.json';assert not dest.exists()
owner=(ROOT/'user/sessions/latest.json').read_bytes();checks=[];report={'completed':False,'checks':checks}
rng=random.Random(212301);maxima={'E':0.,'B':0.,'potential':0.}
def fake_state(ex):return {'system_id':'fixture','edit_token':'phase','revision':0,'frame':'EM_SI_FIXED_INERTIAL','time_s':0.,'paused':True,'experiment':json.loads(json.dumps(ex.payload())),'scientific_generation':generation()}
def particle(model):return Experiment('test_particle',model,Phase((1e6,1e6,1e6),(0.,0.,0.)),.001,{'electric_acting':True,'magnetic_acting':True},charge_C=0.,mass_kg=1.)
def compare(model,points,samples):
    for point,s in zip(points,samples):
        ref=model.evaluate(point);assert s['valid']==ref['valid'] and s['position_m']==ref['position_m']
        assert s['source_ids']==ref['source_ids']
        if not s['valid']:assert s['reason']==ref['reason'];continue
        for tag,key,scale in [('E','electric_field_V_m',ref['electric_scale_V_m']),('B','magnetic_field_T',ref['magnetic_scale_T'])]:
            error=math.dist(s[key],ref[key])/max(scale,1e-300);maxima[tag]=max(maxima[tag],error);assert error<=3e-12,(tag,error,point)
        error=abs(s['electric_potential_V']-ref['electric_potential_V'])/max(s['potential_scale_V'],1e-300)
        maxima['potential']=max(maxima['potential'],error);assert error<=3e-12,('potential',error,point)
        for key in ('electric_scale_V_m','magnetic_scale_T'):assert math.isclose(s[key],ref[key],rel_tol=3e-12,abs_tol=1e-300),(key,s[key],ref[key])
        assert s['potential_zero']==ref['potential_zero']
try:
    models=[Model((),(.2,-.1,.3),(0.,0.,1.)),Model((Source('q',(0.,0.,0.),.25,1e-9),))]
    for count in (1,2,8,128,128):
        sources=tuple(Source(str(i),tuple(rng.uniform(-8,8) for _ in range(3)),.02,(-1)**i*1e-7,tuple(rng.uniform(-1e5,1e5) for _ in range(3))) for i in range(count))
        models.append(Model(sources,(.2,-.1,.3),(.01,-.02,1.)))
    models+=[Model((Source('tiny',(0.,0.,0.),1e-210,1e-200),)),Model((Source('huge',(1e17,0.,0.),1.,1e200,(1e200,-2e200,3e200)),))]
    for index,model in enumerate(models):
        s=StaticSampler(lambda:None,lambda _:None);s.begin(fake_state(particle(model)))
        points=[[rng.uniform(-3,3) for _ in range(3)] for _ in range(64)]
        if index==1:
            points += [[x,0.,0.] for x in (0.,.25,math.nextafter(.25,0.),math.nextafter(.25,math.inf),.25+40*math.ulp(.25))]
        if index==7:points += [[1e-100,0.,0.]]
        if index==7:
            for reader in (lambda:model.evaluate([1e-200,0.,0.]),lambda:s.evaluate([[1e-200,0.,0.]])):
                try:reader()
                except ValueError:pass
                else:raise AssertionError('Original scalar numeric domain widened')
        values=s.evaluate(points);compare(model,points,values)
        if index==1:assert values[-2]['numeric_provider']=='scalar_boundary_reference'
        checks.append({'case':'scalar'+str(index),'sources':len(model.sources),'points':len(points),'all_contributions_compared':True})

    storage=I/f'c212-em-worker/static-sampler-{args.label}-proof';assert not storage.exists();storage.mkdir()
    em_laboratory.STORAGE=storage;lab=em_laboratory.EMLaboratory()
    try:
        with lab.command_lock:
            lab._start()
            fixture=json.loads((ROOT/'evidence/native-em128-c212hpotb.json').read_bytes())['fixture'];ex=Experiment.from_payload(fixture);ex.save(storage/'fixture.json')
            def guard():
                s=lab._current();return {k:s[k] for k in ('system_id','edit_token','revision','frame')}|{'expected_time_s':s['time_s']}
            lab._worker({'command':'load','file':'fixture',**guard()})
            for i in range(64):lab._worker({'command':'set_timestep',**guard(),'dt_s':.0005 if i%2==0 else .001,'expected_dt_s':lab._current()['experiment']['dt_s']})
            before=lab._current();axis=[-3+6*i/32 for i in range(33)];grid={'x_m':axis,'y_m':axis,'z_m':0.}
            provider=StaticSampler(lab._current,lab._worker)
            layer=sample_slice(lab._current,provider.query,lab.command_lock,grid,None,provider=provider)
            assert len(layer['measurement']['samples'])==1089 and layer['batch_protocol']['budget_s']==2
            assert [b['samples'] for b in layer['batch_protocol']['batches']]==[128]*8+[65]
            assert layer['batch_protocol']['provider']['all_declared_sources']==128
            model=ex.model.field_snapshot(ex.phase);points=[s['position_m'] for s in layer['measurement']['samples']]
            compare(model,points,layer['measurement']['samples'])
            assert lab._current()['experiment']==before['experiment'] and lab._current()['time_preferences']==before['time_preferences']
            checks.append({'case':'real_worker_fenced1089','numeric_ms':layer['batch_protocol']['elapsed_wall_ms'],'segments':len(layer['geometry']['segments']),'phase_and_timing_preserved':True})
            rejections=[]
            for key in ('paused','time_s','revision','edit_token','frame','experiment','scientific_generation'):
                def corrupted_state():
                    s=lab._current();s[key]=False if key=='paused' else s[key]+1 if key in ('time_s','revision') else 'wrong';return s
                provider=StaticSampler(corrupted_state,lab._worker);provider.begin(before)
                try:provider.query({'command':'field_map',**guard(),'points_m':[[1.,2.,3.]]})
                except ValueError:rejections.append(key)
                else:raise AssertionError('Changed phase fence accepted: '+key)
            for kind in ('type','paused','time_s'):
                def corrupt_ack(request):
                    ack=lab._worker(request);ack[kind]='wrong';return ack
                provider=StaticSampler(lab._current,corrupt_ack);provider.begin(before)
                try:provider.query({'command':'field_map',**guard(),'points_m':[[1.,2.,3.]]})
                except ValueError:rejections.append('ack '+kind)
                else:raise AssertionError('Wrong snapshot ack accepted')
            provider=StaticSampler(lab._current,lab._worker)
            try:sample_slice(lab._current,provider.query,lab.command_lock,grid,None,budget_s=1e-12,provider=provider)
            except TimeoutError:rejections.append('original wall budget')
            else:raise AssertionError('Budget was bypassed')
            assert lab._current()['experiment']==before['experiment']
            report['rejections']=rejections;report['numeric_ms']=layer['batch_protocol']['elapsed_wall_ms'];report['provider']=layer['batch_protocol']['provider']
    finally:lab.close()
    assert owner==(ROOT/'user/sessions/latest.json').read_bytes()
    report.update(completed=True,maximum_normalized_errors=maxima,owner_pointer_preserved=True,
                  scope='All fields/potential/scales and exclusion domain vs original scalar, real worker fences and1089/128-source/64timing within unchanged2s. No fresh native profile or final experience acceptance.')
finally:
    report['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),I/'app/em_static_sampler.py',I/'app/em_slice.py',I/'app/em_laboratory.py']}
    dest.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'completed':report['completed'],'cases':len(checks),'errors':maxima,'numeric_ms':report.get('numeric_ms'),'rejections':len(report.get('rejections',[]))}),flush=True)
