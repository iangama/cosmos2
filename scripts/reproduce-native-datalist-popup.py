"""Inspect the remaining editable species suggestions through the real nuclear pages."""
from pathlib import Path
import hashlib
import json
import time
import urllib.request
from cef_page_v2 import Page
from ordinary_native_input_v8 import NativeInput

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'output/datalist-popup-before-20261120a'
OUT=ROOT/'evidence/datalist-popup-before-20261120a.json'


def main():
    assert not FOLDER.exists() and not OUT.exists();FOLDER.mkdir()
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    proof=dict(completed=False,native_suggestions_accepted=False,session=session,
      scope='Ordinary header/link navigation, mouse focus and Windows typing into the real species field. No Apply/Save/Export. Capture without refocusing; DOM/API only read. Visual review determines whether the native data-list suggestions are drawn.')
    with Page() as page:
        window=NativeInput(session['app'],page)
        page.wait_for_function('location.pathname==="/"&&appState.mode==="atlas"&&!pending')
        before=json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/state',timeout=20))
        window.click('#forces');page.wait_for_function('location.pathname==="/forces.html"&&typeof response!=="undefined"&&response?.ok&&!pending',timeout=90000)
        window.click('a[href="/nuclei.html"]');page.wait_for_function('location.pathname==="/nuclei.html"&&typeof nuclearCatalog!=="undefined"&&nuclearCatalog',timeout=90000)
        window.click('#nuclear-energy-link');page.wait_for_function('location.pathname==="/nuclear-energy.html"&&typeof energyResult!=="undefined"&&energyResult&&!energyBusy',timeout=90000)
        original=page.evaluate('JSON.stringify(energyResult)')
        window.fill('#energy-target','C-1');time.sleep(.6)
        proof['field']=page.evaluate('({value:document.getElementById("energy-target").value,options:document.getElementById("energy-target").list.options.length,matching:[...document.getElementById("energy-target").list.options].filter(o=>o.value.startsWith("C-1")).map(o=>o.value)})')
        path=FOLDER/'species-suggestions.png';proof['capture']=window.capture(path)
        proof['capture']['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        assert page.evaluate('JSON.stringify(energyResult)')==original
        window.key(27);window.click('a.brand')
        page.wait_for_function('location.pathname==="/"&&appState.mode==="atlas"&&!pending')
        after=json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/state',timeout=20))
        proof['physical_phase_preserved']=before.get('physics')==after.get('physics')
        assert proof['physical_phase_preserved']
        proof['actions']=window.actions;proof['completed']=True
    proof['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(completed=True,field=proof['field']),ensure_ascii=False))


if __name__=='__main__':main()
