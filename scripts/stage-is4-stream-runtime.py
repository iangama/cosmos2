"""Stage an isolated trajectory renderer; preserve the measured V2 executable."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1];UP=ROOT/'.upstream/openspace'
DEST=ROOT/'.runtime-is4-stream';STAGE=ROOT/'output/is4-stream-runtime-staging'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    receipt=ROOT/'evidence/built-runtime-is4-stream.json'
    if receipt.exists() or DEST.exists():raise FileExistsError('Preserve staged runtime.')
    prep=json.loads((STAGE/'preparation.json').read_text(encoding='utf-8'))
    assert all(sha(ROOT/n)==v for n,v in prep['preserved_sha256'].items())
    prior=json.loads((ROOT/'evidence/built-runtime-node-lifecycle-v2.json').read_text(encoding='utf-8'))
    inherited={n:v for n,v in prior['source_sha256'].items() if n.startswith('.upstream/')}
    assert all(sha(ROOT/n)==v for n,v in inherited.items())
    changed={n:sha(UP/n) for n in prep['before_sha256']}
    patch=''.join(''.join(difflib.unified_diff((STAGE/'before'/n).read_text(encoding='utf-8').splitlines(True),(UP/n).read_text(encoding='utf-8').splitlines(True),fromfile='before/'+n,tofile='is4-stream/'+n)) for n in changed)
    (STAGE/'is4-stream.patch').write_text(patch,encoding='utf-8')
    shutil.copytree(ROOT/'.runtime-node-lifecycle-v2',DEST,ignore=shutil.ignore_patterns('cefcache','logs','*.dmp'))
    shutil.copy2(UP/'bin/Release/OpenSpace.exe',DEST/'bin/OpenSpace.exe')
    files=[UP/n for n in changed]+[ROOT/n for n in inherited]+[Path(__file__),ROOT/'scripts/prepare-is4-stream-runtime.py',ROOT/'IS-4-TRANSPORTE-NATIVO-CONTRATO.md',STAGE/'preparation.json',STAGE/'is4-stream.patch']
    archive=STAGE/'executed-build-sources.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    assert all(sha(ROOT/n)==v for n,v in prep['preserved_sha256'].items())
    receipt.write_text(json.dumps({'schema':1,'built':True,'accepted':False,'runtime':str(DEST),'engine_sha256':sha(DEST/'bin/OpenSpace.exe'),
        'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in files},'source_archive_sha256':sha(archive),'preserved_sha256':prep['preserved_sha256'],
        'scope':'Own bounded normalized trajectory receiver in optional constellation-line mode; shared VBO line/endpoint, CRC32 and monotonic binding guards. Native proof/UI/performance pending.'},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'built':True,'runtime':str(DEST),'accepted':False}))


if __name__=='__main__':main()
