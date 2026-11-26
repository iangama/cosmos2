"""K4 real save/branch/export journeys and a second-process archived restore."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import argparse
import copy
import hashlib
import itertools
import json
import math
import shutil
import subprocess
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
import zipfile
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is6-layers-product0.20.0/app';sys.path.insert(0,str(APP))
from cef_page import Page
from is6_product_scene import lua
import is6_layer_contract as contract
import is6_layers_store as storage
import body_field_scene
h=SourceFileLoader('k4_native_helpers',str(ROOT/'scripts/benchmark-body-points-native.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);parser.add_argument('--phase',choices=['first','restart'],required=True);parser.add_argument('--seed-label',default='20261104a');args=parser.parse_args()
    for label in [args.label,args.seed_label]:
        if not label or len(label)>24 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):parser.error('Invalid label')
    folder=ROOT/('output/is6-layers-storage-native-'+args.label);out=ROOT/('evidence/is6-layers-storage-native-'+args.label+'.json')
    if folder.exists() or out.exists():raise FileExistsError('Preserve native evidence')
    manifest_path=APP.parent/'build-manifest.json';manifest=json.loads(manifest_path.read_text());assert manifest['candidate']=='0.20.0' and manifest['promoted'] is False
    hashes=dict(manifest['source_sha256'])
    for name,seal in manifest['files_sha256'].items():hashes[(APP/name).relative_to(ROOT).as_posix()]=seal
    for path in [Path(__file__),manifest_path,ROOT/'scripts/run-is6-layers-storage-verification.py',ROOT/'scripts/cef_page.py',ROOT/'scripts/benchmark-body-points-native.py',ROOT/'scripts/verify-native-solar-integration.py',ROOT/'scripts/capture-window.ps1']:
        hashes[path.relative_to(ROOT).as_posix()]=sha(path)
    seed=None
    if args.phase=='restart':
        seed_path=ROOT/('evidence/is6-layers-storage-native-'+args.seed_label+'.json');seed=json.loads(seed_path.read_text());assert seed['accepted'] and seed['phase']=='first'
        process=ROOT/('evidence/is6-layers-storage-native-process-'+args.seed_label+'.json');assert json.loads(process.read_text())['accepted']
        for path in [seed_path,process]:hashes[path.relative_to(ROOT).as_posix()]=sha(path)
        for item in seed['stored_archives']:hashes[item['path']]=item['sha256']
    assert all(sha(ROOT/p)==seal for p,seal in hashes.items())
    launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'));assert Path(launch['serverScript']).resolve()==APP/'server.py'
    folder.mkdir();archive=folder/'executed-sources-and-records.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name in hashes:z.write(ROOT/name,name)
    store=storage.Store(APP.parent/'layer-checkpoints')
    r=dict(accepted=False,completed=False,phase=args.phase,session=launch,source_sha256=hashes,
           owner_sha256=sha(ROOT/'user/sessions/latest.json'),sciences={},checks=[],captures=[],refusals=[],saved={},cancellation_attempts=[],stored_archives=[],page_errors=[],
           scope='K4 native store/restore slice only. Separate first/restart receipts; no final 0.20.0 performance, automatic legacy migration, promotion or full IS6/v1 acceptance.')
    def persist():out.write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    def state():return h.get('/api/layers/state')
    def command(name,**fields):return h.post('/api/layers/command',dict(command=name,guard=state()['guard'],**fields))
    def click(page,selector):
        page.evaluate('(()=>{const e=document.querySelector('+json.dumps(selector)+');for(let p=e.parentElement;p;p=p.parentElement)if(p.tagName==="DETAILS")p.open=true;})()')
        page.wait_for_function('!document.querySelector('+json.dumps(selector)+').disabled',timeout=30000);page.locator(selector).click()
        page.wait_for_function('!layerInstrument.pending&&!layerInstrument.snapshot?.busy',timeout=70000)
    def success(page):
        assert not page.evaluate('layerInstrument.error'),page.evaluate('layerInstrument.error')
        assert not state()['error'] and not state()['recovery_required'],state()['error']
    def context(phase):
        names=['LabGrid','LabBarycenter','LabProbe']
        for body in phase['bodies']:names.extend(body[k] for k in ['scene_node','label_node','shape_node','spin_node'] if body.get(k))
        return h.native('local f={};for _,n in ipairs('+lua(names)+') do if openspace.hasSceneGraphNode(n) then local ok,v=pcall(openspace.propertyValue,"Scene."..n..".Renderable.Enabled");if ok and type(v)=="boolean" then f[n]=v end end end;return {camera=openspace.navigation.getNavigationState("Root"),flags=f}')
    def same_context(a,b):
        assert a['flags']==b['flags'] and a['camera'].keys()==b['camera'].keys()
        for key,value in a['camera'].items():
            if key=='Up':assert all(abs(x-y)<=1e-12 for x,y in zip(value,b['camera'][key],strict=True))
            else:assert value==b['camera'][key],key
    def set_visible(page,visible):
        for key in ['spatial','magnetic']:
            selector='#layers-'+key+'-visible'
            if page.evaluate('document.querySelector('+json.dumps(selector)+').checked')!=visible[key]:click(page,selector)
        success(page);assert state()['artifact']['visible']==visible
    def confirm(phase,*,expected_digest=None,visible=None):
        s=state();assert s['active'] and not s['busy'] and not s['recovery_required']
        got=command('get_artifact')['result'];scientific=got['scientific'];digest=contract.digest(scientific)
        assert digest==got['sha256']==s['artifact']['sha256']
        if expected_digest:assert digest==expected_digest
        if visible is not None:assert got['visible']==s['artifact']['visible']==visible
        source=scientific['spatial']['phase'];run=contract.artifact.Run.restore(scientific['spatial'])
        assert contract.magnetic(source,scientific['magnetic'])==scientific['magnetic']
        assert contract.compose(source,run.payload,scientific['magnetic'],dict(spatial=True,magnetic=True))==scientific['admission']
        scene=s['scene'];g=body_field_scene.build(scientific['magnetic']);expected=body_field_scene.product(g['body_to_render'],g['point_model_m'])
        raw=h.native('local f={};for _,n in ipairs('+lua(scene['magnetic_nodes'])+') do f[n]=openspace.propertyValue("Scene."..n..".Renderable.DrawElements") end;return {spatial=openspace.propertyValue("Scene.'+scene['spatial_wire']+'.Renderable.DrawElements"),magnetic=f,local_point=openspace.propertyValue("Scene.'+scene['magnetic_frame']+'_probe.Translation.Position"),point=openspace.worldPosition('+lua(scene['magnetic_frame']+'_probe')+'),center=openspace.worldPosition('+lua(scene['magnetic_frame'])+')}')
        flags=s['artifact']['visible'];assert raw['spatial'] is flags['spatial'] and all(v is flags['magnetic'] for v in raw['magnetic'].values())
        assert max(abs(x-y) for x,y in zip(raw['local_point'],expected,strict=True))<=.001
        assert all(abs((p-c)-e)<=math.ulp(p)+math.ulp(c)+.001 for p,c,e in zip(raw['point'],raw['center'],expected,strict=True))
        assert h.test.phase(h.get('/api/state')['physics'])==h.test.phase(phase)
        r['checks'].append(dict(body=scientific['magnetic']['body_reference_id'],digest=digest,visible=flags,archived=s['artifact']['archived'],live_source_guard=s['artifact']['live_source_guard'],native=raw))
        return scientific,digest
    def leave(page,phase,baseline):
        scene=state()['scene'];click(page,'#layers-leave');success(page);assert not state()['active'];same_context(baseline,context(phase))
        nodes=[scene['spatial_frame'],scene['spatial_wire'],scene['spatial_frame'].replace('SpatialFrame_','SpatialFocus_'),scene['magnetic_frame'],*scene['magnetic_nodes'],*[scene['magnetic_frame']+s for s in ['_basis','_probe','_display_probe']]]
        absent=h.native('local r={};for _,n in ipairs('+lua(nodes)+') do r[n]=openspace.hasSceneGraphNode(n) end;return r');assert not any(absent.values())
        r.setdefault('cleanups',[]).append(dict(nodes=absent,context=context(phase)))
    def capture(page,target,scale,section='overview'):
        page.locator('#ui-scale').select_option(scale)
        if section=='storage':page.evaluate('document.getElementById("layers-storage").open=true;document.getElementById("layers-storage-fields").scrollIntoView({block:"start"})')
        else:page.evaluate('document.getElementById("layers-storage").open=false;document.getElementById("layers-panel").scrollTop=0')
        time.sleep(.2);name='cosmos2-is6-storage-'+args.label+'-'+target+'-'+section+'-'+str(int(float(scale)*100))+'.png'
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',name],check=True,capture_output=True)
        path=ROOT/'evidence'/name;rgb=folder/name;im=Image.open(path);assert im.size==(1920,1080);im.convert('RGB').save(rgb)
        layout=page.evaluate('(()=>{const e=document.getElementById("layers-panel"),r=e.getBoundingClientRect(),b=document.getElementById("layers-leave").getBoundingClientRect();return {scroll:e.scrollWidth,client:e.clientWidth,panel:{top:r.top,bottom:r.bottom},leave:{top:b.top,bottom:b.bottom},error:layerInstrument.error};})()')
        assert layout['scroll']==layout['client'] and not layout['error'];assert layout['panel']['top']<=layout['leave']['top']<layout['leave']['bottom']<=layout['panel']['bottom']
        r['captures'].append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),RGB=rgb.relative_to(ROOT).as_posix(),RGB_sha256=sha(rgb),layout=layout));persist()
    def export_check(page,digest):
        before=set(store.exports.glob('*.json'));click(page,'#layers-export');success(page);new=set(store.exports.glob('*.json'))-before;assert len(new)==1
        path=new.pop();data=json.loads(path.read_text());scientific,visible=storage.decode(data);assert contract.digest(scientific)==digest and visible==state()['artifact']['visible']
        r.setdefault('exports',[]).append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path)))
    def refusal(path,payload,phase):
        before=state();camera=context(phase);answer=h.post(path,payload,expected=400);after=state()
        assert answer['ok'] is False and after['guard']==before['guard'] and after['scene']==before['scene'] and after['artifact']==before['artifact']
        same_context(camera,context(phase));assert h.test.phase(h.get('/api/state')['physics'])==h.test.phase(phase)
        r['refusals'].append(dict(path=path,error=answer['error']))
    persist()
    try:
        with Page() as page:
            page.on('pageerror',lambda e:r['page_errors'].append(e));page.goto(h.test.BASE+'/');page.wait_for_function('appState&&atlasState&&layerInstrument.snapshot&&!pending')
            assert h.get('/api/state')['mode']=='atlas' and not state()['active'];assert state()['checkpoint_available'] is (args.phase=='restart')
            click(page,'#open-layers');click(page,'#layers-copy');page.wait_for_function('appState.physics?.bodies.length===4&&!pending',timeout=70000)
            phase=h.get('/api/state')['physics'];r['source_phase']=phase;baseline=context(phase);r['base_context']=baseline
            assert baseline['flags'] and any(baseline['flags'].values())
            if args.phase=='first':
                for target in ['399','599']:
                    body=next(b for b in phase['bodies'] if b['reference_id']=='sol:naif:'+target);page.locator('#layers-body').select_option(body['id']);click(page,'#layers-create');success(page)
                    scientific,digest=confirm(phase);r['sciences'][target]=scientific
                    visible=dict(spatial=target=='599',magnetic=target=='399');set_visible(page,visible);click(page,'#layers-save');success(page)
                    restored,stored_flags,_=store.load();assert restored==scientific and stored_flags==visible
                    page.evaluate('document.getElementById("layers-branch-name").value='+json.dumps('Referência '+target));click(page,'#layers-branch-create');success(page)
                    branch=state()['branch_parent'];r['saved'][target]=dict(digest=digest,visible=visible,branch_id=branch)
                    if target=='399':
                        set_visible(page,dict(spatial=True,magnetic=False));page.evaluate('document.getElementById("layers-branch-name").value="Filho terrestre"');click(page,'#layers-branch-create');success(page)
                        child=state()['branch_parent'];assert next(b for b in state()['branches'] if b['id']==child)['parent']==branch;r['saved'][target]['child_id']=child
                        click(page,'#layers-load');success(page);assert state()['artifact']['archived'];confirm(phase,expected_digest=digest,visible=visible)
                    export_check(page,digest)
                    good=store.path.read_bytes();bad=json.loads(good);bad['checkpoint']['scientific']['magnetic']['field_norm_T']*=2
                    envelope=bad['checkpoint'];envelope['scientific_sha256']=contract.digest(envelope['scientific']);envelope['checkpoint_sha256']=contract.digest({k:v for k,v in envelope.items() if k!='checkpoint_sha256'});bad['record_sha256']=contract.digest({k:v for k,v in bad.items() if k!='record_sha256'})
                    store.path.write_text(json.dumps(bad),encoding='utf8');refusal('/api/layers/command',dict(command='load',guard=state()['guard']),phase);store.path.write_bytes(good)
                    for branch_id in ['../latest',None]:refusal('/api/layers/command',dict(command='branch_load',guard=state()['guard'],branch_id=branch_id),phase)
                    command('get_artifact');set_visible(page,dict(spatial=True,magnetic=True));page.wait_for_function('!layerInstrument.snapshot.error')
                    for scale in ['1','1.5']:capture(page,target,scale)
                    capture(page,target,'1.5','storage');page.locator('#ui-scale').select_option('1');leave(page,phase,baseline)
                # The latest file stays Jovian; branch switches must not rewrite it.
                latest=store.path.read_bytes();click(page,'#layers-load-saved');success(page);confirm(phase,expected_digest=r['saved']['599']['digest'],visible=r['saved']['599']['visible'])
                page.locator('#layers-branches').select_option(r['saved']['399']['child_id']);click(page,'#layers-branch-load');success(page);confirm(phase,expected_digest=r['saved']['399']['digest'],visible=dict(spatial=True,magnetic=False))
                assert store.path.read_bytes()==latest;leave(page,phase,baseline)
            else:
                assert phase['system_id']!=seed['source_phase']['system_id']
                r['new_live_identity']=phase['system_id'];r['archived_source_identity']=seed['source_phase']['system_id']
                click(page,'#layers-load-saved');success(page);assert state()['artifact']['archived']
                scientific,digest=confirm(phase,expected_digest=seed['saved']['599']['digest'],visible=seed['saved']['599']['visible']);r['sciences']['599']=scientific
                assert scientific['spatial']['phase']['system_id']==seed['source_phase']['system_id'] and state()['artifact']['live_source_guard']['system_id']==phase['system_id']
                hidden=context(phase)['flags'];assert hidden.keys()==baseline['flags'].keys() and all(v is False for v in hidden.values())
                for spatial,magnetic in itertools.product([False,True],repeat=2):
                    visible=dict(spatial=spatial,magnetic=magnetic);set_visible(page,visible);click(page,'#layers-save');success(page);leave(page,phase,baseline)
                    click(page,'#layers-load-saved');success(page);confirm(phase,expected_digest=digest,visible=visible)
                for scale in ['1','1.5']:capture(page,'599',scale)
                capture(page,'599','1.5','storage');page.locator('#ui-scale').select_option('1')
                page.locator('#layers-branches').select_option(seed['saved']['399']['child_id']);click(page,'#layers-branch-load');success(page)
                scientific,earth_digest=confirm(phase,expected_digest=seed['saved']['399']['digest'],visible=dict(spatial=True,magnetic=False));r['sciences']['399']=scientific
                set_visible(page,dict(spatial=True,magnetic=True));export_check(page,earth_digest)
                # A public load races public cancellation during genuine hidden
                # preparation, retaining the confirmed Earth pair on success.
                cancelled=False
                for attempt in range(5):
                    before=state();camera=context(phase);replies=[];payload=dict(command='load',guard=before['guard'])
                    def restore():
                        req=urllib.request.Request(h.test.BASE+'/api/layers/command',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
                        try:response=urllib.request.urlopen(req,timeout=70)
                        except urllib.error.HTTPError as error:response=error
                        replies.append(dict(status=response.status,body=json.load(response)))
                    worker=threading.Thread(target=restore);worker.start();deadline=time.monotonic()+5;answer=None;cancel_error=None
                    while worker.is_alive() and time.monotonic()<deadline:
                        tx=state()['transaction']
                        if tx and tx['cancellable']:
                            try:answer=h.post('/api/layers/cancel',dict(transaction_id=tx['id']))
                            except AssertionError as error:cancel_error=str(error)
                            break
                        time.sleep(.005)
                    worker.join(timeout=70);assert not worker.is_alive() and len(replies)==1
                    r['cancellation_attempts'].append(dict(attempt=attempt,load_reply=replies[0],cancel_reply=answer,error=cancel_error))
                    if answer:
                        assert answer['ok'] and replies[0]['status']==400 and state()['guard']==before['guard'] and state()['scene']==before['scene'];same_context(camera,context(phase));cancelled=True;break
                    page.locator('#layers-branches').select_option(seed['saved']['399']['child_id']);click(page,'#layers-branch-load');success(page);set_visible(page,dict(spatial=True,magnetic=True))
                assert cancelled,'No genuine restoration cancellation was observed'
                command('get_artifact');page.wait_for_function('!layerInstrument.snapshot.error')
                for scale in ['1','1.5']:capture(page,'399',scale)
                capture(page,'399','1.5','storage');page.locator('#ui-scale').select_option('1');leave(page,phase,baseline)
            assert h.test.phase(h.get('/api/state')['physics'])==h.test.phase(phase) and not r['page_errors']
            assert sha(ROOT/'user/sessions/latest.json')==r['owner_sha256'] and all(sha(ROOT/p)==seal for p,seal in hashes.items())
            for path in [store.path,*store.branches.glob('*.json'),*store.exports.glob('*.json')]:
                target=folder/'stored-snapshots'/path.relative_to(store.folder);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
                r['stored_archives'].append(dict(path=target.relative_to(ROOT).as_posix(),sha256=sha(target)))
            with zipfile.ZipFile(archive,'a',zipfile.ZIP_DEFLATED) as z:
                for item in r['stored_archives']:z.write(ROOT/item['path'],item['path'])
            r.update(accepted=True,completed=True,archive_sha256=sha(archive))
    except Exception:r['failure']=traceback.format_exc()
    finally:
        try:
            if state()['active'] or state()['recovery_required']:command('leave')
            h.post('/api/command',dict(command='atlas'));h.native('openspace.toggleShutdown();return {closing=true}')
        except Exception:r['cleanup_failure']=traceback.format_exc();r['accepted']=False
        persist()
        if h._socket:h._socket.close()
    print(json.dumps(dict(accepted=r['accepted'],phase=args.phase,checks=len(r['checks']),captures=len(r['captures']),refusals=len(r['refusals']),failure=r.get('failure','').splitlines()[-1:])),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
