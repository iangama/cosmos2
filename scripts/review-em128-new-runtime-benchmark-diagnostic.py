"""Independent stdlib audit of frozen EM128 frames, resources and mechanics."""
from pathlib import Path
from datetime import datetime
import hashlib
import itertools
import json
import math
import statistics
import sys
import tarfile

ROOT=Path(__file__).resolve().parents[1];label=sys.argv[1]
assert 1<=len(label)<=18 and all(c.isalnum() or c in '_-' for c in label)
source=ROOT/f'evidence/native-em128-{label}.json';r=json.loads(source.read_bytes())
result={'benchmark':str(source.relative_to(ROOT)),'benchmark_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'audit_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'accepted':False,'scope':'This fixed128-charge native profile only; no10k EM, planetary fields, GR mesh or wholeC2-12 acceptance. Frozen source validation, independently recomputed frames and mechanical sums; does not independently calibrate Windows hardware counters.'}
def percentile(values,q):
    v=sorted(values);x=(len(v)-1)*q;a=math.floor(x);b=math.ceil(x)
    return v[a]+(v[b]-v[a])*(x-a)
def stats(v):
    return {'frames':len(v),'median_ms':statistics.median(v)*1000,'p95_ms':percentile(v,.95)*1000,'p99_ms':percentile(v,.99)*1000,'over100ms':sum(x>.1 for x in v)}
def validate_frames(v,context):
    assert v and all(math.isfinite(x) and x>0 for x in v)
    s=stats(v)
    for key,limit in (('median_ms',16.7),('p95_ms',25),('p99_ms',50),('over100ms',0)):
        if s[key]>limit:criteria_failures.append({'context':context,'criterion':key+' <= '+str(limit),'observed':s[key]})
    return s
def mechanics(p):
    xs=p['phase']['position_m'];vs=p['phase']['velocity_m_s'];ms=p['system']['mass_kg'];qs=p['system']['charge_C']
    k=sum(.5*m*math.fsum(c*c for c in v) for m,v in zip(ms,vs))
    u=math.fsum(ke*qs[a]*qs[b]/math.dist(xs[a],xs[b]) for a,b in itertools.combinations(range(128),2))
    momentum=[math.fsum(m*v[c] for m,v in zip(ms,vs)) for c in range(3)]
    angular=[math.fsum(m*(x[(c+1)%3]*v[(c+2)%3]-x[(c+2)%3]*v[(c+1)%3]) for m,x,v in zip(ms,xs,vs)) for c in range(3)]
    return k+u,k+abs(u),momentum,angular,math.fsum(m*math.hypot(*v) for m,v in zip(ms,vs)),math.fsum(m*math.hypot(*x)*math.hypot(*v) for m,x,v in zip(ms,xs,vs))
def validate_state(s):
    p=s['experiment'];assert not s['paused'] and s['notice'] is None and s['requested_model_s_per_wall_s']==1
    assert p['mode']=='mutual_electrostatic' and p['dt_s']==.001 and p['controls']=={'acting':True} and len(p['system']['ids'])==128
    assert p['system']==r['fixture']['system'] and s['scientific_generation']==r['scientific_generation']
    assert len(p['phase']['position_m'])==len(p['phase']['velocity_m_s'])==128
    assert s['time_s']==p['phase']['time_s']
    if r.get('time_controls_profile'):
        assert s['execution_generation']==r['execution_generation'] and s['time_preferences']['rate']==1
        assert len(s['time_preferences']['timestep_changes'])==64 and s['time_preferences']['dropped_timestep_changes']==0
ram=[];gpu=[];budgets=[];rates=[];summaries=[];energy_errors=[];p_errors=[];l_errors=[];criteria_failures=[]
try:
    assert r['completed'] and r['warmup_s']==30 and r['route_duration_s']==60 and len(r['runs'])==3
    assert r['owner_pointer_preserved'] and r['installed_product_files_preserved']==82
    assert [x['run'] for x in r['runs']]==[1,2,3]
    a=r['frozen_source_archive'];archive=ROOT/a['path'];assert hashlib.sha256(archive.read_bytes()).hexdigest()==a['sha256']
    with tarfile.open(archive,'r:gz') as tar:
        def frozen(path):return tar.extractfile(str(path).replace('\\','/')).read()
        for path,digest in r['configuration_sha256'].items():assert hashlib.sha256(frozen(path)).hexdigest()==digest,path
        version=r['scientific_generation']['version'];assert version in ('0.3.0','0.4.0')
        prefix=r.get('candidate_source_prefix','output/c212-em-v'+('03' if version=='0.3.0' else '04')+'-product/em/')
        assert prefix in ('output/c212-em-v03-product/em/','output/c212-em-v04-product/em/','output/c212-em-potential-product/em/','output/c212-em-cloud-native-product/em/','output/c212-em-time-product/em/','output/c212-em-integration-product/em/','output/c212-em-cloud-editor-product/em/','output/c212-em-framing-product/em/','output/c212-em-viewport-product/em/')
        assert bool(r.get('integration_profile'))==(prefix in ('output/c212-em-integration-product/em/','output/c212-em-cloud-editor-product/em/','output/c212-em-framing-product/em/','output/c212-em-viewport-product/em/'))
        assert bool(r.get('cloud_editor_profile'))==(prefix in ('output/c212-em-cloud-editor-product/em/','output/c212-em-framing-product/em/','output/c212-em-viewport-product/em/'))
        if r.get('cloud_editor_profile'):
            assert r['session']['emCloudEditorCandidate']
        assert bool(r.get('framing_profile'))==(prefix in ('output/c212-em-framing-product/em/','output/c212-em-viewport-product/em/'))
        assert bool(r.get('viewport_profile'))==(prefix=='output/c212-em-viewport-product/em/')
        if r.get('viewport_profile'):assert r['session']['emViewportCandidate']
        if r.get('framing_profile'):
            assert r['session']['emFramingCandidate']
            if r.get('viewport_profile'):
                from em_viewport_profile_audit import audit_dependencies
            else:
                from em_framing_profile_audit import audit_dependencies
            result['framing_static_dependencies']=audit_dependencies(r,frozen)
        if r.get('integration_profile'):
            assert r['session']['emIntegrationCandidate'] and r['integration_UI']=={'interface_scale':1,'active_panel':'layers'}
        for path,digest in r['scientific_generation']['files_sha256'].items():assert r['configuration_sha256'][prefix+path]==digest
        if r.get('time_controls_profile'):
            assert prefix in ('output/c212-em-time-product/em/','output/c212-em-integration-product/em/','output/c212-em-cloud-editor-product/em/','output/c212-em-framing-product/em/','output/c212-em-viewport-product/em/') and r['execution_generation']['protocol']==2
            for name,digest in r['execution_generation']['files_sha256'].items():assert r['configuration_sha256'][prefix+name]==digest
        assert r['scientific_generation']['version']==version
        constants=json.loads(frozen(prefix+'constants.json'));ke=1/(4*math.pi*constants['vacuum_electric_permittivity_F_m']['value'])
        if version=='0.4.0':
            build=json.loads(frozen(prefix+'build-receipt.json').decode('utf-8-sig'));assert build['abi']==1
            for name,key in (('pair_kernel.cpp','cpp_sha256'),('cosmos2_em_pair.dll','dll_sha256')):
                assert r['configuration_sha256'][prefix+name]==build[key]
            assert r['configuration_sha256']['scripts/build-em-pair-kernel.ps1']==build['builder_sha256']
            assert r['configuration_sha256']['output/c212-em-native-kernel-staging/CMakeLists.txt']==build['cmake_sha256']
        variant=r.get('runtime_variant','em-cloud');assert variant in ('em-cloud','topic-cleanup')
        runtime_prefix='.runtime-'+variant
        runtime=json.loads(frozen('evidence/built-runtime-'+variant+'.json'));assert r['engine_sha256']==runtime['engine_sha256']
        assert r['configuration_sha256'][runtime_prefix+'/bin/OpenSpace.exe']==r['engine_sha256']
        if variant=='topic-cleanup':
            assert hashlib.sha256(frozen(runtime['patch'])).hexdigest()==runtime['patch_sha256']
            assert hashlib.sha256(frozen('evidence/built-runtime-em-cloud.json')).hexdigest()==runtime['base_receipt_sha256']
            for name,digest in runtime['changed_source_sha256'].items():
                assert hashlib.sha256(frozen('.upstream/openspace/'+name)).hexdigest()==digest
            for filename,key in (('scripts/build-topic-cleanup-runtime.ps1','builder_sha256'),('scripts/stage-topic-cleanup-runtime.py','stager_sha256')):
                assert hashlib.sha256(frozen(filename)).hexdigest()==runtime[key]
    assert hashlib.sha256((ROOT/runtime_prefix/'bin/OpenSpace.exe').read_bytes()).hexdigest()==r['engine_sha256']
    e0,scale0,p0,l0,_,_=mechanics(r['fixture'])
    assert r['fixture']['dt_s']==.001 and r['requested_model_s_per_wall_s']==1
    assert len(r['frozen_field_map']['samples'])==97
    for run in r['runs']:
        c=run['capture'];assert c['width']==1920 and c['height']==1080 and not c['capacity_reached'] and c['invalid_samples']==0
        v=run['frame_times_s']
        if 'raw_capture_samples_s' in run:
            assert run['raw_capture_samples_s'][1:]==v
        else:
            # The older potential runner stores every retained native interval
            # once, after dropping the protocol's transitional first interval.
            # Recompute all criteria from that vector; no intervals are filtered.
            assert r.get('potential_profile') and 'raw_capture_samples_s' not in run
            result['capture_storage_note']='Potential runner stores all retained native intervals once; transitional first interval omitted. Full vector, durations, subroutes and budgets independently audited.'
        assert abs(math.fsum(v)-60)<.5 and abs(run['wall_interval_s']-60)<.5
        s=validate_frames(v,'run'+str(run['run']))
        for key,value in s.items():assert math.isclose(run['statistics'][key],value,abs_tol=1e-9)
        for index,mark in enumerate(run['memory']):
            end=run['memory'][index+1]['first_frame'] if index<2 else len(v)
            validate_frames(v[mark['first_frame']:end],'run'+str(run['run'])+' camera'+str(index+1));validate_state(mark['physics'])
            resident=mark['ram']['sum_working_set_bytes'];assert resident==sum(p['working_set_bytes'] for p in mark['ram']['processes']) and resident<=8*2**30
            pids={p['pid'] for p in mark['ram']['processes']};assert {r['session']['app'],r['session']['server'],r['em_worker_pid']}<=pids
            ram.append(resident)
            adapters=mark['engine_gpu']['adapters'];adapters=adapters.values() if isinstance(adapters,dict) else adapters
            physical=[a for a in adapters if a['vendor_id']==4098 and a['status']=='ok'];assert physical
            budgets.extend(a['budget_bytes'] for a in physical)
            log=mark['engine_gpu'].get('script_log')
            if log is not None:assert log['initialized'] and not log['failed'] and log['dropped']==0 and 0<=log['queued_bytes']<=8*1024*1024
        for value in (run['initial'],run['final']):validate_state(value)
        assert run['initial']['system_id']==run['final']['system_id']
        rate=(run['final']['time_s']-run['initial']['time_s'])/run['wall_interval_s']
        if rate<.9:criteria_failures.append({'run':run['run'],'criterion':'model rate >=0.9 for1 requested','observed':rate})
        assert math.isclose(rate,run['observed_model_s_per_wall_s'],abs_tol=1e-12);rates.append(rate)
        path=ROOT/run['gpu_report'];assert hashlib.sha256(path.read_bytes()).hexdigest()==run['gpu_sha256']
        g=json.loads(path.read_text(encoding='utf-8-sig'));assert len(g['samples'])==66 and not g['counter_errors']
        assert g['engine_sha256']==r['engine_sha256'] and g['session']['app']==r['session']['app']
        collector='scripts/collect-em-potential-gpu-memory-diagnostic.ps1' if r.get('potential_profile') else 'scripts/collect-em128-candidate-gpu-memory.ps1'
        assert g['collector_sha256']==r['configuration_sha256'][collector]
        assert {r['session']['app'],r['session']['server'],r['em_worker_pid']}<=set(g['owned_processes'])
        start=datetime.fromisoformat(run['capture_start_utc']);end=datetime.fromisoformat(run['capture_end_utc'])
        assert datetime.fromisoformat(g['samples'][0]['utc'].replace('Z','+00:00'))<=start
        assert datetime.fromisoformat(g['samples'][-1]['utc'].replace('Z','+00:00'))>=end
        for sample in g['samples']:
            scenario=sample['scenario'];assert not sample['invalid_samples'] and scenario['mode']=='em' and not scenario['paused']
            assert scenario['renderer_confirmed'] and scenario['fixture_count']==128 and scenario['system_id']==run['initial']['system_id'] and scenario['requested_rate']==1
            assert abs(scenario['native_time']-scenario['physical_time'])<=1
            if r.get('potential_profile'):
                assert scenario['potential_samples']==1089 and scenario['potential_layer_id']==run['frozen_potential_render']['layer_id']
                assert scenario['potential_visible'] is run['expected_potential_visible'] and scenario['electric_visible'] is run['expected_electric_visible']
            total=sum(p['bytes'] for p in sample['product'] if p['counter']=='dedicated usage');assert total==sample['product_dedicated_sum_bytes']
        peak=max(sample['product_dedicated_sum_bytes'] for sample in g['samples']);assert peak<=5.5*2**30 and peak<min(budgets);gpu.append(peak)
        en,_,p,l,ps,ls=mechanics(run['final']['experiment'])
        ee=abs(en-e0)/scale0;pe=math.dist(p,p0)/ps if ps else math.dist(p,p0);le=math.dist(l,l0)/ls if ls else math.dist(l,l0)
        assert ee<1e-6 and pe<1e-10 and le<1e-10,(ee,pe,le)
        energy_errors.append(ee);p_errors.append(pe);l_errors.append(le)
        summaries.append({'run':run['run'],'rate':rate,**s})
        if r.get('potential_profile'):
            if r.get('framing_profile'):
                if r.get('viewport_profile'):
                    from em_viewport_profile_audit import audit_potential
                else:
                    from em_framing_profile_audit import audit_potential
                result.setdefault('framing_potential_audits',[]).append(audit_potential(r,run,ke))
            render=run['frozen_potential_render'];assert render['sample_count']==1089 and render['complete'] and render['segment_count']>0
            assert render['grid']['x_m']==render['grid']['y_m'] and len(render['grid']['x_m'])==33
            assert render['metadata']['time_s']==0 and render['metadata']['system_id']==run['initial']['system_id']
            for mark in run['memory']:
                p=mark['potential'];assert not p['error'] and not p['confirmation_uncertain'] and p['render']['layer_id']==render['layer_id']
                assert p['settings']['visible'] is run['expected_potential_visible'] and mark['physics']['editor']['visual']['electric_visible'] is run['expected_electric_visible']
                flags=mark['independent_native_visibility'];assert set(flags)=={m['node'] for m in render['meshes']} and all(v is run['expected_potential_visible'] for v in flags.values())
    pauses=r['pause_latency_samples'];assert len(pauses)==20 and all(0<=p['worker_elapsed_ms']<=p['wall_ms']<=250 for p in pauses)
    if r.get('potential_profile'):
        assert [x['expected_potential_visible'] for x in r['runs']]==[True,False,True]
        assert [x['expected_electric_visible'] for x in r['runs']]==[True,True,False]
        assert len(r['potential_sampling_wall_ms'])==len(r['potential_numeric_sampling_ms'])==3
        assert max(r['potential_numeric_sampling_ms'])<=2000 and max(r['potential_sampling_wall_ms'])<=3000
        result.update(potential_samples=1089,field_vector_samples=97,potential_numeric_sampling_max_ms=max(r['potential_numeric_sampling_ms']),potential_API_sampling_max_ms=max(r['potential_sampling_wall_ms']),
                      measured_layer_combinations=['E and potential visible','E visible, potential hidden','potential visible, E hidden'])
    result.update(accepted=not criteria_failures,criteria_failures=criteria_failures,three_EM128_routes_measured_and_integrity_verified=True,frozen_source_archive=a,runs=summaries,
                  observed_rate_min=min(rates),p95_ms_max=max(s['p95_ms'] for s in summaries),p99_ms_max=max(s['p99_ms'] for s in summaries),
                  pause_wall_max_ms=max(p['wall_ms'] for p in pauses),resident_sum_max_GiB=max(ram)/2**30,
                  WDDM_dedicated_sum_max_GiB=max(gpu)/2**30,engine_DXGI_budget_min_GiB=min(budgets)/2**30,
                  energy_error_max=max(energy_errors),momentum_normalized_max=max(p_errors),angular_normalized_max=max(l_errors),
                  memory_method='WDDM per-process dedicated sums may repeat shared allocations. Product RAM sums may repeat shared pages. DXGI budget belongs to engine; other applications excluded from product tally.')
except BaseException as error:
    result['failure']=type(error).__name__+': '+str(error)
    raise
finally:
    (ROOT/f'evidence/native-em128-{label}-review.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if not result['accepted']:raise SystemExit(1)
