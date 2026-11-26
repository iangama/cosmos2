"""Actual science workers and transactional bridge, with scene calls mocked.

This checks cancellation/commit ownership; it cannot accept native rendering.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import shutil
import sys
import threading
import time
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/is5-reference-product0.16.0/app'
WORKER=ROOT/'output/is5-compression-worker-staging'
STAGE=ROOT/'output/is5-compression-admission-staging'
for p in [BASE,WORKER,STAGE]:sys.path.insert(0,str(p))
from is5_laboratory import SolarLaboratory
from is5_compression_client import Client
from is5_compression_artifact import core
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


class Bridge(SolarLaboratory):
    def __init__(self,folder):
        # No protocol thread/native connection. Exercise the production compute
        # and cancel methods directly; each real Client owns its real worker.
        self.storage=folder;self.lock=threading.Lock();self._calculation=None
        self.client=None;self._branch_parent=None;self._command_admitted=False
        self.public=dict(active=False,busy=False);self.error=None
        self.scene=None;self.attach_count=0;self.fail_attach=False

    def _hide(self):pass
    def _attach(self,state):
        if self.fail_attach:raise ValueError('Injected native-attach failure')
        self.scene=copy.deepcopy(state['source']);self.attach_count+=1
    def _restore(self):self.scene=None


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--label',required=True);args=ap.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):ap.error('Invalid label')
    folder=ROOT/f'output/is5-compression-bridge-{args.label}';path=ROOT/f'evidence/is5-compression-bridge-{args.label}.json'
    if folder.exists() or path.exists():raise FileExistsError('Preserve bridge evidence')
    receipt=ROOT/'evidence/is5-compression-worker-artifact-20261029a.json';accepted=json.loads(receipt.read_text());assert accepted['accepted']
    fixture=ROOT/'output/is4-body-snapshot-20261025b/IGRF14-13.json'
    phase=json.loads(fixture.read_text())['phase'];phase_before=copy.deepcopy(phase)
    hashes={**accepted['source_sha256']}
    for p in [Path(__file__),STAGE/'is5_laboratory.py',receipt,fixture,ROOT/'IS-5-COMPRESSAO-PRODUTO-CONTRATO.md']:
        hashes[p.relative_to(ROOT).as_posix()]=sha(p)
    assert all(sha(ROOT/n)==v for n,v in hashes.items())
    folder.mkdir();archive=folder/'executed-sources.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=hashes,archive_sha256=sha(archive),groups=[],
           limits_before_execution=dict(cancel_s=6.,settle_s=2.,calculation_s=660),
           scope='Real workers and physical calculation; scene attachment mocked. No HTTP/CEF/native/visual/profile acceptance.')
    b=Bridge(folder/'checkpoints')
    def persist():path.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    def passed(name,**data):r['groups'].append(dict(name=name,**data));persist();print(json.dumps(r['groups'][-1]),flush=True)
    def begin(config):
        result={}
        def body():
            try:b._compute('create',dict(source_phase=phase,configuration=config),retain_parent=b.client is not None)
            except Exception as error:result['error']=str(error)
        t=threading.Thread(target=body);t.start()
        until=time.monotonic()+15
        while time.monotonic()<until:
            with b.lock:
                tx=b._calculation
                if tx and tx['client'] is not None:return t,result,tx
            if not t.is_alive():break
            time.sleep(.01)
        raise AssertionError('Candidate transaction not published')
    def cancel(config):
        t,result,tx=begin(config);pid=tx['client'].process.pid;began=time.perf_counter()
        reply=b.cancel(dict(transaction_id=tx['id']));elapsed=time.perf_counter()-began
        t.join(2);assert not t.is_alive() and 'cancelado' in result.get('error',''),result
        assert elapsed<=6. and reply['cancelled_transaction_id']==tx['id']
        assert tx['client'].process.poll() is not None and b._calculation is None
        try:b.cancel(dict(transaction_id=tx['id']))
        except ValueError:pass
        else:raise AssertionError('Stale cancellation accepted')
        return elapsed,pid
    config=dict(parameters={**core.base.DEFAULT_PARAMETERS,'duration_s':1000*31557600.,'volume_m3':2.5},
                density_history=dict(kind='exponential',ratio=1.05),mode='prescribed_density',
                acting={k:True for k in ['strong','weak','electromagnetic']},
                channel_switches={k:True for k in core.network.CHANNELS},include_coulomb=True,include_screening=True)
    persist()
    try:
        elapsed,pid=cancel(config)
        assert b.client is None and b.scene is None and b.attach_count==0
        passed('cancel_initial_creation_without_scene_commit',cancel_s=elapsed,terminated_owner_pid=pid)
        source=ROOT/'output/is5-compression-worker-artifact-20261029a/checkpoints/saved.json'
        b.storage.mkdir(exist_ok=True);shutil.copy2(source,b.storage/'saved.json')
        b._compute('load',{})
        old=b.client;before=old.call('get_result')['result'];state=old.snapshot();scene=copy.deepcopy(b.scene)
        b._branch_parent='a'*32
        elapsed,pid=cancel(config)
        assert b.client is old and b.scene==scene and b._branch_parent=='a'*32
        assert old.call('get_result')['result']==before
        after=old.snapshot()
        for key in ['artifact_id','artifact_sha256','edit_token','revision','view','configuration','sample','source']:
            assert state[key]==after[key],key
        time.sleep(.2);assert old.call('get_result')['result']==before
        passed('cancel_recalculation_preserves_exact_confirmed_state_no_late_commit',cancel_s=elapsed,terminated_owner_pid=pid)
        short=copy.deepcopy(config);short['parameters']['duration_s']=1.;short['density_history']=dict(kind='constant')
        b.fail_attach=True
        try:b._compute('create',dict(source_phase=phase,configuration=short))
        except ValueError as error:assert 'Injected native-attach' in str(error)
        else:raise AssertionError('Attach failure accepted')
        assert b.client is old and b.scene==scene and old.call('get_result')['result']==before
        b.fail_attach=False
        passed('injected_scene_failure_preserves_previous_client')
        b._compute('create',dict(source_phase=phase,configuration=short),preferences=state['view'],retain_parent=True)
        assert b.client is not old and old.process.poll() is not None
        assert b.client.call('get_result')['result']['configuration']==short
        assert b.client.snapshot()['view']==state['view'] and b._branch_parent=='a'*32
        assert b.attach_count==2 and b._calculation is None and phase==phase_before
        passed('successful_commit_replaces_and_closes_previous_owner_preserves_view_parent_source')
        assert all(sha(ROOT/n)==v for n,v in hashes.items())
        r.update(accepted=True,completed=True)
    except Exception:r['failure']=traceback.format_exc()
    finally:
        if b.client is not None:b.client.close()
        persist()
    print(json.dumps({k:r.get(k) for k in ['accepted','completed','failure']}),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
