"""Record repeat body-focus camera state at both interface scales, without product edits."""
from pathlib import Path
import hashlib
import json
import subprocess
import time
from importlib.machinery import SourceFileLoader
from websockets.sync.client import connect
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
h=SourceFileLoader('repeat_view_helpers',str(ROOT/'scripts/verify-native-solar-tide.py')).load_module()
destination=ROOT/'evidence/is3-repeat-view-diagnostic-20261023a.json'
if destination.exists():raise FileExistsError('Preserve diagnostic.')
report={'scope':'Camera/UI-scale diagnostic only; no product mutation or final visual acceptance.','runs':[]}
with connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.2,ping_interval=None) as ws:
    ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}));topic=0
    def native(code):
        global topic
        topic+=1;ws.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True}}))
        reply=json.loads(ws.recv(timeout=15));assert reply.get('topic')==topic;return reply['payload']['1']
    with Page() as p:
        p.goto('http://127.0.0.1:4700/');p.wait_for_function('appState?.mode==="atlas"&&atlasState&&!pending')
        h.click(p,'#experiment');p.wait_for_function('appState?.physics?.atlas_initial&&!pending')
        state=h.get('/api/state')['physics'];before=h.physical(state)
        jupiter=next(b for b in state['bodies'] if b['reference_id']=='sol:naif:599')
        if not p.evaluate('document.getElementById("solar-panel").open'):h.click(p,'#solar-panel > summary')
        p.locator('#solar-body').select_option(jupiter['id'])
        query='return {navigation=openspace.navigation.getNavigationState("LabRoot"),size=openspace.propertyValue("Scene.'+jupiter['scene_node']+'.Renderable.Size"),enabled=openspace.propertyValue("Scene.'+jupiter['scene_node']+'.Renderable.Enabled"),position=openspace.propertyValue("Scene.'+jupiter['scene_node']+'.Translation.Position")}';
        for i,scale in enumerate(['1','1.5','1','1.5']):
            p.locator('#ui-scale').select_option(scale)
            p.evaluate('document.getElementById("solar-view-body").scrollIntoView({block:"center"})')
            hit=p.evaluate('(() => {const e=document.getElementById("solar-view-body"),r=e.getBoundingClientRect(),z=Number(getComputedStyle(document.body).zoom)||1;return {rect:{x:r.x,y:r.y,width:r.width,height:r.height},zoom:z,atCSS:document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.id,atScaled:document.elementFromPoint((r.x+r.width/2)*z,(r.y+r.height/2)*z)?.id};})()')
            h.click(p,'#solar-view-body');immediate=native(query);time.sleep(.75);settled=native(query)
            p.evaluate('document.getElementById("jupiter-field-reading").scrollIntoView({block:"center"})')
            name='cosmos2-is3-repeat-view-20261023a-'+str(i+1)+'.png'
            subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',name],check=True,capture_output=True)
            report['runs'].append({'scale':scale,'hit':hit,'immediate':immediate,'settled':settled,'capture':'evidence/'+name})
            destination.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        p.locator('#ui-scale').select_option('1');h.click(p,'#atlas')
        assert h.physical(h.get('/api/state')['physics'])==before
        report['phase_preserved']=True
report['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
destination.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
