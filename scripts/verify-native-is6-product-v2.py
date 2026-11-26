"""Own real HTTP/CEF/native admission of the unpromoted spatial candidate."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
from concurrent.futures import ThreadPoolExecutor
import argparse
import copy
import hashlib
import json
import subprocess
import sys
import time
import traceback
import zipfile
from PIL import Image
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is6-spatial-product0.18.0/app'
sys.path.insert(0,str(APP))
from is6_product_scene import Owner,artifact,protocol
from is4_laboratory import ParticleLaboratory
h=SourceFileLoader('is6_product_helpers',str(ROOT/'scripts/verify-native-solar-integration.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/('output/is6-product-native-'+args.label);receipt=ROOT/('evidence/is6-product-native-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve native evidence')
    service_path=ROOT/'evidence/is6-product-service-20261102b.json';assert json.loads(service_path.read_text())['accepted']
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert Path(session['serverScript']).resolve()==(APP/'server.py').resolve()
    manifest=json.loads((APP.parent/'build-manifest.json').read_text())
    hashes=dict(manifest['source_sha256']);hashes.update({(APP/n).relative_to(ROOT).as_posix():v for n,v in manifest['files_sha256'].items()})
    for p in [Path(__file__),APP.parent/'build-manifest.json',service_path,ROOT/'scripts/cef_page.py',ROOT/'scripts/capture-window.ps1',ROOT/'scripts/verify-native-solar-integration.py',ROOT/'scripts/engine-command.py']:
        hashes[p.relative_to(ROOT).as_posix()]=sha(p)
    assert all(sha(ROOT/n)==v for n,v in hashes.items())
    folder.mkdir()
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=hashes,session=session,groups=[],refusals=[],captures=[],page_errors=[],timings=[],
           owner_sha256=sha(ROOT/'user/sessions/latest.json'),limits_before_execution=dict(scene_ready_s=15.,command_s=30.),
           scope='Real spatial HTTP/CEF/native journeys and product scene protocol only; screenshots require separate visual review; no profile or promotion acceptance.')
    def persist():receipt.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def passed(name):r['groups'].append(name);persist();print(name,flush=True)
    def state():return h.get('/api/spatial/state')
    def command(operation,expected=200,**extra):
        began=time.monotonic();result=h.post('/api/spatial/command',dict(command=operation,guard=state()['guard'],**extra),expected)
        elapsed=time.monotonic()-began;r['timings'].append(dict(command=operation,elapsed_s=elapsed));assert elapsed<=30.,(operation,elapsed)
        return result
    def absent(scene):
        assert not any(h.native('return {'+','.join(k+'=openspace.hasSceneGraphNode('+json.dumps(scene[k])+')' for k in ['frame','wire','focus'])+'}').values())
    def native_state(s):
        return h.native('return {draw=openspace.propertyValue("Scene.'+s['scene']['wire']+'.Renderable.DrawElements"),camera=openspace.navigation.getNavigationState("Root")}')
    def capture(name):
        path=ROOT/('evidence/cosmos2-is6-product-'+args.label+'-'+name+'.png')
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',path.name],check=True,capture_output=True)
        im=Image.open(path);assert im.size==(1920,1080)
        rgb=folder/path.name;im.convert('RGB').save(rgb)
        r['captures'].append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),RGB=rgb.relative_to(ROOT).as_posix(),RGB_sha256=sha(rgb)));persist()
    def idle(page):page.wait_for_function('!spatialInstrument.pending&&!spatialInstrument.snapshot.busy',timeout=40000)
    def click(page,selector):
        page.wait_for_function('!document.querySelector('+json.dumps(selector)+').disabled',timeout=40000)
        page.locator(selector).click();idle(page)
    direct_owner=None;direct_native=None
    try:
        with Page() as page:
            page.on('pageerror',lambda error:r['page_errors'].append(error));page.goto(h.BASE+'/')
            page.wait_for_function('appState!==null&&spatialInstrument.snapshot!==null&&!pending')
            assert not state()['active']
            h.click(page,'#open-spatial');click(page,'#spatial-copy')
            page.wait_for_function('appState?.mode==="experiment"&&appState.physics.paused&&!pending',timeout=70000)
            phase=h.get('/api/state')['physics'];held=h.phase(copy.deepcopy(phase));original=h.native('return {camera=openspace.navigation.getNavigationState("Root")}')
            assert len(phase['bodies'])==4
            first_artifact=None
            for body in phase['bodies']:
                page.locator('#spatial-body').select_option(body['id'])
                began=time.monotonic();click(page,'#spatial-create');elapsed=time.monotonic()-began
                s=state();assert s['active'] and not s['error'] and s['artifact']['source']['body_id']==body['id'],s
                assert elapsed<=30. and s['scene']['ready_s']<=15.
                r['timings'].append(dict(command='CEF_create',body=body['reference_id'],elapsed_s=elapsed,scene_ready_s=s['scene']['ready_s']))
                actual=command('get_artifact')['result'];run=artifact.Run.restore(actual)
                assert s['artifact']['sample']==run.sample(s['artifact']['view']) and native_state(s)['draw']
                view={**s['artifact']['view'],'selected_radial_index':32,'selected_azimuth_index':95,'reference_radial_index':0}
                for field,value in [('radial',32),('azimuth',95),('reference',0)]:page.evaluate('document.getElementById('+json.dumps('spatial-'+field)+').value='+json.dumps(str(value)))
                click(page,'#spatial-sample');s=state();assert s['artifact']['view']==view and s['artifact']['sample']==run.sample(view)
                if first_artifact is None:
                    command('branch_create',name='Sol · origem');command('save');first_artifact=state()['artifact'];first_parent=state()['branch_parent']
                page.evaluate('document.getElementById("spatial-panel").scrollTop=0');capture(body['reference_id'].split(':')[-1]+'-100')
                click(page,'#spatial-visible');hidden=state();assert not native_state(hidden)['draw'] and hidden['artifact']['sha256']==s['artifact']['sha256']
                click(page,'#spatial-visible');assert native_state(state())['draw']
                assert h.phase(h.get('/api/state')['physics'])==held
                old=state()['scene'];click(page,'#spatial-leave');absent(old)
                assert h.native('return {camera=openspace.navigation.getNavigationState("Root")}')==original
            passed('Four_bodies_CEF_creation_exact_probes_visibility_native_transforms_and_restored_camera_phase')
            click(page,'#spatial-load-saved');s=state();assert s['artifact']==first_artifact and s['branch_parent']==first_parent
            old_guard=s['guard'];command('branch_create',name='Sol · filho');child=state()['branch_parent']
            assert next(b for b in state()['branches'] if b['id']==child)['parent']==first_parent
            export=command('export')['result'];assert json.loads(Path(export['path']).read_text())['lineage_parent']==child
            command('branch_load',branch_id=first_parent);assert state()['branch_parent']==first_parent
            response=h.post('/api/spatial/command',dict(command='save',guard=old_guard),400);assert not response['ok'];r['refusals'].append('stale_view')
            for path,payload,name in [('/api/command',dict(command='atlas'),'orbital_change'),('/api/solar-zone/command',dict(command='create'),'solar_zone'),('/api/particles/command',dict(command='create'),'particle')]:
                assert not h.post(path,payload,400)['ok'];r['refusals'].append(name)
            config={**state()['artifact']['configuration'],'radial_count':257,'vertical_amplification':500.}
            command('configure',configuration=config);s=state();assert s['artifact']['configuration']==config and s['artifact']['id']!=first_artifact['id']
            assert s['scene']['ready_s']<=15.
            page.wait_for_function('spatialInstrument.snapshot.artifact?.id==='+json.dumps(s['artifact']['id']))
            page.locator('#ui-scale').select_option('1.5');page.evaluate('document.getElementById("spatial-panel").scrollTop=0');time.sleep(.3);capture('maximum-150')
            page.evaluate('document.getElementById("spatial-reading").scrollIntoView({block:"start"})');capture('probes-150')
            page.locator('#ui-scale').select_option('1');command('load');assert state()['artifact']==first_artifact
            passed('Saved_restore_maximum_resolution_branch_lineage_export_and_source_conflict_guards')
            # Genuine native initialization leaves a cancellable preparation window.
            page.wait_for_function('!spatialInstrument.snapshot.busy')
            page.locator('#spatial-resolution').select_option('257')
            before=state();camera=native_state(before);before_scene=before['scene']
            page.locator('#spatial-recompute').click()
            page.wait_for_function('spatialInstrument.snapshot.transaction?.cancellable',timeout=12000)
            tx=state()['transaction'];assert tx and tx['cancellable']
            assert not h.post('/api/spatial/command',dict(command='save',guard=before['guard']),400)['ok'];r['refusals'].append('concurrent_spatial')
            assert not h.post('/api/command',dict(command='atlas'),400)['ok'];r['refusals'].append('concurrent_source')
            assert not h.post('/api/spatial/cancel',dict(transaction_id='wrong'),400)['ok'];r['refusals'].append('wrong_cancel_id')
            click(page,'#spatial-cancel');after=state()
            assert after['artifact']==before['artifact'] and after['guard']==before['guard']
            assert after['scene']==before_scene and native_state(after)==camera
            assert h.phase(h.get('/api/state')['physics'])==held
            passed('Real_CEF_cancel_during_preparation_preserves_artifact_camera_view_phase_rejects_concurrent_commands')
            # Product-specific rollback, after real commits and readback failure.
            scene=state()['scene'];command('leave');absent(scene)
            class Native:
                _native=ParticleLaboratory._native
                def __init__(self):self.engine=None;self.topic=0;self.lose=False;self.fail_read=False;self.arm_read=False
                def __call__(self,code):
                    if self.arm_read and 'return {exists=' in code:
                        self.arm_read=False;raise RuntimeError('Injected readback failure after real commit')
                    result=self._native(code)
                    if 'local is6_product_commit=' in code:
                        if self.lose:self.lose=False;raise RuntimeError('Injected lost ACK after real product commit')
                        if self.fail_read:self.fail_read=False;self.arm_read=True
                    return result
            direct_native=Native();direct_owner=Owner(direct_native,phase)
            command('load_saved',source_guard=artifact.body.guard(phase))
            run=artifact.Run.restore(command('get_artifact')['result'])
            command('leave')
            initial=direct_owner.prepare(run,folder/'direct-first');direct_owner.commit(initial)
            context=direct_owner._capture();first=direct_owner.active
            for mode in ['lose','fail_read']:
                candidate=direct_owner.prepare(run,folder/('direct-'+mode));setattr(direct_native,mode,True)
                try:direct_owner.commit(candidate)
                except RuntimeError:pass
                else:raise AssertionError('Failed product commit accepted')
                assert direct_owner.active is first and direct_owner._capture()==context and first.read_native()['draw'] and not candidate.read_native()['draw']
                candidate.close()
            direct_owner.close();direct_owner=None;absent(dict(frame=first.frame,wire=first.wire,focus=first.focus))
            passed('Product_owner_lost_ACK_and_post_commit_readback_failure_real_native_rollback_before_publication')
            assert not r['page_errors'] and sha(ROOT/'user/sessions/latest.json')==r['owner_sha256']
            assert all(sha(ROOT/n)==v for n,v in hashes.items())
            r.update(accepted=True,completed=True)
    except Exception:r['failure']=traceback.format_exc()
    finally:
        try:
            if direct_owner:direct_owner.close()
            if direct_native and direct_native.engine:direct_native.engine.close()
            if state()['active'] or state().get('recovery_required'):command('leave')
            if h.get('/api/state')['mode']=='experiment':h.post('/api/command',dict(command='atlas'))
        except Exception:r['cleanup_failure']=traceback.format_exc();r['accepted']=False
        try:h.native('openspace.toggleShutdown();return {closing=true}')
        except Exception as error:r['shutdown_response']=str(error)
        persist()
    print(json.dumps({k:v for k,v in r.items() if k not in {'source_sha256','session','captures'}}),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
