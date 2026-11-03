"""Fork native runners/auditors by changing collector identities only; preserve criteria."""
from pathlib import Path
import ast
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PAIRS={
    'benchmark-em128-potential-native.py':{
        'benchmark-em128-potential-native.py':'benchmark-em128-potential-native-diagnostic.py',
        'collect-em-potential-gpu-memory.ps1':'collect-em-potential-gpu-memory-diagnostic.ps1'},
    'benchmark-em-cloud-source128-native.py':{
        'collect-em-cloud-gpu-memory.ps1':'collect-em-cloud-gpu-memory-diagnostic.ps1'},
    'review-em128-new-runtime-benchmark.py':{
        'collect-em-potential-gpu-memory.ps1':'collect-em-potential-gpu-memory-diagnostic.ps1'},
    'review-em-cloud-source128-benchmark.py':{
        'collect-em-cloud-gpu-memory.ps1':'collect-em-cloud-gpu-memory-diagnostic.ps1'},
}


def main():
    dest=ROOT/'output/em-diagnostic-profile-forks-20261023';receipt=ROOT/'evidence/em-diagnostic-profile-forks-20261023.json'
    if dest.exists() or receipt.exists():raise FileExistsError('Preserve previous forks.')
    dest.mkdir();records={};sources=[]
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for name,replacements in PAIRS.items():
        original=ROOT/'scripts'/name;new=original.with_name(original.stem+'-diagnostic.py')
        if new.exists():raise FileExistsError(new)
        source=original.read_text(encoding='utf-8');fork=source
        for before,after in replacements.items():
            assert before in fork;fork=fork.replace(before,after)
        reversed_fork=fork
        for before,after in replacements.items():reversed_fork=reversed_fork.replace(after,before)
        assert reversed_fork==source
        assert ast.dump(ast.parse(reversed_fork))==ast.dump(ast.parse(source))
        new.write_text(fork,encoding='utf-8')
        records[name]={'original_sha256':sha(original),'fork':new.relative_to(ROOT).as_posix(),
            'fork_sha256':sha(new),'only_literal_collector_or_own_source_identity_substitutions':replacements,
            'full_text_and_AST_equal_after_reversing_identity_substitutions':True}
        sources += [original,new]
    sources += [ROOT/'scripts/collect-em-potential-gpu-memory-diagnostic.ps1',ROOT/'scripts/collect-em-cloud-gpu-memory-diagnostic.ps1',Path(__file__).resolve()]
    archive=dest/'originals-forks-and-collectors.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sources:z.write(p,p.relative_to(ROOT).as_posix())
    receipt.write_text(json.dumps({'schema':1,'prepared':True,'records':records,'archive_sha256':sha(archive),
        'scope':'Only explicit collector/source identity substitutions; all loops, durations, assertions, physical fixtures and numerical/resource/latency limits unchanged. This preparation does not approve any native profile.'},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'receipt':receipt.relative_to(ROOT).as_posix(),'forks':len(records)}))


if __name__=='__main__':main()
