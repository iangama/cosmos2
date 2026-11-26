"""Correlated bounded replies; state and graceful quit may interrupt a calculation."""
from pathlib import Path
from collections import deque
import copy
import json
import math
import subprocess
import sys
import threading
import time

MAX_BYTES=16*1024*1024


class Client:
    def __init__(self,storage):
        self.condition=threading.Condition();self.write_lock=threading.Lock()
        self.last=self.ready=None;self.dead=False;self.serial=0;self.pending={};self.stderr=deque(maxlen=20)
        self.process=subprocess.Popen([sys.executable,'-Xutf8','-u',str(Path(__file__).with_name('is5_coulomb_worker.py')),'--storage',str(storage)],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',bufsize=1)
        def reader():
            try:
                while True:
                    line=self.process.stdout.readline(MAX_BYTES+1)
                    if not line:break
                    if len(line.encode('utf-8'))>MAX_BYTES:raise ValueError('Coulomb publication exceeds budget')
                    value=json.loads(line)
                    with self.condition:
                        state=value.get('state')
                        if state is not None:
                            if self.last is None or state['worker_id']!=self.last['worker_id'] or state['sequence']>self.last['sequence']:
                                self.last=state
                        if value.get('type')=='ready':self.ready=value
                        if value.get('type') in ['ack','error'] and value.get('id') in self.pending:
                            self.pending[value['id']]=value
                        self.condition.notify_all()
            except Exception as error:
                self.stderr.append(str(error))
            finally:
                with self.condition:self.dead=True;self.condition.notify_all()
        def errors():
            for line in self.process.stderr:self.stderr.append(line.rstrip()[:1000])
        self.reader=threading.Thread(target=reader,daemon=True);self.reader.start()
        self.errors=threading.Thread(target=errors,daemon=True);self.errors.start()
        deadline=time.monotonic()+45
        try:
            with self.condition:
                while self.ready is None or self.last is None:
                    if self.dead or time.monotonic()>deadline:raise RuntimeError('Coulomb worker did not initialize: '+' '.join(self.stderr))
                    self.condition.wait(.05)
            if self.ready.get('protocol')!=2 or self.ready.get('kind')!='is5_coulomb_calculated_solar_zone':
                raise ValueError('Coulomb worker protocol differs')
        except Exception:
            self._terminate()
            self.reader.join(2);self.errors.join(2)
            self.process.stdin.close();self.process.stdout.close();self.process.stderr.close()
            raise

    def snapshot(self):
        with self.condition:return copy.deepcopy(self.last)

    @staticmethod
    def guard(state):
        return {k:state[k] for k in ['worker_id','artifact_id','edit_token','revision']}

    def _terminate(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(5)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(5)
        with self.condition:self.dead=True;self.condition.notify_all()

    def call(self,name,extra=None,guard=None):
        calculation=name in ['create','configure','restart','load','branch_load']
        deadline=time.monotonic()+(300 if calculation else 8 if name=='quit' else 30)
        with self.write_lock:
            with self.condition:
                if self.dead:raise RuntimeError('Coulomb worker exited: '+' '.join(self.stderr))
                if len(self.pending)>=16:raise ValueError('Coulomb request limit16 reached')
                self.serial+=1;identifier=self.serial;self.pending[identifier]=None
                request={'id':identifier,'command':name,**(extra or {})}
                if name not in ['state','quit']:request['guard']=self.guard(self.last) if guard is None else copy.deepcopy(guard)
            try:
                serialized=json.dumps(request,allow_nan=False)+'\n'
                if len(serialized.encode('utf-8'))>MAX_BYTES:raise ValueError('Coulomb request exceeds budget')
                self.process.stdin.write(serialized);self.process.stdin.flush()
            except Exception:
                with self.condition:self.pending.pop(identifier,None)
                raise
        try:
            with self.condition:
                while self.pending[identifier] is None:
                    if self.dead:raise RuntimeError('Coulomb worker exited: '+' '.join(self.stderr))
                    if time.monotonic()>deadline:
                        self._terminate()
                        raise RuntimeError('Coulomb transport deadline exceeded; worker terminated before any late publication')
                    self.condition.wait(.05)
                reply=copy.deepcopy(self.pending[identifier])
            if reply['type']=='error':raise ValueError(reply['message'])
            return reply
        finally:
            with self.condition:self.pending.pop(identifier,None)

    def close(self):
        try:
            if self.process.poll() is None:
                try:self.call('quit')
                finally:
                    self.process.stdin.close()
                    try:self.process.wait(8)
                    except subprocess.TimeoutExpired:self._terminate()
        finally:
            self._terminate()
            self.reader.join(2);self.errors.join(2)
            if not self.process.stdin.closed:self.process.stdin.close()
            self.process.stdout.close();self.process.stderr.close()
