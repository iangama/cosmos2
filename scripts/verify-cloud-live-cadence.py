"""Observe confirmed native phases; sampling gives a declared lower-bound cadence."""
from pathlib import Path
import json
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:4700'
def state():return json.load(urllib.request.urlopen(BASE+'/api/state',timeout=5))
def command(name,**data):
    request=urllib.request.Request(BASE+'/api/command',data=json.dumps({'command':name,**data}).encode(),
        headers={'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(request,timeout=65))
initial_mode=state()['mode'];samples=[]
try:
    command('enter');command('rate',value=1);command('resume');time.sleep(1)
    began=time.perf_counter();deadline=began+10;next_sample=began
    while time.perf_counter()<deadline:
        s=state();p=s['physics'];n=(s.get('cloud_view')or{}).get('native')
        assert s['error'] is None and s['engine_connected'] and not p['paused']
        assert p['test_particle_cloud']['test_particles']==10000
        assert n and n['state']=='accepted' and n['gpu_buffer_uploaded']
        m=n['metadata'];assert m['cloud_id']==p['test_particle_cloud']['cloud_id'] and m['count']==10000
        samples.append({'offset_s':time.perf_counter()-began,'worker_time':p['time'],
            'native_time':m['time_model'],'worker_sequence':p['cloud_transport']['metadata']['sequence'],
            'native_sequence':m['sequence'],'native_time_lag_model':p['time']-m['time_model']})
        next_sample+=.025;delay=next_sample-time.perf_counter()
        if delay>0:time.sleep(delay)
    elapsed=samples[-1]['offset_s']-samples[0]['offset_s']
    native=[s['native_sequence'] for s in samples]
    native_times=[s['native_time'] for s in samples]
    assert all(b>=a for a,b in zip(native,native[1:]))
    assert all(b>=a for a,b in zip(native_times,native_times[1:]))
    count=sum(a!=b for a,b in zip(native,native[1:]))
    phase_count=sum(a!=b for a,b in zip(native_times,native_times[1:]))
    rate=(samples[-1]['worker_time']-samples[0]['worker_time'])/elapsed
    assert rate>=.9 and count>=90
    assert max(s['native_time_lag_model'] for s in samples)<=.5
    report={'status':'live_confirmed_10k_cadence_observed','duration_s':elapsed,'samples':samples,
        'requested_observer_hz':40,'observed_distinct_native_confirmations':count,
        'observed_native_confirmation_hz_lower_bound':count/elapsed,
        'observed_distinct_native_phase_hz_lower_bound':phase_count/elapsed,
        'worker_published_sequence_rate_hz':(samples[-1]['worker_sequence']-samples[0]['worker_sequence'])/elapsed,
        'model_time_rate':rate,
        'maximum_observer_gap_s':max(b['offset_s']-a['offset_s'] for a,b in zip(samples,samples[1:])),
        'maximum_native_time_lag_model':max(s['native_time_lag_model'] for s in samples),
        'minimum_native_time_lag_model':min(s['native_time_lag_model'] for s in samples),
        'scope':'40Hz HTTP observer may miss native updates and adds its own load. This is a measured lower bound, not an exact GPU refresh counter or another formal frame profile. Producer30Hz is a target, not a measured guarantee.'}
    (ROOT/'evidence/cloud-live-cadence-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2),flush=True)
finally:
    command('pause')
    if initial_mode=='atlas':command('atlas')
