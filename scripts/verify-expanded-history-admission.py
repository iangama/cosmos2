"""Offline identity/clock/membership refusals for schema6; preserved GPU bytes are fixtures."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import traceback
import zipfile

import expanded_residency_contract_v3 as c
import expanded_residency_history_audit as history_audit

ROOT = Path(__file__).resolve().parents[1]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and all(ch in 'abcdefghijklmnopqrstuvwxyz0123456789-' for ch in args.label)
    folder = ROOT / f'output/is6-expanded-history-offline-{args.label}'
    out = ROOT / f'evidence/is6-expanded-history-offline-{args.label}.json'
    assert not folder.exists() and not out.exists()
    source_names = ['scripts/verify-expanded-history-admission.py', 'scripts/owned_process_history.py',
                    'scripts/expanded_residency_history_audit.py', 'scripts/expanded_residency_contract_v3.py',
                    'scripts/collect_expanded_residency_v4.py', 'scripts/expanded_residency_audit_v3.py',
                    'scripts/profile-expanded-residency-v3.py', 'scripts/audit-expanded-residency-v3.py',
                    'scripts/run-expanded-residency-v3.py', 'IS-6-PERCURSO-AMPLIADO16-RESIDENCIA-REVISAO-D.md',
                    'IS-6-PERCURSO-AMPLIADO16-RESIDENCIA-OBSERVADOR-LIMITES.md',
                    'evidence/is6-owned-history-fixture-20261113a.json', 'evidence/is6-expanded-residency-audit-offline-20261113b.json',
                    'evidence/is6-dynamics16-profile-20261112a.json', 'evidence/gpu-pdh-is6d16-20261112a-1.json']
    sources = {name:sha(ROOT / name) for name in source_names}
    folder.mkdir()
    with zipfile.ZipFile(folder / 'executed-sources.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for name in sources:
            archive.write(ROOT / name, name)
    answer = dict(accepted=False, completed=False, source_sha256=sources, checks=[], refusals=[],
                  scope='Offline admission of native lifetime evidence with preserved raw GPU/RAM fixtures; no new performance measurement.')

    def refuse(name, value):
        try:
            c.gpu_row(value, gpu['session'])
        except (ValueError, KeyError, TypeError, AssertionError) as error:
            answer['refusals'].append(dict(name=name, error=str(error)))
        else:
            raise AssertionError('Invalid fixture accepted: '+name)

    try:
        native = json.loads((ROOT / source_names[-4]).read_text())
        assert native['accepted'] and native['completed']
        profile = json.loads((ROOT / source_names[-2]).read_text())
        gpu = json.loads((ROOT / source_names[-1]).read_text())
        row = copy.deepcopy(gpu['samples'][0])
        q = row['query_utc_filetime']
        before = dict(owned=copy.deepcopy(gpu['inventory_before']), excluded_completed=[], excluded_old_parent_links=[],
                      started_filetime=q-500000, finished_filetime=q-400000)
        after = copy.deepcopy(before); after.update(started_filetime=q+400000, finished_filetime=q+500000)
        ram = copy.deepcopy(profile['runs'][0]['samples'][0]['ram'])
        for entry in ram['processes']:
            entry.update(read_started_filetime=q-300000, read_finished_filetime=q-200000)
        known = []
        for identity in before['owned']:
            first = q-10000000
            known.append(dict(identity=identity, first_observed_filetime=first, exit=None,
                              last_native=dict(created_filetime=identity['created_filetime'], exited_filetime=0,
                                               wait=258, code=259, observed_filetime=q+450000)))
        row.update(inventory_before=before, inventory_after=after, native_history=dict(records=known), ram=ram,
                   configured_counter_paths=gpu['configured_counter_paths'], counter_paths_after=gpu['counter_paths_after'],
                   counter_metadata=gpu['counter_metadata'], owned_without_exposed_gpu_counter=gpu['owned_without_exposed_gpu_counter'])
        c.gpu_row(row, gpu['session'])
        answer['checks'].append('Preserved raw GPU/RAM values admitted with temporally matched retained identities')
        parent = next(entry for entry in before['owned'] if entry['pid']==gpu['session']['app'])
        new_pid = max(entry['pid'] for entry in before['owned'])+1000
        child = dict(pid=new_pid, parent=parent['pid'], name='OpenSpace_Helper.exe', executable='C:\\fixture\\OpenSpace_Helper.exe',
                     created_filetime=q+100000, started_unix=(q+100000-116444736000000000)/1e7,
                     scope_root=False, parent_created_filetime=parent['created_filetime'])
        born = copy.deepcopy(row)
        born['inventory_after']['owned'].append(child)
        born['native_history']['records'].append(dict(identity=child, first_observed_filetime=q+200000, exit=None,
                       last_native=dict(created_filetime=q+100000, exited_filetime=0, wait=258, code=259, observed_filetime=q+450000)))
        born['owned_without_exposed_gpu_counter'].append(new_pid)
        c.gpu_row(born, gpu['session'])
        answer['checks'].append('Native-proven late birth admitted; unexposed GPU remains explicit, without an invented zero')
        retired = copy.deepcopy(born)
        retired['inventory_after']['owned'] = [entry for entry in retired['inventory_after']['owned'] if entry['pid']!=new_pid]
        child_old = retired['native_history']['records'][-1]
        child_old['identity']['created_filetime'] = q-10000000
        child_old['identity']['started_unix'] = (q-10000000-116444736000000000)/1e7
        child_old.update(first_observed_filetime=q-9000000, exit=dict(code=0,exited_filetime=q+200000,observed_filetime=q+450000),
                         last_native=dict(created_filetime=q-10000000,exited_filetime=q+200000,wait=0,code=0,observed_filetime=q+450000))
        retired['inventory_before']['owned'].append(copy.deepcopy(child_old['identity']))
        retired['ram']['processes'].append(dict(pid=new_pid,created_filetime=q-10000000,working_set_bytes=1024,private_bytes=512,
                                               read_started_filetime=q-300000,read_finished_filetime=q-200000))
        retired['ram']['sum_working_set_bytes'] += 1024
        c.gpu_row(retired, gpu['session'])
        answer['checks'].append('Exit after a real RAM reading admitted with exact native time and code0')
        bad=copy.deepcopy(retired);bad['native_history']['records'][-1]['exit']['code']=7;refuse('nonzero-exit',bad)
        bad=copy.deepcopy(retired);bad['native_history']['records'][-1]['last_native']['wait']=258;refuse('exit-not-signaled',bad)
        bad=copy.deepcopy(retired);bad['native_history']['records'][-1]['exit']['exited_filetime']=0;refuse('zero-exit-FILETIME',bad)
        bad=copy.deepcopy(retired);bad['ram']['processes'][-1]['read_started_filetime']=q+300000;bad['ram']['processes'][-1]['read_finished_filetime']=q+350000;refuse('RAM-after-native-exit',bad)
        bad=copy.deepcopy(born);bad['native_history']['records'].pop();refuse('unknown-sampled-child',bad)
        bad=copy.deepcopy(born);bad['native_history']['records'][-1]['last_native']['created_filetime']+=1;refuse('retained-PID-identity-changed',bad)
        bad=copy.deepcopy(born);bad['native_history']['records'][-1]['identity']['created_filetime']=q-1000000;bad['native_history']['records'][-1]['identity']['started_unix']=(q-1000000-116444736000000000)/1e7;bad['native_history']['records'][-1]['last_native']['created_filetime']=q-1000000;refuse('late-old-process-reappeared',bad)
        bad=copy.deepcopy(row);bad['counter_paths_after']=[];refuse('paths-changed-within-query',bad)
        bad=copy.deepcopy(born);bad['owned_without_exposed_gpu_counter'].remove(new_pid);refuse('unexposed-child-silently-omitted',bad)
        assert all(sha(ROOT / name)==seal for name,seal in sources.items())
        answer.update(accepted=True, completed=True)
    except Exception:
        answer['failure']=traceback.format_exc()
    out.write_text(json.dumps(answer,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({key:value for key,value in answer.items() if key!='source_sha256'},ensure_ascii=False),flush=True)
    return 0 if answer['accepted'] else 1


if __name__=='__main__':
    raise SystemExit(main())
