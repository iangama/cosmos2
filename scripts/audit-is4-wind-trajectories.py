"""Recompute raw trajectory errors and static energy using Decimal60 potentials."""
from pathlib import Path
from decimal import Decimal,localcontext
import argparse
import hashlib
import json
import math
import sys
import traceback
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/is4-solar-wind-staging';APP=ROOT/'output/is4-body-particle-product0.8.1/app'
sys.path[:0]=[str(STAGE),str(APP)]
from is4_wind_field import DEFAULT,AU_M
from is4_wind_snapshot import Snapshot
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
D=Decimal.from_float

def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--audit-label');args=p.parse_args()
    label=args.audit_label or args.label
    if any(not s or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in s) for s in [label,args.label]):p.error('Invalid label')
    path=ROOT/('evidence/is4-wind-trajectories-'+args.label+'.json');out=ROOT/('evidence/is4-wind-trajectories-audit-'+label+'.json')
    if out.exists():raise FileExistsError('Preserve audit')
    r=json.loads(path.read_text());result=dict(schema=1,accepted=False,source=path.relative_to(ROOT).as_posix(),source_sha256=sha(path),auditor_sha256=sha(Path(__file__)),cases=[])
    try:
        assert r['accepted'] and r['completed'] and len(r['cases'])==11 and not r.get('failure')
        with zipfile.ZipFile(ROOT/('output/is4-wind-trajectories-'+args.label+'/executed-sources-and-fixtures.zip')) as z:
            assert all(hashlib.sha256(z.read(n)).hexdigest()==v for n,v in r['source_sha256'].items())
            assert hashlib.sha256(z.read('dependency/scipy-integrate-rk.py')).hexdigest()==r['DOP853_source_sha256']
        assert all(sha(ROOT/n)==v for n,v in r['source_sha256'].items())
        phase=json.loads((ROOT/'output/is4-body-snapshot-20261025b/IGRF14-13.json').read_text())['phase']
        with localcontext() as ctx:
            ctx.prec=60
            for case in r['cases']:
                cfg={**DEFAULT,'polarity':case['fixture']['polarity']};model=Snapshot(phase,cfg);c=case['fixture'];rows=[]
                lat=math.radians(c['latitude_deg']);origin=c['radius_AU']*AU_M*np.array([math.cos(lat),0.,math.sin(lat)])
                # Independent Cartesian construction for the initial velocity;
                # the tested ODE used a spherical construction at every point.
                radius=np.linalg.norm(origin);a=cfg['radial_field_at_AU_T']*AU_M**2;p_sign=c['polarity']*(1 if origin[2]>0 else -1)
                B=p_sign*a*(origin/radius**3+cfg['rotation_rate_rad_s']/(cfg['wind_speed_m_s']*radius**2)*np.array([origin[1],-origin[0],0.]))
                direction=B/np.linalg.norm(B);axis=np.eye(3)[int(np.argmin(abs(direction)))];side=np.cross(direction,axis);side/=np.linalg.norm(side)
                velocity=cfg['wind_speed_m_s']*origin/radius+c['relative_speed_m_s']*(math.sin(math.radians(c['pitch_deg']))*side+math.cos(math.radians(c['pitch_deg']))*direction)
                K=.5*c['mass_kg']*float(np.dot(velocity,velocity));assert math.isclose(K,case['initial_K_J'],rel_tol=2e-14)
                rho=c['relative_speed_m_s']*math.sin(math.radians(c['pitch_deg']))/(abs(c['charge_C'] or 1.602176634e-19)/c['mass_kg']*np.linalg.norm(B))
                assert math.isclose(rho,case['initial_gyroradius_m'],rel_tol=2e-14)
                radiusD=lambda x:sum(v*v for v in x).sqrt()
                o=[D(float(v)) for v in origin];v0=[D(float(v)) for v in velocity]
                phi=lambda x:-D(float(c['polarity']))*D(cfg['rotation_rate_rad_s'])*D(cfg['radial_field_at_AU_T'])*D(AU_M)**2*abs(x[2])/radiusD(x)
                p0=phi(o);g0=sum(-D(s.GM_m3_s2)/radiusD([x-D(y) for x,y in zip(o,s.position_model_m)]) for s in model.sources)
                maximum_decimal_difference=0.
                for row in case['refinement']:
                    file=ROOT/row['trajectory'];assert sha(file)==row['trajectory_sha256'];states=json.loads(file.read_text())['states'];assert len(states)==40
                    pe=[];ve=[];energies=[];lasttime=0.
                    for s in states:
                        assert s['time_s']>lasttime;lasttime=s['time_s'];assert s['position_origin_m']==origin.tolist()
                        assert [math.fsum([x,y]) for x,y in zip(s['position_origin_m'],s['position_offset_m'])]==s['position_m']
                        pe.append(math.dist(s['position_offset_m'],s['reference_offset_m']));ve.append(math.dist(s['velocity_m_s'],s['reference_velocity_m_s']))
                        x=[a+D(b) for a,b in zip(o,s['position_offset_m'])];v=[D(a) for a in s['velocity_m_s']]
                        deltaK=D(.5)*D(c['mass_kg'])*sum((a-b)*(a+b) for a,b in zip(v,v0))
                        de=phi(x)-p0;dg=sum(-D(source.GM_m3_s2)/radiusD([a-D(b) for a,b in zip(x,source.position_model_m)]) for source in model.sources)-g0
                        energy=deltaK+(D(c['charge_C'])*de if c['controls']['electric'] else Decimal(0))+(D(c['mass_kg'])*dg if c['controls']['gravity'] else Decimal(0))
                        error=abs(float(energy)-s['energy_change_J']);maximum_decimal_difference=max(maximum_decimal_difference,error/K)
                        # Initial basis rounding and final dot-product arithmetic
                        # may differ by a few ulps of K; do not test cancellation
                        # against the tiny energy residual's own magnitude.
                        assert error<=2e-13*K,(case['id'],row['steps'],error/K)
                        energies.append(abs(float(energy)))
                    assert math.isclose(max(pe),row['maximum_position_error_m'],rel_tol=1e-12,abs_tol=1e-10)
                    assert math.isclose(max(ve),row['maximum_velocity_error_m_s'],rel_tol=1e-12,abs_tol=1e-10)
                    assert row['work_residual_relative']<=1e-12
                    rows.append(dict(steps=row['steps'],position_error_m=max(pe),velocity_error_m_s=max(ve),decimal_energy_error_J=max(energies),decimal_energy_error_relative_K0=max(energies)/K))
                if c['refine']:
                    ratios=[rows[i]['position_error_m']/rows[i+1]['position_error_m'] for i in range(2)];assert all(3.4<=v<=4.6 for v in ratios)
                    for i in range(2):
                        if c['synthetic'] or rows[i+1]['decimal_energy_error_relative_K0']>1e-11:assert 3.4<=rows[i]['decimal_energy_error_J']/rows[i+1]['decimal_energy_error_J']<=4.6
                assert rows[-1]['position_error_m']<=5e-4*rho+1e-4
                assert rows[-1]['velocity_error_m_s']<=5e-4*max(c['relative_speed_m_s'],float(np.linalg.norm(velocity)))
                result['cases'].append(dict(id=case['id'],refinement=rows,maximum_energy_recalculation_difference_relative_K0=maximum_decimal_difference))
        result.update(accepted=True,scope='Recomputed raw paired-coordinate errors and Decimal60 static energy, eleven preserved Parker test cases. Does not replace field/model, product, persistence or performance validation.')
    except Exception:result['failure']=traceback.format_exc()
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(accepted=result['accepted'],cases=len(result['cases']),failure=result.get('failure'))))
    return 0 if result['accepted'] else 1

if __name__=='__main__':raise SystemExit(main())
