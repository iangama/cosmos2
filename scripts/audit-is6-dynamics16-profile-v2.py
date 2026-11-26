"""Independently reconstruct native frame, RAM, rawPDH ownership and clock metrics."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import traceback
import zipfile

import gpu_pdh_audit_dynamics16 as gpu
import windows_gpu_pdh_v2 as pdh
from is6_pair_profile_support import frame_statistics

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);label=parser.parse_args().label
    assert label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label)
    source=ROOT/f'evidence/is6-dynamics16-profile-{label}.json';out=ROOT/f'evidence/is6-dynamics16-profile-audit-v2-{label}.json'
    assert not out.exists(),'Preserve independent audit'
    r=json.loads(source.read_text());answer=dict(accepted=False,profile=source.relative_to(ROOT).as_posix(),profile_sha256=sha(source),auditor_sha256=sha(Path(__file__)),runs=[])
    try:
        assert r['completed'] and len(r['runs'])==4 and not r['page_errors'] and not r.get('failure') and not r.get('cleanup_failure')
        assert r['warmup_s']==30 and r['window_s']==60 and r['owner_app_kept_open']
        assert len(r['processes'])==4 and set(r['processes'].values())=={0}
        assert r['limits_before_execution']==dict(median_ms=16.7,p95_ms=25.,p99_ms=50.,over_100ms=0,RAM_bytes=8*2**30,GPU_bytes=5.5*2**30,measured_rate_min=.9)
        assert all(sha(ROOT/n)==s for n,s in r['source_sha256'].items())
        archive=ROOT/f'output/is6-dynamics16-profile-{label}/executed-sources.zip';assert sha(archive)==r['source_archive_sha256']
        with zipfile.ZipFile(archive) as z:
            assert len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(r['source_sha256'])
            assert all(hashlib.sha256(z.read(n)).hexdigest()==s for n,s in r['source_sha256'].items())
        assert sha(ROOT/'user/sessions/latest.json')==r['owner_sha256']
        assert sha(Path(r['session']['runtime'])/'bin/OpenSpace.exe')==r['engine_sha256']
        prep=r['process_tree_preparation'];count=0;previous=None
        for observation in prep['observations']:
            if 'error' in observation:count=0;previous=None
            else:count=count+1 if observation['owned']==previous else 1;previous=observation['owned']
            assert count==observation['consecutive_stable']
        assert count==prep['consecutive_stable']==5 and 4<=prep['elapsed_s']<45
        expected=[(True,1.,None),(False,.1,None),(False,1.,'sol:naif:399'),(False,10.,'sol:naif:606')]
        maximum_ram=maximum_gpu=frames=0
        for row,recipe in zip(r['runs'],expected,strict=True):
            assert (row['recipe']['paused'],row['recipe']['rate'],row['recipe']['reference_id'])==recipe
            metrics=frame_statistics(row['capture'],row['wall_interval_s'])
            raw=row['capture']['samples_s'];raw=raw if isinstance(raw,list) else [raw[str(i)] for i in range(1,len(raw)+1)]
            metrics['maximum_ms']=max(raw[1:])*1000;frames+=metrics['frames']
            assert row['trace']['truncated'] is False and row['trace']['stats']
            for item in row['trace']['stats'].values():
                assert type(item['count']) in (int,float) and item['count']>0 and math.isfinite(item['count']) and item['count']==int(item['count'])
                assert 0<=item['maximum_s']<=item['total_s'] and math.isfinite(item['total_s'])
            initial=row['initial'];assert len(initial['bodies'])==16 and initial['paused'] and initial['time']==0
            epoch=initial['atlas_initial']['source']['epoch'];assert epoch['et_tdb_s']==r['atlas_epoch']['et_tdb_s']
            a,b=row['phase_at_capture_start'],row['phase_at_capture_end']
            ratio=(b['time']-a['time'])/row['wall_interval_s']/recipe[1]
            if recipe[0]:assert a['time']==b['time']==0
            else:assert ratio>=.9 and b['time']>a['time'] and row['prewarm_phase']['time']>0
            last=-1
            for part,sample in enumerate(row['samples']):
                assert abs(sample['offset_s']-part*20)<.5
                p=sample['physics'];assert p['paused'] is recipe[0] and p['requested_rate']==recipe[1] and p['revision']==0
                assert len(p['bodies'])==16 and p['atlas_initial']==initial['atlas_initial'] and p['scientific_generation']==initial['scientific_generation']
                assert [b['mass'] for b in p['bodies']]==[b['mass'] for b in initial['bodies']]
                assert p['time']>=last;last=p['time']
                if recipe[0]:assert p['time']==0
                assert p['dynamics16']['inertial_frame']['encoding']=='split_inertial_origin'
                assert p['dynamics16']['elapsed_s']==p['time']*p['physical_scale']['time_unit_s']
                assert not p['dynamics16']['electromagnetic_coupling'] and not p['dynamics16']['nuclear_coupling']
                assert sample['native']['camera']['Anchor']==row['expected_anchor']
                assert sample['ui']==dict(scale='1',mode='experiment',hidden=False)
                ram=sample['ram'];assert ram['sum_working_set_bytes']==sum(v['working_set_bytes'] for v in ram['processes'])<=8*2**30
                maximum_ram=max(maximum_ram,ram['sum_working_set_bytes'])
            final=row['final'];assert final['paused'] and final['time']*final['physical_scale']['time_unit_s']<30*86400
            path=ROOT/row['gpu_report'];assert sha(path)==row['gpu_sha256'];report=json.loads(path.read_text())
            assert report['expected_worker']==('paused' if recipe[0] else 'any')
            assert report['scenario_before']['paused'] is recipe[0] and report['scenario_before']['requested_rate']==recipe[1]
            assert report['scenario_before']['revision']==0 and report['scenario_before']['fixture_count'] is None
            gpu_result=gpu.audit(report,expected_samples=66,expected_session=r['session'],engine_sha256=r['engine_sha256'],generation=pdh.generation(),coverage=[row['capture_start_utc'],row['capture_end_utc']])
            peak=gpu_result['peak_dedicated_plus_shared_bytes'];assert peak<=5.5*2**30;maximum_gpu=max(maximum_gpu,peak)
            for sample in row['samples']:assert {p['pid'] for p in sample['ram']['processes']}==set(report['owned_processes'])
            answer['runs'].append(dict(run=row['run'],recipe=row['recipe'],GPU_peak_GiB=peak/2**30,measured_rate_ratio=ratio,final_model_days=final['time']*final['physical_scale']['time_unit_s']/86400,**metrics))
        answer.update(accepted=True,frames=frames,RAM_peak_GiB=maximum_ram/2**30,GPU_peak_GiB=maximum_gpu/2**30)
    except Exception:answer['failure']=traceback.format_exc()
    out.write_text(json.dumps(answer,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(answer,ensure_ascii=False),flush=True)
    return 0 if answer['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
