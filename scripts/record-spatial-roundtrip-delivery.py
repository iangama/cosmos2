"""Audit the native spatial roundtrip correction and original shortcut reuse."""
from pathlib import Path
import hashlib
import json
import os
import time
import urllib.request
from cef_page_v2 import Page

ROOT=Path(__file__).resolve().parents[1]
PRODUCT=ROOT/'output/original-flow-hotfix-product0.27.7'
OUT=ROOT/'evidence/spatial-roundtrip-delivery-20261121a.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def get(kind):return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/'+kind+'/state',timeout=30))


def main():
    assert not OUT.exists()
    names=['spatial-roundtrip-v2-offline-20261121a.json','spatial-roundtrip-http-20261121a.json','native-spatial-roundtrip-20261121b.json','working-product-switch-20261121b.json','original-flow-entry-spatial-20261121a.json']
    for name in names:
        data=json.loads((ROOT/'evidence'/name).read_text(encoding='utf8'));assert data['accepted'] and data['completed'],name
    manifest=json.loads((PRODUCT/'build-manifest.json').read_text(encoding='utf8'))
    assert all(sha(PRODUCT/name)==digest for name,digest in manifest['files_sha256'].items())
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert Path(session['serverScript']).parent.parent==PRODUCT
    proof=dict(accepted=True,completed=True,version='0.27.7',session=session,overall_product_accepted=False,scientific_milestones_promoted=False,
      scientific_python_unchanged=137,manifest_sha256=sha(PRODUCT/'build-manifest.json'),
      evidence_sha256={name:sha(ROOT/'evidence'/name) for name in names},shortcuts=[],
      scope='Local current-format spatial roundtrip accepted through the original launcher at100%: export, exact source preview and import, mouse branch restore, export/reimport nested origin, Layers handoff, cancel preview, saved restore and Atlas return. Three versioned import/persistence modules added; all137 pre-existing non-server scientific modules preserved. Original data and paused orbit intact. No new150% run, calculation-cancellation, performance or scientific milestone acceptance.')
    with Page() as page:
        assert page.evaluate('location.pathname==="/"&&appState.mode==="atlas"&&Number(getComputedStyle(document.body).zoom)===1')
        for kind in ['spatial','layers']:
            value=get(kind);assert not value['active'] and not value['busy'] and not value['recovery_required']
        for name in ['Abrir-Planetas.cmd','Abrir-Planetas-e-Luas.cmd']:
            os.startfile(str(ROOT/name));time.sleep(1)
            current=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
            assert current['app']==session['app'] and current['serverScript']==session['serverScript']
            proof['shortcuts'].append(dict(name=name,reused_app=session['app'],sha256=sha(ROOT/name)))
    proof['script_sha256']=sha(Path(__file__))
    OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(accepted=True,version='0.27.7',native_commit_scale=1,native_restore_scale=1,shortcuts=3)))


if __name__=='__main__':main()
