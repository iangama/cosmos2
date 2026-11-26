"""Acquire JUP348 as a bounded candidate input, without loading it in production."""
from pathlib import Path
import datetime
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'output/jupiter-acquisition-20261023'
BASE = 'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/'
RECEIPT = ROOT / 'evidence/jupiter-acquisition-20261023.json'
assert not RECEIPT.exists(), 'Preserve the completed acquisition receipt.'
DEST.mkdir(exist_ok=True)
files = {}
for name in ['aa_checksums.txt', 'jup348.cmt', 'jup348.mrg', 'jup365.cmt', 'jup365.mrg', 'jup348.bsp']:
    path = DEST / name
    url = BASE + name
    if not path.exists():
        partial = path.with_name(path.name + '.partial')
        assert not partial.exists(), 'Inspect the earlier partial download before resuming.'
        print('Downloading ' + name, flush=True)
        total = 0
        with urllib.request.urlopen(url, timeout=45) as response, partial.open('xb') as output:
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > (80 * 1024 * 1024 if name.endswith('.bsp') else 1024 * 1024):
                    raise ValueError('Input exceeded the bounded acquisition size.')
                output.write(block)
        partial.replace(path)
    raw = path.read_bytes()
    files[name] = {'file': path.relative_to(ROOT).as_posix(), 'url': url, 'bytes': len(raw),
                   'sha256': hashlib.sha256(raw).hexdigest(), 'md5': hashlib.md5(raw).hexdigest()}
checksum_lines = (DEST / 'aa_checksums.txt').read_text().splitlines()
expected = next(line.split()[0] for line in checksum_lines if line.split()[-1] == 'jup348.bsp')
assert files['jup348.bsp']['md5'] == expected == 'a19ec916c95267772d5f261dc248b1dd'
assert (DEST / 'jup348.bsp').read_bytes()[:8] == b'DAF/SPK '
report = {'schema': 1, 'acquired_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'files': files, 'published_MD5_matched': True,
          'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'scope': 'Candidate acquisition only; extract 599 relative to 5 before use, preserving DE442s authority. No production files changed.'}
RECEIPT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'bytes': files['jup348.bsp']['bytes'], 'sha256': files['jup348.bsp']['sha256'],
                  'published_MD5_matched': True}), flush=True)
