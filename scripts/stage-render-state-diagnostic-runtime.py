"""Stage the GL diagnostic engine separately, preserving the measured runtimes."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
UP=ROOT/'.upstream/openspace'
SOURCE=ROOT/'.runtime-topic-cleanup'
TARGET=ROOT/'.runtime-render-state-diagnostic'
RECEIPT=ROOT/'evidence/built-runtime-render-state-diagnostic.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    if TARGET.exists() or RECEIPT.exists():raise FileExistsError('Preserve staged runtime.')
    preparation=ROOT/'output/render-state-diagnostic-staging/preparation.json'
    p=json.loads(preparation.read_text())
    assert all(sha(ROOT/name)==digest for name,digest in p['preserved_sha256'].items())
    assert all(sha(UP/name)==digest for name,digest in p['changed_sha256'].items())
    assert sha(UP/p['new_header'])==p['new_header_sha256']
    engine=UP/'bin/Release/OpenSpace.exe'
    assert sha(engine)!=p['preserved_sha256']['.runtime-topic-cleanup/bin/OpenSpace.exe']
    shutil.copytree(SOURCE,TARGET,ignore=shutil.ignore_patterns('cefcache','logs','*.dmp'))
    shutil.copy2(engine,TARGET/'bin/OpenSpace.exe')
    patch=''
    for name in p['changed_sha256']:
        before=ROOT/'output/render-state-diagnostic-staging/before'/name
        patch+=''.join(difflib.unified_diff(before.read_text().splitlines(True),(UP/name).read_text().splitlines(True),
            fromfile='before/'+name,tofile='render-state-diagnostic/'+name))
    patch+=''.join(difflib.unified_diff([],(UP/p['new_header']).read_text().splitlines(True),
        fromfile='/dev/null',tofile='render-state-diagnostic/'+p['new_header']))
    path=ROOT/'patches/render-state-diagnostic.patch'
    if path.exists():raise FileExistsError(path)
    path.write_text(patch)
    sources=[UP/name for name in p['changed_sha256']]+[UP/p['new_header'],preparation,Path(__file__).resolve(),
        ROOT/'scripts/prepare-render-state-diagnostic.py',ROOT/'scripts/build-render-state-diagnostic-runtime.ps1']
    archive=ROOT/'output/render-state-diagnostic-staging/executed-build-sources.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name in sources:z.write(name,name.relative_to(ROOT).as_posix())
    assert all(sha(ROOT/name)==digest for name,digest in p['preserved_sha256'].items())
    report={'schema':1,'status':'separate_unapproved_opt_in_GL_observation_runtime','target':str(TARGET),
        'engine_sha256':sha(TARGET/'bin/OpenSpace.exe'),'base_runtime_receipt_sha256':sha(ROOT/'evidence/built-runtime-topic-cleanup.json'),
        'preserved_sha256':p['preserved_sha256'],'source_sha256':{name.relative_to(ROOT).as_posix():sha(name) for name in sources},
        'source_archive_sha256':sha(archive),'patch':path.relative_to(ROOT).as_posix(),'patch_sha256':sha(path),
        'scope':'Bounded opt-in GL state/readback observations only, disabled by default. No rendering fix or science change; observations can stall GPU and do not count as performance measurements. No automatic selection/promotion.'}
    RECEIPT.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'target':str(TARGET),'engine_sha256':report['engine_sha256']}),flush=True)


if __name__=='__main__':main()
