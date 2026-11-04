"""One bounded command at a time, newest snapshot only, no unbounded protocol log."""
from pathlib import Path
from collections import deque
import copy
import json
import subprocess
import sys
import threading
import time


class Client:
    def __init__(self,storage):
        self.condition=threading.Condition();self.command_lock=threading.Lock();self.last=None;self.reply=None;self.ready=None;self.dead=False;self.serial=0;self.stderr=deque(maxlen=20)
        self.process=subprocess.Popen([sys.executable,'-Xutf8','-u',str(Path(__file__).with_name('is4_worker.py')),'--storage',str(storage)],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',bufsize=1)
        def reader():
            try:
                for line in self.process.stdout:
                    if len(line)>4*1024*1024:raise ValueError('Particle worker publication exceeds budget')
                    value=json.loads(line)
                    with self.condition:
                        if value.get('state') is not None:self.last=value['state']
                        if value.get('type')=='ready':self.ready=value
                        if value.get('type') in ['ack','error']:self.reply=value
                        self.condition.notify_all()
            finally:
                with self.condition:self.dead=True;self.condition.notify_all()
        def errors():
            for line in self.process.stderr:self.stderr.append(line.rstrip()[:1000])
        self.reader=threading.Thread(target=reader,daemon=True);self.reader.start()
        self.errors=threading.Thread(target=errors,daemon=True);self.errors.start()
        deadline=time.monotonic()+15
        with self.condition:
            while self.ready is None or self.last is None:
                if self.dead or time.monotonic()>deadline:raise RuntimeError('Particle worker failed to initialize: '+' '.join(self.stderr))
                self.condition.wait(timeout=.05)
        if self.ready.get('protocol')!=1:raise ValueError('Particle worker protocol differs')

    def snapshot(self):
        with self.condition:return copy.deepcopy(self.last)

    @staticmethod
    def guard(state):
        exp=state['experiment']
        return {'worker_id':state['worker_id'],'experiment_id':None if exp is None else exp['id'],'edit_token':None if exp is None else exp['edit_token'],
            'revision':None if exp is None else exp['revision'],'expected_time_s':None if exp is None else exp['phase']['time_s'],'frame':state['frame']}

    def call(self,name,extra=None,guard=None):
        with self.command_lock:
            with self.condition:
                if self.dead:raise RuntimeError('Particle worker exited: '+' '.join(self.stderr))
                self.serial+=1;identifier=self.serial;self.reply=None
                request={'id':identifier,'command':name,**(extra or {})}
                if name not in ['state','quit']:request['guard']=self.guard(self.last) if guard is None else copy.deepcopy(guard)
            self.process.stdin.write(json.dumps(request,allow_nan=False)+'\n');self.process.stdin.flush()
            deadline=time.monotonic()+15
            with self.condition:
                while self.reply is None or self.reply.get('id')!=identifier:
                    if self.dead or time.monotonic()>deadline:raise RuntimeError('Particle command did not acknowledge; refresh before retrying')
                    self.condition.wait(timeout=.05)
                reply=copy.deepcopy(self.reply)
            if reply['type']=='error':raise ValueError(reply['message'])
            return reply

    def close(self):
        if self.process.poll() is None:
            try:self.call('quit');self.process.stdin.close();self.process.wait(timeout=8)
            finally:
                if self.process.poll() is None:self.process.terminate();self.process.wait(timeout=5)
        self.reader.join(timeout=2);self.errors.join(timeout=2)
        self.process.stdout.close();self.process.stderr.close()
