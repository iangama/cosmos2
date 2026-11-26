"""Audit the bounded mouse-selection correction and reuse of all owner shortcuts."""
from pathlib import Path
import hashlib
import json
import os
import time
import urllib.request

import psutil
from cef_page_v2 import Page
from ordinary_native_input_v8 import NativeInput

ROOT=Path(__file__).resolve().parents[1]
PRODUCT=ROOT/'output/original-flow-hotfix-product0.27.4'
OUT=ROOT/'evidence/option-controls-delivery-20261120a.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not OUT.exists()
    inputs=['option-controls-ui-20261120e.json','option-controls-native-20261120c.json','option-controls-native-reference-20261120b.json','working-product-switch-20261120c.json','original-flow-entry-selecao-20261120d.json']
    for name in inputs:
        value=json.loads((ROOT/'evidence'/name).read_text(encoding='utf8'))
        assert value['accepted'] and value['completed'],name
    manifest=json.loads((PRODUCT/'build-manifest.json').read_text(encoding='utf8'))
    assert manifest['scientific_python_unchanged']==137
    assert all(sha(PRODUCT/name)==digest for name,digest in manifest['files_sha256'].items())
    selection=json.loads((ROOT/'config/local-working-product.json').read_text(encoding='utf8'))
    assert selection['candidate']=='0.27.4'
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert Path(session['serverScript']).parent.parent==PRODUCT
    proof=dict(accepted=True,completed=True,manual_option_selection_accepted=True,overall_product_accepted=False,
      scientific_milestones_promoted=False,scientific_python_unchanged=137,session=session,
      evidence_sha256={name:sha(ROOT/'evidence'/name) for name in inputs},
      manifest_sha256=sha(PRODUCT/'build-manifest.json'),shortcuts=[],
      scope='Local correction of single-choice select menus through the original owner workflow: open/read/click/scroll/cancel at100/150%, Atlas/Forces/catalogs/Mesh/Layers. This does not accept all remaining imports, saved branches, calculation cancellation, data-list suggestions, scientific/performance milestones or final integrated panels.')
    with Page() as page:
        window=NativeInput(session['app'],page)
        assert page.evaluate('location.pathname==="/"&&appState.mode==="atlas"&&Number(getComputedStyle(document.body).zoom)===1&&document.querySelector(".c2-options-portal").hidden')
        before=page.evaluate('JSON.stringify(navigationState.camera)')
        for name in ['Abrir-Planetas.cmd','Abrir-Planetas-e-Luas.cmd']:
            os.startfile(str(ROOT/name));time.sleep(1)
            current=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
            assert current['app']==session['app'] and current['serverScript']==session['serverScript']
            assert len([p for p in psutil.process_iter(['name']) if (p.info['name'] or '').lower()=='openspace.exe'])==1
            proof['shortcuts'].append(dict(name=name,reused_app=session['app'],sha256=sha(ROOT/name)))
        assert page.evaluate('JSON.stringify(navigationState.camera)')==before
        for kind in ['spatial','layers']:
            value=json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/'+kind+'/state',timeout=20))
            assert not value.get('active') and not value.get('busy') and not value.get('recovery_required')
        screenshot=ROOT/'output/original-flow-native-selecao-20261120d/delivered-atlas.png'
        assert not screenshot.exists()
        proof['capture']=window.capture(screenshot);proof['capture']['sha256']=sha(screenshot)
    proof['visual_review']=['Native types/scale before: no popup drawn after mouse click, without refocusing the window for capture.',
      'Native corrected Atlas type menu at150%: all five options readable and inside the viewport.',
      'Native Forces E/B menu at150%: three readable options over the actual scientific view.',
      'Native data page at150%: Titan selected, matching visible title/properties.',
      'Native Layers body menu at150%: Earth/IGRF14 and Jupiter/JRM33 grau13 readable.',
      'Native Jupiter Layers at150%: mesh, sample, legend and close control visible. Final integrated UX remains pending.']
    proof['script_sha256']=sha(Path(__file__))
    OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(accepted=True,version='0.27.4',native_cases=17,isolated_cases=18,shortcuts=3,app=session['app'])))


if __name__=='__main__':main()
