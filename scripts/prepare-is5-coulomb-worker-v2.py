"""Preserve failed A; prepare direct-interpreter/Windows-job process ownership."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/is5-coulomb-worker-staging'
TARGET=ROOT/'output/is5-coulomb-worker-v2-staging'
if TARGET.exists():raise FileExistsError('Preserve worker v2')
TARGET.mkdir()
for p in BASE.glob('*.py'):shutil.copy2(p,TARGET/p.name)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(TARGET/'base-manifest.json').write_text(json.dumps(dict(base_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in BASE.glob('*.py')},
    A_rejection='is5-coulomb-worker-artifact-20261029a',reason='Direct interpreter PID ownership and OS job instead of Python monitor thread'),indent=2)+'\n')
p=TARGET/'is5_coulomb_artifact.py';text=p.read_text()
text=text.replace("'is5_coulomb_client.py']","'is5_coulomb_client.py','is5_coulomb_process.py']")
p.write_text(text)
p=TARGET/'is5_coulomb_client.py';text=p.read_text()
text=text.replace('MAX_BYTES=16*1024*1024','from is5_coulomb_process import python_argv\n\nMAX_BYTES=16*1024*1024')
text=text.replace("[sys.executable,'-Xutf8','-u',str(Path(__file__).with_name('is5_coulomb_worker.py')),'--storage',str(storage)]",
                  "python_argv(Path(__file__).with_name('is5_coulomb_worker.py'),['--storage',str(storage)])")
p.write_text(text)
p=TARGET/'is5_coulomb_worker.py';text=p.read_text()
text=text.replace('from is5_solar_source import digest','from is5_solar_source import digest\nfrom is5_coulomb_process import python_argv,CalculationJob')
text=text.replace("        task['error_thread'].join(1)","        task['job'].close()\n        task['error_thread'].join(1)")
old="""        try:
            process=subprocess.Popen([sys.executable,'-Xutf8','-u',str(Path(__file__).with_name('is5_coulomb_calculate.py')),
                '--request',str(path),'--parent-pid',str(os.getpid())],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,
                text=True,encoding='utf-8')
        except Exception:
            path.unlink(missing_ok=True)
            raise
"""
new="""        job=CalculationJob();process=None
        try:
            process=subprocess.Popen(python_argv(Path(__file__).with_name('is5_coulomb_calculate.py'),
                ['--request',str(path),'--parent-pid',str(os.getpid())]),stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,encoding='utf-8')
            job.assign(process)
        except Exception:
            job.close()
            if process is not None:
                if process.poll() is None:process.terminate();process.wait(5)
                process.stderr.close()
            path.unlink(missing_ok=True)
            raise
"""
assert text.count(old)==1;text=text.replace(old,new)
text=text.replace("pending=dict(request=copy.deepcopy(request),process=process,input=path", "pending=dict(request=copy.deepcopy(request),process=process,job=job,input=path")
text=text.replace("if set(answer)!={'ok','run'} or answer['run']", "if set(answer)!={'ok','run','process_id'} or answer['process_id']!=task['process'].pid or answer['run']")
p.write_text(text)
