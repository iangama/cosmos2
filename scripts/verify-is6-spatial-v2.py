"""Independent80dps metric/tensor/quadrature and discrete spatial-mesh checks."""
from pathlib import Path
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import platform
import sys
import traceback
import zipfile
import mpmath as mp

ROOT=Path(__file__).resolve().parents[1]
MODEL=ROOT/'output/is6-spatial-staging/is6_spatial.py'
FIXTURES=ROOT/'output/is6-spatial-fixtures-20261101a/fixtures-before-execution.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def tensor_reference_raw(gm,r):
    """Build the diagonal metric, its derivatives, Gamma and Riemann directly.

    No closed-form curvature expression is used in this reference evaluator.
    Time coordinate is ct; evaluate away from the polar coordinate singularity.
    """
    c=mp.mpf(299792458);rs=2*mp.mpf(gm)/(c*c);r=mp.mpf(r);theta=mp.pi/3
    def metric(i,x,t):
        f=1-rs/x
        return [-f,1/f,x*x,x*x*mp.sin(t)**2][i]
    g=[metric(i,r,theta) for i in range(4)]
    d=[[mp.mpf(0) for i in range(4)] for axis in range(4)]
    dd=[[[mp.mpf(0) for i in range(4)] for b in range(4)] for a in range(4)]
    for i in range(4):
        d[1][i]=mp.diff(lambda x:metric(i,x,theta),r)
        d[2][i]=mp.diff(lambda t:metric(i,r,t),theta)
        dd[1][1][i]=mp.diff(lambda x:metric(i,x,theta),r,2)
        dd[2][2][i]=mp.diff(lambda t:metric(i,r,t),theta,2)
        dd[1][2][i]=dd[2][1][i]=mp.diff(lambda x:mp.diff(lambda t:metric(i,x,t),theta),r)
    gamma={};dgamma={}
    for a in range(4):
        for b in range(4):
            for c in range(4):
                numerator=(d[b][a] if a==c else 0)+(d[c][a] if a==b else 0)-(d[a][b] if b==c else 0)
                gamma[a,b,c]=numerator/(2*g[a])
                for axis in range(4):
                    derivative=(dd[axis][b][a] if a==c else 0)+(dd[axis][c][a] if a==b else 0)-(dd[axis][a][b] if b==c else 0)
                    dgamma[axis,a,b,c]=derivative/(2*g[a])-numerator*d[axis][a]/(2*g[a]*g[a])
    curvature={}
    for a in range(4):
        for b in range(4):
            for c in range(4):
                for e in range(4):
                    curvature[a,b,c,e]=dgamma[c,a,b,e]-dgamma[e,a,b,c]+mp.fsum(
                        gamma[a,k,c]*gamma[k,b,e]-gamma[a,k,e]*gamma[k,b,c] for k in range(4))
    kretschmann=mp.fsum((g[a]*value)**2/(g[a]*g[b]*g[c]*g[e]) for (a,b,c,e),value in curvature.items())
    ricci=max(abs(mp.fsum(curvature[a,b,a,e] for a in range(4)))/mp.sqrt(abs(g[b]*g[e])) for b in range(4) for e in range(4))
    return kretschmann,ricci


def tensor_reference(gm,r):
    with mp.workdps(120):
        curvature,ricci=tensor_reference_raw(gm,r)
    return +curvature,+ricci


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/f'output/is6-spatial-{args.label}';receipt=ROOT/f'evidence/is6-spatial-{args.label}.json'
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve spatial evidence')
    fixture=json.loads(FIXTURES.read_text());contract=ROOT/'IS-6-MALHA-ESPACIAL-CONTRATO-PREVIO.md'
    assert sha(contract)==fixture['contract_sha256']
    files=[Path(__file__),MODEL,FIXTURES,contract,ROOT/'IS-6-MALHA-ESPACIAL-REFERENCIA-B.md',ROOT/'scripts/prepare-is6-spatial-fixtures.py',
           ROOT/'IS-6-MALHA-ESPACIAL-PREPARACAO-20261101.md',ROOT/'scripts/prepare-is6-spatial-research.py',
           ROOT/'output/is6-spatial-research-20261101/acquisition.json',ROOT/'output/is6-spatial-research-20261101/oist-gr-lecture8.pdf']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files};folder.mkdir()
    archive=folder/'executed-sources.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name in hashes:z.write(ROOT/name,name)
    limits=dict(metric_relative=3e-13,small_clock_relative=3e-12,length_relative=3e-12,
                curvature_relative=3e-11,zero_absolute=1e-30,embedding_relative=3e-13,
                final_radial_polyline_relative=2e-4,rotation_relative=3e-13)
    r=dict(accepted=False,completed=False,source_sha256=hashes,archive_sha256=sha(archive),limits_before_execution=limits,
           reference=dict(mpmath=mp.__version__,dps=80,tensor_work_dps=120,python=platform.python_version()),groups=[],comparisons=0,
           maxima={},samples=[],intervals=[],mesh_refinement=[],refusals=[],
           scope='Isolated spatial Schwarzschild model only; no body binding, HTTP, CEF, native scene, visual, profile or orbital acceptance.')
    def persist():receipt.write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    def passed(name):r['groups'].append(name);persist();print(json.dumps(dict(group=name,passed=True)),flush=True)
    def compare(name,actual,expected,limit):
        actual,expected=mp.mpf(actual),mp.mpf(expected)
        error=abs(actual-expected)/abs(expected) if expected else abs(actual)
        r['comparisons']+=1;r['maxima'][name]=max(r['maxima'].get(name,0),float(error))
        assert error<=(mp.mpf(limit) if expected else mp.mpf('1e-30')),(name,str(actual),str(expected),str(error),limit)
    persist()
    try:
        spec=importlib.util.spec_from_file_location('is6_spatial_candidate',MODEL)
        model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)
        generation=model.generation();r['generation']=generation
        mp.mp.dps=80;c=mp.mpf(299792458)
        for index,row in enumerate(fixture['samples']):
            p=row['source'];radius=mp.mpf(row['radius_m']);rs=2*mp.mpf(p['GM_m3_s2'])/(c*c);u=rs/radius;f=1-u;s=mp.sqrt(f)
            value=model.sample(p,row['radius_m'])
            references=dict(schwarzschild_radius_m=rs,compactness=u,metric_ct_ct=-f,metric_rr=1/f,
                metric_theta_theta_m2=radius**2,metric_phi_phi_m2=radius**2,static_clock_ratio=s,
                static_clock_deficit=1-s,radial_stretch_excess=1/s-1,circumference_m=2*mp.pi*radius,
                embedding_gradient=mp.sqrt(rs/(radius-rs)))
            for name,expected in references.items():
                compare(name,value[name],expected,3e-12 if name in ['static_clock_deficit','radial_stretch_excess'] else 3e-13)
            compare('embedding_metric_identity',1+value['embedding_gradient']**2,value['metric_rr'],3e-13)
            tensor,ricci=tensor_reference(p['GM_m3_s2'],row['radius_m'])
            compare('Kretschmann_tensor',value['Kretschmann_m_inverse4'],tensor,3e-11)
            assert tensor>0 and ricci<=mp.mpf('1e-50')*max(rs/radius**3,mp.mpf('1e-300'))
            r['samples'].append(dict(index=index,result=value,tensor_K=str(tensor),orthonormal_Ricci_residual=str(ricci)))
        first=fixture['samples'][0]
        guarded=tensor_reference(first['source']['GM_m3_s2'],first['radius_m'])[0]
        with mp.workdps(160):high_precision=tensor_reference_raw(first['source']['GM_m3_s2'],first['radius_m'])[0]
        compare('tensor_guard_digits_control',guarded,high_precision,1e-60)
        passed('Metric_static_clocks_small_deficits_embedding_and_independent_Riemann_K_Ricci80plus40guard')
        for row in fixture['intervals']:
            p=row['source'];a,b=mp.mpf(row['inner_m']),mp.mpf(row['outer_m']);rs=2*mp.mpf(p['GM_m3_s2'])/(c*c)
            length=mp.quad(lambda x:1/mp.sqrt(1-rs/x),[a,b])
            extra=mp.quad(lambda x:1/mp.sqrt(1-rs/x)-1,[a,b])
            actual=model.radial_distance(p,row['inner_m'],row['outer_m'])
            compare('proper_length_quadrature',actual['proper_length_m'],length,3e-12)
            compare('proper_excess_quadrature',actual['proper_length_excess_m'],extra,3e-12)
            for emitter,receiver in [(row['inner_m'],row['outer_m']),(row['outer_m'],row['inner_m'])]:
                expected=mp.sqrt((1-rs/mp.mpf(emitter))/(1-rs/mp.mpf(receiver)))
                actual_clock=model.compare_clocks(p,emitter,receiver)
                compare('clock_frequency_ratio',actual_clock['received_over_emitted_frequency'],expected,3e-13)
                compare('clock_fractional_shift',actual_clock['fractional_frequency_shift'],expected-1,3e-12)
            r['intervals'].append(dict(configuration=row,result=actual,reference_length=str(length),reference_excess=str(extra)))
        flat=fixture['flat_source'];sample=model.sample(flat,1.)
        assert sample['static_clock_ratio']==1 and sample['static_clock_deficit']==sample['Kretschmann_m_inverse4']==sample['embedding_gradient']==0
        assert model.radial_distance(flat,1.,8.)['proper_length_m']==7. and model.radial_distance(flat,1.,8.)['proper_length_excess_m']==0
        assert model.radial_distance(fixture['samples'][0]['source'],8.,8.)['proper_length_m']==0
        passed('Independent_radial_quadrature_and_short_interval_excess_clocks_both_directions_flat_exact_limit')
        def options(a,b,n=33,basis=None,center=None,amp=1.):
            return dict(inner_radius_m=a,outer_radius_m=b,radial_count=n,azimuth_sectors=96,
                        orientation=copy.deepcopy(basis or fixture['bases'][0]),center_m=list(center or [0.,0.,0.]),vertical_amplification=amp)
        mesh_source=fixture['samples'][0]['source']
        for row in fixture['intervals'][::2]:
            previous=None;history=[]
            a,b=row['inner_m'],row['outer_m'];rs=2*mp.mpf(mesh_source['GM_m3_s2'])/(c*c)
            exact=mp.quad(lambda x:1/mp.sqrt(1-rs/x),[mp.mpf(a),mp.mpf(b)])
            for count in fixture['radial_counts']:
                payload=model.mesh(mesh_source,options(a,b,count))
                radii=payload['meridian_radius_m'];z=payload['meridian_embedding_height_m']
                polyline=math.fsum(math.hypot(radii[i+1]-radii[i],z[i+1]-z[i]) for i in range(count-1))
                error=abs(mp.mpf(polyline)-exact)/exact
                if previous is not None and previous>mp.mpf('1e-12'):assert error<previous,(a,b,count,str(error),str(previous))
                previous=error
                assert len(payload['physical_vertices_relative_m'])==count*97
                for i in range(count):
                    start=i*97;points=payload['physical_vertices_relative_m'][start:start+97]
                    assert points[0]==points[-1]
                    polygon=math.fsum(math.dist(points[j],points[j+1]) for j in range(96))
                    compare('azimuth_polygon',polygon,2*96*mp.mpf(radii[i])*mp.sin(mp.pi/96),3e-13)
                history.append(dict(radial_count=count,polyline_m=polyline,relative_error=float(error)))
            assert previous<=mp.mpf('2e-4')
            r['mesh_refinement'].append(dict(interval=[a,b],history=history))
        passed('33_65_129_257_radial_refinement_closed96sector_rings_metric_and_vertex_budget')
        original=model.mesh(mesh_source,options(2.,8.))
        for basis in fixture['bases']:
            for center in fixture['centers']:
                for amp in fixture['amplifications']:
                    value=model.mesh(mesh_source,options(2.,8.,basis=basis,center=center,amp=amp))
                    assert value['source']==original['source'] and value['meridian_radius_m']==original['meridian_radius_m'] and value['meridian_embedding_height_m']==original['meridian_embedding_height_m']
                    assert value['center_m']==center and value['vertical_amplification']==amp
                    # Check increments directly, preserving small source-relative details.
                    for vector in [[2.,3.,5.],[1e-10,-2e-10,3e-10],[1e18,2e18,-3e18]]:
                        changed=model.transform(vector,basis)
                        compare('rotation_vector_norm',math.hypot(*changed),mp.sqrt(mp.fsum(mp.mpf(x)**2 for x in vector)),3e-13)
                    for i in [0,len(value['physical_vertices_relative_m'])//2,-1]:
                        v=value['physical_vertices_relative_m'][i];graph=value['display_vertices_relative_m'][i]
                        native=original['physical_vertices_relative_m'][i]
                        recovered=[math.fsum(v[k]*basis[j][k] for k in range(3)) for j in range(3)]
                        vector_error=math.dist(recovered,native)/math.hypot(*native)
                        r['comparisons']+=1;r['maxima']['rotation_inverse_vector']=max(r['maxima'].get('rotation_inverse_vector',0),vector_error)
                        assert vector_error<=3e-13
                        projected=math.fsum(graph[k]*basis[2][k] for k in range(3))
                        compare('graphical_amplification',projected,mp.mpf(native[2])*amp,3e-13)
        flat_mesh=model.mesh(flat,options(1.,8.,amp=1000.))
        assert set(flat_mesh['meridian_embedding_height_m'])=={0.}
        passed('Three_planes_rotation_separate_center_and_display_amplification_preserve_intrinsic_geometry')
        def refuse(name,call):
            before=model.generation()
            try:call()
            except ValueError:pass
            else:raise AssertionError('Accepted invalid request: '+name)
            assert model.generation()==before
            r['refusals'].append(name)
        for value in [True,None,'1',float('nan'),float('inf'),-1.,.5,1e27]:
            refuse('GM:'+repr(value),lambda value=value:model.sample(dict(GM_m3_s2=value,material_radius_m=0.),2.))
        for value in [True,None,'1',float('nan'),0.,1e21]:
            refuse('radius:'+repr(value),lambda value=value:model.sample(mesh_source,value))
        refuse('missing_source',lambda:model.sample({},2.))
        refuse('extra_source',lambda:model.sample({**mesh_source,'extra':1},2.))
        refuse('material_interior',lambda:model.sample({**mesh_source,'material_radius_m':3.},2.))
        refuse('horizon',lambda:model.sample(mesh_source,1.))
        refuse('reversed_interval',lambda:model.radial_distance(mesh_source,8.,2.))
        bad_options=[]
        for field,value in [('radial_count',True),('radial_count',258),('azimuth_sectors',True),('azimuth_sectors',97),('vertical_amplification',-1),('vertical_amplification',1001),('center_m',[0,True,0]),('center_m',[0,1e21,0]),('orientation',[[2,0,0],[0,1,0],[0,0,1]]),('orientation',[[1,0,0],[0,1,0],[0,0,-1]]),('outer_radius_m',2.)]:
            bad={**options(2.,8.),field:value};bad_options.append((field,copy.deepcopy(bad)));saved=copy.deepcopy(bad)
            refuse('mesh:'+field+':'+repr(value),lambda bad=bad:model.mesh(mesh_source,bad))
            assert bad==saved
        refuse('extra_mesh_field',lambda:model.mesh(mesh_source,{**options(2.,8.),'extra':1}))
        assert model.generation()==generation and all(sha(ROOT/n)==v for n,v in hashes.items())
        passed('Strict_types_domain_schema_resolution_orientation_refusals_inputs_and_generation_immutable')
        r.update(accepted=True,completed=True)
    except Exception:r['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps({k:r.get(k) for k in ['accepted','completed','comparisons','maxima','failure']}),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
