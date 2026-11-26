"""Read and preserve the current product/session before import/restore UI curation."""
from importlib.machinery import SourceFileLoader
from pathlib import Path
import datetime as dt
import hashlib
import json
import shutil
import urllib.request
from cef_page_v2 import Page

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'output/native-reference-import-20261121a'
OUT=ROOT/'evidence/native-reference-import-preflight-20261121a.json'
preservation=SourceFileLoader('reference_preservation',str(ROOT/'scripts/preserve-working-session-for-upgrade.py')).load_module()


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not FOLDER.exists() and not OUT.exists();FOLDER.mkdir()
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    product=Path(session['serverScript']).parent.parent
    assert product==ROOT/'output/original-flow-hotfix-product0.27.5'
    manifest=json.loads((product/'build-manifest.json').read_text(encoding='utf8'))
    assert all(sha(product/name)==digest for name,digest in manifest['files_sha256'].items())
    app=preservation.get('/api/state')
    instruments={kind:preservation.get('/api/'+kind+'/state') for kind in ['spatial','layers','particles','solar-zone']}
    assert all(not value.get('active') and not value.get('busy') and not value.get('recovery_required') for value in instruments.values())
    assert app['mode']=='atlas' and not app.get('physics'), 'Preserve an active experiment separately before changing its UI'
    with Page() as page:
        browser=page.evaluate('({path:location.pathname,zoom:getComputedStyle(document.body).zoom,notice:document.getElementById("notice")?.textContent})')
        assert browser['path']=='/' and browser['zoom']=='1'
    proof=dict(accepted=False,completed=False,session=session,browser=browser,app=app,instruments=instruments,
      captured_utc=dt.datetime.now(dt.timezone.utc).isoformat(),files=[],
      navigation=preservation.native_read('return openspace.navigation.getNavigationState("Root")'),
      manifest_sha256=sha(product/'build-manifest.json'),
      scope='Read-only live-state observation and private local preservation before import/restore curation. No UI actions, scientific promotion or acceptance of import/restore in this preflight.')
    for directory in product.iterdir():
        if not directory.is_dir() or directory.name in {'app','data','execution-logs','__pycache__'}:continue
        for source in sorted(directory.rglob('*')):
            if not source.is_file() or '__pycache__' in source.parts:continue
            relative=source.relative_to(product);destination=FOLDER/'preserved-before'/relative
            digest=sha(source);destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)
            assert sha(source)==sha(destination)==digest
            proof['files'].append(dict(relative=relative.as_posix(),sha256=digest,bytes=source.stat().st_size))
    proof['script_sha256']=sha(Path(__file__));proof.update(accepted=True,completed=True)
    OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(accepted=True,files=len(proof['files']),mode=app['mode'])))


if __name__=='__main__':main()
