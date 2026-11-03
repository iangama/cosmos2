"""Guarded source editing, visual independence and SI exports in a real EM worker."""
from pathlib import Path
import hashlib
import json
import queue
import subprocess
import sys
import threading
import time
import uuid

ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/c212-em-staging'
owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes()
storage=ROOT/'output/c212-em-worker'/('editor-'+uuid.uuid4().hex)
process=subprocess.Popen([sys.executable,'-u',str(STAGE/'em_worker.py'),'--storage',str(storage)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
messages=queue.Queue();latest=None;serial=0
def reader():
    for line in process.stdout:messages.put(json.loads(line))
    messages.put({'type':'closed'})
threading.Thread(target=reader,daemon=True).start()
def read():
    global latest
    value=messages.get(timeout=10);assert value['type']!='closed'
    if value['type']=='snapshot':latest=value
    return value
def call(name,error=False,**args):
    global serial
    serial+=1;process.stdin.write(json.dumps({'command':name,'id':serial,**args},allow_nan=False)+'\n');process.stdin.flush()
    while True:
        value=read()
        if value.get('id')==serial:
            assert value['type']==('error' if error else 'ack'),value
            return value
def guard():return {k:latest[k] for k in ('system_id','edit_token','revision','frame')}|{'expected_time_s':latest['time_s']}
def physical():return json.dumps({k:latest[k] for k in ('experiment','editor')},sort_keys=True)
rejections=[];cases=[]
try:
    assert read()['type']=='ready'
    while latest is None:read()
    source={'id':'edited-fixed','position_m':[-2,1,.5],'charge_C':1e-9,'exclusion_radius_m':.1,'magnetic_moment_A_m2':[0,0,1e5]}
    old=guard();call('edit',**guard(),edit={'operation':'create_source','source':source})
    assert latest['revision']==1 and latest['editor']['physics_revision']==1
    phase=latest['experiment']['phase']
    for key,value in [('revision',old['revision']),('system_id','other'),('edit_token','other'),('expected_time_s',-.1),('frame','other'),('revision',True)]:
        before=physical();call('edit',error=True,**(guard()|{key:value}),edit={'operation':'remove_source','id':source['id']});assert physical()==before;rejections.append('stale or invalid '+key)
    call('set_visual',**guard(),changes={'selected_id':source['id'],'electric_visible':False,'map_radius_m':4.,'azimuth_rad':.8})
    before=latest['editor']['reference'];count=len(latest['editor']['interventions'])
    call('edit',**guard(),edit={'operation':'update_source','id':source['id'],'changes':{'charge_C':-2e-9,'magnetic_moment_A_m2':[1e5,0,0]}})
    assert latest['experiment']['phase']==phase and len(latest['editor']['interventions'])==count+1
    call('export_sample',**guard(),position_m=[3,2,1]);export=call('export_sample',**guard(),position_m=[3,2,1])['result']
    assert export['experiment']==latest['experiment'] and export['editor']==latest['editor'] and export['revision']==latest['revision'] and export['time_s']==latest['time_s']
    probe=call('probe',**guard(),position_m=[3,2,1])['result'];assert probe==export['sample']
    assert export['particle_force']['valid'] and export['frame']==latest['frame'] and export['sample_units']['electric_field_V_m']=='V/m'
    call('save',**guard(),file='edited');saved=physical();call('advance',**guard(),steps=32);call('load',**guard(),file='edited')
    assert physical()==saved and latest['revision']==2 and latest['editor']['visual']['selected_id']==source['id']
    call('edit',**guard(),edit={'operation':'remove_source','id':source['id']});assert latest['editor']['visual']['selected_id'] is None
    cases.append('create/edit/select/export/save/advance/load/remove source, exact SI sample and persisted revision/history/visual state')
    # Rendering controls may change while integrating; they never pause it,
    # change physical revision, add interventions or reset the reference.
    ref=latest['editor']['reference'];history=latest['editor']['interventions'];rev=latest['revision'];start=latest['time_s']
    call('resume');call('set_visual',**guard(),changes={'electric_visible':True,'magnetic_visible':False})
    assert not latest['paused'] and latest['revision']==rev and latest['editor']['reference']==ref and latest['editor']['interventions']==history
    before_sources=latest['experiment']['model'];call('edit',error=True,**guard(),edit={'operation':'create_source','source':source})
    assert latest['experiment']['model']==before_sources and latest['revision']==rev;rejections.append('physical edit while running')
    deadline=time.monotonic()+5
    while latest['time_s']<=start:
        assert time.monotonic()<deadline;read()
    call('pause');cases.append('visibility during running preserves continued evolution, physics revision, references and history')
    call('load_preset',**guard(),preset='coulomb');b={'id':'third','position_m':[3,2,1],'velocity_m_s':[.1,.2,.3],'charge_C':1e-7,'mass_kg':1.,'exclusion_radius_m':.1}
    call('edit',**guard(),edit={'operation':'create_body','body':b});assert len(latest['experiment']['system']['ids'])==3
    call('edit',**guard(),edit={'operation':'update_body','id':'third','changes':{'mass_kg':2.,'charge_C':-1e-7}})
    value=call('export_sample',**guard(),position_m=[10,0,0])['result'];assert 'particle_force' not in value and value['sample']['valid']
    call('edit',**guard(),edit={'operation':'remove_body','id':'third'});assert len(latest['experiment']['system']['ids'])==2
    before=physical();call('edit',error=True,**guard(),edit={'operation':'update_body','id':'positive','changes':{'mass_kg':0}});assert physical()==before
    rejections.append('invalid mutual mass');cases.append('active charge create/edit/remove with separate model and exported SI fields')
    call('quit');process.wait(timeout=5);assert process.returncode==0
    assert not process.stderr.read();assert owner.read_bytes()==original
    report={'status':'isolated_EM_editor_actual_worker_guarded_transactions_and_exports_verified','cases':cases,
            'refusals_without_physical_mutation':rejections,'clean_exit':True,'owner_pointer_preserved':True,
            'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (STAGE/'em_worker.py',STAGE/'em_editor.py',STAGE/'em_experiment.py',STAGE/'em_migrate.py',Path(__file__))},
            'scope':'Worker IPC and data only. No native UI, scene graph or performance approval.'}
    (ROOT/'evidence/em-editor-worker-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
finally:
    if process.poll() is None:process.terminate();process.wait(timeout=5)
    assert owner.read_bytes()==original
