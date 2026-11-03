"""Build isolated original/aligned author reference; never overwrite evidence."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT/'output/is5-coulomb-research-20261028'
source = STAGE/'eos22.f'
aligned = STAGE/'eos22-CTF-aligned.f'
binary = STAGE/'reference-coulomb-CTF-aligned'
receipt = STAGE/'reference-CTF-alignment.json'
if any(p.exists() for p in [aligned, binary, receipt]):
    raise FileExistsError('Preserve reference alignment')
original = source.read_text(encoding='ascii')
old = 'CTF=Zion**2*.2513*(Z13-1.+.2/sqrt(Z13))'
new = 'CTF=Zion**2*(18.d0/175.d0)*(12.d0/acos(-1.d0))**(2.d0/3.d0)*(Z13-1.+.2/sqrt(Z13))'
assert original.count(old) == 1
aligned.write_text(original.replace(old, new), encoding='ascii')
compiler = ROOT/'.tooling/fortran/usr/bin/x86_64-linux-gnu-gfortran-13'
command = [str(compiler), '-B', str(ROOT/'.tooling/fortran/usr/lib/gcc/x86_64-linux-gnu/13'),
           '-B', '/usr/lib/gcc/x86_64-linux-gnu/13', '-std=legacy', '-ffixed-line-length-none', '-O2',
           str(aligned), str(STAGE/'reference-driver.f90'), '-o', str(binary)]
run = subprocess.run(command, text=True, capture_output=True, timeout=120)
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r = dict(completed=run.returncode == 0, scientific_acceptance=False, command=command,
         returncode=run.returncode, stdout=run.stdout, stderr=run.stderr,
         substitution=dict(old=old, new=new, occurrences=1),
         sha256={p.name:sha(p) for p in [source, aligned, Path(__file__), STAGE/'reference-driver.f90']})
if run.returncode == 0:
    r['sha256'][binary.name] = sha(binary)
receipt.write_text(json.dumps(r, indent=2)+'\n', encoding='utf-8')
print(json.dumps(dict(completed=r['completed'], failure=run.stderr)))
raise SystemExit(run.returncode)
