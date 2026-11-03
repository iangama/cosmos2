"""Candidate live worker: bounded cadence, pause, checkpoint and old point lookup."""
from pathlib import Path
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
import psutil

ROOT=Path(__file__).resolve().parents[1]
INSTALLED='--installed' in sys.argv
SOURCE=ROOT/('app' if INSTALLED else 'output/c211-history-staging')
STRESS='--stress' in sys.argv
with tempfile.TemporaryDirectory() as tmp:
    env=dict(os.environ);env['PYTHONPATH']=str(ROOT/'app')
    worker=subprocess.Popen([sys.executable,'-X','utf8','-u',str(SOURCE/'worker.py'),'--storage',tmp],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
    events=queue.Queue();state=None;serial=0;costs=[]
    def reader():
        for line in worker.stdout:events.put(json.loads(line))
    threading.Thread(target=reader,daemon=True).start()
    def message(timeout=15):
        global state
        event=events.get(timeout=timeout)
        if event['type']=='snapshot':
            state=event
            if event['history_evaluation_ms']>.1:costs.append(event['history_evaluation_ms'])
        return event
    def command(name,**parameters):
        global serial
        serial+=1;worker.stdin.write(json.dumps({'command':name,'id':serial,**parameters})+'\n');worker.stdin.flush()
        while True:
            event=message()
            if event.get('id')==serial:
                assert event['type']=='ack',event
                return event
    def guard():
        return {k:state[k] for k in ('system_id','edit_token','revision')}|{'expected_time':state['time'],'frame':state['contract']['frame'],
            'instruments_revision':state['instruments']['revision'],'history_revision':state['instrument_history']['revision']}
    try:
        while state is None:message()
        if STRESS:command('reset',count=128)
        for x in (1.7e10+i*1e6 for i in range(16 if STRESS else 2)):
            command('configure_instruments',**guard(),operation='create',definition={'name':'Histórico','mode':'fixed','position_m':[x,-9e9,3e9]})
        command('configure_history',**guard(),recording=True,cadence_wall_s=.25)
        command('resume');started=time.perf_counter()
        while state['instrument_history']['next_sequence']<(132 if STRESS else 8):message(timeout=5)
        command('pause');paused=json.loads(json.dumps(state));elapsed=time.perf_counter()-started
        rate=paused['time']/elapsed;pauses=[]
        if STRESS:
            for _ in range(20):
                command('resume');time.sleep(.05);began=time.perf_counter();command('pause')
                pauses.append((time.perf_counter()-began)*1000)
            paused=json.loads(json.dumps(state))
        data=command('history_curves',system_id=state['system_id'],edit_token=state['edit_token'])['result']
        assert len(data['samples'])>=8 and all(a['time_s']<b['time_s'] for a,b in zip(data['samples'],data['samples'][1:]))
        assert rate>=(.9 if STRESS else .85)
        if STRESS:
            assert len(data['samples'])==128 and data['dropped']>=4 and max(pauses)<=250
            full=command('history_export',system_id=state['system_id'],edit_token=state['edit_token'])['result']
            assert len(full['samples'])==128 and all(len(r['reading']['readings'])==16 for r in full['samples'])
        sequence=data['samples'][2]['sequence'];point=command('history_point',system_id=state['system_id'],edit_token=state['edit_token'],sequence=sequence)['result']
        assert point['reading']['time']*state['physical_scale']['time_unit_s']==data['samples'][2]['time_s']
        command('save');command('resume');time.sleep(.3);command('pause');command('load')
        assert state['bodies']==paused['bodies'] and state['time']==paused['time']
        restored=command('history_curves',system_id=state['system_id'],edit_token=state['edit_token'])['result']
        assert restored==data
        assert command('history_point',system_id=state['system_id'],edit_token=state['edit_token'],sequence=sequence)['result']==point
        report={'status':'installed_verified' if INSTALLED else 'candidate_worker_verified_not_native_product3_7','samples':len(data['samples']),'cadence_wall_s':.25,
                'confirmed_times_increase':True,'checkpoint_history_and_phase_exact':True,'selected_original_point_exact':True,
                'model_units_per_wall_s':rate,'sample_evaluation_ms_max':max(costs),'warnings':None}
        if STRESS:report.update(profile='isolated_worker_128_masses_16_probes_128_records_not_native_frame_benchmark',
            dropped=data['dropped'],twenty_pause_roundtrip_ms_max=max(pauses),curves_payload_bytes=len(json.dumps(data).encode()),
            full_export_bytes=len(json.dumps(full).encode()),worker_process_tree_working_set_sum_MiB=sum(p.memory_info().rss for p in [psutil.Process(worker.pid),*psutil.Process(worker.pid).children(recursive=True)])/2**20)
    finally:
        if worker.poll() is None:command('quit')
        worker.wait(timeout=5);errors=worker.stderr.read();assert worker.returncode==0,errors
    report['warnings']=errors
    report['generation']=state['scientific_generation']['model_version']
    (ROOT/('evidence/history-worker-stress-check.json' if STRESS else f'evidence/history-worker-installed-{state["scientific_generation"]["model_version"]}-check.json' if INSTALLED else 'evidence/history-worker-prototype-check.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
