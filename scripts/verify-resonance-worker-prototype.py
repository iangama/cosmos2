"""Worker orbital capture, original samples, pauses, restore and missing IDs."""
from pathlib import Path
import copy,json,os,queue,subprocess,sys,tempfile,threading,time
ROOT=Path(__file__).resolve().parents[1];INSTALLED='--installed' in sys.argv
SOURCE=ROOT/('app' if INSTALLED else 'output/c211-resonances-product/app')
with tempfile.TemporaryDirectory(prefix='cosmos2-orbital-worker-') as temp:
    env=dict(os.environ);env['PYTHONPATH']=str(SOURCE)
    worker=subprocess.Popen([sys.executable,'-X','utf8','-u',str(SOURCE/'worker.py'),'--storage',temp],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
    events=queue.Queue();state=None;serial=0
    def reader():
        for line in worker.stdout:events.put(json.loads(line))
    threading.Thread(target=reader,daemon=True).start()
    def command(command_name,**parameters):
        global state,serial
        serial+=1;worker.stdin.write(json.dumps({'command':command_name,'id':serial,**parameters})+'\n');worker.stdin.flush()
        while True:
            value=events.get(timeout=35)
            if value['type']=='snapshot':state=value
            if value.get('id')==serial:
                assert value['type']=='ack',value
                return value
    def identity():return {k:state[k] for k in ('system_id','edit_token','revision')}|{'expected_time':state['time'],'frame':state['contract']['frame'],'orbital_revision':state['orbital_instruments']['revision']}
    try:
        command('snapshot');command('load_resonant_experiment',**identity(),preset='resonant2')
        assert len(state['bodies'])==3 and state['revision']==0 and not state['interventions']
        removed=state['orbital_instruments']['definition']['outer_id']
        before=copy.deepcopy(state)
        reading=command('sample_orbital_instruments',**identity())['result'];assert reading['available']
        assert state['bodies']==before['bodies'] and state['conservation']==before['conservation']
        command('configure_orbital_instruments',**identity(),operation='capture',recording=True,cadence_wall_s=.25)
        command('rate',value=10);began=time.perf_counter();start=state['time'];command('resume');time.sleep(1.5);command('pause')
        rate=(state['time']-start)/(time.perf_counter()-began)
        assert state['orbital_instruments']['sample_count']>=4 and rate>8.,(rate,state)
        curves=command('orbital_curves',system_id=state['system_id'],edit_token=state['edit_token'])['result']
        assert all(row['available'] for row in curves['samples'])
        point=command('orbital_point',system_id=state['system_id'],edit_token=state['edit_token'],sequence=curves['samples'][0]['sequence'])['result']
        assert point['reading']['time']==curves['samples'][0]['time']
        command('save');pointer=(Path(temp)/'latest.json').read_bytes();frozen=copy.deepcopy(state)
        branch=command('create_branch',**identity(),name='Ângulos confirmados')['result']
        pauses=[]
        for _ in range(20):
            command('resume');time.sleep(.04);started=time.perf_counter();command('pause');pauses.append((time.perf_counter()-started)*1000)
        assert max(pauses)<250,pauses
        command('load_branch',**identity(),branch_id=branch['id'])
        assert state['bodies']==frozen['bodies'] and state['time']==frozen['time'] and state['conservation']==frozen['conservation'] and state['orbital_instruments']==frozen['orbital_instruments']
        assert (Path(temp)/'latest.json').read_bytes()==pointer
        command('remove_body',**identity(),body=removed);command('resume');time.sleep(.35);command('pause')
        assert not state['orbital_instruments']['latest']['available']
        assert state['orbital_instruments']['definition']['outer_id']==removed
        command('save');command('load');assert not state['orbital_instruments']['latest']['available']
        command('restart_seed');assert len(state['bodies'])==3 and state['time']==0 and state['orbital_instruments']['sample_count']==0
        report={'status':'installed_orbital_worker_verified' if INSTALLED else 'candidate_orbital_worker_verified_not_installed','live_samples':len(curves['samples']),'measured_rate_requested10':rate,'pause20_max_ms':max(pauses),'sample_query_preserves_phase_and_reference':True,'archive_phase_reference_history_exact':True,'main_pointer_preserved_by_archive':True,'removed_identity_remains_unavailable':True,'restart_restores_synthetic_seed_and_clears_capture':True}
    finally:
        if worker.poll() is None:command('quit')
        worker.wait(timeout=5);errors=worker.stderr.read();assert worker.returncode==0 and not errors,{'returncode':worker.returncode,'stderr':errors}
    report['stderr']=errors
    (ROOT/('evidence/resonance-worker-installed-check.json' if INSTALLED else 'evidence/resonance-worker-prototype-check.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
