"""One harmless owned PowerShell probe; never resumes threads or changes policy."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import time
import traceback
import psutil

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument('--label', required=True)
args = parser.parse_args()
if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
    parser.error('Invalid label')
out = ROOT / ('evidence/local-ui-powershell-probe-' + args.label + '.json')
if out.exists():
    raise FileExistsError('Preserve PowerShell probe')
entry = ROOT / 'Iniciar-Cosmos2.cmd'
owner = ROOT / 'user/sessions/latest.json'
record = dict(accepted=False, completed=False, source_sha256={Path(__file__).relative_to(ROOT).as_posix():sha(Path(__file__))},
    entry_sha256=sha(entry), owner_sha256=sha(owner), observations=[],
    scope='Single harmless PowerShell console-output probe after execution permissions changed. No thread resume, security policy change, native startup, shortcut activation or GPU/profile acceptance.')
child = None
try:
    executable = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    child = subprocess.Popen([str(executable), '-NoProfile', '-NonInteractive', '-Command',
        "[Console]::WriteLine('COSMOS2_PS_PROBE')"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    record['pid'] = child.pid
    deadline = time.monotonic() + 10
    while child.poll() is None and time.monotonic() < deadline:
        try:
            p = psutil.Process(child.pid)
            cpu = p.cpu_times()
            record['observations'].append(dict(status=p.status(), threads=p.num_threads(), cpu_s=cpu.user+cpu.system))
        except psutil.NoSuchProcess:
            break
        time.sleep(.25)
    record['timed_out'] = child.poll() is None
    if child.poll() is None:
        child.terminate()
    stdout, stderr = child.communicate(timeout=5)
    record.update(exit=child.returncode, stdout=stdout, stderr=stderr, completed=True,
                  accepted=child.returncode == 0 and stdout.strip() == 'COSMOS2_PS_PROBE')
    assert sha(entry) == record['entry_sha256'] and sha(owner) == record['owner_sha256']
except Exception:
    record['failure'] = traceback.format_exc()
finally:
    if child is not None and child.poll() is None:
        child.terminate()
        child.communicate(timeout=5)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
print(json.dumps(record, ensure_ascii=True))
