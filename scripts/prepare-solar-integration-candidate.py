"""Fork the installed 3.13 Python product into isolated IS-1/2 storage."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'output/is12-solar-product'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    receipt = ROOT / 'evidence/is12-solar-candidate-prepared-20261023.json'
    if DEST.exists() or receipt.exists():
        raise FileExistsError('Candidate/receipt already exists; do not overwrite it.')
    owner = ROOT / 'user/sessions/latest.json'
    owner_before = sha(owner) if owner.exists() else None
    session = ROOT / 'output/session.json'
    session_before = sha(session) if session.exists() else None
    files = sorted(p for p in (ROOT / 'app').rglob('*')
                   if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    source_hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in files}
    DEST.mkdir()
    archive = DEST / 'installed-3.13-before-solar.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.relative_to(ROOT).as_posix())
    shutil.copytree(ROOT / 'app', DEST / 'app',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    (DEST / 'gravity-sessions').mkdir()
    report = {
        'schema': 1, 'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'candidate': DEST.relative_to(ROOT).as_posix(),
        'base': 'installed root app, checkpoint protocol 3.13; no J acceptance inherited',
        'base_files_sha256': source_hashes,
        'base_archive': archive.relative_to(ROOT).as_posix(),
        'base_archive_sha256': sha(archive),
        'owner_pointer_sha256': owner_before, 'session_pointer_sha256': session_before,
        'owner_preserved': (sha(owner) if owner.exists() else None) == owner_before,
        'session_pointer_preserved': (sha(session) if session.exists() else None) == session_before,
        'installed_preserved': all(sha(ROOT / p) == value for p, value in source_hashes.items()),
        'accepted_for_product': False,
    }
    receipt.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'candidate': report['candidate'], 'base_files': len(files),
                      'installed_preserved': report['installed_preserved'],
                      'owner_preserved': report['owner_preserved']}))


if __name__ == '__main__':
    main()
