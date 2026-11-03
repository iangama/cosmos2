"""Real hidden candidates, cancelled preparation and lost native acknowledgement."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import argparse,copy,hashlib,json,sys,threading,traceback,zipfile
from cef_page import Page
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'output/is6-spatial-bridge-staging'))
import is6_scene_transaction as tx
from is4_laboratory import ParticleLaboratory
h=SourceFileLoader('transaction_helpers',str(ROOT/'scripts/verify-native-solar-integration.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

class Native:
    _native=ParticleLaboratory._native
    def __init__(self):self.engine=None;self.topic=0;self.cancel=None;self.lose=False
    def __call__(self,code):
        result=self._native(code)
        if self.cancel is not None and 'openspace.addSceneGraphNode' in code:self.cancel.set();self.cancel=None
        if self.lose and 'local is6_commit_candidate=' in code:
            self.lose=False;raise RuntimeError('Injected lost acknowledgement AFTER real engine commit')
        return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/f'output/is6-scene-transaction-{args.label}';receipt=ROOT/f'evidence/is6-scene-transaction-{args.label}.json'
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve previous evidence')
    anchor=ROOT/'evidence/is6-spatial-native-20261101a.json';parent=json.loads(anchor.read_text());assert parent['accepted']
    files=[Path(__file__),Path(tx.__file__),ROOT/'IS-6-PONTE-CENA-CONTRATO.md',ROOT/'evidence/is6-spatial-prototype-visual-20261101a.json']
    hashes=dict(parent['source_sha256']);hashes.update({p.relative_to(ROOT).as_posix():sha(p) for p in files})
    assert all(sha(ROOT/n)==v for n,v in hashes.items());folder.mkdir()
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for n in hashes:archive.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=hashes,groups=[],page_errors=[],owner_sha256=sha(ROOT/'user/sessions/latest.json'),scope='Native transaction protocol only; no product0.18, UI, visual or profile acceptance.')
    def persist():receipt.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def passed(name):r['groups'].append(name);persist();print(name,flush=True)
    native=Native();owner=None;pending=None;persist()
    try:
        with Page() as page:
            page.on('pageerror',lambda e:r['page_errors'].append(e));page.goto(h.BASE+'/')
            page.wait_for_function('appState!==null&&!pending&&solarZoneState!==null')
            assert not h.get('/api/solar-zone/state')['active']
            if h.get('/api/state')['mode']=='experiment':h.post('/api/command',dict(command='atlas'))
            page.wait_for_function('appState?.mode==="atlas"&&!pending');h.click(page,'#copy-solar')
            page.wait_for_function('!pending&&appState?.physics?.paused&&appState.physics.bodies.length===4',timeout=70000)
            phase=h.get('/api/state')['physics'];held=h.phase(copy.deepcopy(phase));owner=tx.Owner(native,phase)
            original=owner._capture();generation=tx.generation();runs={}
            for body in phase['bodies'][:2]:
                runs[body['reference_id']]=tx.base.artifact.Run.create(phase,dict(body_id=body['id'],source_guard=tx.base.artifact.body.guard(phase)),copy.deepcopy(tx.base.artifact.DEFAULT_CONFIGURATION))
            def prepare(name,run=None):return owner.prepare(run or next(iter(runs.values())),folder/name)
            def unchanged(active,context):
                assert owner.active is active and owner._capture()==context
                if active:assert active.read_native()['draw'] is active.visible
                assert h.phase(h.get('/api/state')['physics'])==held
            def absent(candidate):
                result=native('return {a=openspace.hasSceneGraphNode('+tx.lua(candidate.frame)+'),b=openspace.hasSceneGraphNode('+tx.lua(candidate.wire)+'),c=openspace.hasSceneGraphNode('+tx.lua(candidate.focus)+')}')
                assert not any(result.values())
            pending=prepare('first');assert not pending.read_native()['draw'];unchanged(None,original)
            owner.commit(pending);pending=None;first=owner.active;assert first.read_native()['draw']
            context=owner._capture();pending=prepare('replacement',list(runs.values())[1]);unchanged(first,context)
            owner.commit(pending);pending=None;absent(first);active=owner.active;context=owner._capture()
            passed('Hidden_preparation_and_acknowledged_swap_remove_only_previous_nodes')
            event=threading.Event();native.cancel=event
            cancelled=tx.Candidate(native,next(iter(runs.values())),folder/'cancelled')
            try:cancelled.attach(event)
            except ValueError:pass
            else:raise AssertionError('Cancellation accepted')
            assert event.is_set();absent(cancelled);unchanged(active,context)
            try:owner.commit(cancelled,cancel=event)
            except ValueError:pass
            else:raise AssertionError('Late cancelled candidate published')
            passed('Cancellation_after_actual_node_creation_cleans_candidate_and_refuses_late_publication')
            pending=prepare('missing-focus');native('openspace.removeSceneGraphNode('+tx.lua(pending.focus)+');return {removed=true}')
            try:owner.commit(pending)
            except Exception:pass
            else:raise AssertionError('Missing focus accepted')
            unchanged(active,context);pending.close();absent(pending);pending=None
            passed('Missing_native_node_refuses_commit_preserves_previous_scene_camera_phase')
            pending=prepare('lost-ack');native.lose=True
            try:owner.commit(pending)
            except RuntimeError:pass
            else:raise AssertionError('Lost acknowledgement published ownership')
            assert not native.lose and owner.error is None and not pending.read_native()['draw']
            unchanged(active,context);pending.close();absent(pending);pending=None
            passed('Lost_acknowledgement_after_real_engine_swap_rolls_back_without_publishing')
            digest=tx.base.artifact.digest(active.run.payload)
            active.set_visible(False);active.set_visible(True)
            assert tx.base.artifact.digest(active.run.payload)==digest
            owner.close();absent(active);unchanged(None,original)
            assert not r['page_errors'] and sha(ROOT/'user/sessions/latest.json')==r['owner_sha256']
            assert tx.generation()==generation and all(sha(ROOT/n)==v for n,v in hashes.items())
            passed('Visibility_close_restore_original_camera_flags_without_changing_owner_or_phase')
            r.update(accepted=True,completed=True)
    except Exception:r['failure']=traceback.format_exc()
    finally:
        try:
            if pending:pending.close()
            if owner:owner.close()
            if h.get('/api/state')['mode']=='experiment':h.post('/api/command',dict(command='atlas'))
        except Exception:r['cleanup_failure']=traceback.format_exc();r['accepted']=False
        try:native('openspace.toggleShutdown();return {closing=true}')
        except Exception as error:r['shutdown_response']=str(error)
        if native.engine:native.engine.close()
        persist()
    print(json.dumps(r,ensure_ascii=False),flush=True);return 0 if r['accepted'] else 1

if __name__=='__main__':raise SystemExit(main())
