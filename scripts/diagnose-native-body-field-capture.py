"""Controlled fixed-scene UI-scale and CEF visibility diagnostic; no product-file edits."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import subprocess
import shutil
from PIL import Image
import sys
import time
import traceback
import zipfile
from importlib.machinery import SourceFileLoader
from websockets.sync.client import connect
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is3-tides-product/app'
STAGING=ROOT/'output/is3-body-vector-staging'
sys.path.insert(0,str(APP));sys.path.insert(0,str(STAGING))
from body_field_scene import prepare
h=SourceFileLoader('native_body_vector_helpers',str(ROOT/'scripts/verify-native-solar-tide.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def normalize(value):
    if isinstance(value,dict):
        if value and set(value)=={str(i) for i in range(1,len(value)+1)}:
            return [normalize(value[str(i)]) for i in range(1,len(value)+1)]
        return {k:normalize(v) for k,v in value.items()}
    if isinstance(value,list):return [normalize(v) for v in value]
    return value


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    folder=ROOT/('output/is3-native-capture-diagnostic-'+args.label);receipt=ROOT/('evidence/is3-native-capture-diagnostic-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve prototype evidence.')
    # Explicit prerequisite: both remaining J profiles accepted before native planet geometry.
    sequence=json.loads((ROOT/'evidence/em-j-diagnostic-profile-sequence-20261023b.json').read_text())
    assert sequence['accepted'] and sequence['completed']
    staged=json.loads((ROOT/'evidence/is3-body-field-geometry-check-20261023a.json').read_text())
    assert staged['accepted']
    launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'));assert launch.get('jupiterFieldCandidate')
    owner=ROOT/'user/sessions/latest.json';owner_sha=sha(owner)
    files=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [STAGING/'body_field_geometry.py',STAGING/'body_field_scene.py',Path(__file__).resolve(),
        ROOT/'scripts/cef_page.py',ROOT/'IS-3-VETOR-NATIVO-CONTRATO.md']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    folder.mkdir()
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    report={'schema':1,'session':launch,'source_sha256':hashes,'runs':[],'captures':[],
        'completed':False,'accepted':False,
        'scope':'Controlled scale/CEF visibility diagnosis; the same Earth reading/geometry/camera is retained for every comparison. Temporary native rendering bench using fresh actual paused-worker readings. Product files unchanged; controls/annotation temporarily driven by harness and cleared afterward. No persistent UI feature, field lines, Lorentz or performance acceptance.'}
    def persist():receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    persist();topic=0;nodes=[];hidden=None
    try:
        with connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.2,ping_interval=None,max_size=4*1024*1024) as ws:
            ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
            def native(code):
                nonlocal topic
                topic+=1;ws.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True}}))
                reply=json.loads(ws.recv(timeout=15));assert reply.get('topic')==topic;return normalize(reply['payload']['1'])
            def clean():
                nonlocal nodes,hidden
                code=''
                if nodes:
                    code='local n=openspace.navigation.getNavigationState("LabRoot");local owned={'+','.join('['+json.dumps(node)+']=true' for node in nodes)+'};if owned[n.Anchor] then local a=openspace.worldPosition(n.Anchor);local r=openspace.worldPosition("LabRoot");openspace.setPropertyValueSingle("Scene.LabCameraAnchor.Translation.Position",{a[1]-r[1],a[2]-r[2],a[3]-r[3]});n.Anchor="LabCameraAnchor";openspace.navigation.setNavigationState(n) end;'
                code+=''.join('if openspace.hasSceneGraphNode('+json.dumps(node)+') then openspace.removeSceneGraphNode('+json.dumps(node)+') end;' for node in reversed(nodes))
                if hidden:
                    for node,enabled in hidden:
                        code+='if openspace.hasSceneGraphNode('+json.dumps(node)+') then openspace.setPropertyValueSingle("Scene.'+node+'.Renderable.Enabled",'+str(enabled).lower()+') end;'
                if code:native(code+'return {cleared=true}')
                nodes=[];hidden=None
            try:
                with Page() as page:
                    page.goto('http://127.0.0.1:4700/');page.wait_for_function('appState&&!pending')
                    if page.evaluate('appState.mode')=='experiment':h.click(page,'#atlas')
                    page.wait_for_function('appState?.mode==="atlas"&&atlasState&&!pending')
                    original_atlas=h.get('/api/atlas/state')
                    h.click(page,'#copy-solar');page.wait_for_function('appState?.physics?.bodies.length===4&&!pending',timeout=70000)
                    first=h.get('/api/state')['physics'];before=h.physical(first)
                    if not page.evaluate('document.getElementById("solar-panel").open'):h.click(page,'#solar-panel > summary')
                    for target,model,panel,button,reading_name in [('399','IGRF14','earth-field-panel','earth-field-sample','earthFieldReading'),
                        ]:
                        body=next(b for b in first['bodies'] if b['reference_id']=='sol:naif:'+target)
                        page.locator('#solar-body').select_option(body['id'])
                        if not page.evaluate('document.getElementById('+json.dumps(panel)+').open'):h.click(page,'#'+panel+' > summary')
                        h.click(page,'#'+button);page.wait_for_function(reading_name+'?.body_id==='+json.dumps(body['id'])+'&&!pending')
                        reading=page.evaluate(reading_name);code,result=prepare(reading);r,g=result['render'],result['geometry']
                        assert h.physical(h.get('/api/state')['physics'])==before
                        nodes=r['nodes']
                        flagcode='return {marker=openspace.propertyValue("Scene.'+body['scene_node']+'.Renderable.Enabled"),label=openspace.propertyValue("Scene.'+body['label_node']+'.Renderable.Enabled")}'
                        flags=native(flagcode);hidden=[(body['scene_node'],flags['marker']),(body['label_node'],flags['label'])]
                        native(code+'openspace.setPropertyValueSingle("Scene.'+body['scene_node']+'.Renderable.Enabled",false);openspace.setPropertyValueSingle("Scene.'+body['label_node']+'.Renderable.Enabled",false);return {ready=true}')
                        vec=lambda value:'{'+','.join(format(v,'.17g') for v in value)+'}'
                        native('openspace.navigation.setNavigationState({Anchor='+json.dumps(r['frame_node'])+',ReferenceFrame="LabRoot",Position='+vec(r['view']['position_render_relative_m'])+',Up='+vec(r['view']['up_render'])+'});return {queued=true}')
                        status=native('local a=openspace.worldPosition('+json.dumps(r['frame_node'])+');local b=openspace.worldPosition('+json.dumps(body['scene_node'])+');local p=openspace.worldPosition('+json.dumps(r['label_node'])+');return {center=openspace.propertyValue("Scene.'+r['frame_node']+'.Translation.Position"),point_local=openspace.propertyValue("Scene.'+r['label_node']+'.Translation.Position"),center_world=a,point_world=p,center_delta={a[1]-b[1],a[2]-b[2],a[3]-b[3]},point_relative={p[1]-a[1],p[2]-a[2],p[3]-a[3]}}')
                        limits=[math.ulp(p)+math.ulp(c)+.001 for p,c in zip(status['point_world'],status['center_world'])]
                        report['pending_confirmation']={'model':model,'status':status,'world_difference_limits_m':limits,'render':r};persist()
                        assert max(abs(x-y) for x,y in zip(status['center'],g['center_render_m']))<=.001
                        assert max(abs(x) for x in status['center_delta'])<=.001
                        assert max(abs(x-y) for x,y in zip(status['point_local'],r['label_position_render_relative_m']))<=.001
                        assert all(abs(x-y)<=limit for x,y,limit in zip(status['point_relative'],r['label_position_render_relative_m'],limits))
                        run={'model':model,'reading':reading,'render':r,'native_confirmation':status,'world_difference_limits_m':limits}
                        for scale in ['1.5']:
                            page.locator('#ui-scale').select_option(scale)
                            page.evaluate('document.getElementById('+json.dumps('earth-field-reading' if target=='399' else 'jupiter-field-reading')+').scrollIntoView({block:"center"})')
                            page.evaluate('document.getElementById("notice").textContent="Prévia: grade de referência em SI · amostra fixa · seta B com comprimento apenas gráfico."')
                            visibility=native('return {visible=openspace.propertyValue("Modules.CefWebGui.Visible")}')['visible']
                            for browser_visible in [True,False,True]:
                                try:
                                    native('openspace.setPropertyValueSingle("Modules.CefWebGui.Visible",'+str(browser_visible).lower()+');return {updated=true}')
                                    checks='local nodes={'+','.join(json.dumps(node) for node in r['nodes'][1:])+'};local flags={};for _,node in ipairs(nodes) do local e=openspace.propertyValue("Scene."..node..".Renderable.Enabled");local ok,o=pcall(openspace.propertyValue,"Scene."..node..".Renderable.Opacity");flags[node]={enabled=e,opacity=ok and o or tostring(o)} end;return {camera=openspace.navigation.getNavigationState("LabRoot"),flags=flags,gui_visible=openspace.propertyValue("Modules.CefWebGui.Visible"),center=openspace.propertyValue("Scene.'+r['frame_node']+'.Translation.Position")}'
                                    state_before=native(checks)
                                    native('openspace.cosmos2BeginFrameCapture(240);return {ok=true}')
                                    deadline=time.monotonic()+5
                                    while native('return openspace.cosmos2MemoryMetrics()')['capture_samples']<10:
                                        if time.monotonic()>deadline:raise TimeoutError('Quadros posteriores não confirmados.')
                                        time.sleep(.05)
                                    time.sleep(.75)
                                    captured=native('local m=openspace.cosmos2MemoryMetrics();openspace.cosmos2EndFrameCapture();return {count=m.capture_samples}')
                                    assert captured['count']>=10,captured
                                    shots=ROOT/'user/screenshots';before_shots=set(shots.rglob('*.png'))
                                    native('openspace.takeScreenshot();return {requested=true}')
                                    until=time.monotonic()+10;new_shots=[]
                                    while time.monotonic()<until:
                                        new_shots=[path for path in shots.rglob('*.png') if path not in before_shots]
                                        try:
                                            for path in new_shots:
                                                with Image.open(path) as check:check.load()
                                            if new_shots:break
                                        except (OSError,ValueError):pass
                                        time.sleep(.1)
                                    else:raise TimeoutError('Screenshot interno ausente/incompleto.')
                                    internal=[]
                                    for number,path in enumerate(new_shots):
                                        copy=ROOT/'evidence'/('cosmos2-is3-capture-diagnostic-'+args.label+'-'+str(len(report['captures'])+1)+'-engine-'+str(number)+'.png')
                                        shutil.copy2(path,copy);internal.append({'original':path.relative_to(ROOT).as_posix(),'path':copy.relative_to(ROOT).as_posix(),'sha256':sha(copy)})
                                    filename='cosmos2-is3-capture-diagnostic-'+args.label+'-'+str(len(report['captures'])+1)+'-'+str(int(float(scale)*100))+'-'+('cef-on' if browser_visible else 'cef-off')+'.png'
                                    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',filename],check=True,capture_output=True)
                                    state_after=native(checks)
                                    report['captures'].append({'model':model,'scale':scale,'CEF_visible':browser_visible,'path':'evidence/'+filename,'sha256':sha(ROOT/'evidence'/filename),'frames_confirmation':captured,'native_before':state_before,'native_after':state_after,'engine_captures':internal});persist()
                                finally:native('openspace.setPropertyValueSingle("Modules.CefWebGui.Visible",'+str(visibility).lower()+');return {restored=true}')
                        report['runs'].append(run);report.pop('pending_confirmation',None);persist()
                        # Move camera to the surviving body before removing its temporary anchor.
                        native('openspace.navigation.setNavigationState({Anchor='+json.dumps(body['scene_node'])+',ReferenceFrame="LabRoot",Position={0,-800000000,240000000},Up={0,0,1}});return {queued=true}')
                        clean()
                    assert h.physical(h.get('/api/state')['physics'])==before
                    page.locator('#ui-scale').select_option('1');h.click(page,'#atlas')
                    page.goto('http://127.0.0.1:4700/');page.wait_for_function('appState?.mode==="atlas"&&!pending')
                    after=h.get('/api/atlas/state');assert after['epoch']==original_atlas['epoch'] and after['bodies']==original_atlas['bodies']
            finally:clean()
        assert all(sha(ROOT/p)==digest for p,digest in hashes.items())
        assert sha(owner)==owner_sha
        report['checks']={'model_readings_phase_unchanged':True,'native_local_centers_and_points_within_1mm_world_difference_within_ULP_bound':True,
            'temporary_nodes_removed_markers_restored_Atlas_preserved':True,'product_files_and_owner_unchanged':True}
        report['completed']=report['accepted']=True
    except Exception:report['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps({'receipt':receipt.relative_to(ROOT).as_posix(),'accepted':report['accepted'],'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
