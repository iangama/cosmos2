"""Build an isolated candidate after exact compression-worker acceptance."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/is5-reference-product0.16.0/app'
WORKER=ROOT/'output/is5-compression-worker-staging'
STAGE=ROOT/'output/is5-compression-product-staging'
TARGET=ROOT/'output/is5-compression-product0.17.0'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--worker-receipt',default='evidence/is5-compression-worker-artifact-20261029a.json');args=ap.parse_args()
    receipt=(ROOT/args.worker_receipt).resolve();assert receipt.is_relative_to(ROOT)
    receipts=[receipt,ROOT/'evidence/is5-compression-bridge-20261029a.json',
              ROOT/'evidence/is5-native-reference-20261029b.json',
              ROOT/'evidence/is5-reference-visual-review-20261029b.json',
              ROOT/'evidence/is5-reference-profile-audit-20261029b.json']
    for p in receipts:
        result=json.loads(p.read_text());assert result['accepted'],p
        assert all(sha(ROOT/n)==v for n,v in result.get('source_sha256',{}).items()),p
    worker=json.loads(receipt.read_text());assert worker['completed']
    assert worker['generation']['core']['id']=='is5:thermal-row-closed-baryon-prescribed-density-CNOII-PC-zone'
    manifest=json.loads((BASE.parent/'build-manifest.json').read_text())
    base_files={p.relative_to(BASE).as_posix():sha(p) for p in BASE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert base_files==manifest['files_sha256']
    if TARGET.exists():raise FileExistsError('Preserve compression product')
    staged={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    shutil.copytree(BASE,TARGET/'app',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    app=TARGET/'app'
    for p in WORKER.glob('*.py'):shutil.copy2(p,app/p.name)
    for name in staged:
        destination=app/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(STAGE/name,destination)
    server=app/'server.py';s=server.read_text()
    old="if self.path == '/api/shutdown':";assert s.count(old)==2
    # Only the admission branch bypasses the scene-command mutex.
    s=s.replace(old,"if self.path in ('/api/shutdown','/api/solar-zone/cancel'):",1)
    old="            elif self.path == '/api/particles/command':";assert s.count(old)==1
    s=s.replace(old,"            elif self.path == '/api/solar-zone/cancel':\n                self.json_response(SOLAR_ZONE.cancel(request))\n"+old)
    server.write_text(s)
    files={p.relative_to(app).as_posix():sha(p) for p in app.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),ROOT/'IS-5-COMPRESSAO-PRODUTO-CONTRATO.md',*receipts]}
    sources.update({(STAGE/n).relative_to(ROOT).as_posix():v for n,v in staged.items()})
    result=dict(candidate='0.17.0',promoted=False,accepted=False,files_sha256=files,source_sha256=sources,
                base_files_sha256=base_files,worker_receipt=receipt.relative_to(ROOT).as_posix(),
                scope='Prepared candidate only; bridge/native/visual/profile verification required.')
    (TARGET/'build-manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    assert all(sha(BASE/n)==v for n,v in base_files.items())
    print(json.dumps(dict(prepared=True,accepted=False,candidate=str(TARGET),files=len(files))))


if __name__=='__main__':main()
