"""Fresh process, first mass edit after integration, with bounded diagnostics."""
from pathlib import Path
import json
import queue
import subprocess
import sys
import threading
import time
import tempfile

ROOT=Path(__file__).resolve().parents[1]
records=[]
with tempfile.TemporaryDirectory(prefix='cosmos2-worker-') as storage:
    process=subprocess.Popen([sys.executable,'-u',str(ROOT/'app/worker.py'),'--storage',storage],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    messages=queue.Queue();stderr=[];latest=None
    def read():
        for line in process.stdout:messages.put(json.loads(line))
    def read_errors():
        for line in process.stderr:stderr.append(line.rstrip())
    threading.Thread(target=read,daemon=True).start();threading.Thread(target=read_errors,daemon=True).start()
    serial=0
    def command(name,**args):
        global serial,latest
        serial+=1;began=time.perf_counter()
        process.stdin.write(json.dumps({'command':name,'id':serial,**args})+'\n');process.stdin.flush()
        deadline=began+8
        while True:
            message=messages.get(timeout=max(.01,deadline-time.perf_counter()))
            if message['type']=='snapshot':latest=message
            if message.get('type')=='error':raise RuntimeError(message)
            if message.get('type')=='ack' and message.get('id')==serial:
                records.append({'command':name,'elapsed_ms':(time.perf_counter()-began)*1000,
                                'worker_elapsed_ms':message.get('elapsed_ms'),'revision':message.get('revision')})
                return message
    passed=False
    try:
        assert messages.get(timeout=5)['type']=='ready'
        command('reset',count=32);command('resume');time.sleep(1);command('pause')
        before=latest
        ack=command('set_mass',body='p0',mass=2)
        assert ack['revision']==1 and latest['revision']==1 and latest['bodies'][0]['mass']==2
        assert [(p['position'],p['velocity']) for p in latest['bodies']]==[(p['position'],p['velocity']) for p in before['bodies']]
        command('save');command('resume');time.sleep(.25);command('pause');command('load')
        assert latest['bodies']==[{**p,'mass':2} if p['id']=='p0' else p for p in before['bodies']]
        command('quit');process.wait(timeout=3);assert process.returncode==0
        passed=True
    except Exception as error:
        records.append({'error':f'{type(error).__name__}: {error}'})
    finally:
        if process.poll() is None:process.kill();process.wait()
    report={'passed':passed,'commands':records,'stderr':stderr,'scope':'isolated first-mutation/ACK and checkpoint test'}
    (ROOT/'evidence/worker-intervention-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if not passed:raise SystemExit(1)
