"""Stage the live-cloud engine separately, preserving approved query/baseline bytes."""
from pathlib import Path
import copy
import hashlib
import json
import shutil
import subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
query=ROOT/'.runtime-perf-query';target=ROOT/'.runtime-cloud';upstream=ROOT/'.upstream/openspace'
receipt=json.loads((ROOT/'evidence/built-runtime-query.json').read_text())
query_sha=sha(query/'bin/OpenSpace.exe')
baseline_sha=sha(ROOT/'.runtime-built/bin/OpenSpace.exe')
assert query_sha==receipt['built_files']['OpenSpace.exe']
assert baseline_sha==receipt['baseline_runtime_preserved']['OpenSpace.exe_sha256']
assert not target.exists(),'Preserve existing cloud runtime'
new=upstream/'bin/Release/OpenSpace.exe'
assert sha(new)!=query_sha,'Cloud executable has not been linked'
patch=subprocess.run(['git','-C',str(upstream),'diff','--',
    'modules/base/rendering/pointcloud/renderablepointcloud.cpp',
    'modules/base/rendering/pointcloud/renderablepointcloud.h'],check=True,capture_output=True).stdout
assert b'updateConfirmedCloud' in patch
(ROOT/'patches/cloud-position-stream.patch').write_bytes(patch)
shutil.copytree(query,target,ignore=shutil.ignore_patterns('cefcache','logs'))
shutil.copy2(new,target/'bin/OpenSpace.exe')
receipt['source_patches']={p.name:sha(p) for p in sorted((ROOT/'patches').glob('*.patch'))}
receipt['built_files']['OpenSpace.exe']=sha(target/'bin/OpenSpace.exe')
receipt['target']=str(target)
receipt['content']='Isolated unapproved candidate: opt-in confirmed10k aggregate position stream. Not selected automatically.'
receipt['approved_query_runtime_preserved']={'path':str(query),'OpenSpace.exe_sha256':query_sha}
receipt['changed_source_sha256'].update({str(p.relative_to(upstream)):sha(p) for p in
    (upstream/'modules/base/rendering/pointcloud/renderablepointcloud.cpp',upstream/'modules/base/rendering/pointcloud/renderablepointcloud.h')})
assert sha(query/'bin/OpenSpace.exe')==query_sha and sha(ROOT/'.runtime-built/bin/OpenSpace.exe')==baseline_sha
(ROOT/'evidence/built-runtime-cloud.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'target':str(target),'candidate_sha256':receipt['built_files']['OpenSpace.exe'],'query_preserved':query_sha,'baseline_preserved':baseline_sha},indent=2))
