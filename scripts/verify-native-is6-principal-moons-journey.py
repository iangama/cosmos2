"""Complete the native search, smooth travel, return, content and export journey."""
import argparse
import hashlib
from importlib.machinery import SourceFileLoader
import json
import math
from pathlib import Path
import time
import traceback
from cef_page_v2 import Page

ROOT=Path(__file__).resolve().parents[1]
h=SourceFileLoader('planet_journey_helpers',str(ROOT/'scripts/benchmark-body-points-native.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
QUERIES=[('Mercurio','Mercury'),('Venus','Venus'),('Terra','Earth'),('Lua','Moon'),
         ('Marte','Mars'),('Jupiter','Jupiter'),('Saturno','Saturn'),('Urano','Uranus'),('Netuno','Neptune'),('Io','Io'),('Europa','Europa'),('Ganimedes','Ganymede'),('Calisto','Callisto'),('Encelado','Enceladus'),('Tita','Titan')]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True)
    label=parser.parse_args().label
    if not label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label): parser.error('Invalid label')
    path=ROOT/f'evidence/is6-principal-moons-journey-native-{label}.json'
    if path.exists():raise FileExistsError('Preserve journey evidence')
    profile=json.loads((ROOT/'evidence/is6-principal-moons-navigation-profile-20261111a.json').read_text())
    assert profile['completed'] or profile.get('failure') and profile.get('owner_app_kept_open')
    result=dict(completed=False,accepted=False,checks={},errors=[],script_sha256=sha(Path(__file__)),
                source_manifest_sha256=sha(ROOT/'output/is6-principal-moons-navigation-product0.25.1/build-manifest.json'))
    protected={name:sha(ROOT/name) for name in ['user/sessions/latest.json','Iniciar-Cosmos2.cmd']}
    original=None;old_scale='1'
    nav=lambda action,**request:h.post('/api/navigation/'+action,request)['navigation']
    def persist():path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    def click(page,selector):
        page.locator(selector).click();page.wait_for_function('!navigationBusy&&!pending&&!atlasPending',timeout=70000)
    persist()
    try:
        before=h.get('/api/navigation/favorites')['views']
        saved=nav('save',name='Jornada temporária · vista inicial')['views']
        original=next(x['id'] for x in saved if x['id'] not in {r['id'] for r in before})
        with Page() as page:
            page.on('pageerror',result['errors'].append);page.goto('http://127.0.0.1:4700/')
            page.wait_for_function('navigationState&&atlasState&&appState?.mode==="atlas"&&!pending')
            old_scale=page.evaluate('$("ui-scale").value');page.locator('#ui-scale').select_option('1')
            assert not page.evaluate('document.body.inert')
            page.locator('#type-filter').select_option('all')
            page.locator('#nearby-filter').select_option('0')
            result['checks']['search']=[]
            for query,target in QUERIES:
                page.evaluate('$("search").value='+json.dumps(query)+';$("search").dispatchEvent(new Event("input",{bubbles:true}))')
                visible=page.evaluate('[...document.querySelectorAll("#destinations [data-target]")].filter(e=>!e.hidden).map(e=>e.dataset.target)')
                assert target in visible,(query,visible)
                click(page,'#destinations [data-target="'+target+'"]')
                assert page.evaluate('selectedTarget')==target
                result['checks']['search'].append(dict(query=query,target=target,visible=visible))
            page.evaluate('$("search").value="";$("search").dispatchEvent(new Event("input",{bubbles:true}))')
            page.evaluate('$("system-tree").open=true')
            for target in ['Io','Europa','Ganymede','Callisto','Enceladus','Titan']:
                click(page,'[data-tree-target="'+target+'"]')
                assert page.evaluate('selectedTarget')==target
            page.locator('#type-filter').select_option('moon')
            visible=page.evaluate('[...document.querySelectorAll("#destinations [data-target]")].filter(e=>!e.hidden).map(e=>e.dataset.target)')
            assert set(visible)=={'Moon','Io','Europa','Ganymede','Callisto','Enceladus','Titan'}
            page.locator('#type-filter').select_option('all')
            result['checks']['tree_and_seven_moon_filter']=True
            click(page,'#destinations [data-target="Io"]')
            page.locator('#smooth-flight').set_checked(True)
            initial=h.get('/api/navigation/state')
            click(page,'#visit-target')
            started=h.get('/api/navigation/state')
            assert started['flying'],started
            page.wait_for_function('!navigationState.flying&&navigationState.navigation.Anchor==="Io"',timeout=20000)
            arrived=h.get('/api/navigation/state');assert arrived['target']=='Io' and not arrived['flying']
            click(page,'#return-view')
            returned=h.get('/api/navigation/state')
            assert returned['et']==initial['et'] and returned['navigation']['Anchor']==initial['navigation']['Anchor']
            a,b=returned['navigation']['Position'],initial['navigation']['Position']
            assert max(abs(x-y) for x,y in zip(a,b))<=max(.01,math.sqrt(sum(x*x for x in b))*1e-12)
            result['checks']['smooth_and_return']=dict(started=started,arrived=arrived,returned=returned)
            click(page,'#destinations [data-target="Titan"]');click(page,'#visit-target')
            page.wait_for_function('!navigationBusy&&navigationState.flying')
            click(page,'#cancel-flight')
            assert not h.get('/api/navigation/state')['flying']
            page.locator('#smooth-flight').set_checked(False);click(page,'#visit-target')
            page.wait_for_function('navigationState.navigation.Anchor==="Titan"')
            result['checks']['cancel_and_direct_arrival']=True
            click(page,'#export-atlas')
            page.wait_for_function('$("notice").textContent.startsWith("Estado e fontes salvos: ")&&!$("export-atlas").disabled')
            exported=Path(page.locator('#notice').inner_text().split('Estado e fontes salvos: ',1)[1])
            data=json.loads(exported.read_text(encoding='utf8'));atlas=data['atlas']
            assert len(atlas['bodies'])==16 and len(atlas['renderer']['positions'])==16
            assert {b['naif_id'] for b in atlas['bodies']}=={'10','199','299','399','301','499','599','699','799','899','501','502','503','504','602','606'}
            result['checks']['export']=dict(path=exported.as_posix(),sha256=sha(exported),body_count=16)
            page.locator('#open-content').click()
            page.wait_for_function('location.pathname==="/content.html"')
            assert page.evaluate('new URLSearchParams(location.search).get("body")')=='606'
            page.wait_for_function('document.body.innerText.includes("Titã")')
            page.wait_for_function('document.getElementById("reference-title").textContent.includes("sol:naif:606")')
            assert page.locator('.property-card').count()==7
            result['checks']['selected_body_content_link']=dict(url=page.evaluate('location.href'))
            assert not result['errors'],result['errors']
        result.update(completed=True,accepted=True)
    except Exception:result['failure']=traceback.format_exc()
    finally:
        try:
            if original:
                restored=nav('restore',id=original);nav('delete',id=original)
            with Page() as page:
                page.goto('http://127.0.0.1:4700/');page.wait_for_function('navigationState&&atlasState')
                page.locator('#ui-scale').select_option(old_scale)
                if original:page.evaluate('selectTarget('+json.dumps(restored['target'])+',true)')
            result['protected_unchanged']={name:sha(ROOT/name)==seal for name,seal in protected.items()}
            assert all(result['protected_unchanged'].values())
            result['app_kept_open']=h.get('/api/state')['mode']=='atlas'
        except Exception:result['cleanup_failure']=traceback.format_exc();result['accepted']=False
        persist()
    print(json.dumps(dict(accepted=result['accepted'],failure=result.get('failure'),cleanup_failure=result.get('cleanup_failure'))))
    return 0 if result['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
