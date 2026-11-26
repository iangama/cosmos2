"""Live isolated joint cloud worker: cadence, SI selection, pause, archive and reset."""
from pathlib import Path
import json
import math
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/('app' if '--installed' in sys.argv else 'output/c211-cloud-product/app')
with tempfile.TemporaryDirectory(prefix='cosmos2-cloud-worker-') as folder:
    worker=subprocess.Popen([sys.executable,'-X','utf8','-u',str(SOURCE/'worker.py'),'--storage',folder,
        '--cloud-output',str(Path(folder)/'cloud.bin')],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
        env={**os.environ,'PYTHONPATH':str(SOURCE)})
    events=queue.Queue();serial=0;state=None;sizes=[];cloud_samples=[]
    def read():
        for line in worker.stdout:
            value=json.loads(line)
            if value.get('type')=='snapshot' and value.get('test_particle_cloud') is not None:
                sizes.append(len(line))
                if not value['paused']:cloud_samples.append((time.perf_counter(),value['sequence'],value['compute_ms']))
            events.put(value)
    threading.Thread(target=read,daemon=True).start()
    def command(name,**parameters):
        global serial,state
        serial+=1
        worker.stdin.write(json.dumps({'id':serial,'command':name,**parameters})+'\n');worker.stdin.flush()
        while True:
            response=events.get(timeout=35)
            if response['type']=='snapshot':state=response
            if response.get('id')==serial:
                assert response['type']=='ack',response
                return response
    def guard():
        return {k:state[k] for k in ('system_id','edit_token','revision')}|{'expected_time':state['time'],'frame':state['contract']['frame']}
    try:
        command('snapshot');command('load_cloud_experiment',**guard(),parameters={'count':10000})
        assert state['paused'] and len(state['bodies'])==1 and state['test_particle_cloud']['test_particles']==10000
        cloud=state['test_particle_cloud']['cloud_id'];source=state['bodies'][0]['id']
        command('rate',value=1);began=time.perf_counter();start=state['time'];command('resume')
        time.sleep(2);command('pause');rate=(state['time']-start)/(time.perf_counter()-began)
        assert rate>.9,rate
        live_samples=list(cloud_samples)
        assert state['bodies'][0]['position']==[0.,0.,0.] and state['bodies'][0]['velocity']==[0.,0.,0.]
        ack=command('cloud_point',system_id=state['system_id'],edit_token=state['edit_token'],cloud_id=cloud,index=9999)
        assert ack['result']['source_id']==source and ack['result']['mass_kg']==0. and ack['result']['time_model']==state['time']
        point=ack['result'];theta=(9999*math.pi*(3-math.sqrt(5)))%(2*math.pi)+state['time']/8.
        expected=[4e9*math.cos(theta),4e9*math.sin(theta),0.]
        relative_position_error=math.dist(point['position_m'],expected)/4e9
        assert relative_position_error<2e-10,relative_position_error
        sys.path.insert(0,str(SOURCE))
        import cloud_transport
        metadata,xyz=cloud_transport.decode((Path(folder)/'cloud.bin').read_bytes(),state['system_id'],state['edit_token'],
            cloud,source,state['contract']['frame'],10000,state['cloud_transport']['metadata']['sequence'])
        assert metadata==state['cloud_transport']['metadata'] and xyz[9999].tolist()==point['position_m']
        command('save');saved=json.loads(json.dumps(state));pauses=[]
        for _ in range(20):
            command('resume');time.sleep(.04);began=time.perf_counter();command('pause');pauses.append((time.perf_counter()-began)*1000)
        assert max(pauses)<250,pauses
        command('load');assert state['bodies']==saved['bodies'] and state['time']==saved['time'] and state['conservation']==saved['conservation']
        assert state['test_particle_cloud']['cloud_id']==cloud
        command('restart_seed');assert state['time']==0. and state['test_particle_cloud']['cloud_id']!=cloud
        command('set_cloud',**guard(),parameters=None);assert state['test_particle_cloud'] is None
        command('reset',count=256);assert len(state['bodies'])==256 and state['test_particle_cloud'] is None
        command('load');assert state['test_particle_cloud']['cloud_id']==cloud
        report={'status':'isolated_joint_cloud_worker_verified_not_installed','active_sources':1,'test_particles':10000,
            'measured_rate_requested1':rate,'pause20_max_ms':max(pauses),'individual_SI_selection':True,
            'save_load_exact_source_phase_and_integrals':True,'cloud_restored_after_plain_reset':True,
            'maximum_cloud_snapshot_line_bytes':max(sizes),
            'individual_Kepler_relative_position_error':relative_position_error,
            'live_distinct_sequences':len({x[1] for x in live_samples}),
            'live_compute_max_ms':max(x[2] for x in live_samples),
            'publication_target_hz':30,'scope':'Worker only; native transport/live selection and formal10k profile still pending.'}
        report['live_confirmed_binary_matches_selected_SI_phase']=True
        assert max(sizes)<40000
    finally:
        if worker.poll() is None:command('quit')
        worker.wait(timeout=10)
        errors=worker.stderr.read()
        assert worker.returncode==0 and not errors,{'returncode':worker.returncode,'stderr':errors}
    report['stderr']=errors
    (ROOT/'evidence/cloud-worker-prototype-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)
