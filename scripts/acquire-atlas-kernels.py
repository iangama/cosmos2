"""Small fixed JPL kernel set, provider MD5 plus local SHA256 receipt."""
from pathlib import Path
import datetime
import hashlib
import json
import urllib.request

ROOT=Path(__file__).resolve().parents[1];folder=ROOT/'data/spice';folder.mkdir(parents=True,exist_ok=True)
base='https://naif.jpl.nasa.gov/pub/naif/generic_kernels/'
sources={'de442s.bsp':'spk/planets/de442s.bsp','naif0012.tls':'lsk/naif0012.tls',
         'pck00011.tpc':'pck/pck00011.tpc','de442s.mrg':'spk/planets/de442s.mrg',
         'de442_tech-comments.txt':'spk/planets/de442_tech-comments.txt',
         'aa_checksums.txt':'spk/planets/aa_checksums.txt'}
records={}
for name,remote in sources.items():
    path=folder/name
    if not path.exists():
        with urllib.request.urlopen(base+remote,timeout=45) as response:
            raw=response.read(40*1024*1024+1)
        if len(raw)>40*1024*1024:raise RuntimeError('Unexpected kernel size')
        path.write_bytes(raw)
    raw=path.read_bytes()
    records[name]={'url':base+remote,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
published=dict((line.split()[1],line.split()[0]) for line in (folder/'aa_checksums.txt').read_text().splitlines() if line.strip())
actual=hashlib.md5((folder/'de442s.bsp').read_bytes()).hexdigest()
if actual!=published['de442s.bsp']:raise RuntimeError('JPL published checksum mismatch')
records['de442s.bsp'].update(provider_md5=published['de442s.bsp'],provider_md5_verified=True)
receipt={'acquired_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':records,
         'scope':'JPL/NAIF fixed local kernels. SHA256 is locally calculated; provider MD5 recorded for transfer verification, not a signature.'}
(ROOT/'evidence/atlas-kernels-acquisition.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
