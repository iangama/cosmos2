"""Stage a separate topic lifecycle candidate; preserve every existing runtime."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
BEFORE = ROOT/'output/c212-topic-cleanup-before'
UPSTREAM = ROOT/'.upstream/openspace'
TARGET = ROOT/'.runtime-topic-cleanup'
RECEIPT = ROOT/'evidence/built-runtime-topic-cleanup.json'
NAMES = ('src/topic/connection.cpp', 'include/openspace/topic/connection.h', 'src/topic/server.cpp')

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

preserved = json.loads((BEFORE/'preserved-sha256.json').read_text())
assert not RECEIPT.exists(), 'Preserve a completed candidate'
for name, digest in preserved.items(): assert sha(ROOT/name) == digest, name
engine = UPSTREAM/'bin/Release/OpenSpace.exe'
assert sha(engine) != preserved['.runtime-em-cloud/bin/OpenSpace.exe']
patch = ''
for name in NAMES:
    patch += ''.join(difflib.unified_diff((BEFORE/name).read_text().splitlines(True), (UPSTREAM/name).read_text().splitlines(True),
                    fromfile='em-cloud-before/'+name, tofile='topic-cleanup-candidate/'+name))
patch_path = ROOT/'patches/completed-topic-lifecycle.patch'
if patch_path.exists(): assert patch_path.read_text() == patch
else: patch_path.write_text(patch)

def copy_missing(source, target):
    if Path(target).exists():
        assert sha(Path(source)) == sha(Path(target)), str(target)
        return target
    for attempt in range(6):
        try: return shutil.copy2(source, target)
        except PermissionError:
            if attempt == 5: raise
            time.sleep(.2)

shutil.copytree(ROOT/'.runtime-em-cloud', TARGET, ignore=shutil.ignore_patterns('cefcache','logs','*.dmp'),
                dirs_exist_ok=True, copy_function=copy_missing)
shutil.copy2(engine, TARGET/'bin/OpenSpace.exe')
for name, digest in preserved.items(): assert sha(ROOT/name) == digest, name
receipt = {'schema': 1, 'status': 'separate_unapproved_completed_topic_cleanup_runtime',
           'target': str(TARGET), 'engine_sha256': sha(TARGET/'bin/OpenSpace.exe'),
           'source_commit': subprocess.check_output(['git','-C',str(UPSTREAM),'rev-parse','HEAD'],text=True).strip(),
           'changed_source_sha256': {name: sha(UPSTREAM/name) for name in NAMES},
           'patch': str(patch_path.relative_to(ROOT)), 'patch_sha256': sha(patch_path),
           'base_receipt_sha256': sha(ROOT/'evidence/built-runtime-em-cloud.json'),
           'preserved_sha256': preserved,
           'builder_sha256': sha(ROOT/'scripts/build-topic-cleanup-runtime.ps1'),
           'stager_sha256': sha(Path(__file__)),
           'scope': 'Retire completed asynchronous topics at next main-thread preSync, before new messages. '
                    'Keep pending callbacks and active subscriptions. Physics and approved installed product unchanged. '
                    'No automatic runtime selection or promotion; integration, lifecycle and performance checks still required.'}
RECEIPT.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'target':str(TARGET),'engine_sha256':receipt['engine_sha256']}),flush=True)
