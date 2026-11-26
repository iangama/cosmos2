"""Material worker process: confirmed cadence, pause, archives and safe domain."""
from pathlib import Path
import copy,json,math,os,queue,subprocess,sys,tempfile,threading,time
ROOT=Path(__file__).resolve().parents[1];INSTALLED='--installed' in sys.argv
SOURCE=ROOT/('app' if INSTALLED else 'output/c211-tides-product/app')
with tempfile.TemporaryDirectory(prefix='cosmos2-tides-worker-') as temp:
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
            event=events.get(timeout=35)
            if event['type']=='snapshot':state=event
            if event.get('id')==serial:
                assert event['type']=='ack',event
                return event
    def guard():return {k:state[k] for k in ('system_id','edit_token','revision')}|{'expected_time':state['time'],'frame':state['contract']['frame']}
    def system(fall=False):
        command('pause');command('snapshot')
        n=math.sqrt(6.6743e-11*2e25/1e24);v=.5*math.sqrt(1.5)*1e8*n
        command('new_system',**guard(),name='Material sintético',mass_kg=1e25,position_m=[-4e7,0.,0.],velocity_m_s=[0.,-v if not fall else 0.,0.])
        source=state['bodies'][0]['id']
        command('create_body',**guard(),name='Companheiro pontual',mass_kg=1e25,position_m=[4e7,0.,0.],velocity_m_s=[-2e6 if fall else 0.,v if not fall else 0.,0.])
        companion=state['bodies'][1]['id']
        command('set_tides',**guard(),body=source,parameters={'radius_m':1e7,'love_k2':.3,'time_lag_s':0. if fall else .003/n,'inertia_kg_m2':.33*1e25*1e14,'spin_rad_s':[0.,0.,0.] if fall else [.25*n,.1*n,1.4*n],'provenance':'Synthetic worker material test, not observed interior'})
        return source,companion
    try:
        command('snapshot');source,companion=system()
        command('configure_instruments',**guard(),instruments_revision=state['instruments']['revision'],operation='create',definition={'name':'Maré ao vivo','mode':'follow','body_id':companion,'offset_m':[0.,0.,0.],'exclude_followed_source':True})
        command('configure_history',**guard(),instruments_revision=state['instruments']['revision'],history_revision=state['instrument_history']['revision'],recording=True,cadence_wall_s=.25)
        start=state['time'];began=time.perf_counter();command('resume');time.sleep(1.5);command('pause')
        rate=(state['time']-start)/(time.perf_counter()-began)
        assert rate>.8 and state['instrument_history']['sample_count']>=4,(rate,state)
        assert state['energy_error']<1e-9 and state['conservation']['angular_momentum_error_normalized']<1e-9
        assert state['material_tides']['dissipated_heat_J']>0.
        history=command('history_export',system_id=state['system_id'],edit_token=state['edit_token'])['result']
        assert all(any('tide' in s for s in row['reading']['source_snapshot_si']) for row in history['samples'])
        command('save');pointer=(Path(temp)/'latest.json').read_bytes()
        base=copy.deepcopy(state);archive=command('create_branch',**guard(),name='Maré confirmada')['result']
        pauses=[]
        for _ in range(20):
            command('resume');time.sleep(.04);began=time.perf_counter();command('pause');pauses.append((time.perf_counter()-began)*1000)
        assert max(pauses)<250,pauses
        command('load_branch',**guard(),branch_id=archive['id'])
        assert state['bodies']==base['bodies'] and state['material_tides']==base['material_tides'] and state['conservation']==base['conservation'] and state['time']==base['time']
        assert state['instrument_history']==base['instrument_history'] and (Path(temp)/'latest.json').read_bytes()==pointer
        source,companion=system(True);confirmed=copy.deepcopy(state);command('resume')
        deadline=time.monotonic()+4
        while time.monotonic()<deadline:
            event=events.get(timeout=4)
            if event['type']=='snapshot':
                state=event
                if state['paused'] and state['integration_notice']:break
        else:raise AssertionError('Material domain did not pause worker')
        assert state['bodies']==confirmed['bodies'] and state['time']==confirmed['time'] and state['material_tides']==confirmed['material_tides'],state
        report={'status':'installed_material_worker_verified' if INSTALLED else 'candidate_material_worker_verified_not_installed','live_history_samples':len(history['samples']),'measured_canonical_rate':rate,'pause20_wall_max_ms':max(pauses),'archive_phase_spin_heat_history_reference_exact':True,'main_pointer_untouched_by_archive':True,'domain_trial_pauses_with_last_confirmed_phase':True}
    finally:
        if worker.poll() is None:command('quit')
        worker.wait(timeout=5);errors=worker.stderr.read();assert worker.returncode==0 and not errors,{'returncode':worker.returncode,'stderr':errors}
    report['stderr']=errors
    (ROOT/('evidence/tides-worker-installed-check.json' if INSTALLED else 'evidence/tides-worker-prototype-check.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
