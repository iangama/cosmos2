"""Record CEF coordinates and actual hit targets at150percent; preserve the owner view."""
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path
import traceback
from cef_page_v2 import Page

ROOT=Path(__file__).resolve().parents[1]
h=SourceFileLoader('dynamics16_hit_helpers',str(ROOT/'scripts/benchmark-body-points-native.py')).load_module()
out=ROOT/'evidence/is6-dynamics16-ui150-diagnostic-20261112b.json';assert not out.exists()
r=dict(completed=False);view_id=None
try:
    assert h.get('/api/state')['mode']=='atlas'
    before=h.get('/api/navigation/favorites')['views']
    saved=h.post('/api/navigation/save',dict(name='Diagnóstico150 temporário'))['navigation']['views']
    view_id=next(x['id'] for x in saved if x['id'] not in {b['id'] for b in before})
    h.post('/api/command',dict(command='enter'))
    with Page() as page:
        page.wait_for_function('appState?.mode==="experiment"&&!pending')
        r['previous_scale']=page.evaluate('$("ui-scale").value')
        page.locator('#ui-scale').select_option('1.5')
        page.evaluate('if(document.body.classList.contains("details-open"))$("panel-toggle").click()')
        page.evaluate('$("solar-panel").open=true;$("solar-body").value=appState.physics.bodies[0].id;$("solar-body").dispatchEvent(new Event("change",{bubbles:true}));$("solar-view-body").scrollIntoView({block:"center"})')
        r['coordinates']=page.evaluate('(() => {const e=$("solar-view-body"),r=e.getBoundingClientRect(),z=Number(getComputedStyle(document.body).zoom)||1;const x=r.x+r.width/2,y=r.y+r.height/2;return {x,y,z,viewport:[innerWidth,innerHeight],screen:[screen.width,screen.height],dpr:devicePixelRatio,atRect:document.elementFromPoint(x,y)?.id,atTimesZoom:document.elementFromPoint(x*z,y*z)?.id,rect:{x:r.x,y:r.y,width:r.width,height:r.height}}})()')
        r['camera_before']=h.native('return openspace.navigation.getNavigationState()')
        page.locator('#solar-view-body').click()
        r['camera_after_v2_click']=h.native('return openspace.navigation.getNavigationState()')
        point=r['coordinates']
        for kind in ['mousePressed','mouseReleased']:
            page.call('Input.dispatchMouseEvent',dict(type=kind,x=point['x'],y=point['y'],button='left',clickCount=1))
        page.wait_for_function('$("notice").textContent.includes("Corpo selecionado")',timeout=5000)
        r['camera_after_rect_click']=h.native('return openspace.navigation.getNavigationState()')
        r['expected_anchor']=h.get('/api/state')['physics']['bodies'][0]['scene_node']
        r['completed']=True
except Exception:r['failure']=traceback.format_exc()
finally:
    try:
        if h.get('/api/state')['mode']=='experiment':h.post('/api/command',dict(command='atlas'))
        if view_id:h.post('/api/navigation/restore',dict(id=view_id));h.post('/api/navigation/delete',dict(id=view_id))
        with Page() as page:page.locator('#ui-scale').select_option(r.get('previous_scale','1'))
    except Exception:r['cleanup_failure']=traceback.format_exc()
    out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(r,ensure_ascii=False),flush=True)
