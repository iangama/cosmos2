"""Stage this project's generated Release dependency-copy list with native Python.

The native CMake copy command intermittently denies the first write of SDK DLLs
on this machine. Files are staged byte-for-byte; no security settings change.
The generated build retains its normal copy/check targets.
"""
from pathlib import Path
import re
import shlex
import shutil
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
project=ROOT/'build'/'openspace'/'apps'/'OpenSpace'/'openspace_copy_external_dependencies.vcxproj'
count=0
for node in ET.parse(project).iter():
    if not node.tag.endswith('Command') or '/bin/Release' not in (node.text or ''):
        continue
    for kind,arguments in re.findall(r' -E (copy_if_different|copy_directory) ([^\r\n]+)',node.text or ''):
        source,dest=map(Path,shlex.split(arguments))
        source.resolve().relative_to(ROOT)
        dest.resolve().relative_to(ROOT)
        dest.mkdir(parents=True,exist_ok=True)
        if kind=='copy_directory':
            shutil.copytree(source,dest,dirs_exist_ok=True)
        else:
            target=dest/source.name
            if not target.exists() or target.stat().st_size!=source.stat().st_size or target.stat().st_mtime_ns!=source.stat().st_mtime_ns:
                shutil.copy2(source,target)
        count+=1
if count == 0:
    raise RuntimeError('Generated Release dependency list is empty')
print(f'Staged {count} dependency entries',flush=True)
