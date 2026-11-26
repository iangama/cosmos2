"""Check genuine refused input plus explicitly synthetic native counter-lifetime fixtures."""
import copy
from collections import deque
import hashlib
import json
from pathlib import Path

import c214_profile_gpu_v2 as gpu

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out=ROOT/'evidence/c214-profile-gpu-lifetimes-20261114a.json'
    assert not out.exists()
    data=ROOT/'output/c214-orbits-profile-20261114a/memory.jsonl'
    report_path=ROOT/'evidence/c214-orbits-profile-collector-20261114a.json'
    report=json.loads(report_path.read_text())
    with data.open() as stream:
        first=json.loads(next(stream))
        original=json.loads(deque(stream,maxlen=1)[0])
    assert report['valid'] is False
    assert gpu.gpu_row(first,report['session'])==gpu.base.gpu_row(first,report['session'])
    refused=[]

    def refusal(name,row):
        try:gpu.gpu_row(row,report['session'])
        except (ValueError,KeyError,TypeError) as error:refused.append(dict(name=name,error=str(error)))
        else:raise AssertionError('Unexpected admission: '+name)

    refusal('original_A_has_no_final_witness',original)
    # Separate synthetic completion: never alter/reclassify A or claim these are measurements.
    value=copy.deepcopy(original)
    lost=gpu.changes(value)[0]
    pid=gpu.raw_gpu.parse_path(lost[0])['pid']
    initial_tree=copy.deepcopy(value['inventory_after'])
    initial_history=copy.deepcopy(value['native_history'])
    a=initial_tree['finished_filetime']+100_000
    b=a+500_000
    value['counter_transition']=dict(kind='native-counter-lifetime/1',started_filetime=a,finished_filetime=b,
        duration_s=.05,budget_s=.25,initial_inventory=initial_tree,initial_history=initial_history,
        removed_paths=lost,added_paths=[])
    value['inventory_after']['owned']=[row for row in value['inventory_after']['owned'] if row['pid']!=pid]
    value['inventory_after'].update(started_filetime=a+10_000,finished_filetime=b-10_000)
    record=next(r for r in value['native_history']['records'] if r['identity']['pid']==pid)
    record['last_native'].update(wait=0,code=0,observed_filetime=b-20_000)
    record['exit']=dict(code=0,exited_filetime=record['last_native']['exited_filetime'],observed_filetime=b-20_000)
    baseline=gpu.gpu_row(value,report['session'])
    assert gpu.transition(value,report['session'])['removed_pids']==[pid]
    assert baseline['GPU_bytes']==value['product_dedicated_plus_shared_sum_bytes']
    for name,change in [
        ('expired_wait',lambda r:r['counter_transition'].update(duration_s=.251)),
        ('no_witness',lambda r:r.update(counter_transition=None)),
        ('nonzero_exit',lambda r:next(x for x in r['native_history']['records'] if x['identity']['pid']==pid)['exit'].update(code=1)),
        ('unsignaled_exit',lambda r:next(x for x in r['native_history']['records'] if x['identity']['pid']==pid)['last_native'].update(wait=258)),
        ('missing_gauge',lambda r:r['raw_counter_samples'].pop()),
        ('stale_timestamp',lambda r:next(x for x in r['raw_counter_samples'] if f'pid_{pid}_' in x['path']).update(raw_timestamp_filetime=r['query_filetime']-10_000_000)),
        ('gauge_after_exit',lambda r:next(x for x in r['raw_counter_samples'] if f'pid_{pid}_' in x['path']).update(raw_timestamp_filetime=r['query_filetime']+10_000_000)),
        ('still_listed_live',lambda r:r['inventory_after']['owned'].append(copy.deepcopy(next(x for x in r['inventory_before']['owned'] if x['pid']==pid))))]:
        changed=copy.deepcopy(value);change(changed);refusal(name,changed)
    changed=copy.deepcopy(value)
    changed['counter_paths_after'].append(lost[0]);changed['counter_paths_after'].sort()
    changed['counter_transition']['removed_paths']=gpu.changes(changed)[0]
    refusal('half_removed_pair',changed)
    # A child born after the full gauge call has no fabricated sample/bytes.
    born=copy.deepcopy(first)
    new_pid=45454
    root=next(row for row in born['inventory_before']['owned'] if row['pid']==report['session']['app'])
    identity=copy.deepcopy(next(row for row in original['inventory_before']['owned'] if row['pid']==pid))
    birth=max(born['inventory_after']['finished_filetime'],gpu.filetime(born['call_finished_utc']))+100_000
    identity.update(pid=new_pid,parent=root['pid'],parent_created_filetime=root['created_filetime'],
                    created_filetime=birth,started_unix=(birth-116444736000000000)/1e7,scope_root=False)
    born['inventory_after']['owned'].append(identity)
    born['inventory_after'].update(started_filetime=birth+10_000,finished_filetime=birth+50_000)
    new_record=copy.deepcopy(record)
    new_record.update(identity=identity,first_observed_filetime=birth+20_000,exit=None)
    new_record['last_native']=dict(created_filetime=birth,exited_filetime=0,code=259,wait=258,observed_filetime=birth+40_000)
    born['native_history']['records'].append(new_record)
    paths=[f'\\gpu process memory(pid_{new_pid}_luid_0x00000000_0x0000d742_phys_0)\\{kind}' for kind in ['dedicated usage','shared usage']]
    born['counter_paths_after']=sorted(born['counter_paths_after']+paths)
    born['owned_without_exposed_gpu_counter']=sorted(born['owned_without_exposed_gpu_counter']+[new_pid])
    a=birth+60_000;b=birth+100_000
    born['counter_transition']=dict(kind='native-counter-lifetime/1',started_filetime=a,finished_filetime=b,duration_s=.004,budget_s=.25,
        initial_inventory=copy.deepcopy(born['inventory_after']),initial_history=copy.deepcopy(born['native_history']),removed_paths=[],added_paths=sorted(paths))
    born['inventory_after'].update(started_filetime=a+10_000,finished_filetime=b-10_000)
    assert gpu.gpu_row(born,report['session'])['GPU_bytes']==first['product_dedicated_plus_shared_sum_bytes']
    assert gpu.transition(born,report['session'])['added_after_query_pids']==[new_pid]
    changed=copy.deepcopy(born)
    changed['counter_transition']['added_paths']=paths[:1]
    refusal('incomplete_added_witness',changed)
    changed=copy.deepcopy(born)
    changed['inventory_before']['owned'].append(copy.deepcopy(identity))
    refusal('already_existing_context',changed)
    folder=ROOT/'output/c214-profile-gpu-fixtures-20261114a';folder.mkdir()
    for name,row in [('original-refused-row',original),('synthetic-signaled-exit',value),('synthetic-born-after-query',born)]:
        (folder/(name+'.json')).write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),Path(gpu.__file__),report_path,*folder.glob('*.json')]}
    proof=dict(accepted=True,completed=True,groups=3,refusals=refused,source_sha256=sources,
               original_data_sha256=sha(data),scope='Offline admission with actual refused A plus separately labeled synthetic fixtures; A remains refused, no native performance acceptance')
    out.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(accepted=True,refusals=len(refused),groups=3)))


if __name__=='__main__':main()
