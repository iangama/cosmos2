"""Actual owner journey for filtered species suggestions and original energy forms."""
from pathlib import Path
import hashlib
import json
import time
import traceback
import urllib.request
from cef_page_v2 import Page
from ordinary_option_input_v2 import OptionInput

ROOT=Path(__file__).resolve().parents[1]
PRODUCT=ROOT/'output/original-flow-hotfix-product0.27.5'
FOLDER=ROOT/'output/editable-options-native-20261120a'
OUT=ROOT/'evidence/editable-options-native-20261120a.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def get():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/state',timeout=30))


def main():
    assert not OUT.exists() and not FOLDER.exists();FOLDER.mkdir()
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert Path(session['serverScript']).parent.parent==PRODUCT
    manifest=json.loads((PRODUCT/'build-manifest.json').read_text(encoding='utf8'))
    assert all(sha(PRODUCT/name)==digest for name,digest in manifest['files_sha256'].items())
    proof=dict(accepted=False,completed=False,checks=[],captures=[],actions=[],session=session,
      manifest_sha256=sha(PRODUCT/'build-manifest.json'),saved_session_sha256=sha(PRODUCT/'gravity-sessions/latest.json'),
      source_sha256={name:sha(ROOT/name) for name in ['scripts/verify-native-editable-options.py','scripts/ordinary_option_input_v2.py','scripts/ordinary_native_input_v8.py','scripts/cef_page_v2.py']},
      scope='Original shortcut/header/nuclear links. Windows mouse, typing and wheel select species, apply the original reaction form, query separation and add/remove a product. DOM/HTTP observe only. No Save/Export, scientific promotion or full product acceptance.')
    def persist():OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    with Page() as page:
        window=OptionInput(session['app'],page)
        def wait(expression):page.wait_for_function(expression,timeout=90000)
        def click(selector,ready=None):
            proof['step']=selector;persist();window.click(selector)
            if ready:wait(ready)
        def capture(name):
            time.sleep(.3);path=FOLDER/(name+'.png');assert not path.exists()
            row=window.capture(path);row['sha256']=sha(path);proof['captures'].append(row);persist()
        def choose_species(selector,prefix,value,capture_name=None):
            proof['step']='type-'+selector;persist();window.fill(selector,prefix)
            wait('!document.querySelector(".c2-suggestions-portal").hidden')
            if capture_name:capture(capture_name)
            click('.c2-suggestions-list [data-suggestion-value='+json.dumps(value)+']')
            wait('document.querySelector('+json.dumps(selector)+').value==='+json.dumps(value)+'&&document.querySelector(".c2-suggestions-portal").hidden')
        def check(name,**values):proof['checks'].append(dict(name=name,**values));proof['actions']=list(window.actions);persist()
        ready='location.pathname==="/"&&appState.mode==="atlas"&&!pending'
        try:
            wait(ready);before=get()
            for scale in ['1','1.5']:
                window.select('#ui-scale',scale)
                window.select('#type-filter','planet');assert page.evaluate('document.querySelectorAll("#destinations [data-target]:not([hidden])").length')==8
                window.select('#type-filter','all')
                click('#forces','location.pathname==="/forces.html"&&typeof response!=="undefined"&&response?.ok&&!pending')
                click('a[href="/nuclei.html"]','location.pathname==="/nuclei.html"&&typeof nuclearCatalog!=="undefined"&&nuclearCatalog')
                click('#nuclear-energy-link','location.pathname==="/nuclear-energy.html"&&typeof energyResult!=="undefined"&&energyResult&&!energyBusy')
                assert page.evaluate('Number(getComputedStyle(document.body).zoom)')==float(scale)
                original=page.evaluate('JSON.stringify(energyResult)');target=page.evaluate('document.getElementById("energy-target").value')
                choose_species('#energy-target','C-1','C-12','species-suggestions-'+scale.replace('.','-'))
                assert page.evaluate('!document.getElementById("energy-draft").hidden')
                assert page.evaluate('JSON.stringify(energyResult)')==original
                choose_species('#energy-target',target,target)
                click('#calculate-energy','!energyBusy&&document.getElementById("energy-draft").hidden')
                assert page.evaluate('Number.isFinite(energyResult.Q.value)')
                check('mouse-species-selection-and-original-reaction-form',scale=scale)
                choose_species('#separation-species','C-1','C-12')
                click('#calculate-separation','!energyBusy&&document.getElementById("separation-title").textContent.includes("C-12")')
                check('selected-species-reaches-separation-model',scale=scale,separation_title=page.evaluate('document.getElementById("separation-title").textContent'))
                count=page.evaluate('document.getElementById("energy-products").children.length')
                click('#add-product')
                wait('document.querySelector("#energy-products>.product-row:last-child input").hasAttribute("data-c2-list")')
                choose_species('#energy-products>.product-row:last-child input','He','He-4')
                assert page.evaluate('document.querySelector("#energy-products>.product-row:last-child").children[1].value')=='1'
                click('#energy-products>.product-row:last-child button')
                assert page.evaluate('document.getElementById("energy-products").children.length')==count
                check('dynamic-product-suggestions-preserve-quantity-and-removal',scale=scale)
                click('a.brand',ready)
                assert get().get('physics')==before.get('physics')
            window.select('#ui-scale','1')
            assert sha(PRODUCT/'gravity-sessions/latest.json')==proof['saved_session_sha256']
            assert all(sha(PRODUCT/name)==digest for name,digest in manifest['files_sha256'].items())
            proof['physical_phase_preserved']=True;proof.update(accepted=True,completed=True)
        except Exception:proof['failure']=traceback.format_exc()
        finally:proof['actions']=list(window.actions);persist()
    print(json.dumps({key:proof.get(key) for key in ['accepted','completed','step','checks','failure']},ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
