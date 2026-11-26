"""Sequential four-force journeys share one frozen four-body source phase."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
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
APP=ROOT/'output/is6-spatial-product0.18.5/app'
sys.path.insert(0,str(APP))
from is6_product_scene import artifact, lua
h=SourceFileLoader('is6_joint_helpers',str(ROOT/'scripts/verify-native-solar-integration.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out=ROOT/'evidence/is6-journey-camera-diagnostic-20261102a.json'
    if out.exists():raise FileExistsError('Preserve diagnostic')
    r=dict(accepted=False,completed=False,scope='Diagnose native camera/flag differences after an Earth particle view; no journey acceptance',source_sha256={str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))})
    def persist():out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    def click(page,selector):
        page.evaluate('(()=>{const e=document.querySelector('+json.dumps(selector)+');for(let p=e.parentElement;p;p=p.parentElement)if(p.tagName==="DETAILS")p.open=true;})()')
        page.wait_for_function('!document.querySelector('+json.dumps(selector)+').disabled',timeout=30000)
        page.locator(selector).click()
    try:
        with Page() as page:
            page.goto(h.BASE+'/');page.wait_for_function('appState&&atlasState&&particleState&&!pending')
            click(page,'#copy-solar');page.wait_for_function('appState.physics?.bodies.length===4&&!pending',timeout=70000)
            phase=h.get('/api/state')['physics'];body=next(b for b in phase['bodies'] if b['reference_id']=='sol:naif:399')
            page.locator('#solar-body').select_option(body['id'])
            page.evaluate('document.getElementById("earth-field-latitude").value="-23.55";document.getElementById("earth-field-longitude").value="-46.63";document.getElementById("earth-field-altitude").value="1"')
            click(page,'#body-field-show');page.wait_for_function('appState.body_field_preview?.reading.body_id==='+json.dumps(body['id'])+'&&!pending',timeout=30000)
            def context():
                names=['LabGrid','LabBarycenter','LabProbe']
                for b in phase['bodies']:names.extend(b[k] for k in ['scene_node','label_node','shape_node','spin_node'] if b.get(k))
                return h.native('local f={};for _,n in ipairs('+lua(names)+') do if openspace.hasSceneGraphNode(n) then local ok,v=pcall(openspace.propertyValue,"Scene."..n..".Renderable.Enabled");if ok and type(v)=="boolean" then f[n]=v end end end;return {camera=openspace.navigation.getNavigationState("Root"),flags=f}')
            r['before']=context();persist()
            click(page,'#particle-create');page.wait_for_function('particleState.active&&!particlePending',timeout=30000)
            click(page,'#particle-leave');page.wait_for_function('!particleState.active&&!particlePending',timeout=30000)
            r['after']=context();r['flags_equal']=r['before']['flags']==r['after']['flags']
            a=r['before']['camera'];b=r['after']['camera']
            r['different_camera_keys']=[k for k in a.keys()|b.keys() if a.get(k)!=b.get(k)]
            r['component_differences']={k:[b[k][i]-a[k][i] for i in range(3)] for k in ['Position','Up']}
            r.update(completed=True,accepted=True);persist()
    except Exception:r['failure']=traceback.format_exc()
    finally:
        try:
            s=h.get('/api/particles/state')
            if s['active']:h.post('/api/particles/command',dict(command='leave'))
            h.post('/api/command',dict(command='atlas'));h.native('openspace.toggleShutdown();return {closing=true}')
        except Exception:r['cleanup_failure']=traceback.format_exc()
        persist()
    print(json.dumps({k:v for k,v in r.items() if k not in ['source_sha256','before','after']},ensure_ascii=False))
    return 0 if r['accepted'] else 1

if __name__=='__main__':raise SystemExit(main())
