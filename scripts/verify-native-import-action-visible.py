"""Verify that normal Tab/scroll exposes the complete150% import action without importing twice."""
from pathlib import Path
import hashlib
import json
import time
import urllib.request
from cef_page_v2 import Page
from ordinary_option_input_v3 import OptionInput

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/native-import-action-visible-20261121a.json'
FOLDER=ROOT/'output/native-reference-import-20261121a'


def get():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/layers/state',timeout=30))


def main():
    assert not OUT.exists()
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    with Page() as page:
        window=OptionInput(session['app'],page)
        ids={row['id'] for row in get()['branches']}
        window.select('#ui-scale','1.5');window.click('#open-layers')
        assert page.evaluate('document.getElementById("layers-import-file").files.length')==1
        window.click('#layers-import-preview')
        page.wait_for_function('!layerInstrument.pending&&!layerInstrument.readingFile&&layerInstrument.snapshot.import_preview?.valid')
        window.fill('#layers-import-name','Acao de importacao conferida em150')
        window.key(9)
        page.wait_for_function('document.activeElement===document.getElementById("layers-import-commit")')
        observed=page.evaluate('(()=>{const e=document.getElementById("layers-import-commit"),r=e.getBoundingClientRect(),p=document.getElementById("layers-panel").getBoundingClientRect();return {text:e.textContent,enabled:!e.disabled,full_button_inside_panel:r.top>=p.top&&r.bottom<=p.bottom,focused:document.activeElement===e}})()')
        assert observed['enabled'] and observed['full_button_inside_panel'] and observed['focused']
        time.sleep(.3);path=FOLDER/'layers-import-button-150-fully-visible.png';assert not path.exists()
        capture=window.capture(path);capture['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        window.click('#layers-import-cancel');page.wait_for_function('!layerInstrument.pending&&!layerInstrument.snapshot.import_preview')
        window.click('#layers-panel-close');window.select('#ui-scale','1')
        assert {row['id'] for row in get()['branches']}==ids
        proof=dict(accepted=True,completed=True,session=session,observed=observed,capture=capture,actions=window.actions,
          script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          scope='Supplementary native150% visual/keyboard check: Tab from the name field scrolls the complete enabled Import button into view. Preview cancelled, no duplicate branch created. Does not claim import commit at150%; actual commit was tested separately at100%.')
        OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        print(json.dumps(dict(accepted=True,observed=observed),ensure_ascii=False))


if __name__=='__main__':main()
