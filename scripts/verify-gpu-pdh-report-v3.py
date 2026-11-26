"""Independent native-PDH receipt, tampering and fresh-interpreter admission."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import subprocess
import sys
import traceback
import windows_gpu_pdh_v2 as pdh
import gpu_pdh_audit_v3 as audit
import owned_process_snapshot as ownership

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def read(path):
    def unique(pairs):
        result = {}
        for key,value in pairs:
            if key in result:
                raise ValueError('Duplicate GPU receipt JSON key')
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8-sig'),object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite GPU receipt JSON')))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label',required=True)
    parser.add_argument('--input',default='evidence/gpu-pdh-20261105b.json')
    parser.add_argument('--reopen',action='store_true')
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    source = (ROOT / args.input).resolve()
    if not source.is_relative_to(ROOT / 'evidence'):
        raise ValueError('Owned GPU receipt required')
    original = read(source)
    expected_session = read(ROOT / 'output/session.json')
    engine_sha = sha(ROOT / '.runtime-is4-stream/bin/OpenSpace.exe')
    generation = pdh.generation()
    def checked(value):
        return audit.audit(value,expected_samples=3,expected_session=expected_session,
                           engine_sha256=engine_sha,generation=generation)
    assert all(sha(ROOT / name) == seal for name,seal in original['source_sha256'].items())
    assert original['ownership_generation'] == ownership.generation()
    summary = checked(original)
    if args.reopen:
        print(json.dumps(summary))
        return 0
    out = ROOT / ('evidence/gpu-pdh-preflight-' + args.label + '.json')
    if out.exists():
        raise FileExistsError('Preserve native PDH preflight')
    sources = dict(original['source_sha256'])
    for path in [Path(__file__),source]:
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
    result = dict(accepted=False,completed=False,source_sha256=sources,native_report=source.relative_to(ROOT).as_posix(),
        native_report_sha256=sha(source),summary=summary,refusals=[],
        owner_sha256=sha(ROOT / 'user/sessions/latest.json'),
        scope='Real native PDH byte-gauge preflight in its declared scenario and independent receipt audit. No frame/resource budget acceptance, experiment sampling or product promotion.')
    def first(value):
        return value['samples'][0]['raw_counter_samples'][0]
    def refuse(name,edit):
        value = copy.deepcopy(original)
        edit(value)
        try:
            checked(value)
        except (ValueError,TypeError,KeyError,OverflowError) as error:
            result['refusals'].append(dict(case=name,error=str(error)))
        else:
            raise AssertionError('Invalid PDH report accepted: '+name)
    try:
        cases = [
            ('Unverified ownership method',lambda v:v.update(ownership_method='PPID only')),
            ('Invalid native creation time',lambda v:v['inventory_before'][0].update(created_filetime=0)),
            ('Wrong schema',lambda v:v.update(schema=3)),
            ('Boolean schema',lambda v:v.update(schema=True)),
            ('Refused native capture',lambda v:v.update(valid=False)),
            ('Native failure hidden',lambda v:v.update(failure='Failure')),
            ('Different session',lambda v:v['session'].update(app=1)),
            ('Different executable',lambda v:v.update(engine_sha256='0'*64)),
            ('Different source generation',lambda v:v['generation'].update(version='9.9.9')),
            ('Native API failure',lambda v:first(v).update(raw_api_status=5)),
            ('Formatted API failure',lambda v:first(v).update(formatted_api_status=5)),
            ('Invalid raw CStatus',lambda v:first(v).update(raw_status=0x800007D1)),
            ('Invalid formatted CStatus',lambda v:first(v).update(formatted_status=2)),
            ('Wrong raw type',lambda v:first(v).update(raw_type=0)),
            ('Wrong formatted type',lambda v:first(v).update(formatted_type=0)),
            ('Applied counter scaling',lambda v:first(v).update(format=0x400)),
            ('Negative bytes',lambda v:first(v).update(raw_first_value=-1)),
            ('Boolean bytes',lambda v:first(v).update(formatted_bytes=True)),
            ('Raw/formatted mismatch',lambda v:first(v).update(formatted_bytes=first(v)['formatted_bytes']+1)),
            ('Omitted selected counter',lambda v:v['samples'][0]['raw_counter_samples'].pop()),
            ('Duplicated selected counter',lambda v:v['samples'][0]['raw_counter_samples'].append(copy.deepcopy(first(v)))),
            ('Changed instance inventory',lambda v:v['counter_paths_after'].pop()),
            ('Duplicate owned identity',lambda v:v['owned_processes'].append(v['owned_processes'][0])),
            ('Reused process identity',lambda v:v['inventory_after'][0].update(started_unix=v['inventory_after'][0]['started_unix']+1)),
            ('Zero assigned to unexposed identity',lambda v:v['owned_without_exposed_gpu_counter'].pop()),
            ('Omitted GPU identity',lambda v:v['owned_gpu_processes'].pop()),
            ('GPU sum changed',lambda v:v['samples'][0].update(product_dedicated_plus_shared_sum_bytes=0)),
            ('Projected bytes changed',lambda v:v['samples'][0]['products'][0].update(bytes=original['samples'][0]['products'][0]['bytes']+1)),
            ('Counter metadata identity changed',lambda v:next(iter(v['counter_metadata'].values())).update(instance='wrong')),
            ('Sample loss',lambda v:v['samples'].pop()),
            ('Scenario changed',lambda v:v['samples'][1]['scenario'].update(mode='atlas' if original['expected_mode']=='experiment' else 'experiment')),
            ('Final worker changed',lambda v:v['scenario_after'].update(paused=not original['scenario_after']['paused'])),
            ('NaN sampling offset',lambda v:v['samples'][0].update(monotonic_offset_s=float('nan'))),
            ('Infinite sampling offset',lambda v:v['samples'][0].update(monotonic_offset_s=float('inf'))),
            ('Dropped sampling interval',lambda v:v['samples'][1].update(monotonic_offset_s=99.)),
            ('Missing native time basis',lambda v:v['samples'][0].pop('time_basis')),
            ('Local timestamp relabelled UTC',lambda v:v['samples'][0].update(query_utc_filetime=v['samples'][0]['query_filetime'])),
            ('Timezone offset invented',lambda v:v['samples'][0].update(local_to_utc_seconds=0.)),
        ]
        for label,edit in cases:
            refuse(label,edit)
        # NEW_DATA is documented successful data, not an error to normalize.
        changed = copy.deepcopy(original)
        for sample in changed['samples']:
            for row in sample['raw_counter_samples']:
                row.update(raw_status=1,formatted_status=1)
        assert checked(changed) == summary
        fresh = subprocess.run([sys.executable,'-Xutf8',str(Path(__file__)),'--label',args.label,
            '--input',str(source),'--reopen'],capture_output=True,text=True,encoding='utf8',timeout=90,check=True)
        assert json.loads(fresh.stdout) == summary
        assert all(sha(ROOT / name) == seal for name,seal in sources.items())
        assert sha(ROOT / 'user/sessions/latest.json') == result['owner_sha256']
        result.update(accepted=True,completed=True,fresh_interpreter=json.loads(fresh.stdout),
                      documented_NEW_DATA_status_preserved=True)
    except Exception:
        result['failure'] = traceback.format_exc()
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(dict(accepted=result['accepted'],refusals=len(result['refusals']),failure=result.get('failure'))))
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
