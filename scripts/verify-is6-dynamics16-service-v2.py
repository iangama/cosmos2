"""Before native launch: independent SI readings, numerical replay and persistence."""
import argparse
import copy
import datetime as dt
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is6-dynamics16-product0.26.1/app'
sys.path.insert(0,str(APP))
import numpy as np
import dynamics16_runtime as runtime
import system16_import as model
from session import Session
from body_registry import validate_registry, digest

UTC='2026-10-11T12:00:00Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def guard(p):
    return {k:p[k] for k in ['system_id','edit_token','revision']}|dict(expected_time=p['time'],frame=p['contract']['frame'])


def phase(sim):
    return [[p.m,p.x,p.y,p.z,p.vx,p.vy,p.vz] for p in sim.particles]


def independent(p, selected):
    with localcontext() as ctx:
        ctx.prec=70
        D=Decimal.from_float;length=D(p['physical_scale']['length_unit_m']);unit=D(p['physical_scale']['nominal_GM_unit_m3_s2'])
        result={}
        for source in p['bodies']:
            if source['id']==selected['id']:continue
            delta=[(D(source['position'][k])-D(selected['position'][k]))*length for k in range(3)]
            radius=sum(x*x for x in delta).sqrt()
            result[source['id']]=[float(D(source['mass'])*unit*x/radius**3) for x in delta]
        return result


class Worker:
    def __init__(self,folder):
        folder.mkdir(parents=True,exist_ok=True)
        self.errors=(folder/'worker-stderr.log').open('w',encoding='utf8')
        self.process=subprocess.Popen([sys.executable,'-Xutf8','-u',str(APP/'worker.py'),'--storage',str(folder)],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.errors,text=True,encoding='utf8')
        self.events=queue.Queue();self.serial=0;self.latest=None
        def read():
            for line in self.process.stdout:
                try:self.events.put(json.loads(line))
                except ValueError:self.events.put(dict(type='invalid',line=line))
            self.events.put(dict(type='eof'))
        self.thread=threading.Thread(target=read,daemon=True);self.thread.start()
        assert self.events.get(timeout=20)['type']=='ready'
        self.latest=self.events.get(timeout=20);assert self.latest['type']=='snapshot'

    def call(self,name,expect_error=False,**fields):
        self.serial+=1
        self.process.stdin.write(json.dumps(dict(command=name,id=self.serial,**fields),allow_nan=False)+'\n');self.process.stdin.flush()
        deadline=time.monotonic()+40
        while True:
            response=self.events.get(timeout=max(.001,deadline-time.monotonic()))
            assert response['type'] not in ('eof','invalid'),response
            if response['type']=='snapshot':self.latest=response
            if response.get('id')==self.serial and response['type'] in ('ack','error'):
                assert (response['type']=='error')==expect_error,response
                return response

    def close(self):
        if self.process.poll() is None:self.call('quit')
        self.process.wait(timeout=10);self.errors.close();self.thread.join(timeout=2)
        assert self.process.returncode==0


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True)
    label=parser.parse_args().label
    assert label and len(label)<=24 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label)
    folder=ROOT/f'output/is6-dynamics16-service-{label}';receipt=ROOT/f'evidence/is6-dynamics16-service-{label}.json'
    assert not folder.exists() and not receipt.exists(),'Preserve service evidence'
    manifest=json.loads((APP.parent/'build-manifest.json').read_text(encoding='utf8'))
    assert {p.relative_to(APP).as_posix():sha(p) for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts}==manifest['files_sha256']
    cpu=json.loads((ROOT/'evidence/is6-dynamics16-verification-20261112b.json').read_text())
    assert cpu['accepted'] and json.loads((ROOT/'evidence/is6-dynamics16-audit-20261112b.json').read_text())['accepted']
    series_path=ROOT/cpu['propagation']['series_file'];assert sha(series_path)==cpu['propagation']['series_sha256']
    series=json.loads(series_path.read_text());folder.mkdir()
    paths=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [Path(__file__),APP.parent/'build-manifest.json',ROOT/'IS-6-DINAMICA16-INTERFACE-CONTRATO.md',
              ROOT/'evidence/is6-dynamics16-verification-20261112b.json',ROOT/'evidence/is6-dynamics16-audit-20261112b.json',series_path]
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for name in sources:archive.write(ROOT/name,name)
    protected={n:sha(ROOT/n) for n in ['user/sessions/latest.json','Iniciar-Cosmos2.cmd','output/session.json',
        'output/is6-principal-moons-navigation-product0.25.1/build-manifest.json']}
    report=dict(accepted=False,completed=False,started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        source_sha256=sources,source_archive_sha256=sha(folder/'executed-sources.zip'),protected_sha256=protected,
        limits_before_execution=dict(acceleration_component_m_s2=1e-10,acceleration_relative_component=1e-10,
            numerical_replay_position_m=.001,numerical_replay_velocity_m_s=1e-8),checks={},refusals=[],
        scope='Isolated Session and real worker service; full native UI, HTTP admission, visual and own profile remain separate.')
    def persist():receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    def progress(name):print(json.dumps(dict(progress=name)),flush=True);persist()
    def refuse(name,call,session=None):
        before=None if session is None else (copy.deepcopy(session.state()),phase(session.sim))
        try:call()
        except (ValueError,TypeError):pass
        else:raise AssertionError('Accepted invalid input: '+name)
        if before is not None:assert (session.state(),phase(session.sim))==before,name
        report['refusals'].append(name)
    worker=None
    persist()
    try:
        initial=model.prepare(model.catalog.states(utc=UTC))
        session=Session(folder/'session');session.import_atlas(initial);first=session.state()
        assert session.sim.N==16 and [b['reference_id'].split(':')[-1] for b in first['bodies']]==model.IDS
        assert all([b[k] for k in ('mass','position','velocity')]==[s[k] for k in ('mass','position','velocity')] for b,s in zip(first['bodies'],initial['bodies']))
        assert first['dynamics16']['initial_body_count']==16
        assert first['scientific_generation']['candidate_extension']['initial_format']==model.KIND+'/'+model.VERSION
        assert first['dynamics16']['inertial_frame']['encoding']=='split_inertial_origin'
        assert not first['dynamics16']['electromagnetic_coupling'] and not first['dynamics16']['nuclear_coupling']
        errors=[]
        for body in first['bodies']:
            before=(phase(session.sim),session.revision,session.edit_token)
            read=session.dynamics16_reading({**guard(first),'body_id':body['id']})
            assert len(read['sources'])==15 and body['id'] not in {r['id'] for r in read['sources']}
            assert read['scientific_generation']==first['scientific_generation'] and read['frame']==first['contract']['frame']
            oracle=independent(first,body);maximum=0.
            for source in read['sources']:
                for value,expected in zip(source['acceleration_m_s2'],oracle[source['id']]):
                    error=abs(value-expected);maximum=max(maximum,error)
                    assert error<=1e-10
                    if abs(expected)>1e-12:assert error/abs(expected)<=1e-10
            totals=[float(sum(Decimal.from_float(v[k]) for v in oracle.values())) for k in range(3)]
            assert max(abs(x-y) for x,y in zip(read['acceleration_m_s2'],totals))<=1e-10
            assert before==(phase(session.sim),session.revision,session.edit_token)
            errors.append(dict(body=body['reference_id'],source_count=15,maximum_component_error_m_s2=maximum))
        report['checks']['16_centers_240_source_contributions_Decimal70']=errors
        progress('sixteen SI readings')
        valid={**guard(first),'body_id':first['bodies'][0]['id']}
        variants=[]
        for key in valid:
            bad=copy.deepcopy(valid);del bad[key];variants.append(('missing '+key,bad))
        for key,value in [('unexpected',1),('system_id','stale'),('edit_token','stale'),('revision',True),('expected_time',True),('frame','SSB'),('body_id','unknown')]:
            variants.append((key+' invalid',{**valid,key:value}))
        for name,bad in variants:refuse(name,lambda b=bad:session.dynamics16_reading(b),session)
        for naif in ['1','2','3','4','5','6','7','8','999']:
            rows=copy.deepcopy(session.registry);issued=list(session.issued_ids)
            rows[-1]['id']=f'exp:{initial["branch_id"]}:naif:{naif}';issued[-1]=rows[-1]['id']
            refuse('registry barycenter/invented '+naif,lambda r=rows,i=issued:validate_registry(r,i,session.system_id,None,initial))
        rows=copy.deepcopy(session.registry);rows[-1]=copy.deepcopy(rows[0])
        refuse('duplicate identity',lambda:validate_registry(rows,session.issued_ids,session.system_id,None,initial))
        for method in ['earth_field','jupiter_field','set_j2','set_tides','set_cloud']:
            refuse('sixteen domain '+method,lambda m=method:getattr(session,m)(valid),session)
        # Explicit dispatch must reject altered initial values even after resealing.
        from import_dispatch import validate
        for name,change in [('GM',lambda v:v['bodies'][0].__setitem__('mass',2.)),
                            ('schema',lambda v:v.__setitem__('schema',2)),
                            ('extra',lambda v:v.__setitem__('unknown',1)),
                            ('barycenter',lambda v:v['bodies'][6].__setitem__('naif_id','5'))]:
            bad=copy.deepcopy(initial);change(bad);bad['initial_state_sha256']=model.digest({k:v for k,v in bad.items() if k!='initial_state_sha256'})
            refuse('initial injection '+name,lambda b=bad:session.import_atlas(b),session)
        progress('transactional refusals')
        propagation=[];replay=[]
        for index,seconds in enumerate(series['seconds']):
            session.integrate(seconds/model.U['time_unit_s'])
            current=np.array(phase(session.sim))[:,1:]
            expected=np.array(series['canonical_IAS15'][index])
            pmax=float(np.abs(current[:,:3]-expected[:,:3]).max()*model.U['length_unit_m'])
            vmax=float(np.abs(current[:,3:]-expected[:,3:]).max()*model.U['velocity_unit_m_s'])
            assert pmax<=.001 and vmax<=1e-8,(seconds,pmax,vmax)
            replay.append(current.tolist());propagation.append(dict(seconds=seconds,position_m=pmax,velocity_m_s=vmax))
            if seconds in (21600.,86400.,2592000.):
                old_phase=phase(session.sim);old_state=session.state();session.save()
                loaded=Session(session.directory);loaded.load()
                assert phase(loaded.sim)==old_phase and loaded.sim.t==session.sim.t
                assert loaded.atlas_initial==initial and loaded.registry==session.registry and loaded.issued_ids==session.issued_ids
                assert loaded.state()['dynamics16']==old_state['dynamics16']
                assert loaded.edit_token!=session.edit_token and loaded.restoration['status']=='same_generation'
                refuse('restore stale token '+str(seconds),lambda:loaded.dynamics16_reading({**guard(old_state),'body_id':old_state['bodies'][0]['id']}),loaded)
        report['checks']['121_states_30_days_against_accepted_IAS15']=propagation
        (folder/'service-30-day-series.json').write_text(json.dumps(dict(seconds=series['seconds'],canonical_phase=replay),allow_nan=False)+'\n',encoding='utf8')
        report['checks']['exact_checkpoint_restore_at_6h_1day_30days']=True
        progress('30 day numerical replay and checkpoints')
        # A resealed frame mutation must still fail atomically.
        path=session.directory/'latest.json';saved_bytes=path.read_bytes();bad=json.loads(saved_bytes)
        bad['split_inertial_frame']['origin_velocity_m_s'][0]+=1
        bad['manifest_sha256']=digest({k:v for k,v in bad.items() if k!='manifest_sha256'})
        path.write_text(json.dumps(bad),encoding='utf8')
        refuse('resealed inertial origin',session.load,session);path.write_bytes(saved_bytes)
        original=session.create_branch({**guard(session.state()),'name':'Dinâmica16 original'})
        first_id=original['id'];selected=session.registry[-1]['id'];old_mass=session.sim.particles[-1].m
        session.set_mass(selected,old_mass*1.01)
        assert session.registry[-1]['reference_id']=='sol:naif:606' and session.interventions[-1]['type']=='set_mass'
        child=session.create_branch({**guard(session.state()),'name':'Titã +1% como intervenção'})
        assert child['parent_id']==first_id and child['revision']==1
        comparison=session.compare_branches({**guard(session.state()),'first_id':first_id,'second_id':child['id']})
        assert comparison['same_physical_instant'] and len(comparison['body_differences'])==16
        target=next(r for r in comparison['body_differences'] if r['id']==selected)
        assert target['delta_mass_kg']!=0 and target['delta_position_m']==[0.,0.,0.]
        (folder/'branch-comparison.json').write_text(json.dumps(comparison,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
        session.load_branch({**guard(session.state()),'branch_id':first_id});assert session.sim.particles[-1].m==old_mass
        session.save();snapshot=copy.deepcopy(session.state());saved_phase=phase(session.sim)
        report['checks']['branch_child_intervention_comparison_export']=dict(parent=first_id,child=child['id'],body=selected)
        # Fresh process uses the actual worker parser, binary archive and dispatch.
        worker=Worker(session.directory);worker.call('load');restored=copy.deepcopy(worker.latest)
        assert [[b['mass'],*b['position'],*b['velocity']] for b in restored['bodies']]==saved_phase
        assert restored['dynamics16']==snapshot['dynamics16'] and restored['paused']
        assert len(worker.call('dynamics16_reading',**guard(restored),body_id=restored['bodies'][0]['id'])['result']['sources'])==15
        from laboratory import Laboratory
        bridge=Laboratory.__new__(Laboratory);bridge.mode='experiment'
        def dispatch(request):
            request=dict(request);name=request.pop('command');return worker.call(name,**request)
        bridge._worker_command=dispatch
        for body in restored['bodies']:
            routed=bridge._apply(dict(command='dynamics16_reading',**guard(restored),body_id=body['id']))
            assert len(routed['result']['sources'])==15
        bridge.mode='atlas'
        refuse('real Laboratory rejects reading outside experiment',lambda:bridge._apply(dict(command='dynamics16_reading',**guard(restored),body_id=restored['bodies'][0]['id'])))
        report['checks']['real_Laboratory_apply_16_readings_and_mode_guard']=True
        worker.call('resume');time.sleep(.15);worker.call('pause');advanced=copy.deepcopy(worker.latest)
        assert advanced['time']>restored['time'] and advanced['paused'] and advanced['requested_rate']==1.
        worker.call('dynamics16_reading',expect_error=True,**guard(restored),body_id=restored['bodies'][0]['id'])
        worker.call('load');assert worker.latest['bodies']==restored['bodies']
        worker.close();worker=None
        report['checks']['fresh_worker_restore_pause_clock_and_stale_phase']=True
        progress('fresh worker and branch persistence')
        # Legacy3/4 operate only in new temporary namespaces; real owner storage stays untouched.
        import atlas as legacy_catalog
        import atlas_import
        import solar_catalog
        import solar_import
        legacy=[]
        for name,package in [('three',atlas_import.prepare(atlas_import.experiment_subset(legacy_catalog.states(utc=UTC)))),
                             ('four',solar_import.prepare(solar_catalog.states(UTC)))]:
            old=Session(folder/('legacy-'+name));old.import_atlas(package);old.integrate(21600/model.U['time_unit_s']);old.save()
            restored_old=Session(old.directory);restored_old.load()
            assert phase(restored_old.sim)==phase(old.sim) and restored_old.state()['dynamics16'] is None
            assert old.state()['scientific_generation']['candidate_extension']['id']=='is3-body-fields'
            worker=Worker(old.directory);worker.call('load');assert len(worker.latest['bodies'])==len(package['bodies'])
            if name=='four':assert len(worker.call('solar_reading',**guard(worker.latest),body_id=worker.latest['bodies'][1]['id'])['result']['sources'])==3
            worker.close();worker=None;legacy.append(dict(kind=package['kind'],bodies=len(package['bodies']),exact_restore=True))
        report['checks']['legacy_three_and_four']=legacy
        assert all(sha(ROOT/n)==s for n,s in protected.items())
        assert all(sha(ROOT/n)==s for n,s in sources.items())
        report.update(completed=True,accepted=True,protected_unchanged=True,finished_utc=dt.datetime.now(dt.timezone.utc).isoformat())
        persist();print(json.dumps(dict(accepted=True,refusals=len(report['refusals']),checks=list(report['checks']))),flush=True)
    except BaseException as error:
        report.update(error=repr(error),traceback=traceback.format_exc());persist();raise
    finally:
        if worker is not None:
            try:worker.close()
            except BaseException:pass


if __name__=='__main__':main()
