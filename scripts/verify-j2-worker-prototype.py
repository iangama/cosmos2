"""Process-level J2 with live cadence, pauses, archive restore and domain stop."""
from pathlib import Path
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[1];INSTALLED='--installed' in sys.argv
SOURCE=ROOT/('app' if INSTALLED else 'output/c211-j2-product')
with tempfile.TemporaryDirectory() as temp:
    env=dict(os.environ);env['PYTHONPATH']=str(ROOT/'app')
    worker=subprocess.Popen([sys.executable,'-X','utf8','-u',str(SOURCE/'worker.py'),'--storage',temp],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
    events=queue.Queue();state=None;serial=0
    def reader():
        for line in worker.stdout:events.put(json.loads(line))
    threading.Thread(target=reader,daemon=True).start()
    def command(command_name,**parameters):
        global state,serial
        serial+=1;worker.stdin.write(json.dumps({'command':command_name,'id':serial,**parameters})+'\n');worker.stdin.flush()
        while True:
            event=events.get(timeout=35)
            if event['type']=='snapshot':state=event
            if event.get('id')==serial:
                assert event['type']=='ack',event
                return event
    def guard():return {k:state[k] for k in ('system_id','edit_token','revision')}|{'expected_time':state['time'],'frame':state['contract']['frame']}
    try:
        command('reset',count=2);source=state['bodies'][0]['id'];target=state['bodies'][1]['id']
        command('set_j2',**guard(),body=source,parameters={'j2':.002,'radius_eq_m':1e8,
            'axis':[0.,0.,1.],'provenance':'Ensaio sintético do worker'})
        command('configure_instruments',**guard(),instruments_revision=state['instruments']['revision'],
            operation='create',definition={'name':'Ao vivo J2','mode':'fixed','position_m':[1.7e10,-9e9,3e9]})
        command('configure_history',**guard(),instruments_revision=state['instruments']['revision'],
            history_revision=state['instrument_history']['revision'],recording=True,cadence_wall_s=.25)
        start=state['time'];began=time.perf_counter();command('resume');time.sleep(1.5);command('pause')
        rate=(state['time']-start)/(time.perf_counter()-began)
        assert state['time']>1.2 and state['instrument_history']['sample_count']>=4 and rate>.8,(rate,state)
        assert state['energy_error']<1e-10 and state['conservation']['angular_momentum_error_normalized'] is None
        history=command('history_export',system_id=state['system_id'],edit_token=state['edit_token'])['result']
        assert all(any('j2' in source for source in row['reading']['source_snapshot_si']) for row in history['samples'])
        command('save');pointer=(Path(temp)/'latest.json').read_bytes()
        base=json.loads(json.dumps(state));archive=command('create_branch',**guard(),name='J2 confirmado')['result']
        pauses=[]
        for _ in range(20):
            command('resume');time.sleep(.04);began=time.perf_counter();command('pause');pauses.append((time.perf_counter()-began)*1000)
        assert max(pauses)<250
        command('load_branch',**guard(),branch_id=archive['id'])
        assert state['bodies']==base['bodies'] and state['time']==base['time'] and state['gravity_effects']==base['gravity_effects']
        assert state['conservation']==base['conservation'] and state['instrument_history']==base['instrument_history']
        assert (Path(temp)/'latest.json').read_bytes()==pointer
        # An inward initial state is valid; the first trial enters the exterior
        # boundary and must pause without committing that invalid trial phase.
        command('reset',count=2);source,target=[b['id'] for b in state['bodies']]
        unit=state['physical_scale']['mass_unit_kg'];velocity=state['physical_scale']['velocity_unit_m_s']
        command('set_body',**guard(),body=target,mass_kg=1e-4*unit,position_m=[1.3e8,0.,0.],velocity_m_s=[-3*velocity,0.,0.])
        command('set_j2',**guard(),body=source,parameters={'j2':.002,'radius_eq_m':1e8,
            'axis':[0.,0.,1.],'provenance':'Ensaio exterior de queda radial'})
        confirmed=json.loads(json.dumps(state));command('resume')
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            event=events.get(timeout=3)
            if event['type']=='snapshot':
                state=event
                if state['paused'] and state['integration_notice']:break
        else:raise AssertionError('Exterior boundary did not pause worker')
        assert state['bodies']==confirmed['bodies'] and state['time']==confirmed['time'] and 'J2' in state['integration_notice']
        report={'status':'installed_J2_worker_verified' if INSTALLED else 'candidate_J2_worker_verified_not_installed',
                'live_history_samples':len(history['samples']),'measured_canonical_rate':rate,'pause20_wall_max_ms':max(pauses),
                'archive_phase_model_history_reference_exact':True,'main_pointer_untouched_by_archive':True,
                'interior_trial_pauses_with_last_confirmed_phase':True}
    finally:
        if worker.poll() is None:command('quit')
        worker.wait(timeout=5);errors=worker.stderr.read();assert worker.returncode==0 and not errors,{'returncode':worker.returncode,'stderr':errors}
    report['stderr']=errors
    (ROOT/('evidence/j2-worker-installed-check.json' if INSTALLED else 'evidence/j2-worker-prototype-check.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
