"""Build an isolated reference-browser candidate from accepted0.15.0 sources."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/is5-coulomb-zone-product0.15.0/app'
STAGE=ROOT/'output/is5-solar-reference-browser-staging'
TARGET=ROOT/'output/is5-reference-product0.16.0'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    receipts=['evidence/is5-native-coulomb-20261029c.json',
              'evidence/is5-coulomb-visual-review-20261029c.json',
              'evidence/is5-coulomb-zone-profile-audit-20261029c.json',
              'evidence/is5-solar-reference-browser-20261029a.json']
    for name in receipts:
        evidence=json.loads((ROOT/name).read_text(encoding='utf-8'))
        assert evidence['accepted'],name
        assert all(sha(ROOT/n)==v for n,v in evidence.get('source_sha256',{}).items())
        if 'profile' in evidence:
            p=ROOT/evidence['profile'];assert sha(p)==evidence['profile_sha256']
            report=json.loads(p.read_text());assert report['completed'] and not report.get('failure')
            assert all(sha(ROOT/n)==v for n,v in report['source_sha256'].items())
    if TARGET.exists():raise FileExistsError('Preserve reference candidate')
    app=TARGET/'app'
    shutil.copytree(BASE,app,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in ['is5_reference_browser.py','is5_reference_manifest.py']:
        shutil.copy2(STAGE/name,app/name)
    shutil.copytree(STAGE/'references',app/'references')
    for name,original in [('README-B23-original.txt','README-original-0.txt'),
                          ('B23-metadata-original.json','record-10822316.json')]:
        assert sha(STAGE/name)==sha(ROOT/'output/is5-solar-reference-staging'/original)
        shutil.copy2(STAGE/name,app/'references'/name)
    for name in ['stellar-reference.js','stellar-reference.css','stellar-reference-panel.html']:
        shutil.copy2(STAGE/name,app/'ui'/name)
    def edit(path,old,new):
        text=path.read_text(encoding='utf-8');assert text.count(old)==1,(path,old)
        path.write_text(text.replace(old,new),encoding='utf-8')
    server=app/'server.py'
    edit(server,'from navigation import Navigation','from urllib.parse import urlsplit\nfrom is5_reference_browser import Library\nSOLAR_REFERENCES = Library()\nfrom navigation import Navigation')
    edit(server,'    def do_GET(self):','''    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path.startswith('/api/stellar-reference/'):
            try:
                result=SOLAR_REFERENCES.query(parsed.path.removeprefix('/api/stellar-reference/'),parsed.query)
                return self.json_response(result)
            except ValueError as error:
                return self.json_response({'ok':False,'error':str(error)},400)''')
    index=app/'ui/index.html'
    edit(index,'<link rel="stylesheet" href="is5-zone.css">','<link rel="stylesheet" href="is5-zone.css">\n<link rel="stylesheet" href="stellar-reference.css">')
    edit(index,'<button id="open-content">Dados e fontes</button>','<button id="open-content">Dados e fontes</button><button id="open-stellar-reference" aria-controls="stellar-reference-panel" aria-expanded="false">Perfis solares</button>')
    edit(index,'<div id="scene-targets"', (STAGE/'stellar-reference-panel.html').read_text()+'\n<div id="scene-targets"')
    edit(index,'</body></html>','<script src="stellar-reference.js"></script></body></html>')
    files={p.relative_to(app).as_posix():sha(p) for p in app.rglob('*') if p.is_file()}
    manifest=dict(candidate='0.16.0',promoted=False,source_receipts={name:sha(ROOT/name) for name in receipts},
                  recipe_sha256=sha(Path(__file__)),files_sha256=files)
    (TARGET/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(candidate=str(TARGET),files=len(files),promoted=False)))


if __name__=='__main__':main()
