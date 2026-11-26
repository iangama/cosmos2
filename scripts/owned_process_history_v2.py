"""Retained native identity observer with raw poll timings and no cmdline reads."""
import copy
import ctypes as ct
import hashlib
import json
from pathlib import Path
import time

import owned_process_history as legacy

ROOT=Path(__file__).resolve().parents[1]
FILES=[*legacy.FILES,Path(__file__),ROOT/'C2-14-ORBITAS-PERFIL-REVISAO-C-20261121.md']


class History(legacy.History):
    def __init__(self,session,path):
        super().__init__(session,path)
        self.sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}
        self.poll_path=Path(path).with_name('process-polls.jsonl')
        self.poll_stream=self.poll_path.open('x',encoding='utf8',newline='\n')

    def discover(self,entry,parent=None):
        pid=entry['pid']
        if pid in self.records:
            identity=self.records[pid]['identity']
            assert identity['parent']==entry['parent'] and identity['name']==entry['name'],'Retained PID/name/parent changed'
            self.refresh(pid)
            return identity
        assert len(self.records)<512,'Process history budget exhausted'
        handle=self.kernel.OpenProcess(0x101000,False,pid)
        if not handle:raise ct.WinError(ct.get_last_error())
        self.handles[pid]=handle
        value=self.native(pid)
        size=ct.c_uint32(32768);path=ct.create_unicode_buffer(size.value)
        if not self.kernel.QueryFullProcessImageNameW(handle,0,path,ct.byref(size)):
            self.kernel.CloseHandle(self.handles.pop(pid));raise ct.WinError(ct.get_last_error())
        identity=dict(**entry,created_filetime=value['created_filetime'],
          started_unix=(value['created_filetime']-116444736000000000)/1e7,
          executable=path.value,scope_root=pid in self.roots)
        assert Path(identity['executable']).name.lower()==entry['name'].lower(),'Native image differs from Toolhelp entry'
        if parent is not None:
            if identity['created_filetime']<parent['created_filetime']:
                self.old_parent_links[pid]=dict(identity=identity,parent_created_filetime=parent['created_filetime'])
                self.kernel.CloseHandle(self.handles.pop(pid));return None
            identity['parent_created_filetime']=parent['created_filetime']
        record=dict(identity=identity,first_observed_filetime=value['observed_filetime'],exit=None,last_native=value,
          command_line=None,command_line_policy='Not collected by the high-frequency native observer; host checks root launch arguments separately.')
        self.records[pid]=record
        self.emit('birth',record=copy.deepcopy(record))
        self.refresh(pid)
        return identity

    def step(self):
        started=self.clock();began=time.perf_counter();previous=self.previous_poll
        initial_count=self.polls
        try:return super().step()
        finally:
            finished=self.clock();ended=time.perf_counter()
            row=dict(index=initial_count,started_filetime=started,finished_filetime=finished,
              started_monotonic_s=self.previous_poll,duration_s=ended-self.previous_poll,
              gap_s=None if previous is None else self.previous_poll-previous,
              completed=self.polls==initial_count+1)
            self.poll_stream.write(json.dumps(row,separators=(',',':'),allow_nan=False)+'\n')
            self.poll_stream.flush()

    def snapshot(self):
        result=super().snapshot()
        result['generation']=dict(id='cosmos2:retained-native-history-v2',version='0.2.0',source_sha256=self.sources)
        return result

    def close(self):
        super().close()
        self.poll_stream.close()
