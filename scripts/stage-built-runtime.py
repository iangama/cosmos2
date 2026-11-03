"""Stage own Release binaries beside distribution assets; preserve official runtime."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
official = ROOT / '.runtime'
binaries = ROOT / '.upstream/openspace/bin/Release'
target = ROOT / '.runtime-built'
required = ('OpenSpace.exe', 'OpenSpace_Helper.exe', 'libcef.dll', 'resources.pak', 'icudtl.dat')
if any(not (binaries / name).is_file() for name in required):
    raise RuntimeError('Release incompleto; finalize a compilação antes do estágio.')
def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

official_hash = digest(official / 'bin/OpenSpace.exe')
shutil.copytree(official, target, dirs_exist_ok=True,
                ignore=shutil.ignore_patterns('cefcache', 'logs'))
shutil.rmtree(target / 'bin/cefcache', ignore_errors=True)
shutil.copytree(binaries, target / 'bin', dirs_exist_ok=True,
                ignore=shutil.ignore_patterns('*.pdb', '*.lib', '*.exp', 'codegen-tool.exe'))
receipt = {'schema': 1, 'source_commit': '8b2778bed19f0c0501eed110c71dd00bd5305c55',
           'source_components': {'Ghoul': {'commit':subprocess.check_output(
               ['git','-C',str(ROOT/'.upstream/openspace/ext/ghoul'),'rev-parse','HEAD'],text=True).strip(),
               'patch':'ghoul-utf8-font.patch'}},
           'source_patches': {p.name: digest(p) for p in sorted((ROOT / 'patches').glob('*.patch'))},
           'official_exe_sha256': official_hash,
           'built_files': {name: digest(target / 'bin' / name) for name in required},
           'target': str(target), 'content': 'Official distribution assets with own Release engine/helper and matching CEF SDK binaries; no scientific datasets republished.'}
if digest(official / 'bin/OpenSpace.exe') != official_hash:
    raise RuntimeError('Runtime oficial foi alterado durante estágio.')
(ROOT / 'evidence/built-runtime.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
print(json.dumps(receipt, indent=2))
