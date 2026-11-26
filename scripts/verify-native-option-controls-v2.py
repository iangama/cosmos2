"""Manual option journeys with genuine Windows clicks, including popup scrolling."""
from pathlib import Path
import hashlib
import json
import time
import traceback
import urllib.request

from cef_page_v2 import Page
from ordinary_native_input_v7 import NativeInput

ROOT=Path(__file__).resolve().parents[1]
PRODUCT=ROOT/'output/original-flow-hotfix-product0.27.3'
FOLDER=ROOT/'output/option-controls-native-20261120b'
OUT=ROOT/'evidence/option-controls-native-20261120b.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get(route):
    return json.load(urllib.request.urlopen('http://127.0.0.1:4700'+route,timeout=20))


def main():
    assert not FOLDER.exists() and not OUT.exists()
    FOLDER.mkdir()
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert Path(session['serverScript']).parent.parent==PRODUCT
    entry=json.loads((ROOT/'evidence/original-flow-entry-selecao-20261120c.json').read_text(encoding='utf8'))
    assert entry['accepted'] and entry['session']['app']==session['app']
    manifest=json.loads((PRODUCT/'build-manifest.json').read_text(encoding='utf8'))
    assert all(sha(PRODUCT/name)==digest for name,digest in manifest['files_sha256'].items())
    proof=dict(accepted=False,completed=False,session=session,checks=[],captures=[],actions=[],
      source_sha256={str((PRODUCT/name).relative_to(ROOT)).replace('\\','/'):digest for name,digest in manifest['files_sha256'].items()},
      scope='Original owner shortcut/header/link journeys. All selections open and click actual visible option rows with Windows mouse; long lists use Windows wheel. Keyboard only tests cancellation. CDP and HTTP observe; no injected values/clicks, API commands or direct URL navigation. This bounded receipt does not accept every product workflow or scientific milestone.')
    for name in ['scripts/verify-native-option-controls-v2.py','scripts/ordinary_native_input_v7.py','scripts/cef_page_v2.py','config/local-working-product.json','Iniciar-Cosmos2.cmd']:
        proof['source_sha256'][name]=sha(ROOT/name)
    def persist():
        OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    persist()
    with Page() as page:
        window=NativeInput(session['app'],page)
        def wait(expression):page.wait_for_function(expression,timeout=90000)
        def click(selector,ready=None):
            proof['step']=selector;persist()
            wait('(()=>{const e=document.querySelector('+json.dumps(selector)+');return e&&!e.matches(":disabled")&&e.getAttribute("aria-disabled")!=="true";})()')
            window.click(selector)
            if ready:wait(ready)
        def capture(name):
            time.sleep(.25)
            path=FOLDER/(name+'.png')
            assert not path.exists()
            row=window.capture(path);row['sha256']=sha(path)
            proof['captures'].append(row);persist()
        def check(name,**values):
            proof['checks'].append(dict(name=name,**values));proof['actions']=list(window.actions);persist()
        def trigger(source):
            return '#'+page.evaluate('document.querySelector('+json.dumps(source)+').parentElement.querySelector(".c2-choice-trigger").id')
        def open_menu(source,capture_name=None):
            selector=trigger(source)
            if not page.evaluate('document.querySelector('+json.dumps(selector)+').getAttribute("aria-expanded")==="true"'):
                window.key(27)
                click(selector,'!document.querySelector(".c2-options-portal").hidden')
            assert page.evaluate('document.querySelector(".c2-options-list").getBoundingClientRect().height>20')
            if capture_name:capture(capture_name)
        def choose(source,value,capture_name=None):
            open_menu(source,capture_name)
            click('[role=option][data-choice-value='+json.dumps(value)+'][aria-disabled="false"]')
            wait('document.querySelector('+json.dumps(source)+').value==='+json.dumps(value)+'&&document.querySelector(".c2-options-portal").hidden')
        main_ready='location.pathname==="/"&&appState&&atlasState&&!pending&&spatialInstrument.online&&layerInstrument.online'
        try:
            wait(main_ready)
            original=get('/api/state');assert original['mode']=='atlas' and not original.get('physics')
            window.key(27)
            for scale in ['1','1.5']:
                choose('#ui-scale',scale,'scale-menu-'+scale.replace('.','-'))
                wait('Number(getComputedStyle(document.body).zoom)==='+scale)
                choose('#type-filter','planet','type-menu-'+scale.replace('.','-'))
                assert page.evaluate('[...document.querySelectorAll("#destinations [data-target]:not([hidden])")].every(e=>e.dataset.kind==="planet")')
                assert page.evaluate('document.querySelectorAll("#destinations [data-target]:not([hidden])").length')==8
                choose('#type-filter','moon')
                assert page.evaluate('document.querySelectorAll("#destinations [data-target]:not([hidden])").length')==7
                choose('#type-filter','all')
                choose('#distance-sort','nearest');choose('#distance-sort','system')
                choose('#nearby-filter','1e9');choose('#nearby-filter','0')
                check('atlas-filter-options-click-and-update-results',scale=scale,planets=8,moons=7)
                open_menu('#type-filter')
                before=page.evaluate('document.getElementById("type-filter").value')
                window.key(40);window.key(27)
                assert page.evaluate('document.getElementById("type-filter").value')==before
                assert page.evaluate('document.querySelector(".c2-options-portal").hidden')
                check('escape-cancels-without-changing-atlas-filter',scale=scale)
                click('#forces','location.pathname==="/forces.html"&&typeof response!=="undefined"&&response?.ok&&!pending')
                assert page.evaluate('Number(getComputedStyle(document.body).zoom)')==float(scale)
                click('[data-scenario="electromagnetic"]','!pending&&config.scenario==="electromagnetic"')
                choose('#em-field','both','forces-field-menu-'+scale.replace('.','-'))
                assert page.evaluate('document.getElementById("em-field-choice").textContent.includes("Elétrico e magnético")')
                choose('#em-field','magnetic')
                click('[data-scenario="decays"]','!pending&&config.scenario==="decays"')
                choose('#parameters select[name="parent_case"]','sr90','forces-parameter-menu-'+scale.replace('.','-'))
                assert page.evaluate('!document.querySelector("[data-parameter=initial_daughter_fraction]").hidden')
                wait('!pending&&config.parameters.parent_case==="sr90"&&response.configuration.parameters.parent_case==="sr90"')
                assert page.evaluate('!Object.hasOwn(config.parameters,"")')
                choose('#chart-axis','log');choose('#chart-axis','linear')
                capture('forces-selected-result-'+scale.replace('.','-'))
                check('forces-view-and-dynamic-parameter-options-by-mouse',scale=scale,scenario='decays',parent_case='sr90')
                click('a.back',main_ready)
                click('#open-content','location.pathname==="/content.html"&&typeof contentAtlas!=="undefined"&&contentAtlas')
                choose('#reference-body','606','content-body-menu-'+scale.replace('.','-'))
                wait('document.getElementById("reference-title").textContent.includes("Titã")')
                capture('content-last-body-'+scale.replace('.','-'))
                check('long-body-menu-scroll-and-select-titan',atlas_scale=scale,actual_page_zoom=page.evaluate('Number(getComputedStyle(document.body).zoom)||1'))
                click('#planet-catalog-link','location.pathname==="/planet-catalog.html"&&!document.getElementById("catalog-body").disabled')
                choose('#catalog-body','502','planet-catalog-menu-'+scale.replace('.','-'))
                wait('document.getElementById("catalog-body").value==="502"&&document.getElementById("catalog-title").textContent.includes("Europa")')
                capture('planet-catalog-selected-'+scale.replace('.','-'))
                check('planet-catalog-options-by-mouse',atlas_scale=scale,actual_page_zoom=page.evaluate('Number(getComputedStyle(document.body).zoom)||1'))
                click('a.back','location.pathname==="/content.html"&&typeof contentAtlas!=="undefined"&&contentAtlas')
                click('a.back',main_ready)
                assert get('/api/state').get('physics')==original.get('physics')
            choose('#ui-scale','1')
            assert get('/api/state')['mode']=='atlas'
            proof['physical_phase_preserved']=get('/api/state').get('physics')==original.get('physics')
            assert proof['physical_phase_preserved']
            assert all(sha(PRODUCT/name)==digest for name,digest in manifest['files_sha256'].items())
            proof.update(accepted=True,completed=True)
        except Exception:
            proof['failure']=traceback.format_exc()
        finally:
            proof['actions']=list(window.actions);persist()
    print(json.dumps({key:proof.get(key) for key in ['accepted','completed','step','checks','failure']},ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
