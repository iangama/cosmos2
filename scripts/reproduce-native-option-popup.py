"""Open the existing option controls by mouse without refocusing before captures."""
from pathlib import Path
import hashlib
import json
import time
from cef_page_v2 import Page
from ordinary_native_input_v6 import NativeInput

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'output/option-popup-before-20261120a'
OUT = ROOT / 'evidence/option-popup-before-20261120a.json'


def main():
    assert not FOLDER.exists() and not OUT.exists()
    FOLDER.mkdir()
    session = json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    product = Path(session['serverScript']).parent.parent
    proof = dict(session=session, captures=[], actions=[], native_selection_accepted=False,
                 manifest_sha256=hashlib.sha256((product/'build-manifest.json').read_bytes()).hexdigest(),
                 scope='Original shortcut opened the app. Genuine Windows mouse opens native selects; client-area captures do not refocus/restore the window. Read-only DOM and native source inspection are supplementary. Visual review determines the popup defect.')
    with Page() as page:
        window = NativeInput(session['app'], page)
        assert page.evaluate('location.pathname==="/"')
        for selector,name in [('#type-filter','types'),('#ui-scale','scale')]:
            window.key(27)
            window.click(selector)
            time.sleep(.6)
            path=FOLDER/(name+'.png')
            row=window.capture(path)
            row.update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),selector=selector)
            proof['captures'].append(row)
            window.key(27)
        proof['actions']=window.actions
    proof['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(captures=len(proof['captures']),session=session['app'])))


if __name__=='__main__':
    main()
