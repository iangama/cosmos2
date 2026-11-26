"""Real CEF journey, all sixteen cameras/readings, physical phases and original captures."""
import argparse
import copy
import datetime as dt
import hashlib
from importlib.machinery import SourceFileLoader
import json
import math
from pathlib import Path
import shutil
import time
import traceback
import urllib.error
import urllib.request
import zipfile

import numpy as np
from PIL import Image
from cef_page_v2 import Page

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is6-dynamics16-product0.26.2/app'
h=SourceFileLoader('dynamics16_native_helpers',str(ROOT/'scripts/benchmark-body-points-native.py')).load_module()
oracle=SourceFileLoader('dynamics16_native_oracle',str(ROOT/'scripts/verify-is6-dynamics16-service-v3.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def array(value):
    if isinstance(value,dict):return [value[str(i)] for i in range(1,len(value)+1)]
    return value


def geometry(p):
    code='return {positions={'+','.join('openspace.propertyValue("Scene.'+b['scene_node']+'.Translation.Position")' for b in p['bodies'])+'}}'
    expected=np.array([[math.fsum(row[k]*b['position'][k]*p['physical_scale']['length_unit_m'] for k in range(3)) for row in p['atlas_initial']['j2000_to_render_frame']] for b in p['bodies']])
    deadline=time.monotonic()+5
    while True:
        rows=h.native(code)['positions'];actual=np.array([array(row) for row in array(rows)])
        errors=np.abs(actual-expected)
        budgets=np.maximum(.001,np.array([[8*math.ulp(float(x)) for x in row] for row in expected]))
        if np.all(errors<=budgets):return dict(bodies=len(p['bodies']),time=p['time'],maximum_error_m=float(errors.max()),maximum_budget_m=float(budgets.max()),actual_positions_m=actual.tolist())
        if time.monotonic()>deadline:raise AssertionError(dict(error_m=errors.tolist(),budgets_m=budgets.tolist()))
        time.sleep(.05)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);label=parser.parse_args().label
    assert label and len(label)<=24 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label)
    folder=ROOT/f'output/is6-dynamics16-native-{label}';out=ROOT/f'evidence/is6-dynamics16-native-{label}.json'
    assert not folder.exists() and not out.exists(),'Preserve executed native journey'
    assert json.loads((ROOT/'evidence/is6-dynamics16-native-admission-20261112d.json').read_text())['accepted']
    folder.mkdir()
    files=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [Path(__file__),APP.parent/'build-manifest.json',ROOT/'scripts/verify-is6-dynamics16-service-v3.py',
              ROOT/'scripts/cef_page_v2.py',ROOT/'scripts/benchmark-body-points-native.py',ROOT/'IS-6-DINAMICA16-INTERFACE-CONTRATO.md']
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for name in sources:z.write(ROOT/name,name)
    protected={n:sha(ROOT/n) for n in ['user/sessions/latest.json','Iniciar-Cosmos2.cmd',
        'output/is6-principal-moons-navigation-product0.25.1/build-manifest.json']}
    result=dict(completed=False,functional_accepted=False,started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        source_sha256=sources,source_archive_sha256=sha(folder/'executed-sources.zip'),protected_sha256=protected,
        session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig')),page_errors=[],
        selections=[],geometry=[],captures=[],refusals=[],checks={},
        limits_before_execution=dict(position_component_m='max(0.001,8ULP(component))',acceleration_component_m_s2=1e-10),
        scope='Full native journey at100/150percent. Raw framebuffer images need separate direct inspection; own sealed performance profile remains pending.')
    def persist():out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    def click(page,selector):
        page.wait_for_function('document.querySelector('+json.dumps(selector)+')&&!document.querySelector('+json.dumps(selector)+').disabled',timeout=70000)
        page.locator(selector).click();page.wait_for_function('!pending',timeout=70000)
    def capture(page,name,scale):
        page.evaluate('$("lab-panel").scrollTop=0;$("solar-panel").open=true;$("solar-body").scrollIntoView({block:"start"})')
        time.sleep(.5)
        ui=page.evaluate('({scale:$("ui-scale").value,selected:$("solar-body").value,model:$("dynamics16-model").innerText,reading:$("solar-reading").innerText,width:innerWidth,height:innerHeight,scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth})')
        assert ui['scroll']<=ui['client'] and ui['scale']==scale
        existing=set((ROOT/'user/screenshots').rglob('*.png'));h.native('openspace.takeScreenshot();return {requested=true}')
        deadline=time.monotonic()+20
        while True:
            fresh=set((ROOT/'user/screenshots').rglob('*.png'))-existing
            if fresh:
                assert len(fresh)==1;source=next(iter(fresh))
                try:
                    with Image.open(source) as im:assert im.size==(1920,1080);im.load()
                    break
                except OSError:pass
            if time.monotonic()>deadline:raise TimeoutError('Native original PNG incomplete')
            time.sleep(.1)
        target=folder/(name+'-'+str(int(float(scale)*100))+'.png');shutil.copy2(source,target);assert sha(target)==sha(source)
        result['captures'].append(dict(path=target.relative_to(ROOT).as_posix(),sha256=sha(target),native_original=source.relative_to(ROOT).as_posix(),scale=scale,name=name,ui=ui,method='Unedited OpenSpace framebuffer'))
        persist()
    def frozen():
        p=h.get('/api/state')['physics']
        return {k:copy.deepcopy(p[k]) for k in ['system_id','edit_token','revision','time','bodies','atlas_initial','interventions','dynamics16']}
    def refuse(name,path,payload):
        before=frozen();camera=h.native('return openspace.navigation.getNavigationState()')
        request=urllib.request.Request('http://127.0.0.1:4700'+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(request,timeout=30) as response:status=response.status;answer=json.load(response)
        except urllib.error.HTTPError as error:status=error.code;answer=json.load(error)
        assert status==400 and answer.get('ok') is False,(name,status,answer)
        assert frozen()==before,name
        assert h.native('return openspace.navigation.getNavigationState()')==camera,name
        result['refusals'].append(dict(name=name,error=answer['error'],phase_and_camera_unchanged=True));persist()
    original_id=None;previous_scale='1'
    persist()
    try:
        assert Path(result['session']['serverScript']).resolve()==APP/'server.py'
        assert h.get('/api/state')['mode']=='atlas'
        original=h.get('/api/navigation/state');favorites=h.get('/api/navigation/favorites')['views']
        saved=h.post('/api/navigation/save',dict(name='Jornada16 temporária'))['navigation']['views']
        original_id=next(r['id'] for r in saved if r['id'] not in {f['id'] for f in favorites})
        result['original_navigation']=original;result['original_favorites']=favorites
        with Page() as page:
            page.on('pageerror',lambda error:result['page_errors'].append(error))
            page.wait_for_function('appState?.mode==="atlas"&&atlasState&&!pending&&!atlasPending')
            previous_scale=page.locator('#ui-scale').page.evaluate('$("ui-scale").value')
            click(page,'#copy-sixteen')
            page.wait_for_function('appState?.mode==="experiment"&&appState.physics.bodies.length===16&&!pending',timeout=70000)
            initial=h.get('/api/state')['physics'];assert initial['paused'] and initial['time']==0
            assert initial['atlas_initial']['source']['epoch']['et_tdb_s']==original['et']
            result['geometry'].append(geometry(initial))
            assert initial['scientific_generation']['candidate_extension']['version']=='0.26.1'
            assert page.evaluate('["gravity-harmonics","tides-panel","test-cloud"].every(id=>$(id).hidden)')
            assert page.evaluate('Array.from($("solar-panel").querySelectorAll(":scope > details")).every(e=>e.id==="dynamics16-model-panel"?!e.hidden:e.hidden)')
            for scale in ['1','1.5']:
                page.locator('#ui-scale').select_option(scale)
                page.evaluate('$("solar-panel").open=true;if(document.body.classList.contains("details-open"))$("panel-toggle").click()')
                for body in initial['bodies']:
                    page.locator('#solar-body').select_option(body['id']);click(page,'#solar-view-body')
                    deadline=time.monotonic()+5
                    while h.native('return {anchor=openspace.navigation.getNavigationState().Anchor}')['anchor']!=body['scene_node']:
                        if time.monotonic()>deadline:raise TimeoutError('Selected body camera not confirmed')
                        time.sleep(.05)
                    click(page,'#solar-sample')
                    page.wait_for_function('!pending&&solarReading?.body_id==='+json.dumps(body['id'])+'&&solarReading?.system_id===appState.physics.system_id',timeout=70000)
                    read=page.evaluate('solarReading');assert len(read['sources'])==15
                    assert read['body_id'] not in {s['id'] for s in read['sources']}
                    expected=oracle.independent(initial,body)
                    maximum=max(abs(x-y) for s in read['sources'] for x,y in zip(s['acceleration_m_s2'],expected[s['id']]))
                    assert maximum<=1e-10
                    total=[math.fsum(row[k] for row in expected.values()) for k in range(3)]
                    assert max(abs(x-y) for x,y in zip(read['acceleration_m_s2'],total))<=1e-10
                    assert 'm/s²' in page.locator('#solar-reading').inner_text()
                    result['selections'].append(dict(body=body['reference_id'],scale=scale,camera=body['scene_node'],sources=15,maximum_component_error_m_s2=maximum,reading=read))
                    if body['reference_id'] in ('sol:naif:399','sol:naif:599','sol:naif:606'):capture(page,body['name'].lower(),scale)
                    persist()
            result['checks']['all16_selection_camera_reading_both_scales']=True
            # Save before advancing, then verify exact phase restoration through the UI.
            click(page,'#save');saved=h.get('/api/state')['physics'];saved_phase=frozen()
            assert h.get('/api/state')['checkpoint_available']
            click(page,'#play');page.wait_for_function('appState.physics.time>0&&!appState.physics.paused',timeout=15000)
            time.sleep(.3);click(page,'#play');page.wait_for_function('appState.physics.paused',timeout=15000)
            evolved=h.get('/api/state')['physics'];assert evolved['time']>saved['time']
            result['geometry'].append(geometry(evolved))
            assert evolved['atlas_initial']==saved['atlas_initial'] and evolved['bodies']!=saved['bodies']
            click(page,'#load');loaded=h.get('/api/state')['physics']
            assert loaded['bodies']==saved['bodies'] and loaded['time']==saved['time'] and loaded['revision']==saved['revision']
            assert loaded['dynamics16']==saved['dynamics16'] and loaded['edit_token']!=saved['edit_token']
            result['geometry'].append(geometry(loaded))
            result['checks']['save_live_evolution_pause_exact_restore']=dict(evolved_time=evolved['time'],restored_time=loaded['time'],new_token=True)
            body=loaded['bodies'][-1];valid={**oracle.guard(loaded),'body_id':body['id']}
            for name,payload in [('stale token',dict(command='dynamics16_reading',**oracle.guard(saved),body_id=body['id'])),
                ('boolean revision',dict(command='dynamics16_reading',**{**valid,'revision':True})),
                ('unknown body',dict(command='dynamics16_reading',**{**valid,'body_id':'not-issued'})),
                ('extra source',dict(command='dynamics16_reading',**valid,GM=1)),
                ('outside EM domain',dict(command='earth_field',**valid))]:refuse(name,'/api/command',payload)
            refuse('second copy','/api/dynamics16/experiment',dict(utc=loaded['atlas_initial']['source']['epoch']['utc']))
            refuse('injected copy GM','/api/dynamics16/experiment',dict(utc=loaded['atlas_initial']['source']['epoch']['utc'],GM=1))
            # Explicit SI edit uses existing revision guard and keeps the observed source link.
            page.evaluate('$("body-editor").open=true')
            page.locator('#edit-body').select_option(body['id']);click(page,'#prepare-body-edit')
            page.evaluate('$("edit-mass-kg").value=String(Number($("edit-mass-kg").value)*1.001)')
            click(page,'#apply-body-edit');edited=h.get('/api/state')['physics']
            assert edited['revision']==1 and edited['interventions'][-1]['type']=='set_body_si'
            assert edited['bodies'][-1]['reference_id']==body['reference_id'] and edited['bodies'][-1]['mass']>body['mass']
            assert edited['atlas_initial']==loaded['atlas_initial']
            result['geometry'].append(geometry(edited))
            result['checks']['SI_edit_source_link_and_intervention']=edited['interventions'][-1]
            refuse('stale edit revision','/api/command',dict(command='dynamics16_reading',**valid))
            click(page,'#load');assert h.get('/api/state')['physics']['bodies']==saved['bodies']
            click(page,'#atlas');page.wait_for_function('appState?.mode==="atlas"&&!pending')
            for selector,count in [('#copy-atlas',3),('#copy-solar',4)]:
                click(page,selector);page.wait_for_function('appState?.mode==="experiment"&&appState.physics.bodies.length==='+str(count)+'&&!pending',timeout=70000)
                p=h.get('/api/state')['physics'];assert p['paused'] and p['dynamics16'] is None
                result['geometry'].append(geometry(p));result['checks']['legacy_copy_'+str(count)]=True
                click(page,'#atlas');page.wait_for_function('appState?.mode==="atlas"&&!pending')
            assert not result['page_errors'],result['page_errors']
            result.update(completed=True,functional_accepted=True)
    except Exception:result['failure']=traceback.format_exc()
    finally:
        try:
            if h.get('/api/state')['mode']=='experiment':h.post('/api/command',dict(command='atlas'))
            if original_id:
                restored=h.post('/api/navigation/restore',dict(id=original_id))['navigation']
                h.post('/api/navigation/delete',dict(id=original_id))
                assert h.get('/api/navigation/favorites')['views']==result['original_favorites']
                assert restored['et']==result['original_navigation']['et']
            with Page() as page:
                page.locator('#ui-scale').select_option(previous_scale)
                page.evaluate('selectTarget('+json.dumps(result['original_navigation']['target'])+',true)')
            assert all(sha(ROOT/n)==s for n,s in sources.items())
            assert all(sha(ROOT/n)==s for n,s in protected.items())
            result.update(owner_view_restored=True,protected_unchanged=True,owner_app_kept_open=True)
        except Exception:result['cleanup_failure']=traceback.format_exc();result['functional_accepted']=False
        persist()
    print(json.dumps({k:result.get(k) for k in ['functional_accepted','failure','cleanup_failure']}|dict(selections=len(result['selections']),captures=len(result['captures']))),flush=True)
    return 0 if result['functional_accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
