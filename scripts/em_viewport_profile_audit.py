"""Independent stdlib checks for J's unchanged static dependencies and raw SI reads.

No imports from the product's sampler, field solver or geometry assembler.
The original frame, resource and mechanics auditors retain their criteria.
"""
from pathlib import Path
import hashlib
import json
import math

BASE='output/c212-em-viewport-product/'
KEYS=('system_id','edit_token','revision','frame','time_s')

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()

def audit_dependencies(report,frozen):
    conf=report['configuration_sha256']
    audit='scripts/em_viewport_profile_audit.py'
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==conf[audit]
    assert hashlib.sha256(frozen(audit)).hexdigest()==conf[audit]
    assert report['viewport_profile'] and report['session']['emViewportCandidate']
    assert report['framing_profile'] and report['cloud_editor_profile'] and report['integration_profile']
    assert report['session']['emFramingCandidate'] and report['session']['emCloudEditorCandidate']
    proof=json.loads(frozen('evidence/em-framing-static-sampler-release2-check.json'))
    assert proof['completed'] and len(proof['rejections'])==11 and len(proof['checks'])==10
    provider=proof['provider']
    for name,sha in provider['files_sha256'].items():
        assert conf[BASE+name]==sha
    for name in ('constants.json','em_fields.py'):
        assert frozen(BASE+'em/'+name)==frozen(BASE+'em-cloud/'+name)
    proof_sources={p.replace('\\','/'):v for p,v in proof['source_sha256'].items()}
    for name in ('app/em_static_sampler.py','app/em_slice.py'):
        assert conf[BASE+name]==proof_sources['output/c212-em-framing-product/'+name]
    build=json.loads(frozen(BASE+'em-cloud/build-receipt.json').decode('utf-8-sig'))
    assert build['abi']==1
    for name,key in (('cloud_kernel.cpp','cpp_sha256'),('cosmos2_em_cloud.dll','dll_sha256'),('CMakeLists.txt','cmake_sha256')):
        assert conf[BASE+'em-cloud/'+name]==build[key]
    assert conf['scripts/build-em-cloud-kernel.ps1']==build['builder_sha256']
    return {'helper_ABI':1,'constants_and_fields_byte_equal':True,
            'helper_provider_and_assembler_match_validated_release2':True,
            'helper_DLL_CPP_CMake_builder_sealed':True}

def audit_potential(report,run,ke):
    layer=run['frozen_potential_layer'];m=layer['measurement'];g=layer['geometry'];b=layer['batch_protocol']
    render=run['frozen_potential_render'];conf=report['configuration_sha256']
    assert layer['source_snapshot']==report['fixture']
    assert layer['scientific_generation']==report['scientific_generation']
    metadata={k:m[k] for k in KEYS}
    assert metadata==g['metadata']==render['metadata']
    assert m['time_s']==0 and m['frame']=='EM_SI_FIXED_INERTIAL'
    assert m['system_id']==run['initial']['system_id']
    assert g['measurement_sha256']==digest(m) and render['layer_id']==digest(g)
    assert g['algorithm']['sha256']==conf[BASE+'app/em_potential.py']
    assert g['algorithm']['version']=='0.1.1'
    assert b['version']=='0.3.0' and b['maximum_points_per_request']==128
    assert b['all_same_confirmed_snapshot'] is True and b['budget_s']==2
    assert 0<=b['elapsed_wall_ms']<=2000
    assert b['elapsed_wall_ms']==report['potential_numeric_sampling_ms'][run['run']-1]
    assert b['assembler_sha256']==conf[BASE+'app/em_slice.py']
    expected_batches=[{'offset':offset,'samples':min(128,1089-offset)} for offset in range(0,1089,128)]
    assert b['batches']==expected_batches
    provider=b['provider']
    assert provider['kind']=='verified_static_EM_helper_abi1' and provider['version']=='0.1.1'
    assert provider['thread_count']==1 and provider['all_declared_sources']==128
    assert provider['field_queries_in_worker'] is False
    expected_files={'app/em_static_sampler.py',*('em-cloud/'+name for name in (
        'cloud_native.py','cloud_kernel.cpp','CMakeLists.txt','cosmos2_em_cloud.dll','build-receipt.json','constants.json','em_fields.py'))}
    assert set(provider['files_sha256'])==expected_files
    for path,sha in provider['files_sha256'].items():assert conf[BASE+path]==sha
    ex=report['fixture'];assert ex['mode']=='mutual_electrostatic'
    system=ex['system'];positions=ex['phase']['position_m'];ids=system['ids']
    charges=system['charge_C'];radii=system['exclusion_radius_m']
    assert len(ids)==len(positions)==len(charges)==len(radii)==128
    exclusions=[{'id':sid,'position_m':p,'radius_m':r} for sid,p,r in zip(ids,positions,radii)]
    assert g['exclusions']==exclusions
    grid=g['grid'];assert grid==render['grid']
    assert len(grid['x_m'])==len(grid['y_m'])==33 and len(m['samples'])==1089
    points=[[x,y,grid['z_m']] for x in grid['x_m'] for y in grid['y_m']]
    maxima={'E':0.,'B':0.,'potential':0.};valid_count=0;excluded_count=0
    for point,s in zip(points,m['samples']):
        assert s['position_m']==point
        distances=[math.dist(point,p) for p in positions]
        excluded=[sid for sid,d,r in zip(ids,distances,radii) if d<=r]
        assert type(s['valid']) is bool and s['valid']==(not excluded)
        if excluded:
            assert s['source_ids']==excluded and s['reason']=='inside_or_on_source_exclusion'
            assert not {'electric_field_V_m','magnetic_field_T','electric_potential_V'}&s.keys()
            excluded_count+=1;continue
        valid_count+=1;assert s['source_ids']==ids
        terms=[ke*q/r for q,r in zip(charges,distances)]
        vectors=[[ke*q*(x-y)/r**3 for x,y in zip(point,p)] for q,p,r in zip(charges,positions,distances)]
        e=[math.fsum(v[k] for v in vectors) for k in range(3)]
        escale=math.fsum(math.hypot(*v) for v in vectors);pscale=math.fsum(abs(t) for t in terms)
        errors={'E':math.dist(e,s['electric_field_V_m'])/max(escale,1e-300),
                'B':math.hypot(*s['magnetic_field_T']),
                'potential':abs(math.fsum(terms)-s['electric_potential_V'])/max(pscale,1e-300)}
        for key,value in errors.items():
            assert math.isfinite(value) and value<=1e-10,(key,point,value)
            maxima[key]=max(maxima[key],value)
        assert math.isclose(s['electric_scale_V_m'],escale,rel_tol=1e-10,abs_tol=1e-300)
        assert s['magnetic_scale_T']==0 and math.isclose(s['potential_scale_V'],pscale,rel_tol=1e-10,abs_tol=1e-300)
        assert s['potential_zero']=='uniform term at coordinate origin; charge terms at infinity'
        assert s['numeric_provider'] in ('compiled_static_helper_abi1','scalar_boundary_reference')
    assert render['valid_samples']==valid_count and render['sample_count']==1089
    assert render['sample_range_V']==[min(s['electric_potential_V'] for s in m['samples'] if s['valid']),max(s['electric_potential_V'] for s in m['samples'] if s['valid'])]
    # Independent rectangle/sphere check; the product uses axis pruning.
    masked_cells=set()
    for i in range(32):
        for j in range(32):
            for p,radius in zip(positions,radii):
                closest=[min(grid['x_m'][i+1],max(grid['x_m'][i],p[0])),min(grid['y_m'][j+1],max(grid['y_m'][j],p[1])),grid['z_m']]
                if math.dist(p,closest)<=radius:masked_cells.add((i,j));break
    assert g['complete'] is True and g['maximum_segments']==4096 and g['termination']=='complete'
    assert g['source_exclusion_triangle_levels']==2*len(masked_cells)*len(g['levels_V'])
    assert render['segment_count']==len(g['segments']) and render['levels_V']==g['levels_V']
    for segment in g['segments']:
        indices=segment['sample_indices'];a=indices[0];i,j=divmod(a,33)
        assert indices in ([a,a+33,a+34],[a,a+34,a+1]) and (i,j) not in masked_cells
        assert all(m['samples'][idx]['valid'] for idx in indices)
        assert segment['level_V'] in g['levels_V']
    return {'run':run['run'],'samples':1089,'sources':128,'valid_samples':valid_count,'excluded_samples':excluded_count,
            'batch_count':9,'worker_snapshot_fences_implied_by_validated_provider':18,
            'field_queries_in_worker':False,'raw_SI_maximum_errors':maxima,
            'measurement_geometry_and_render_hashes_bound':True,'exclusion_cells_independently_checked':True}
