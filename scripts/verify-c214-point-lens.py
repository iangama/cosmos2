"""Before integration: independent high-precision point-lens geometry, parity and domain checks."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import itertools
import json
import math
import platform
import sys
import traceback
import zipfile

import mpmath as mp

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/c214-point-lens-staging'
PRODUCT=ROOT/'output/original-flow-hotfix-product0.28.4'
FOLDER=ROOT/'output/c214-point-lens-offline-20261121a'
OUT=ROOT/'evidence/c214-point-lens-offline-20261121a.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
U_VALUES=[1.00000001e-6,1e-5,.001,.01,.1,1.,10.,100.,1000.,9999.9999]


def inputs(u=1.,mass=1.,source_ratio=2.):
    gm=1.3271244e20*mass;dl=1e20;ds=source_ratio*dl
    te=math.sqrt((4*gm/299792458**2)*((ds-dl)/ds)/dl)
    return dict(GM_m3_s2=gm,observer_m=[0.,0.,0.],lens_m=[0.,0.,dl],source_m=[ds*te*u,0.,ds])


def relative(actual,expected,tol=5e-12):
    expected=mp.mpf(expected)
    if expected==0:assert abs(actual)<=tol
    else:assert abs((mp.mpf(actual)-expected)/expected)<=tol,(actual,str(expected))


def oracle(cfg):
    # mpmath arithmetic, numerical roots on separate half-lines, numerical derivatives.
    mp.mp.dps=110
    o,l,s=[mp.matrix([mp.mpf(x) for x in cfg[name]]) for name in ['observer_m','lens_m','source_m']]
    lv,sv=l-o,s-o;dl=mp.norm(lv);n=lv/dl;ds=mp.fdot(sv,n);dls=ds-dl
    transverse=sv-ds*n;beta=mp.norm(transverse)/ds
    te=mp.sqrt((4*mp.mpf(cfg['GM_m3_s2'])/mp.mpf(299792458)**2)*dls/(dl*ds));u=beta/te
    fn=lambda x:x-1/x-u
    options=dict(solver='bisect',tol=mp.mpf('1e-90'),maxsteps=600,verify=True)
    outer=mp.findroot(fn,(mp.mpf(1),u+1),**options)
    inner=mp.findroot(fn,(-mp.mpf(1),-1/(u+1)),**options)
    magnifications=[]
    for x in [outer,inner]:
        fx=lambda a,b:a-a/(a*a+b*b)
        fy=lambda a,b:b-b/(a*a+b*b)
        j=mp.matrix([[mp.diff(lambda a:fx(a,0),x),mp.diff(lambda b:fx(x,b),0)],
                     [mp.diff(lambda a:fy(a,0),x),mp.diff(lambda b:fy(x,b),0)]])
        magnifications.append(1/mp.det(j))
    return dict(Dl=dl,Ds=ds,Dls=dls,beta=beta,thetaE=te,u=u,
      theta=[outer*te,inner*te],magnifications=magnifications,
      total=abs(magnifications[0])+abs(magnifications[1]))


def main():
    assert not OUT.exists() and not FOLDER.exists();FOLDER.mkdir()
    source_paths=[STAGE/'point_lens.py',ROOT/'C2-14-LENTE-PONTUAL-CONTRATO-20261121.md',Path(__file__)]
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in source_paths}
    grid=[dict(u=u,mass=mass,source_ratio=ratio,configuration=inputs(u,mass,ratio))
          for mass in [.01,1.,100.] for ratio in [1.5,2.,3.] for u in U_VALUES]
    recipe=dict(source_sha256=sources,grid=grid,precision=110,
      tolerance_relative=5e-12,oracle='Independent half-line root bisection and numerical Jacobian derivatives in mpmath.',
      endpoint_policy='Finite-u grid endpoints deliberately inside strict input domain, fixed before execution. Outside-boundary refusals are separate cases.',
      planned=['90high-precision cases','48signed coordinate permutations','joint length/GM scaling and translation',
               'alignment ring and direct intervention','strict input/geometry/domain refusals','three exact-null-ray weak-limit comparisons'])
    (FOLDER/'recipe-before-execution.json').write_text(json.dumps(recipe,indent=2)+'\n',encoding='utf8')
    with zipfile.ZipFile(FOLDER/'executed-sources.zip','x',zipfile.ZIP_DEFLATED) as archive:
        for p in source_paths:archive.write(p,p.relative_to(ROOT).as_posix())
    proof=dict(accepted=False,completed=False,checks=[],refusals=[],source_sha256=sources,
      source_archive_sha256=sha(FOLDER/'executed-sources.zip'),runtime=dict(python=platform.python_version(),mpmath=mp.__version__),
      scope='CPU only, separate point-lens staging; no service, UI, native, performance or C2-14 promotion. Numerical roots/Jacobian independently recomputed at110digits. Approximation limits remain in force.')
    (FOLDER/'model-results').mkdir()
    def persist():OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    def check(name,action):
        try:values=action();proof['checks'].append(dict(name=name,passed=True,**(values or {})))
        except Exception:proof['checks'].append(dict(name=name,passed=False,failure=traceback.format_exc()))
        persist()
    spec=importlib.util.spec_from_file_location('point_lens_cpu_candidate',STAGE/'point_lens.py')
    core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
    protected={p.relative_to(ROOT).as_posix():sha(p) for p in [ROOT/'output/session.json',ROOT/'config/local-working-product.json']}
    manifest=json.loads((PRODUCT/'build-manifest.json').read_text());assert all(sha(PRODUCT/n)==s for n,s in manifest['files_sha256'].items())
    def high_precision():
        largest=0.
        for index,item in enumerate(grid):
            result=core.experiment(item['configuration']);reference=oracle(item['configuration'])
            assert result['reference']['status']=='two_images'
            for key,field in [('Dl','Dl_m'),('Ds','Ds_m'),('Dls','Dls_m'),('thetaE','einstein_angle_rad'),('u','u')]:relative(result['geometry'][field],reference[key])
            for image,theta,mu in zip(result['reference']['images'],reference['theta'],reference['magnifications']):
                relative(image['theta_signed_rad'],theta);relative(image['magnification_signed'],mu)
                assert image['parity']==(1 if mu>0 else -1)
                assert image['impact_rs']>=1000 and image['lens_equation_residual_thetaE']<=1e-70
                largest=max(largest,float(abs((mp.mpf(image['magnification_signed'])-mu)/mu)))
            relative(result['reference']['magnification_total'],reference['total'])
            relative(result['reference']['magnification_total_minus_unity'],reference['total']-1)
            relative(result['reference']['outer_magnification_minus_unity'],reference['magnifications'][0]-1)
            relative(result['reference']['signed_magnification_sum'],1)
            assert result['reference']['root_product_normalized']==-1
            path=FOLDER/'model-results'/f'{index:03d}.json';path.write_text(json.dumps(result,sort_keys=True,allow_nan=False)+'\n')
        return dict(cases=len(grid),maximum_relative_magnification_error=largest)
    check('roots-parity-jacobian-and-small-excess-agree-with-independent-110digit-oracle',high_precision)
    base_cfg=inputs();base=core.experiment(base_cfg)
    def permutations():
        for permutation in itertools.permutations(range(3)):
            for signs in itertools.product([-1,1],repeat=3):
                transform=lambda v:[signs[i]*v[permutation[i]] for i in range(3)]
                cfg=copy.deepcopy(base_cfg)
                for name in ['observer_m','lens_m','source_m']:cfg[name]=transform(cfg[name])
                result=core.experiment(cfg)
                relative(result['reference']['magnification_total'],base['reference']['magnification_total'])
                for actual,original in zip(result['actual']['images'],base['actual']['images']):
                    expected=transform(original['lens_plane_world_m'])
                    for a,b in zip(actual['lens_plane_world_m'],expected):relative(a,b)
        return dict(cases=48)
    check('all-signed-axis-permutations-preserve-lensing-and-transform-physical-images',permutations)
    def transforms():
        for factor in [2.**-20,2.**20]:
            cfg=copy.deepcopy(base_cfg);cfg['GM_m3_s2']*=factor
            for name in ['observer_m','lens_m','source_m']:cfg[name]=[v*factor for v in cfg[name]]
            result=core.experiment(cfg);relative(result['reference']['magnification_total'],base['reference']['magnification_total'])
            relative(result['geometry']['einstein_angle_rad'],base['geometry']['einstein_angle_rad'])
            for actual,original in zip(result['actual']['images'],base['actual']['images']):relative(actual['impact_m'],original['impact_m']*factor)
        cfg=copy.deepcopy(base_cfg);shift=[2.**40,-2.**45,2.**50]
        for name in ['observer_m','lens_m','source_m']:cfg[name]=[v+t for v,t in zip(cfg[name],shift)]
        translated=core.experiment(cfg);reference=oracle(cfg)
        relative(translated['reference']['magnification_total'],reference['total'])
        return dict(joint_scales=2,translated_coordinate_ulp_m=translated['input_resolution']['maximum_coordinate_ulp_m'])
    check('joint-length-GM-scaling-and-translated-input-resolution',transforms)
    def ring_intervention():
        cfg=copy.deepcopy(base_cfg);cfg['source_m'][0]=0
        ring=core.experiment(cfg);assert ring['reference']['status']=='aligned_point_source_caustic'
        assert ring['reference']['magnification_total'] is None and ring['reference']['images']==[]
        assert ring['actual']['ring']['paraxial_angular_radius_rad']>0
        direct=core.experiment(cfg,bending=False)
        assert direct['reference']==ring['reference'] and direct['actual']['magnification_total']==1
        assert len(direct['actual']['images'])==1 and direct['actual']['images'][0]['physical_deflection_rad']==0
        direct2=core.experiment(base_cfg,bending=False)
        assert direct2['configuration']==base['configuration'] and direct2['reference']==base['reference']
        assert base==core.experiment(base_cfg)
        return dict(alignment='ring-with-undefined-amplification',intervention='direct-image-unit-amplification')
    check('alignment-and-deflection-intervention-are-explicit-and-deterministic',ring_intervention)
    def refusals():
        values=[]
        def refuse(name,cfg,**kwargs):
            try:core.experiment(cfg,**kwargs)
            except ValueError as e:values.append(dict(name=name,error=str(e)))
            else:raise AssertionError('Invalid geometry/input admitted: '+name)
        for value in [True,None,'1',float('nan'),float('inf'),0,-1,1<<10000]:
            cfg=copy.deepcopy(base_cfg);cfg['GM_m3_s2']=value;refuse('invalid-GM-'+str(type(value).__name__)+('-nonfinite' if isinstance(value,float) and not math.isfinite(value) else ''),cfg)
        cfg=copy.deepcopy(base_cfg);cfg['unexpected']=1;refuse('unknown-field',cfg)
        for value in [[1,2],True,[0,0,float('nan')],[0,0,1e26]]:
            cfg=copy.deepcopy(base_cfg);cfg['observer_m']=value;refuse('invalid-observer-vector-'+str(len(values)),cfg)
        cfg=copy.deepcopy(base_cfg);cfg['lens_m']=cfg['observer_m'];refuse('coincident-observer-lens',cfg)
        cfg=copy.deepcopy(base_cfg);cfg['source_m']=[0,0,1e19];refuse('source-in-front-of-lens',cfg)
        cfg=copy.deepcopy(base_cfg);cfg['source_m']=[0,0,1e20];refuse('source-in-lens-plane',cfg)
        refuse('near-nonzero-caustic-below-resolution-domain',inputs(1e-8))
        refuse('finite-u-too-large',inputs(1.01e4))
        cfg=copy.deepcopy(base_cfg);cfg['source_m'][0]=.02*cfg['source_m'][2];refuse('source-angle-too-large',cfg)
        cfg=inputs(5000.,mass=10000.);refuse('secondary-image-outside-weak-impact-domain',cfg)
        cfg=inputs(1.,mass=1e15);cfg['source_m'][0]=0;refuse('einstein-ring-angle-or-impact-outside-domain',cfg)
        refuse('nonboolean-operator',base_cfg,bending=1)
        proof['refusals']=values
        return dict(refusals=len(values))
    check('invalid-input-planes-caustic-angle-and-secondary-impact-are-refused',refusals)
    def weak_limit():
        sys.path.insert(0,str(PRODUCT/'app'));import relativity
        values=[]
        for b in [1000.,3000.,10000.]:
            exact=relativity.trace_ray(b,tolerance=1e-12)
            approx=2/b
            assert exact['status']=='escaped'
            difference=abs(exact['deflection_rad']-approx)/approx
            assert difference<.01
            values.append(dict(impact_rs=b,exact_deflection_rad=exact['deflection_rad'],first_order_deflection_rad=approx,relative_difference=difference))
        assert all(b['relative_difference']<a['relative_difference'] for a,b in zip(values,values[1:]))
        return dict(cases=values,scope='Asymptotic deflection term only, not the complete finite-plane lens geometry.')
    check('existing-null-geodesic-reference-approaches-first-order-deflection',weak_limit)
    def unchanged():
        assert all(sha(ROOT/n)==s for n,s in sources.items())
        assert all(sha(ROOT/n)==s for n,s in protected.items())
        assert all(sha(PRODUCT/n)==s for n,s in manifest['files_sha256'].items())
        return dict(protected_file_sha256=protected)
    check('sources-owner-session-selection-and-delivered-product-are-unchanged',unchanged)
    proof['raw_model_sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in (FOLDER/'model-results').glob('*.json')}
    proof.update(completed=True,accepted=all(c['passed'] for c in proof['checks']))
    persist();print(json.dumps(dict(accepted=proof['accepted'],completed=True,groups=len(proof['checks']),refusals=len(proof['refusals']),failures=[c for c in proof['checks'] if not c['passed']]),ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
