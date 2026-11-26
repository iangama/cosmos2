"""Independently audit the fixed nine-window Atlas profile and raw temporal memory."""
import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import traceback

from is6_pair_profile_support import frame_statistics, LIMITS
from gpu_pdh_audit_v3 import audit
from windows_gpu_pdh_v2 import generation

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label',required=True)
    label = parser.parse_args().label
    if not label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label): parser.error('Invalid label')
    source = ROOT / f'evidence/is6-planet-navigation-profile-{label}.json'
    out = ROOT / f'evidence/is6-planet-navigation-profile-audit-{label}.json'
    if out.exists(): raise FileExistsError('Preserve independent profile audit')
    result = dict(accepted=False, completed=False, runs=[], source=source.relative_to(ROOT).as_posix(),
                  source_sha256=sha(source), auditor_sha256=sha(Path(__file__)))
    try:
        r = read(source); plan_path = ROOT / r['plan_path']; plan = read(plan_path)
        assert sha(plan_path) == r['plan_sha256']
        assert plan['candidate'] == '0.24.0' and plan['window_s'] == 60 and plan['warmup_s'] == 30
        assert plan['resolution'] == [1920,1080] and plan['ui_scale'] == '1' and plan['GPU_samples'] == 66
        assert plan['limits_before_execution'] == {k:LIMITS[k] for k in plan['limits_before_execution']}
        assert all(sha(ROOT/name) == seal for name,seal in plan['source_sha256'].items())
        assert sha(ROOT/plan['source_archive']) == plan['source_archive_sha256']
        assert r['completed'] and r['collection_completed'] and not r.get('failure') and not r.get('cleanup_failure')
        assert not r['page_errors'] and r['owner_app_kept_open'] and all(r['protected_unchanged'].values())
        assert len(r['runs']) == len(plan['targets']) == 9
        pre = r['preflight']; assert sha(ROOT/pre['path']) == pre['sha256']
        audit(read(ROOT/pre['path']), expected_samples=3, expected_session=r['session'],
              engine_sha256=r['engine_sha256'], generation=generation())
        ram_peak = gpu_peak = frames = 0
        for index,(target,row) in enumerate(zip(plan['targets'],r['runs'],strict=True),1):
            assert row['target'] == target and row['index'] == index
            assert (dt.datetime.fromisoformat(row['capture_start_utc'])-dt.datetime.fromisoformat(row['warmup_start_utc'])).total_seconds() >= 30
            stats = frame_statistics(row['capture'], row['wall_interval_s'])
            assert not row['trace']['truncated']
            assert len(row['checks']) == 4
            gpu_path = ROOT / row['gpu']['path']; assert sha(gpu_path) == row['gpu']['sha256']
            gpu = read(gpu_path)
            assert gpu['expected_mode'] == 'atlas' and gpu['expected_worker'] == 'any'
            memory = audit(gpu,expected_samples=66,expected_session=r['session'],
                engine_sha256=r['engine_sha256'],generation=generation(),
                coverage=[row['capture_start_utc'],row['capture_end_utc']])['peak_dedicated_plus_shared_bytes']
            assert memory <= LIMITS['GPU_bytes']
            initial = row['initial_navigation']
            for offset,check in zip([0,20,40,60],row['checks'],strict=True):
                assert abs(check['offset_s']-offset)<.5
                nav = check['navigation']
                assert nav['et'] == initial['et'] and nav['paused'] and not nav['flying']
                assert nav['navigation']['Anchor'] == nav['target'] == target
                assert nav['positions'] == initial['positions'] and nav['rotations'] == initial['rotations']
                a,b=nav['navigation']['Position'],initial['navigation']['Position']
                assert max(abs(x-y) for x,y in zip(a,b,strict=True)) <= max(.01,math.sqrt(sum(x*x for x in b))*1e-12)
                assert check['ui'] == dict(scale='1',target=target,mode='atlas',visible='visible',inert=True)
                assert abs(check['display']['exposure']-plan['exposure'])<1e-6 and check['display']['stars'] is True
                ram = check['ram']; total=sum(p['working_set_bytes'] for p in ram['processes'])
                assert total == ram['sum_working_set_bytes'] <= LIMITS['RAM_bytes']
                assert {p['pid'] for p in ram['processes']} == set(gpu['owned_processes'])
                ram_peak=max(ram_peak,total)
            frames += stats['frames']; gpu_peak=max(gpu_peak,memory)
            result['runs'].append(dict(index=index,target=target,**stats,GPU_peak_GiB=memory/2**30))
        assert all(sha(ROOT/name)==seal for name,seal in r['protected_sha256'].items())
        result.update(accepted=True,completed=True,frames=frames,RAM_peak_GiB=ram_peak/2**30,
                      GPU_peak_GiB=gpu_peak/2**30,scope=plan['scope'])
    except Exception:
        result['failure']=traceback.format_exc()
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(dict(accepted=result['accepted'],windows=len(result['runs']),failure=result.get('failure'))))
    return 0 if result['accepted'] else 1


if __name__=='__main__': raise SystemExit(main())
