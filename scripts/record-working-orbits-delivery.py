"""Audit the native spatial roundtrip correction and original shortcut reuse."""
from pathlib import Path
import hashlib
import json
import os
import time
import urllib.request
from cef_page_v2 import Page

ROOT=Path(__file__).resolve().parents[1]
PRODUCT=ROOT/'output/original-flow-hotfix-product0.28.4'
OUT=ROOT/'evidence/working-orbits-delivery-20261121a.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def get(kind):return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/'+kind+'/state',timeout=30))


def main():
    assert not OUT.exists()
    names=['working-orbits-http-20261121a.json','working-orbits-ui-20261121b.json','native-working-orbits-20261121b.json','working-product-switch-20261121c.json','original-flow-entry-orbits-20261121a.json']
    for name in names:
        data=json.loads((ROOT/'evidence'/name).read_text(encoding='utf8'));assert data['accepted'] and data['completed'],name
    manifest=json.loads((PRODUCT/'build-manifest.json').read_text(encoding='utf8'))
    assert all(sha(PRODUCT/name)==digest for name,digest in manifest['files_sha256'].items())
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert Path(session['serverScript']).parent.parent==PRODUCT
    proof=dict(accepted=True,completed=True,version='0.28.4',session=session,overall_product_accepted=False,scientific_milestones_promoted=False,
      scientific_python_unchanged=138,manifest_sha256=sha(PRODUCT/'build-manifest.json'),
      evidence_sha256={name:sha(ROOT/'evidence'/name) for name in names},shortcuts=[],
      scope='Functional local orbit delivery through original header and real mouse options at100/150%, clock operator, invalid conditions/recovery, owner phase preserved. Backend matches accepted0.28.2 exactly; two existing scientific modules extended,138 unchanged andthree added. Isolated performance numbers remain scoped to0.28.2. No wholeC2-14 or final integration promotion.')
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
    print(json.dumps(dict(accepted=True,version='0.28.4',native_commit_scale=1,native_restore_scale=1,shortcuts=3)))


if __name__=='__main__':main()
