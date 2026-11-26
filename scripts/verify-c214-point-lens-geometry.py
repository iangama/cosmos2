"""Oblique moving-observer geometry and the physical sign of the broken-ray turn."""
from pathlib import Path
import copy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import json
import math
import sys
import traceback
import zipfile

import mpmath as mp

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'output/c214-point-lens-geometry-20261121a'
OUT=ROOT/'evidence/c214-point-lens-geometry-20261121a.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def rotate(v,a):
    c,s=math.cos(a),math.sin(a);d,t=math.cos(a*.7),math.sin(a*.7)
    x,y,z=c*v[0]-s*v[1],s*v[0]+c*v[1],v[2]
    return [d*x+t*z,y,-t*x+d*z]


def main():
    assert not OUT.exists() and not FOLDER.exists();FOLDER.mkdir()
    prior_path=ROOT/'evidence/c214-point-lens-offline-20261121b.json';prior=json.loads(prior_path.read_text())
    assert prior['accepted'] and prior['completed']
    assert all(sha(ROOT/n)==seal for n,seal in prior['source_sha256'].items())
    old=SourceFileLoader('point_lens_geometry_reference',str(ROOT/'scripts/verify-c214-point-lens.py')).load_module()
    cases=[];shift=[3e15,-5e15,7e15]
    for a in [.2,1.1,2.2]:
        for u in [.001,.1,1.,100.]:
            cfg=old.inputs(u);cfg['source_m'][1]=cfg['source_m'][0]*.7
            for name in ['observer_m','lens_m','source_m']:cfg[name]=[v+s for v,s in zip(rotate(cfg[name],a),shift)]
            cases.append(dict(rotation=a,u_recipe=u,configuration=cfg))
    sources=prior['source_sha256']|{prior_path.relative_to(ROOT).as_posix():sha(prior_path),Path(__file__).relative_to(ROOT).as_posix():sha(Path(__file__))}
    recipe=dict(source_sha256=sources,cases=cases,arithmetic_digits=110,
      comparison='Reconstruct image intersections independently along the world-space source offset using numerical roots. Compare serialized world coordinates within4ULPs and ray-plane closure within summed coordinate resolution.',
      turn='S-to-lens and lens-to-O directions must turn toward the mass: opposite transverse sign to lens-equation alpha. Relative broken-line turn discrepancy≤1e-4 includes paraxial construction and serialized coordinate spacing.')
    (FOLDER/'recipe-before-execution.json').write_text(json.dumps(recipe,indent=2)+'\n')
    with zipfile.ZipFile(FOLDER/'executed-sources.zip','x',zipfile.ZIP_DEFLATED) as archive:
        for name in sources:archive.write(ROOT/name,name)
    spec=importlib.util.spec_from_file_location('point_lens_oblique_candidate',ROOT/'output/c214-point-lens-staging/point_lens.py')
    core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
    proof=dict(accepted=False,completed=False,source_sha256=sources,cases=[],
      scope='Supplementary CPU geometry only: arbitrary observer offset, oblique optical axis, two source offsets, world ray/plane closure and physical turn sign. No live UI/scientific milestone promotion.')
    try:
        mp.mp.dps=110
        for index,item in enumerate(cases):
            cfg=item['configuration'];value=core.experiment(cfg);ref=old.oracle(cfg)
            old.relative(value['reference']['magnification_total'],ref['total'])
            o,l,s=[mp.matrix([mp.mpf(x) for x in cfg[k]]) for k in ['observer_m','lens_m','source_m']]
            n=(l-o)/ref['Dl'];transverse=s-o-ref['Ds']*n;axis=transverse/mp.norm(transverse)
            highest_turn_error=0.
            for image,theta,mu in zip(value['reference']['images'],ref['theta'],ref['magnifications']):
                old.relative(image['magnification_signed'],mu)
                expected=l+ref['Dl']*theta*axis
                point=mp.matrix([mp.mpf(x) for x in image['lens_plane_world_m']])
                for actual,e in zip(image['lens_plane_world_m'],expected):assert abs(actual-float(e))<=4*math.ulp(float(e))
                ulps=sum(math.ulp(x) for x in image['lens_plane_world_m'])+sum(math.ulp(x) for x in cfg['lens_m'])
                assert abs(mp.fdot(point-l,n))<=32*ulps
                assert image['ray_vertices_world_m'][0]==cfg['observer_m'] and image['ray_vertices_world_m'][2]==cfg['source_m']
                incoming=(point-s)/mp.norm(point-s);outgoing=(o-point)/mp.norm(o-point)
                ex,ey=[mp.matrix([mp.mpf(x) for x in value['geometry'][k]]) for k in ['sky_x_unit','sky_y_unit']]
                turn=mp.matrix([mp.fdot(outgoing-incoming,e) for e in [ex,ey]])
                alpha=mp.matrix([mp.mpf(x) for x in image['lens_equation_deflection_sky_rad']])
                assert mp.fdot(turn,alpha)<0,'Photon turn points away from the lens'
                error=float(mp.norm(turn+alpha)/mp.norm(alpha));assert error<=1e-4,error
                highest_turn_error=max(highest_turn_error,error)
                for a,b in zip(image['propagating_turn_sky_rad'],image['lens_equation_deflection_sky_rad']):assert a==-b
            path=FOLDER/f'case-{index:02d}.json';path.write_text(json.dumps(value,allow_nan=False)+'\n')
            proof['cases'].append(dict(rotation=item['rotation'],u_recipe=item['u_recipe'],maximum_relative_turn_discrepancy=highest_turn_error,raw_sha256=sha(path)))
        cfg=old.inputs();cfg['lens_m']=rotate(cfg['lens_m'],1.1);cfg['source_m']=[2*x for x in cfg['lens_m']]
        ring=core.experiment(cfg)
        assert ring['geometry']['exact_stored_coordinate_alignment'] and ring['reference']['magnification_total'] is None
        proof['oblique_exact_alignment']='Ring limit, no arbitrary image directions or finite amplification.'
        assert all(sha(ROOT/n)==seal for n,seal in sources.items())
        proof.update(accepted=True,completed=True)
    except Exception:proof['failure']=traceback.format_exc()
    OUT.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({k:proof.get(k) for k in ['accepted','completed','failure','oblique_exact_alignment']}))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
