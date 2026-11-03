"""Installed full-window archives and a32-entry catalog, independently of frames."""
from pathlib import Path
import copy
import hashlib
import json
import shutil
import sys
import tempfile
import time
import uuid

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from session import Session
from branch_store import Store
from body_registry import digest

def guard(s):return {'system_id':s.system_id,'edit_token':s.edit_token,'revision':s.revision,'expected_time':s.sim.t,'frame':s.contract()['frame']}
def phase(s):
    p=s.state();return {k:copy.deepcopy(p[k]) for k in ('bodies','time','revision','system_id','edit_token','conservation','instrument_history')}

with tempfile.TemporaryDirectory() as temp:
    s=Session(temp,128)
    for i in range(16):s.configure_instruments({**guard(s),'instruments_revision':s.instruments['revision'],'operation':'create',
        'definition':{'name':'Perfil '+str(i),'mode':'fixed','position_m':[1.7e10+i*1e6,-9e9,3e9]}})
    s.configure_history({**guard(s),'instruments_revision':s.instruments['revision'],'history_revision':s.instrument_history['revision'],'recording':True,'cadence_wall_s':.25})
    for i in range(132):s.sim.integrate((i+1)*.001);s.collect_history(s.state(),10+i*.3)
    assert len(s.instrument_history['samples'])==128 and s.instrument_history['dropped']==4
    s.save();pointer=(Path(temp)/'latest.json').read_bytes();frozen=phase(s)
    timings={}
    began=time.perf_counter();a=s.create_branch({**guard(s),'name':'Máxima A'});timings['create_full_archive_s']=time.perf_counter()-began
    began=time.perf_counter();b=s.create_branch({**guard(s),'name':'Máxima B'});timings['second_full_archive_s']=time.perf_counter()-began
    began=time.perf_counter();result=s.compare_branches({**guard(s),'first_id':a['id'],'second_id':b['id']});timings['compare_two_full_archives_s']=time.perf_counter()-began
    assert phase(s)==frozen and result['first_curves']==result['second_curves']
    old=frozen['edit_token'];began=time.perf_counter();s.load_branch({**guard(s),'branch_id':a['id']});timings['restore_full_archive_s']=time.perf_counter()-began
    after=phase(s);after['edit_token']=old;assert after==frozen
    assert (Path(temp)/'latest.json').read_bytes()==pointer
    store=s._branches();source=store.directory/a['id'].split(':')[1]
    for i in range(30):
        identifier=uuid.uuid4().hex;target=store.directory/identifier;shutil.copytree(source,target)
        record=json.loads((target/'branch.json').read_text());record.update(id='branch:'+identifier,name='Catálogo '+str(i))
        record['record_sha256']=digest({k:v for k,v in record.items() if k!='record_sha256'});(target/'branch.json').write_text(json.dumps(record))
    began=time.perf_counter();s._branch_catalog=Store(store.directory);timings['load32_receipts_s']=time.perf_counter()-began
    size=len(json.dumps(s.state()['branches']).encode());assert len(s._branches().records)==32 and size<20000
    started=time.perf_counter()
    for _ in range(100):s.state()
    timings['mean_confirmed_state_with32_catalog_ms']=(time.perf_counter()-started)*10
    before=phase(s);files_before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in store.directory.rglob('*') if p.is_file()}
    try:s.create_branch({**guard(s),'name':'Trigésimo terceiro'})
    except ValueError:pass
    else:raise AssertionError('Exceeded archive limit')
    assert phase(s)==before and files_before=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in store.directory.rglob('*') if p.is_file()}
    assert all(timings[k]<30 for k in ('create_full_archive_s','second_full_archive_s','compare_two_full_archives_s','restore_full_archive_s'))
    report={'status':'installed3_8_full_archive_and32_catalog_verified','generation':s.state()['scientific_generation']['model_version'],
        'profile':'128 masses/16 probes/128 records; isolated archive operations, not native frames','timings':timings,
        'catalog_payload_bytes':size,'compact_comparison_bytes':len(json.dumps(result).encode()),
        'thirty_third_archive_rejected_before_file_or_phase_mutation':True,'main_checkpoint_pointer_preserved':True,
        'catalog_disk_bytes':sum(p.stat().st_size for p in store.directory.rglob('*') if p.is_file())}
(ROOT/'evidence/branches-stress-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
