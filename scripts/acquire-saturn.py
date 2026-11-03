"""Acquire the bounded official Saturn input and its immutable receipts."""
from pathlib import Path
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'output/saturn-acquisition'
BASE = 'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/'
DEST.mkdir(parents=True, exist_ok=True)
files = {'sat459.bsp': BASE+'sat459.bsp', 'sat459.cmt': BASE+'sat459.cmt',
         'sat459.mrg': BASE+'sat459.mrg', 'satellite-checksums.txt': BASE+'aa_checksums.txt'}
receipt = {}
for name, url in files.items():
    path = DEST / name
    if not path.exists():
        print('Downloading ' + name, flush=True)
        temporary = path.with_suffix(path.suffix+'.partial')
        count = 0
        with urllib.request.urlopen(url, timeout=60) as response, temporary.open('wb') as stream:
            while block := response.read(1024*1024):
                count += len(block)
                if count > 128*1024*1024:
                    raise ValueError('Input exceeds the declared128MiB acquisition limit')
                stream.write(block)
        temporary.replace(path)
    raw = path.read_bytes()
    receipt[name] = {'url': url, 'file': str(path.relative_to(ROOT)), 'bytes': len(raw),
                     'sha256': hashlib.sha256(raw).hexdigest(), 'md5': hashlib.md5(raw).hexdigest()}
line = next(line for line in (DEST / 'satellite-checksums.txt').read_text().splitlines() if line.split()[-1]=='sat459.bsp')
assert receipt['sat459.bsp']['md5'] == line.split()[0] == 'bcaab4a0eec7195501116701295d8697'
(ROOT / 'evidence/saturn-acquisition.json').write_text(json.dumps({'schema':1,'files':receipt,
    'published_MD5_matched':True,'scope':'Official input in acquisition cache; production subset699 only, to avoid overriding planetary DE442s'},indent=2)+'\n')
print(json.dumps({'bytes': receipt['sat459.bsp']['bytes'], 'sha256': receipt['sat459.bsp']['sha256'], 'published_MD5_matched': True}))
