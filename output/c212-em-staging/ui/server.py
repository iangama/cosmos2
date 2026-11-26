"""Temporary loopback UI for the isolated EM worker; installed Cosmos2 stays intact."""
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
import json
import hashlib
import re
import subprocess
import sys
import threading
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
storage=ROOT.parent/'c212-em-worker'/('ui-'+uuid.uuid4().hex)
worker=subprocess.Popen([sys.executable,'-u',str(ROOT/'em_worker.py'),'--storage',str(storage)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=sys.stderr,text=True,encoding='utf-8')
condition=threading.Condition();command_lock=threading.Lock();latest=None;responses={};serial=0
def reader():
    global latest
    for line in worker.stdout:
        value=json.loads(line)
        with condition:
            if value['type']=='snapshot':latest=value
            elif value.get('id') is not None:responses[value['id']]=value
            condition.notify_all()
threading.Thread(target=reader,daemon=True).start()
def command(value):
    global serial
    with command_lock:
        serial+=1;tag=serial
        worker.stdin.write(json.dumps({**value,'id':tag},allow_nan=False)+'\n');worker.stdin.flush()
        with condition:
            deadline=time.monotonic()+10
            while tag not in responses:
                remaining=deadline-time.monotonic()
                if remaining<=0:raise TimeoutError('EM worker did not confirm; inspect state before repeating a mutation')
                condition.wait(remaining)
            result=responses.pop(tag)
            if result['type']=='error':raise ValueError(result['message'])
            return result
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT/'ui'),**kwargs)
    def json(self,value,status=200):
        raw=json.dumps(value,allow_nan=False).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        if self.path=='/api/state':
            with condition:value=latest
            self.json({'state':value,'worker_pid':worker.pid});return
        if self.path.startswith('/exports/'):
            name=self.path.removeprefix('/exports/')
            if not re.fullmatch('em-measurement-[0-9a-f]{32}\\.json',name):return self.json({'error':'Unknown export'},404)
            path=storage/name
            if not path.is_file():return self.json({'error':'Unknown export'},404)
            raw=path.read_bytes();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Disposition','attachment; filename="cosmos2-em-fontes-leitura.json"');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
        super().do_GET()
    def do_POST(self):
        if self.headers.get('Host')!='127.0.0.1:4716' or self.headers.get('Origin') not in (None,'http://127.0.0.1:4716'):return self.json({'error':'Invalid local origin'},403)
        if self.path=='/api/shutdown':
            self.json({'ok':True});threading.Thread(target=server.shutdown,daemon=True).start();return
        if self.path!='/api/command':return self.json({'error':'Unknown endpoint'},404)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=8192:raise ValueError('Bounded command body required')
            value=json.loads(self.rfile.read(size))
            if not isinstance(value,dict) or value.get('command')=='quit':raise ValueError('Unsupported browser command')
            result=command(value)
            if value.get('command')=='export_sample':
                raw=json.dumps(result['result'],ensure_ascii=False,allow_nan=False,indent=2).encode('utf-8')+b'\n'
                name='em-measurement-'+uuid.uuid4().hex+'.json'
                with (storage/name).open('xb') as stream:stream.write(raw)
                result['artifact']={'file':name,'url':'/exports/'+name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
            self.json(result)
        except (ValueError,TypeError,KeyError,OSError,TimeoutError) as error:self.json({'error':str(error)},400)
    def log_message(self,*_):pass
server=ThreadingHTTPServer(('127.0.0.1',4716),Handler)
print('Isolated EM UI http://127.0.0.1:4716/ ; worker '+str(worker.pid),flush=True)
try:server.serve_forever()
finally:
    if worker.poll() is None:
        try:command({'command':'quit'});worker.wait(timeout=5)
        finally:
            if worker.poll() is None:worker.terminate()
