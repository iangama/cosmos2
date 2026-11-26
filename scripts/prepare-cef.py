"""Install the exact CEF SDK required by OpenSpace 0.22.0, using HTTPS.

Upstream's CMake downloader uses HTTP and treats a partial directory as ready.
This preparation step verifies the publisher's SHA1 and records local SHA256.
It only touches the project's SDK/cache directories.
"""
from pathlib import Path
import hashlib
import json
import tarfile
import urllib.parse
import urllib.request
import stat
import shutil

ROOT = Path(__file__).resolve().parents[1]
NAME = 'cef_binary_127.3.5+g114ea2a+chromium-127.0.6533.120_windows64'
URL = 'https://cef-builds.spotifycdn.com/' + urllib.parse.quote(NAME + '.tar.bz2')
ARCHIVE = ROOT / '.cache' / (NAME + '.tar.bz2')
DEST = ROOT / 'build' / 'openspace' / 'modules' / 'webbrowser' / 'ext' / 'cef'

def digest(path, algorithm):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()

def main():
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    DEST.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(URL + '.sha1', timeout=30) as response:
        expected = response.read().decode().strip().lower()
    if len(expected) != 40 or any(c not in '0123456789abcdef' for c in expected):
        raise ValueError('Invalid CEF publisher checksum')
    if not ARCHIVE.exists():
        temporary = ARCHIVE.with_suffix('.partial')
        with urllib.request.urlopen(URL, timeout=90) as response, temporary.open('wb') as stream:
            downloaded = 0
            while block := response.read(1024 * 1024):
                stream.write(block)
                downloaded += len(block)
                if downloaded % (32 * 1024 * 1024) == 0:
                    print(f'CEF downloaded {downloaded // (1024*1024)} MiB', flush=True)
        temporary.replace(ARCHIVE)
    actual = digest(ARCHIVE, 'sha1')
    if actual != expected:
        raise ValueError(f'CEF checksum mismatch: {actual} != {expected}')
    if not (DEST / NAME / 'Release' / 'libcef.lib').is_file():
        print('Extracting verified CEF SDK', flush=True)
        with tarfile.open(ARCHIVE) as archive:
            archive.extractall(DEST, filter='data')
    # Publisher tar files are read-only. CMake refreshes/copies them during configure.
    for path in (DEST / NAME).rglob('*'):
        if path.is_file():
            path.chmod(path.stat().st_mode | stat.S_IWRITE)
    # Use native Python's filesystem handling for the upstream Release duplicate.
    # CMake 4.1 file(COPY) failed with Permission denied on the first DLL here.
    shutil.copytree(DEST / NAME / 'Release', DEST / NAME / 'RelWithDebInfo', dirs_exist_ok=True)
    receipt = {'name': NAME, 'url': URL, 'bytes': ARCHIVE.stat().st_size,
               'publisher_sha1': expected, 'local_sha256': digest(ARCHIVE, 'sha256'),
               'destination': str(DEST.relative_to(ROOT))}
    (ROOT / 'evidence' / 'cef-acquisition.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt), flush=True)

if __name__ == '__main__':
    main()
