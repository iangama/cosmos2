"""Retry SDK manifest embedding on this project's freshly linked Release artifact.

The immediate post-link write can fail c101008d on this machine. The normal
build is then rerun and must succeed; no Windows security settings are changed.
"""
from pathlib import Path
import json
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
tools = sorted(Path('C:/Program Files (x86)/Windows Kits/10/bin').glob('*/x64/mt.exe'))
if not tools:
    raise RuntimeError('Windows SDK mt.exe ausente.')
manifest = ROOT / '.upstream/openspace/modules/webbrowser'
for name in ('OpenSpace.exe', 'OpenSpace_Helper.exe'):
    artifact = ROOT / '.upstream/openspace/bin/Release' / name
    command = [str(tools[-1]), '-nologo', '-manifest', str(manifest / (name+'.manifest')),
               str(manifest / 'compatibility.manifest'), f'-outputresource:{artifact};#1']
    for attempt in range(1, 6):
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode == 0:
            print(json.dumps({'manifest_embedded': True, 'attempt': attempt, 'artifact': str(artifact)}))
            break
        if attempt == 5:
            raise RuntimeError(completed.stdout+completed.stderr)
        time.sleep(.5)
