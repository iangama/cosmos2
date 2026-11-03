"""Stage the corrected engine independently; retain source and measured-runtime hashes."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]
UP=ROOT/'.upstream/openspace'
DEST=ROOT/'.runtime-node-lifecycle-v2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    receipt=ROOT/'evidence/built-runtime-node-lifecycle-v2.json'
    if receipt.exists():raise FileExistsError('Preserve staged runtime receipt.')
    prep=ROOT/'output/node-lifecycle-v2-staging/preparation.json';r=json.loads(prep.read_text(encoding='utf-8'))
    assert all(sha(UP/name)==value for name,value in r['changed_sha256'].items())
    assert all(sha(ROOT/name)==value for name,value in r['preserved_sha256'].items())
    source=ROOT/'.runtime-topic-cleanup'
    def copied(a,b):
        a,b=Path(a),Path(b)
        if b.exists():
            assert sha(a)==sha(b),str(b)
            return str(b)
        try:
            return shutil.copy2(a,b)
        except PermissionError:
            quote=lambda p:"'"+str(p).replace("'","''")+"'"
            subprocess.run(['powershell.exe','-NoProfile','-Command',
                'Copy-Item -LiteralPath '+quote(a)+' -Destination '+quote(b)+' -ErrorAction Stop'],
                check=True,capture_output=True)
            assert sha(a)==sha(b),str(b)
            return str(b)
    shutil.copytree(source,DEST,ignore=shutil.ignore_patterns('cefcache','logs','*.dmp'),dirs_exist_ok=True,copy_function=copied)
    engine=UP/'bin/Release/OpenSpace.exe';shutil.copy2(engine,DEST/'bin/OpenSpace.exe')
    paths=[UP/name for name in r['changed_sha256']]+[prep,Path(__file__).resolve(),ROOT/'scripts/build-node-lifecycle-v2-runtime.ps1',ROOT/'scripts/prepare-node-lifecycle-runtime.py',ROOT/'output/node-lifecycle-staging/node-lifecycle.patch',ROOT/'output/node-lifecycle-v2-staging/node-lifecycle-v2.patch',ROOT/'output/node-lifecycle-v2-staging/before/src/scene/scene.cpp']
    archive=ROOT/'output/node-lifecycle-v2-staging/executed-build-sources.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
    assert all(sha(ROOT/name)==value for name,value in r['preserved_sha256'].items())
    receipt.write_text(json.dumps({'schema':1,'built':True,'accepted':False,'runtime':str(DEST),'engine_sha256':sha(engine),
        'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in paths},'source_archive_sha256':sha(archive),
        'preserved_sha256':r['preserved_sha256'],'scope':'Independent engine candidate for pending scene-node lifetime; native stress, visual replay and dedicated performance pending.'},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'built':True,'runtime':str(DEST),'accepted':False}))


if __name__=='__main__':main()
