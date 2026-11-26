"""Stage a candidate engine separately, retaining the frozen baseline bytes."""
from pathlib import Path
import copy,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1];baseline=ROOT/'.runtime-built';target=ROOT/'.runtime-perf-query'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
receipt=json.loads((ROOT/'evidence/built-runtime.json').read_text());old=sha(baseline/'bin/OpenSpace.exe');assert old==receipt['built_files']['OpenSpace.exe']
new=ROOT/'.upstream/openspace/bin/Release/OpenSpace.exe';assert sha(new)!=old,'Candidate engine has not linked successfully'
assert not target.exists(),'Preserve existing candidate runtime'
shutil.copytree(baseline,target,ignore=shutil.ignore_patterns('cefcache','logs'))
shutil.copy2(new,target/'bin/OpenSpace.exe')
receipt['baseline_runtime_preserved']={'path':str(baseline),'OpenSpace.exe_sha256':old}
receipt['source_patches']={p.name:sha(p) for p in sorted((ROOT/'patches').glob('*.patch'))}
receipt['built_files']['OpenSpace.exe']=sha(target/'bin/OpenSpace.exe');receipt['target']=str(target)
receipt['content']='Isolated candidate with scene-node property lookup via live registry. Baseline CEF/helper/data preserved; native/performance validation pending.'
receipt['changed_source_sha256']={'src/query/query.cpp':sha(ROOT/'.upstream/openspace/src/query/query.cpp')}
assert sha(baseline/'bin/OpenSpace.exe')==old
(ROOT/'evidence/built-runtime-query.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'target':str(target),'old_exe':old,'new_exe':receipt['built_files']['OpenSpace.exe']},indent=2))
