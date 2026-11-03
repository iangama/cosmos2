"""Freeze a separate EM GPU receiver; preserve all approved runtime executables."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'output/c212-em-cloud-native-before'
UPSTREAM = ROOT/'.upstream/openspace'
TARGET = ROOT/'.runtime-em-cloud'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


preserved = json.loads((BASE/'preserved-sha256.json').read_text())
for path, expected in preserved.items():
    assert sha(ROOT/path) == expected, path
resume = '--resume-partial' in sys.argv
assert not (ROOT/'evidence/built-runtime-em-cloud.json').exists(), 'Preserve a completed runtime candidate'
if TARGET.exists():
    assert resume, 'Use --resume-partial only for an interrupted staging copy'
    assert sha(TARGET/'bin/OpenSpace.exe') == preserved['.runtime-cloud/bin/OpenSpace.exe']
engine = UPSTREAM/'bin/Release/OpenSpace.exe'
assert sha(engine) != preserved['.runtime-cloud/bin/OpenSpace.exe']
sources = {}
patch = ''
for name in ('renderablepointcloud.cpp', 'renderablepointcloud.h'):
    source = UPSTREAM/'modules/base/rendering/pointcloud'/name
    before = BASE/name
    sources[str(source.relative_to(UPSTREAM))] = sha(source)
    patch += ''.join(difflib.unified_diff(before.read_text().splitlines(True), source.read_text().splitlines(True),
                                        fromfile='cloud-approved/'+name, tofile='em-cloud-candidate/'+name))
patch_path = ROOT/'patches/em-cloud-position-binding.patch'
if patch_path.exists():
    assert resume and patch_path.read_text() == patch, 'Preserve an existing different EM patch'
patch_path.write_text(patch)
def copy_missing(source, target):
    if Path(target).exists():
        assert sha(Path(source)) == sha(Path(target)), 'Interrupted stage contains a different file: '+str(target)
        return target
    for attempt in range(6):
        try:
            return shutil.copy2(source, target)
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(.2)
shutil.copytree(ROOT/'.runtime-cloud', TARGET, ignore=shutil.ignore_patterns('cefcache', 'logs', '*.dmp'),
                dirs_exist_ok=resume, copy_function=copy_missing)
shutil.copy2(engine, TARGET/'bin/OpenSpace.exe')
for path, expected in preserved.items():
    assert sha(ROOT/path) == expected, path
receipt = {
    'schema': 1, 'status': 'separate_unapproved_EM_cloud_receiver_built',
    'target': str(TARGET), 'engine_sha256': sha(TARGET/'bin/OpenSpace.exe'),
    'source_commit': subprocess.check_output(['git', '-C', str(UPSTREAM), 'rev-parse', 'HEAD'], text=True).strip(),
    'changed_source_sha256': sources, 'patch': str(patch_path.relative_to(ROOT)),
    'patch_sha256': sha(patch_path), 'preserved_sha256': preserved,
    'builder_sha256': sha(ROOT/'scripts/build-em-cloud-runtime.ps1'), 'stager_sha256': sha(Path(__file__)),
    'scope': 'Explicit EM Borisv2, time/length units1/1. Legacy gravity binding remains available. '
             'No runtime/UI/science/performance approval; never auto-selected for installed product.'}
(ROOT/'evidence/built-runtime-em-cloud.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps({'target': str(TARGET), 'engine_sha256': receipt['engine_sha256']}), flush=True)
