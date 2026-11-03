"""Real scientific/persistence service; controlled scene boundary, no native claim."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse
import copy
import hashlib
import json
import sys
import threading
import time
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT/'output/is6-spatial-product0.18.0/app'
sys.path.insert(0, str(APP))
import is6_laboratory as service
artifact = service.artifact
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/('output/is6-product-service-'+args.label);receipt=ROOT/('evidence/is6-product-service-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve evidence')
    manifest=json.loads((APP.parent/'build-manifest.json').read_text())
    hashes=dict(manifest['source_sha256'])
    hashes.update({(APP/n).relative_to(ROOT).as_posix():v for n,v in manifest['files_sha256'].items()})
    fixture=ROOT/'output/is6-body-fixtures-20261101a/fixtures-before-execution.json'
    for p in [Path(__file__),fixture,APP.parent/'build-manifest.json']:hashes[p.relative_to(ROOT).as_posix()]=sha(p)
    assert all(sha(ROOT/n)==v for n,v in hashes.items())
    folder.mkdir()
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,groups=[],refusals=[],source_sha256=hashes,
           scope='Real mathematics/artifacts/Windows persistence and serial service; scene boundary controlled. No HTTP/CEF/native/visual/profile acceptance.')
    owner_path=ROOT/'user/sessions/latest.json';r['owner_sha256']=sha(owner_path)
    def persist():receipt.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def passed(name):r['groups'].append(name);persist();print(name,flush=True)
    phase=json.loads(fixture.read_text())['phases'][0]
    class Lab:
        def status(self):return dict(mode='experiment',physics=copy.deepcopy(phase))
    control=dict(block=False,entered=threading.Event(),release=threading.Event(),fail=False,commits=0,nodes=set())
    BaseCandidate=service.protocol.Candidate
    class Candidate(BaseCandidate):
        def attach(self,cancel=None):
            self.attached=True;self.visible=False;self.ready_s=0.;control['nodes'].add(self.frame)
            control['entered'].set()
            if control['block']:
                if not control['release'].wait(10):raise TimeoutError('Test barrier')
            service.protocol.check_cancel(cancel)
            return self.read_native()
        def read_native(self):return dict(exists=self.frame in control['nodes'],draw=self.visible)
        def set_visible(self,value):self.visible=value
        def close(self):control['nodes'].discard(self.frame);self.attached=False
    class Owner:
        def __init__(self,native,p):self.current_phase=copy.deepcopy(p);self.active=None;self.faulted=False;self.error=None
        def commit(self,candidate,visible=True,cancel=None):
            service.protocol.check_cancel(cancel)
            if control['fail']:raise RuntimeError('Controlled native refusal')
            if self.active:self.active.close()
            candidate.visible=visible;self.active=candidate;control['commits']+=1
            return candidate.read_native()
        def close(self):
            if self.active:self.active.close();self.active=None
    service.protocol.Candidate=Candidate;service.Owner=Owner
    instrument=None
    try:
        instrument=service.SpatialLaboratory(Lab(),storage=folder/'checkpoints',native=lambda _:None)
        def command(operation,**extra):return instrument.command(dict(command=operation,guard=instrument.status()['guard'],**extra))
        def refusal(name,fn):
            before=instrument.status();held=None if not before['active'] else before['artifact']
            try:fn()
            except (ValueError,RuntimeError,FileNotFoundError):r['refusals'].append(name)
            else:raise AssertionError('Accepted '+name)
            after=instrument.status();assert after['guard']==before['guard'] and after['artifact']==held
        for body in phase['bodies']:
            command('create',source_guard=artifact.body.guard(phase),body_id=body['id'],configuration=copy.deepcopy(artifact.DEFAULT_CONFIGURATION))
            s=instrument.status();p=command('get_artifact')['result'];run=artifact.Run.restore(p)
            assert s['artifact']['sample']==run.sample(s['artifact']['view'])
            view={**s['artifact']['view'],'selected_radial_index':32,'selected_azimuth_index':95,'reference_radial_index':0,'visible':False}
            command('set_view',view=view);assert instrument.status()['artifact']['sha256']==artifact.digest(p)
            assert instrument.status()['artifact']['sample']==run.sample(view)
            external=instrument.status();external['artifact']['configuration']['radial_count']=999
            assert instrument.status()['artifact']['configuration']['radial_count']==65
            command('leave');assert not control['nodes']
        passed('Four_bodies_exact_probes_visibility_preserve_artifact_and_status_isolation')
        command('create',source_guard=artifact.body.guard(phase),body_id=phase['bodies'][0]['id'],configuration=copy.deepcopy(artifact.DEFAULT_CONFIGURATION))
        command('branch_create',name='Referência inicial');parent=instrument.status()['branch_parent']
        command('save');saved=instrument.store.path.read_bytes();old=instrument.status()['artifact']
        config={**old['configuration'],'radial_count':257,'vertical_amplification':0.}
        command('configure',configuration=config);assert instrument.status()['artifact']['id']!=old['id']
        command('load');assert instrument.status()['artifact']==old and instrument.status()['branch_parent']==parent
        command('branch_create',name='Filho');child=instrument.status()['branch_parent'];catalog=instrument.status()['branches'];assert next(b for b in catalog if b['id']==child)['parent']==parent
        command('branch_load',branch_id=parent);assert instrument.status()['branch_parent']==parent
        exported=command('export')['result'];assert json.loads(Path(exported['path']).read_text())['artifact']['id']==old['id']
        passed('Maximum_reconfigure_save_load_branches_lineage_export_confirmed')
        refusal('stale_guard',lambda:instrument.command(dict(command='save',guard={**instrument.status()['guard'],'revision':-1})))
        refusal('bool_guard',lambda:instrument.command(dict(command='save',guard={**instrument.status()['guard'],'revision':True})))
        refusal('bad_config',lambda:command('configure',configuration={**config,'radial_count':True}))
        refusal('extra_field',lambda:command('save',extra=1))
        refusal('bad_probe',lambda:command('set_view',view={**instrument.status()['artifact']['view'],'selected_radial_index':True}))
        refusal('bad_branch_path',lambda:command('branch_load',branch_id='../escape'))
        instrument.store.path.write_text('{}')
        refusal('damaged_checkpoint',lambda:command('load'));instrument.store.path.write_bytes(saved)
        control['fail']=True;refusal('native_refusal',lambda:command('configure',configuration=config));control['fail']=False
        assert len(control['nodes'])==1
        passed('Guard_configuration_probe_path_file_and_scene_refusals_preserve_confirmed_artifact')
        control['block']=True;control['entered'].clear();control['release'].clear();before=instrument.status();commits=control['commits']
        with ThreadPoolExecutor(max_workers=2) as pool:
            preparing=pool.submit(command,'configure',configuration=config)
            assert control['entered'].wait(10)
            s=instrument.status();assert s['busy'] and s['transaction']['cancellable'] and s['artifact']==before['artifact']
            start=time.monotonic();refusal('concurrent_admission',lambda:command('save'));assert time.monotonic()-start<1
            refusal('wrong_cancellation_id',lambda:instrument.cancel(dict(transaction_id='wrong')))
            cancelling=pool.submit(instrument.cancel,dict(transaction_id=s['transaction']['id']))
            until=time.monotonic()+3
            while not instrument.transaction['cancel'].is_set():
                assert time.monotonic()<until;time.sleep(.01)
            control['release'].set()
            try:preparing.result(15)
            except ValueError:pass
            else:raise AssertionError('Cancelled candidate published')
            assert cancelling.result(15)['ok']
        control['block']=False
        assert instrument.status()['artifact']==before['artifact'] and control['commits']==commits and len(control['nodes'])==1
        command('leave');assert not control['nodes']
        command('load_saved',source_guard=artifact.body.guard(phase));assert instrument.status()['artifact']['id']==old['id']
        passed('Cancellation_after_prepared_nodes_nonblocking_admission_no_late_publication_and_restore_after_close')
        command('leave');instrument.close();instrument=None
        assert not control['nodes'] and sha(owner_path)==r['owner_sha256']
        assert all(sha(ROOT/n)==v for n,v in hashes.items())
        r.update(accepted=True,completed=True)
    except Exception:r['failure']=traceback.format_exc()
    finally:
        if instrument:
            try:instrument.close()
            except Exception:r['cleanup_failure']=traceback.format_exc();r['accepted']=False
        persist()
    print(json.dumps({k:v for k,v in r.items() if k not in {'source_sha256'}}),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
