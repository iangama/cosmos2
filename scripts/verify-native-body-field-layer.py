"""Actual persistent vector controls, stale guards, display policy and scene cleanup."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import subprocess
import time
import traceback
import zipfile
from importlib.machinery import SourceFileLoader
from websockets.sync.client import connect
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is3-body-vector-product/app'
h=SourceFileLoader('vector_native_helpers',str(ROOT/'scripts/verify-native-solar-tide.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    folder=ROOT/('output/is3-native-body-layer-'+args.label);receipt=ROOT/('evidence/is3-native-body-layer-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve native evidence.')
    launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'));assert launch.get('bodyVectorCandidate')
    folder.mkdir();files=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [Path(__file__).resolve(),ROOT/'scripts/cef_page.py',ROOT/'IS-3-VETOR-NATIVO-CONTRATO.md',ROOT/'scripts/start-is3-body-vector-candidate.ps1']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    baseline=json.loads((ROOT/'evidence/is3-body-vector-candidate-prepared-20261024.json').read_text())
    report={'schema':1,'session':launch,'source_sha256':hashes,'checks':{},'captures':[],
        'completed':False,'accepted':False,'scope':'Native CEF controls and actual API/worker/scene lifecycle for one frozen vector; captured visibility needs review. No field lines, Lorentz, external currents or sustained performance acceptance.'}
    def persist():receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    persist();topic=0
    try:
        with connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.2,ping_interval=None,max_size=4*1024*1024) as ws:
            ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
            def native(code):
                nonlocal topic
                topic+=1;ws.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True}}))
                reply=json.loads(ws.recv(timeout=15));assert reply.get('topic')==topic;return reply['payload']['1']
            def flags(nodes):
                return native('local f={};for _,n in ipairs({'+','.join(json.dumps(n) for n in nodes)+'}) do f[n]=openspace.hasSceneGraphNode(n) end;return {flags=f}')['flags']
            def capture(model,scale):
                native('openspace.cosmos2BeginFrameCapture(240);return {ok=true}')
                until=time.monotonic()+5
                while native('return openspace.cosmos2MemoryMetrics()')['capture_samples']<10:
                    if time.monotonic()>until:raise TimeoutError('No subsequent rendered frames.')
                    time.sleep(.05)
                time.sleep(.3);native('openspace.cosmos2EndFrameCapture();return {ok=true}')
                name='cosmos2-is3-body-layer-'+args.label+'-'+model+'-'+scale+'.png'
                subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',name],check=True,capture_output=True)
                report['captures'].append({'model':model,'scale':scale,'path':'evidence/'+name,'sha256':sha(ROOT/'evidence'/name)})
            with Page() as page:
                page.goto('http://127.0.0.1:4700/');page.wait_for_function('appState?.mode==="atlas"&&atlasState&&!pending')
                atlas=h.get('/api/atlas/state');h.click(page,'#copy-solar')
                page.wait_for_function('appState?.physics?.bodies.length===4&&!pending',timeout=70000)
                first=h.get('/api/state')['physics'];physical=h.physical(first)
                earth=next(b for b in first['bodies'] if b['reference_id']=='sol:naif:399')
                jupiter=next(b for b in first['bodies'] if b['reference_id']=='sol:naif:599')
                if not page.evaluate('document.getElementById("solar-panel").open'):h.click(page,'#solar-panel > summary')
                if not page.evaluate('document.getElementById("body-field-vector-panel").open'):h.click(page,'#body-field-vector-panel > summary')
                old_nodes=[];layers=[]
                for body,model in [(earth,'earth'),(jupiter,'jupiter')]:
                    page.locator('#solar-body').select_option(body['id']);h.click(page,'#body-field-show')
                    page.wait_for_function('appState?.body_field_preview?.reading.body_id==='+json.dumps(body['id'])+'&&!pending')
                    layer=h.get('/api/state')['body_field_preview'];layers.append(layer)
                    assert all(flags(layer['render']['nodes']).values())
                    assert not any(flags(old_nodes).values()) if old_nodes else True
                    assert h.physical(h.get('/api/state')['physics'])==physical
                    state=native('return {enabled=openspace.propertyValue("Scene.'+body['scene_node']+'.Renderable.Enabled"),anchor=openspace.navigation.getNavigationState().Anchor}')
                    assert not state['enabled'] and state['anchor']==layer['render']['frame_node']
                    if old_nodes:assert native('return {enabled=openspace.propertyValue("Scene.'+earth['scene_node']+'.Renderable.Enabled")}')['enabled']
                    for scale in ['1','1.5']:
                        page.locator('#ui-scale').select_option(scale)
                        page.evaluate('document.getElementById("body-field-status").scrollIntoView({block:"center"})')
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                        capture(model,str(int(float(scale)*100)))
                    old_nodes=layer['render']['nodes'];persist()
                page.locator('#ui-scale').select_option('1')
                report['checks']['Earth_Jupiter_UI_replace_native_mask_and_100_150']=True
                layer=layers[-1]
                request={'command':'show_body_field','model':'JRM33',**h.guard(first),'body_id':jupiter['id'],
                    'radius_m':1.5*71492000.,'latitude_deg':0.,'east_longitude_deg':0.,'degree':13}
                for change in [{'edit_token':'stale'},{'expected_time':1},{'body_id':earth['id']},{'degree':30},{'unknown':1}]:
                    assert not h.post('/api/command',{**request,**change},400)['ok']
                    assert h.get('/api/state')['body_field_preview']['render']['id']==layer['render']['id']
                    assert h.physical(h.get('/api/state')['physics'])==physical
                assert not h.post('/api/command',{'command':'clear_body_field','layer_id':'stale'},400)['ok']
                report['checks']['invalid_requests_preserve_layer_and_physics']=True
                # The layer is owned by the renderer session, so CEF reload reattaches it.
                page.goto('http://127.0.0.1:4700/');page.wait_for_function('appState?.body_field_preview&&!pending')
                assert h.get('/api/state')['body_field_preview']['render']['id']==layer['render']['id']
                assert 'Júpiter' in page.locator('#body-field-status').inner_text()
                report['checks']['CEF_reload_reattaches_same_fixed_reading']=True
                page.locator('#solar-body').select_option(jupiter['id'])
                if not page.evaluate('document.getElementById("solar-panel").open'):h.click(page,'#solar-panel > summary')
                if not page.evaluate('document.getElementById("body-field-vector-panel").open'):h.click(page,'#body-field-vector-panel > summary')
                h.click(page,'#body-field-clear');assert h.get('/api/state')['body_field_preview'] is None
                assert not any(flags(layer['render']['nodes']).values())
                assert native('return {enabled=openspace.propertyValue("Scene.'+jupiter['scene_node']+'.Renderable.Enabled")}')['enabled']
                h.click(page,'#body-field-show');layer=h.get('/api/state')['body_field_preview']
                before_position=native('return {p=openspace.propertyValue("Scene.'+layer['render']['frame_node']+'.Translation.Position")}')['p']
                h.click(page,'#play');page.wait_for_function('appState.physics.time>0&&!pending');time.sleep(.2);h.click(page,'#play')
                page.wait_for_function('appState.physics.paused&&!pending')
                assert 'Amostra fixa' in page.locator('#body-field-status').inner_text()
                assert native('return {p=openspace.propertyValue("Scene.'+layer['render']['frame_node']+'.Translation.Position")}')['p']==before_position
                h.click(page,'#save');saved=h.get('/api/state')['physics'];h.click(page,'#load')
                loaded=h.get('/api/state');assert loaded['physics']['bodies']==saved['bodies'] and loaded['body_field_preview'] is None
                assert not any(flags(layer['render']['nodes']).values())
                report['checks']['clear_restores_marker_evolution_keeps_frozen_position_restore_clears']=True
                page.locator('#solar-body').select_option(next(b['id'] for b in loaded['physics']['bodies'] if b['reference_id']=='sol:naif:399'))
                h.click(page,'#body-field-show');layer=h.get('/api/state')['body_field_preview'];h.click(page,'#atlas')
                assert h.get('/api/state')['body_field_preview'] is None and not any(flags(layer['render']['nodes']).values())
                restored=h.get('/api/atlas/state');assert restored['epoch']==atlas['epoch'] and restored['bodies']==atlas['bodies']
                report['checks']['Atlas_cleans_layer_and_preserves_reference']=True
        assert all(sha(ROOT/name)==digest for name,digest in baseline['base_source_sha256'].items())
        assert sha(ROOT/'user/sessions/latest.json')==baseline['owner_pointer_sha256']
        assert all(sha(ROOT/name)==digest for name,digest in hashes.items())
        report['checks']['base_IS3_product_owner_and_executed_sources_preserved']=True
        report['completed']=report['accepted']=True
    except Exception:report['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps({'receipt':receipt.relative_to(ROOT).as_posix(),'accepted':report['accepted'],'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
