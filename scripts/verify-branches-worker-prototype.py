"""Candidate worker fork protocol; real pause guards and restored IAS15 state."""
from pathlib import Path
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/('app' if '--installed' in sys.argv else 'output/c211-branches-staging')
with tempfile.TemporaryDirectory() as temp:
    env=dict(os.environ);env['PYTHONPATH']=str(ROOT/'app')
    worker=subprocess.Popen([sys.executable,'-X','utf8','-u',str(SOURCE/'worker.py'),'--storage',temp],stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
    events=queue.Queue();state=None;serial=0
    def reader():
        for line in worker.stdout:events.put(json.loads(line))
    threading.Thread(target=reader,daemon=True).start()
    def command(operation,allow_error=False,**parameters):
        global state,serial
        serial+=1;worker.stdin.write(json.dumps({'command':operation,'id':serial,**parameters})+'\n');worker.stdin.flush()
        while True:
            event=events.get(timeout=35)
            if event['type']=='snapshot':state=event
            if event.get('id')==serial:
                assert event['type']==('error' if allow_error else 'ack'),event
                return event
    def guard():
        return {k:state[k] for k in ('system_id','edit_token','revision')}|{'expected_time':state['time'],'frame':state['contract']['frame']}
    try:
        command('snapshot');command('save');pointer=(Path(temp)/'latest.json').read_bytes()
        original=json.loads(json.dumps(state));a=command('create_branch',**guard(),name='Base')['result']
        assert len(state['branches']['branches'])==1
        command('set_mass',body=state['bodies'][0]['id'],mass=state['bodies'][0]['mass']*1.01)
        b=command('create_branch',**guard(),name='Alterada')['result']
        assert b['parent_id']==a['id']
        current=json.loads(json.dumps(state));compared=command('compare_branches',**guard(),first_id=a['id'],second_id=b['id'])['result']
        assert compared['same_physical_instant'] and state['bodies']==current['bodies'] and state['time']==current['time']
        command('load_branch',**guard(),branch_id=a['id'])
        assert state['bodies']==original['bodies'] and state['time']==original['time'] and state['conservation']==original['conservation']
        assert state['branches']['active_id']==a['id'] and (Path(temp)/'latest.json').read_bytes()==pointer
        command('resume');command('create_branch',allow_error=True,**guard(),name='Enquanto evolui')
        command('pause');assert len(state['branches']['branches'])==2
        report={'status':'installed_branch_worker_verified' if '--installed' in sys.argv else 'candidate_branch_worker_verified_not_native',
            'fork_and_compare_do_not_replace_active_phase':True,'parent_lineage_and_paused_state_guard':True,
            'restore_phase_reference_and_active_archive_exact':True,'owner_pointer_untouched':True}
    finally:
        if worker.poll() is None:command('quit')
        worker.wait(timeout=5);errors=worker.stderr.read();assert worker.returncode==0 and not errors,errors
    report['stderr']=errors
    (ROOT/('evidence/branches-worker-installed-check.json' if '--installed' in sys.argv else 'evidence/branches-worker-prototype-check.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
