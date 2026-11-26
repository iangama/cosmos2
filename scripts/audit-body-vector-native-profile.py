"""Recalculate the dedicated four-center native profile from preserved raw data."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import math
import statistics
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def percentile(values, q):
    values = sorted(values)
    index = (len(values)-1)*q
    lo, hi = math.floor(index), math.ceil(index)
    return values[lo]+(values[hi]-values[lo])*(index-lo)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label.')
    source_path = ROOT/('evidence/is3-vector-profile-'+args.label+'.json')
    destination = ROOT/('evidence/is3-vector-profile-audit-'+args.label+'.json')
    if destination.exists():raise FileExistsError('Preserve prior audit.')
    r = json.loads(source_path.read_text(encoding='utf-8'))
    result = {'schema':1,'profile':source_path.relative_to(ROOT).as_posix(),'profile_sha256':sha(source_path),
              'auditor_sha256':sha(Path(__file__)),'accepted':False,'runs':[]}
    try:
        assert r['completed'] and len(r['runs'])==2
        assert r['warmup_s']==30 and r['window_s']==60
        archive = ROOT/r['source_archive']
        assert sha(archive)==r['source_archive_sha256']
        with zipfile.ZipFile(archive) as z:
            assert all(hashlib.sha256(z.read(name)).hexdigest()==value for name,value in r['source_sha256'].items())
        engine = Path(r['session']['runtime'])/'bin/OpenSpace.exe'
        assert sha(engine)==r['engine_sha256']
        limits = r['limits_before_execution']
        assert limits=={'median_ms':16.7,'p95_ms':25.,'p99_ms':50.,'over_100ms':0,'measured_rate_min':.9,'RAM_bytes':8*2**30,'GPU_bytes':5.5*2**30}
        assert r['requested_rate']==.1
        assert [row['model'] for row in r['runs']]==['IGRF14','JRM33']
        ram_peak=gpu_peak=0
        for row in r['runs']:
            values = row['frame_times_s'];capture=row['capture']
            assert capture['width']==1920 and capture['height']==1080
            assert not capture['capacity_reached'] and capture['invalid_samples']==0
            assert all(0<v<1 for v in values)
            assert abs(math.fsum(values)-60)<.5, ('frame_window_seconds',math.fsum(values))
            assert abs(row['wall_interval_s']-60)<.5, ('wall_window_seconds',row['wall_interval_s'])
            intervals=[(row['statistics'],values)]
            for part in row['route_parts']:
                intervals.append((part,values[part['first_frame']:part['end_frame']]))
            for summary,raw in intervals:
                assert len(raw)>100 and summary['frames']==len(raw)
                recomputed={'median_ms':statistics.median(raw)*1000,'p95_ms':percentile(raw,.95)*1000,
                            'p99_ms':percentile(raw,.99)*1000,'over_100ms':sum(v>.1 for v in raw)}
                for key,value in recomputed.items():
                    assert math.isclose(summary[key],value,abs_tol=1e-9),key
                    assert value<=limits[key],(row['run'],key,value)
            frozen=row['frozen_layer'];reading=frozen['reading'];render=frozen['render']
            assert reading['time']==0 and len(render['meshes'])==3 and frozen['native_local_coordinates_confirmed']
            assert reading['provenance']['model'].startswith(row['model'])
            for memory in row['memory']:
                assert memory['layer_id']==render['id']
                v=memory['native_visibility'];assert all(v['flags'].values()) and not v['marker'] and v['anchor']==render['frame_node']
            initial,final=row['initial'],row['final']
            rate=(final['time']-initial['time'])/row['wall_interval_s']/.1
            assert rate>=limits['measured_rate_min'] and math.isclose(rate,row['measured_rate'],abs_tol=1e-12)
            for p in [initial,final,*[m['physics'] for m in row['memory']]]:
                assert [b['reference_id'] for b in p['bodies']]==['sol:naif:10','sol:naif:399','sol:naif:301','sol:naif:599']
                assert not p['paused'] and p['requested_rate']==.1 and p['epsilon']==1e-9
                assert p['atlas_initial']['kind']=='solar_four_physical_centers'
                assert abs(p['energy_error'])<=1e-8
                assert p['conservation']['momentum_error_normalized']<=1e-8
                assert p['conservation']['angular_momentum_error_normalized']<=1e-8
                assert p['atlas_initial']==initial['atlas_initial']
                assert p['system_id']==reading['system_id'] and p['edit_token']==reading['edit_token'] and p['revision']==reading['revision']
            gpu_path=ROOT/row['gpu_report']
            assert sha(gpu_path)==row['gpu_sha256']
            gpu=json.loads(gpu_path.read_text(encoding='utf-8-sig'))
            assert gpu['engine_sha256']==r['engine_sha256'] and gpu['session']['app']==r['session']['app']
            assert gpu['collector_sha256']==r['source_sha256']['scripts/collect-gpu-memory.ps1']
            assert len(gpu['samples'])==66 and not gpu['counter_errors']
            stamps=[dt.datetime.fromisoformat(s['utc'].replace('Z','+00:00')) for s in gpu['samples']]
            assert stamps[0]<=dt.datetime.fromisoformat(row['capture_start_utc'])
            assert stamps[-1]>=dt.datetime.fromisoformat(row['capture_end_utc'])
            assert all(not s['invalid_samples'] and s['scenario']['mode']=='experiment' and not s['scenario']['paused'] and s['scenario']['requested_rate']==.1 for s in gpu['samples'])
            peak=max(s['product_dedicated_sum_bytes'] for s in gpu['samples'])
            assert peak<=limits['GPU_bytes'];gpu_peak=max(gpu_peak,peak)
            for memory in row['memory']:
                resident=memory['ram']['sum_working_set_bytes']
                assert resident<=limits['RAM_bytes'];ram_peak=max(ram_peak,resident)
                physical=[a for a in memory['engine_gpu']['adapters'].values() if a['vendor_id']==4098 and a['status']=='ok']
                assert physical and all(peak<a['budget_bytes'] for a in physical)
            result['runs'].append({'run':row['run'],**row['statistics'],'measured_rate':rate,
                                   'frame_interval_s':math.fsum(values),'GPU_peak_GiB':peak/2**30})
        assert sha(ROOT/'user/sessions/latest.json')==r['owner_pointer_sha256']
        result.update(accepted=True,scope='Two frozen planetary vector views at canonical requested rate.1 only; no live resampling, Lorentz, field lines or inherited J/IS12 acceptance.',RAM_peak_GiB=ram_peak/2**30,GPU_peak_GiB=gpu_peak/2**30)
    except Exception:
        result['failure']=traceback.format_exc()
    destination.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
    return 0 if result['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
