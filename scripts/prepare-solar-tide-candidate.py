"""Fork the audited IS-1/2 product for passive tide API/UI integration."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/is12-solar-product'
DEST=ROOT/'output/is3-tides-product'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    receipt=ROOT/'evidence/is3-tides-candidate-prepared-20261023.json'
    if DEST.exists() or receipt.exists():raise FileExistsError('Preserve candidate and receipt.')
    audit_path=ROOT/'evidence/is2-native-profile-audit-20261023b.json'
    profile_path=ROOT/'evidence/is2-native-profile-20261023b.json'
    audit=json.loads(audit_path.read_text(encoding='utf-8'));profile=json.loads(profile_path.read_text(encoding='utf-8'))
    assert audit['accepted'] and audit['profile_sha256']==sha(profile_path)
    paths=sorted(p for p in (BASE/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    assert all(profile['source_sha256'][name]==digest for name,digest in hashes.items())
    owner=ROOT/'user/sessions/latest.json';pointer=ROOT/'output/session.json'
    DEST.mkdir()
    archive=DEST/'audited-is12-before-tides.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
    shutil.copytree(BASE/'app',DEST/'app',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copy2(ROOT/'output/is3-solar-staging/solar_tides.py',DEST/'app/solar_tides.py')
    (DEST/'gravity-sessions').mkdir()
    report={'schema':1,'created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'base_profile':profile_path.relative_to(ROOT).as_posix(),'base_audit_sha256':sha(audit_path),
        'base_source_sha256':hashes,'base_archive':archive.relative_to(ROOT).as_posix(),'base_archive_sha256':sha(archive),
        'owner_pointer_sha256':sha(owner),'active_session_pointer_sha256':sha(pointer),
        'staging_tide_module_sha256':sha(DEST/'app/solar_tides.py'),
        'scope':'New unapproved IS3 API/UI candidate; base acceptance is preserved, not inherited for new behavior.'}
    receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'candidate':DEST.relative_to(ROOT).as_posix(),'preserved_base_files':len(paths)}))

if __name__=='__main__':main()
