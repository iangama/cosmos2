"""Verify atomic magnetic-view checkpoints, branches, worker dispatch and old copies."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import traceback
import zipfile
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is3-body-view-product/app'
sys.path.insert(0,str(APP))
from session import Session
from body_registry import digest
import body_field_view as view

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


class Worker:
    def __init__(self,folder):
        self.errors=(folder/'worker-stderr.log').open('w',encoding='utf-8')
        self.process=subprocess.Popen([sys.executable,'-u',str(APP/'worker.py'),'--storage',str(folder)],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.errors,text=True,encoding='utf-8')
        self.serial=0
        assert json.loads(self.process.stdout.readline())['type']=='ready'
        self.latest=json.loads(self.process.stdout.readline())

    def call(self,command_name,expect_error=False,**fields):
        self.serial+=1
        self.process.stdin.write(json.dumps({'command':command_name,'id':self.serial,**fields})+'\n');self.process.stdin.flush()
        while True:
            line=self.process.stdout.readline()
            if not line:raise RuntimeError('Worker stopped unexpectedly.')
            response=json.loads(line)
            if response['type']=='snapshot':self.latest=response
            if response.get('id')==self.serial and response['type'] in ('ack','error'):
                assert (response['type']=='error')==expect_error,response
                return response

    def close(self):
        if self.process.poll() is None:self.call('quit')
        self.process.wait(timeout=10);self.errors.close()


helpers=SimpleNamespace(Worker=Worker,
    guard=lambda p:{k:p[k] for k in ['system_id','edit_token','revision']}|{'expected_time':p['time'],'frame':p['contract']['frame']},
    physical=lambda p:{k:copy.deepcopy(p[k]) for k in ['system_id','edit_token','revision','time','bodies','atlas_initial','interventions']})


def phase(session):
    return (session.sim.t,[(p.m,p.x,p.y,p.z,p.vx,p.vy,p.vz) for p in session.sim.particles])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    folder=ROOT/('output/is3-view-checkpoints-'+args.label)
    receipt=ROOT/('evidence/is3-view-checkpoints-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve checkpoint evidence.')
    folder.mkdir()
    paths=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [Path(__file__).resolve(),ROOT/'scripts/verify-solar-tide-worker.py',ROOT/'IS-3-VISUAL-PERSISTENCIA-CONTRATO.md']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for p in paths:archive.write(p,p.relative_to(ROOT).as_posix())
    owner=sha(ROOT/'user/sessions/latest.json')
    prepared=json.loads((ROOT/'evidence/is3-body-view-candidate-prepared-20261024.json').read_text())
    initial=json.loads((ROOT/'output/is3-body-lines-product/gravity-sessions/latest.json').read_text())['atlas_initial']
    report={'schema':1,'accepted':False,'completed':False,'source_sha256':hashes,'roundtrips':[],'checks':{}}
    worker=None
    try:
        for model in ['IGRF14','JRM33']:
            for representation in ['vector','lines']:
                for visible in [False,True]:
                    for evolved in [False,True]:
                        path=folder/(model+'-'+representation+'-'+str(visible)+'-'+str(evolved))
                        session=Session(path);session.import_atlas(initial)
                        state=session.state();body=next(b for b in state['bodies'] if b['reference_id']==('sol:naif:399' if model=='IGRF14' else 'sol:naif:599'))
                        parameters={'latitude_deg':-23.55,'longitude_deg':-46.63,'altitude_m':1000.} if model=='IGRF14' else {'radius_m':1.5*71492000.,'latitude_deg':0.,'east_longitude_deg':0.,'degree':13}
                        reading=getattr(session,'earth_field' if model=='IGRF14' else 'jupiter_field')({**helpers.guard(state),'body_id':body['id'],**parameters})
                        if evolved:session.sim.integrate(21600./state['physical_scale']['time_unit_s'])
                        state=session.state()
                        config={'selected_body_id':body['id'],'representation':representation,'earth':[-23.55,-46.63,1000.],
                                'jupiter':[1.5*71492000.,0.,0.,13]}
                        metadata=view.capture(state,config,{'reading':reading,'representation':representation,'visible':visible})
                        before=phase(session);session.save(renderer_view=metadata)
                        assert phase(session)==before
                        clone=Session(path);clone.load()
                        assert phase(clone)==before and clone.body_field_view==metadata
                        assert clone.edit_token!=session.edit_token
                        request={**helpers.guard(clone.state()),'name':'frozen-view','renderer_view':metadata}
                        record=clone.create_branch(request)
                        assert phase(clone)==before
                        clone.load_branch({**helpers.guard(clone.state()),'branch_id':record['id']})
                        assert phase(clone)==before and clone.body_field_view==metadata
                        report['roundtrips'].append({'model':model,'representation':representation,'visible':visible,'evolved':evolved,
                                                     'checkpoint_and_branch_phase_exact':True})
        report['checks']['atomic_checkpoint_and_branch_roundtrips']=True
        valid=json.loads((path/'latest.json').read_text())
        original_files={p.name:sha(p) for p in path.iterdir() if p.is_file()}
        refused=0
        for change in [lambda m:m['layer'].update(visible=1),
                       lambda m:m['layer']['reading'].update(field_norm_T=0.),
                       lambda m:m.update(fixture_sha256='0'*64),
                       lambda m:m['configuration'].update(earth=[0.,0.,-1.])]:
            bad=copy.deepcopy(metadata);change(bad)
            current=phase(session)
            try:session.save(renderer_view=bad)
            except ValueError:refused+=1
            else:raise AssertionError('Bad save accepted.')
            assert phase(session)==current
            assert {p.name:sha(p) for p in path.iterdir() if p.is_file()}==original_files
            bad_manifest=copy.deepcopy(valid);bad_manifest['body_field_view']=bad
            bad_manifest['manifest_sha256']=digest({k:v for k,v in bad_manifest.items() if k!='manifest_sha256'})
            copied=folder/('bad-load-'+str(refused));copied.mkdir()
            (copied/'latest.json').write_text(json.dumps(bad_manifest)+'\n')
            shutil.copy2(path/valid['binary'],copied/valid['binary'])
            active=Session(copied);before=phase(active)
            try:active.load()
            except ValueError:refused+=1
            else:raise AssertionError('Bad load accepted.')
            assert phase(active)==before
        report['checks']['save_load_refusals_before_files_or_active_phase_mutation']=refused
        source=ROOT/'output/is3-body-lines-product/gravity-sessions'
        old=json.loads((source/'latest.json').read_text());old_hashes={name:sha(source/name) for name in ['latest.json',old['binary']]}
        copied=folder/'old-0.5';copied.mkdir()
        for name in old_hashes:shutil.copy2(source/name,copied/name)
        older=Session(copied);older.load()
        assert older.body_field_view is None and older.state()['restoration']['status']=='changed_generation'
        import rebound
        raw=rebound.Simulation(str(copied/old['binary']))
        assert phase(older)==(raw.t,[(p.m,p.x,p.y,p.z,p.vx,p.vy,p.vz) for p in raw.particles])
        assert all(sha(source/name)==value for name,value in old_hashes.items())
        report['checks']['old_copy_exact_phase_and_absent_view']=True
        storage=folder/'worker';storage.mkdir();worker=helpers.Worker(storage)
        worker.call('import_atlas',initial_state=initial)
        state=copy.deepcopy(worker.latest);body=next(b for b in state['bodies'] if b['reference_id']=='sol:naif:399')
        reading=worker.call('earth_field',**{**helpers.guard(state),'body_id':body['id'],'latitude_deg':0.,'longitude_deg':0.,'altitude_m':0.})['result']
        config={'selected_body_id':body['id'],'representation':'lines','earth':[0.,0.,0.],'jupiter':[1.5*71492000.,0.,0.,13]}
        metadata=view.capture(worker.latest,config,{'reading':reading,'representation':'lines','visible':False})
        physical=helpers.physical(worker.latest);worker.call('save',renderer_view=metadata)
        assert helpers.physical(worker.latest)==physical
        manifest_before=sha(storage/'latest.json')
        bad=copy.deepcopy(metadata);bad['layer']['visible']=1
        worker.call('save',renderer_view=bad,expect_error=True);worker.call('snapshot')
        assert sha(storage/'latest.json')==manifest_before and helpers.physical(worker.latest)==physical
        worker.call('load');assert worker.latest['body_field_view']==metadata
        saved=copy.deepcopy(worker.latest)
        branch=worker.call('create_branch',**{**helpers.guard(saved),'name':'worker-view','renderer_view':metadata})['result']
        worker.call('load_branch',**{**helpers.guard(worker.latest),'branch_id':branch['id']})
        assert worker.latest['body_field_view']==metadata and worker.latest['bodies']==saved['bodies']
        worker.close();worker=None
        report['checks']['actual_worker_save_error_load_branch_dispatch']=True
        assert sha(ROOT/'user/sessions/latest.json')==owner
        assert all(sha(ROOT/name)==value for name,value in hashes.items())
        assert all(sha(ROOT/name)==value for name,value in prepared['base_source_sha256'].items())
        report.update(accepted=True,completed=True,sources_bases_and_owner_preserved=True,
                      scope='Atomic scientific checkpoints and branches with frozen magnetic metadata, actual worker dispatch and old-copy migration. Native scene reconstruction/restart/performance still separate.')
    except Exception:report['failure']=traceback.format_exc()
    finally:
        if worker is not None:worker.close()
        receipt.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'accepted':report['accepted'],'roundtrips':len(report['roundtrips']),
                      'checks':report['checks'],'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
