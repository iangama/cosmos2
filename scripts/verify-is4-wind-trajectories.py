"""Prescribed wind full-orbit Boris versus an independent spherical SI DOP853 RHS."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys
import time
import traceback
import zipfile
import numpy as np
import scipy
from scipy.integrate import solve_ivp
import scipy.integrate._ivp.rk as rk_source

ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/is4-solar-wind-staging';APP=ROOT/'output/is4-body-particle-product0.8.1/app'
sys.path[:0]=[str(STAGE),str(APP)]
from is4_wind_field import DEFAULT,AU_M
from is4_wind_snapshot import Snapshot
from is4_wind_diagnostics import potential_differences
from is4_particles import Phase,boris_step
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def spherical_fields(x,cfg):
    # Independent spherical basis and components; never call Parker/Snapshot.
    r=np.linalg.norm(x);rho=math.hypot(x[0],x[1]);er=x/r
    ep=np.array([-x[1]/rho,x[0]/rho,0.]);et=np.array([x[2]*x[0]/(r*rho),x[2]*x[1]/(r*rho),-rho/r])
    br=cfg['polarity']*(1 if x[2]>0 else -1)*cfg['radial_field_at_AU_T']*(AU_M/r)**2
    bp=-br*cfg['rotation_rate_rad_s']*rho/cfg['wind_speed_m_s']
    return br*er+bp*ep,cfg['wind_speed_m_s']*bp*et,cfg['wind_speed_m_s']*er

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);parser.add_argument('--only');args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/('output/is4-wind-trajectories-'+args.label);receipt=ROOT/('evidence/is4-wind-trajectories-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve trajectories')
    for name in ['is4-wind-field-20261025c.json','is4-wind-potential-20261025a.json']:assert json.loads((ROOT/'evidence'/name).read_text())['accepted']
    folder.mkdir();fixture=ROOT/'output/is4-body-snapshot-20261025b/IGRF14-13.json';phase=json.loads(fixture.read_text())['phase']
    constants=json.loads((STAGE/'constants.json').read_text());charge=constants['elementary_charge_C']['value']
    cases=[]
    for species,radius,lat,polarity in [('proton',.3,10.,1),('electron',.3,-10.,1),('electron',1.,30.,-1),('proton',1.,-30.,-1),('proton',5.,60.,1),('electron',5.,-60.,-1)]:
        cases.append(dict(id=species+'-r'+str(radius)+'-lat'+str(lat)+'-p'+str(polarity),radius_AU=radius,latitude_deg=lat,polarity=polarity,charge_C=charge if species=='proton' else -charge,mass_kg=constants[species+'_mass_kg']['value'],relative_speed_m_s=1e5 if species=='proton' else 1e6,pitch_deg=60.,periods=10.,refine=True,synthetic=False,controls=dict(electric=True,magnetic=True,gravity=True)))
    cases.append(dict(id='synthetic-gradient-energy',radius_AU=1.,latitude_deg=30.,polarity=1,charge_C=3000.,mass_kg=1.,relative_speed_m_s=1e5,pitch_deg=60.,periods=1.,refine=True,synthetic=True,controls=dict(electric=True,magnetic=True,gravity=True)))
    for control in ['electric','magnetic','gravity','neutral']:
        case={**cases[0],'id':'control-'+control,'refine':False,'controls':{k:k!=control for k in ['electric','magnetic','gravity']}}
        if control=='neutral':case['charge_C']=0.
        if control=='magnetic':case['periods']=.1
        cases.append(case)
    if args.only:
        cases=[c for c in cases if c['id']==args.only]
        if not cases:raise ValueError('Unknown case')
    casefile=folder/'cases.json';casefile.write_text(json.dumps(cases,indent=2)+'\n')
    files=[*STAGE.glob('*.py'),STAGE/'constants.json',Path(__file__),fixture,casefile,ROOT/'IS-4-VENTO-SOLAR-CONTRATO-PREVIO.md',Path(rk_source.__file__)]
    hashes={f.relative_to(ROOT).as_posix():sha(f) for f in files if f.is_relative_to(ROOT)}
    with zipfile.ZipFile(folder/'executed-sources-and-fixtures.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
        z.write(Path(rk_source.__file__),'dependency/scipy-integrate-rk.py')
    report=dict(schema=1,accepted=False,completed=False,source_sha256=hashes,scipy_version=scipy.__version__,DOP853_source_sha256=sha(Path(rk_source.__file__)),cases=[],selected_case=args.only)
    def persist():receipt.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    persist()
    try:
        for case in cases:
            began=time.perf_counter();print(json.dumps(dict(case=case['id'],stage='reference')),flush=True)
            cfg={**DEFAULT,'polarity':case['polarity']};model=Snapshot(phase,cfg);lat=math.radians(case['latitude_deg']);seed=case['radius_AU']*AU_M*np.array([math.cos(lat),0.,math.sin(lat)])
            B0,E0,u0=spherical_fields(seed,cfg);direction=B0/np.linalg.norm(B0);axis=np.eye(3)[int(np.argmin(abs(direction)))];side=np.cross(direction,axis);side/=np.linalg.norm(side)
            pitch=math.radians(case['pitch_deg']);velocity=u0+case['relative_speed_m_s']*(math.sin(pitch)*side+math.cos(pitch)*direction)
            q,m=case['charge_C'],case['mass_kg'];nominal_q=charge if q==0 else abs(q);omega=nominal_q/m*np.linalg.norm(B0);period=2*math.pi/omega;duration=case['periods']*period;rho=case['relative_speed_m_s']*math.sin(pitch)/omega
            descriptor=model.descriptor;rotation=np.array(descriptor['model_to_J2000']);sun=next(b for b in phase['bodies'] if b['reference_id']=='sol:naif:10')
            offsets=np.array([(np.array(b['position'])-sun['position'])*phase['physical_scale']['length_unit_m'] for b in phase['bodies']]);gms=np.array([b['mass']*phase['physical_scale']['nominal_GM_unit_m3_s2'] for b in phase['bodies']])
            controls=case['controls']
            def rhs(t,y):
                x=seed+y[:3];B,E,u=spherical_fields(x,cfg);delta=rotation@x-offsets;radii=np.linalg.norm(delta,axis=1)
                g=rotation.T@np.sum(-gms[:,None]*delta/radii[:,None]**3,axis=0) if controls['gravity'] else np.zeros(3)
                return np.r_[y[3:],g+(q/m)*((E if controls['electric'] else np.zeros(3))+np.cross(y[3:],B if controls['magnetic'] else np.zeros(3)))]
            reference=solve_ivp(rhs,[0.,duration],np.r_[np.zeros(3),velocity],method='DOP853',rtol=1e-11,atol=np.array([1e-7]*6),dense_output=True,max_step=period/12)
            assert reference.success,reference.message
            rows=[];K0=.5*m*float(np.dot(velocity,velocity))
            for count in ([2000,4000,8000] if case['refine'] else [8000]):
                state=Phase(tuple(float(v) for v in seed),tuple(float(v) for v in velocity));h=duration/count;positions=[];speeds=[];energies=[];work_residual=0.;states=[]
                for step in range(count):
                    old=state;state,d=boris_step(model,state,float(q),float(m),float(h),electric_acting=controls['electric'],magnetic_acting=controls['magnetic'],gravity_acting=controls['gravity'])
                    scale=.5*m*math.fsum(v*v for v in old.velocity_m_s)+abs(d['electric_work_J'])+abs(d['gravity_work_J'])
                    work_residual=max(work_residual,abs(d['kinetic_change_J']-d['electric_work_J']-d['gravity_work_J'])/scale)
                    if (step+1)%(count//40)==0:
                        truth=reference.sol(state.time_s);positions.append(float(np.linalg.norm(np.array(state.position_offset_m)-truth[:3])));speeds.append(float(np.linalg.norm(np.array(state.velocity_m_s)-truth[3:])))
                        potential=potential_differences(model,seed.tolist(),[0.,0.,0.],state.position_offset_m)
                        deltaK=.5*m*float(np.dot(np.array(state.velocity_m_s)-velocity,np.array(state.velocity_m_s)+velocity))
                        energy=deltaK+(q*potential['electric_potential_change_V'] if controls['electric'] else 0.)+(m*potential['gravity_potential_change_J_kg'] if controls['gravity'] else 0.)
                        energies.append(energy);states.append(dict(time_s=state.time_s,position_m=state.position_m,position_origin_m=state.position_origin_m,position_offset_m=state.position_offset_m,velocity_m_s=state.velocity_m_s,reference_offset_m=truth[:3].tolist(),reference_velocity_m_s=truth[3:].tolist(),potentials=potential,energy_change_J=energy))
                path=folder/(case['id']+'-'+str(count)+'.json');path.write_text(json.dumps(dict(states=states),indent=2)+'\n')
                row=dict(steps=count,maximum_position_error_m=max(positions),maximum_velocity_error_m_s=max(speeds),energy_error_J=max(abs(v) for v in energies),energy_error_relative_K0=max(abs(v) for v in energies)/K0,work_residual_relative=work_residual,trajectory=path.relative_to(ROOT).as_posix(),trajectory_sha256=sha(path));rows.append(row)
                print(json.dumps(dict(case=case['id'],**row)),flush=True)
            result=dict(id=case['id'],fixture=case,initial_K_J=K0,initial_gyroradius_m=float(rho),duration_s=float(duration),reference_evaluations=reference.nfev,refinement=rows,seconds=time.perf_counter()-began)
            report['pending_case']=result;persist()
            if case['refine']:
                ratios=[rows[i]['maximum_position_error_m']/rows[i+1]['maximum_position_error_m'] for i in range(2)];result['position_error_ratios']=ratios
                assert all(3.4<=v<=4.6 for v in ratios),('position convergence',case['id'],ratios)
                er=[rows[i]['energy_error_J']/rows[i+1]['energy_error_J'] for i in range(2)];result['energy_error_ratios']=er
                for i,ratio in enumerate(er):
                    if case['synthetic'] or rows[i+1]['energy_error_relative_K0']>1e-11:assert 3.4<=ratio<=4.6,('energy convergence',case['id'],er)
            assert rows[-1]['maximum_position_error_m']<=5e-4*rho+1e-4
            assert rows[-1]['maximum_velocity_error_m_s']<=5e-4*max(case['relative_speed_m_s'],float(np.linalg.norm(velocity)))
            assert all(row['work_residual_relative']<=1e-12 for row in rows)
            report['cases'].append(result);report.pop('pending_case');persist()
        assert all(sha(ROOT/n)==v for n,v in hashes.items())
        report.update(accepted=True,completed=True,scope='Prescribed Parker SI with four frozen monopoles: six physical ten-period cases, synthetic spatial-energy case and four controls, independent spherical DOP853 plus refinement/work/energy. No product/native/persistence/performance or plasma/MHD acceptance.')
    except Exception:report['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps(dict(accepted=report['accepted'],cases=len(report['cases']),failure=report.get('failure'))),flush=True)
    return 0 if report['accepted'] else 1

if __name__=='__main__':raise SystemExit(main())
