"""Worker orbital capture, original samples, pauses, restore and missing IDs."""
from pathlib import Path
import copy,json,os,queue,subprocess,sys,tempfile,threading,time
ROOT=Path(__file__).resolve().parents[1];INSTALLED='--installed' in sys.argv
SOURCE=ROOT/'app'
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
        command('snapshot');command('reset',count=256)
        assert len(state['bodies'])==256 and state['population_contract']['active_mass_count']==256 and state['population_contract']['all_active_masses_gravitate']
        command('rate',value=1);began=time.perf_counter();start=state['time'];command('resume');time.sleep(1.5);command('pause')
        rate=(state['time']-start)/(time.perf_counter()-began);assert rate>.9,rate
        command('save');frozen=copy.deepcopy(state);pauses=[]
        for _ in range(20):
            command('resume');time.sleep(.04);started=time.perf_counter();command('pause');pauses.append((time.perf_counter()-started)*1000)
        assert max(pauses)<250,pauses
        command('load');assert state['bodies']==frozen['bodies'] and state['time']==frozen['time'] and state['conservation']==frozen['conservation']
        command('restart_seed');assert len(state['bodies'])==256 and state['time']==0.
        report={'status':'installed_256_worker_verified','active_mass_count':256,'measured_rate_requested1':rate,'pause20_max_ms':max(pauses),'save_load_phase_reference_exact':True,'restart_seed_256':True,'scope':'Worker only; native formal256 profile separate'}

    finally:
        if worker.poll() is None:command('quit')
        worker.wait(timeout=5);errors=worker.stderr.read();assert worker.returncode==0 and not errors,{'returncode':worker.returncode,'stderr':errors}
    report['stderr']=errors
    (ROOT/'evidence/p256-worker-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
