"""Analytic chord/tangent/outer-boundary fixtures plus the missing neutral-particle limit."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import traceback
import zipfile
ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/is4-body-particle-staging';sys.path.insert(0,str(STAGE))
from is4_domains import outside_ellipsoid,shell_segment
from is4_particles import Phase,boris_step
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    receipt=ROOT/('evidence/is4-domain-segments-'+args.label+'.json');folder=ROOT/('output/is4-domain-segments-'+args.label)
    if receipt.exists() or folder.exists():raise FileExistsError('Preserve geometry evidence.')
    folder.mkdir();files=[*STAGE.glob('*.py'),Path(__file__)];hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    r={'schema':1,'accepted':False,'completed':False,'source_sha256':hashes}
    try:
        fixtures=[([-2.,0.,0.],[2.,0.,0.],False),([-2.,1.,0.],[2.,1.,0.],True),
                  ([2.,0.,0.],[2.,1.,0.],True),([0.,0.,0.],[0.,0.,0.],False),
                  ([1.,0.,0.],[1.,0.,0.],True),([4.,0.,0.],[4.,1.,0.],False)]
        for a,b,expected in fixtures:assert shell_segment(a,b,1.,3.) is expected,(a,b)
        # Oblate ellipsoid axes2/2/1: crossing polar/equatorial interior,
        # polar tangent, equatorial tangent and fixed exterior point.
        oblate=[([0.,0.,-2.],[0.,0.,2.],False),([-3.,0.,0.],[3.,0.,0.],False),
                ([-3.,0.,1.],[3.,0.,1.],True),([2.,-3.,0.],[2.,3.,0.],True),([0.,0.,2.],[0.,0.,2.],True)]
        for a,b,expected in oblate:assert outside_ellipsoid(a,b,[2.,2.,1.]) is expected
        try:outside_ellipsoid([1e308,0.,0.],[1e308,0.,0.],[1.,1.,1.])
        except ValueError:pass
        else:raise AssertionError('Unrepresentable finite geometry was accepted.')
        class Uniform:
            def segment_in_domain(self,a,b):return True
            def evaluate(self,p):return {'valid':True,'electric_field_V_m':[100.,200.,300.],'magnetic_field_T':[0.,0.,1e5],'gravity_m_s2':[0.,-2.,0.]}
        phase=Phase((2.,3.,4.),(1.,2.,3.))
        for _ in range(100):phase,_=boris_step(Uniform(),phase,0.,1.,.01)
        assert max(abs(a-b) for a,b in zip(phase.position_m,[3.,4.,7.]))<1e-12
        assert max(abs(a-b) for a,b in zip(phase.velocity_m_s,[1.,0.,3.]))<1e-12
        assert all(sha(ROOT/name)==value for name,value in hashes.items())
        r.update(accepted=True,completed=True,analytic_segment_cases=len(fixtures)+len(oblate),neutral_q0_with_E_B_gravity=True,
            scope='Analytic straight-segment inner ellipsoid/outer sphere geometry and neutral Lorentz limit only. No actual IGRF geodetic outer-shell adapter, four-center snapshot, body ODE or native acceptance.')
    except Exception:r['failure']=traceback.format_exc()
    receipt.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps({'accepted':r['accepted'],'failure':r.get('failure')}))
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
