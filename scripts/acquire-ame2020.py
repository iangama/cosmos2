"""Acquire the published AME2020 original, verify pin and record every row."""
from pathlib import Path
import datetime
import hashlib
import json
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from nuclei import DATA, EXPECTED_SHA256, FORMAT, SOURCES, catalog

if not DATA.exists():
    with urllib.request.urlopen(SOURCES[2]['url'], timeout=45) as response:
        raw = response.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024 or hashlib.sha256(raw).hexdigest() != EXPECTED_SHA256:
        raise ValueError('Aquisição AME2020 fora do tamanho/hash fixado.')
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_bytes(raw)
raw = DATA.read_bytes()
data = catalog()
receipt = {'acquired_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'file': str(DATA.relative_to(ROOT)).replace('\\', '/'), 'url': SOURCES[2]['url'],
           'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
           'checksum_kind': 'local SHA256 pin, not a provider signature',
           'published_fortran_format': FORMAT, 'coverage': data['coverage'],
           'parsed_records': len(data['records']), 'ignored_data_rows': 0,
           'sources': SOURCES, 'scope': 'Original evaluated data, original flags and precision retained. No half-lives or isomer states inferred.'}
(ROOT / 'evidence/ame2020-acquisition.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
