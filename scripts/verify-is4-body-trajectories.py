"""Frozen body-field Boris trajectories against an independent DOP853 RHS and step refinement."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import struct
import sys
import time
import traceback
import zipfile
import numpy as np
import scipy
from scipy.integrate import solve_ivp
import scipy.integrate._ivp.rk as rk_source

ROOT=Path(__file__).resolve().parents[1];APP=ROOT/'output/is3-body-points-product/app';STAGE=ROOT/'output/is4-body-particle-staging'
sys.path[:0]=[str(STAGE),str(APP)]
from body_field_lines import Model
from is4_body_snapshot import Snapshot
from is4_particles import Phase,boris_step
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);parser.add_argument('--only');parser.add_argument('--prior');args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    folder=ROOT/('output/is4-body-trajectories-'+args.label);receipt=ROOT/('evidence/is4-body-trajectories-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve trajectory evidence.')
    assert json.loads((ROOT/'evidence/is4-body-snapshot-20261025b.json').read_text(encoding='utf-8'))['accepted']
    folder.mkdir();constants=json.loads((STAGE/'constants.json').read_text(encoding='utf-8'));q_unit=constants['elementary_charge_C']['value']
    fixtures=[]
    for model,degree in [('IGRF14',13),('JRM33',1),('JRM33',13),('JRM33',18)]:
        source=ROOT/('output/is4-body-snapshot-20261025b/'+model+'-'+str(degree)+'.json')
        data=json.loads(source.read_text(encoding='utf-8'))
        for sign in [-1,1]:fixtures.append({'id':model+'-'+str(degree)+'-proton-mass-sign'+str(sign),'data':data,'charge_C':sign*q_unit,
            'mass_kg':constants['proton_mass_kg']['value'],'speed_m_s':1e5,'pitch_deg':60.,'periods':10.,'origin':'Prescribed test charge with proton mass and declared sign; no collective/reaction/annihilation model.'})
        if degree==13:
            fixtures.append({'id':model+'-electron','data':data,'charge_C':-q_unit,'mass_kg':constants['electron_mass_kg']['value'],
                'speed_m_s':1e6,'pitch_deg':60.,'periods':10.,'origin':'Prescribed electron test; no radiation/collective response.'})
    # Supplement: comparable Lorentz/gravity accelerations, one gyro period.
    # It supplements all ten-period physical cases; it does not replace them.
    synthetic=copy.deepcopy(fixtures[0]['data']);p=synthetic['phase'];body=next(b for b in p['bodies'] if b['reference_id']=='sol:naif:399')
    from earth_magnetism import read
    synthetic['reading']={**read(p,body['id'],-23.55,-46.63,500000.),'scientific_generation':p['scientific_generation']}
    b0=Model(synthetic['reading']).field(synthetic['reading']['point_ITRF93_m'])
    fixtures.append({'id':'IGRF14-synthetic-balanced','data':synthetic,'charge_C':.1/math.hypot(*b0),'mass_kg':1.,
        'speed_m_s':100.,'pitch_deg':90.,'periods':1.,'origin':'Synthetic q/m with omega0=0.1/s to compare gravity and Lorentz; not a physical particle species.'})
    if args.only:
        fixtures=[case for case in fixtures if case['id']==args.only]
        if not fixtures:raise ValueError('Unknown case filter.')
    fixture_path=folder/'cases.json';fixture_path.write_text(json.dumps(fixtures,indent=2)+'\n',encoding='utf-8')
    files=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]+[*STAGE.glob('*.py'),STAGE/'constants.json',Path(__file__),ROOT/'IS-4-PARTICULAS-CONTRATO-PREVIO.md',fixture_path]
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(folder/'executed-sources-and-fixtures.zip','w',zipfile.ZIP_DEFLATED) as z:
        for path in files:z.write(path,path.relative_to(ROOT).as_posix())
        z.write(Path(rk_source.__file__),'dependency/scipy-integrate-rk.py')
    report={'schema':1,'accepted':False,'completed':False,'source_sha256':hashes,'scipy_version':scipy.__version__,
        'DOP853_source_sha256':sha(Path(rk_source.__file__)),'selected_case':args.only,'state_comparison_prior':args.prior,'criteria':{'rtol':1e-11,'atol_SI':[1e-11]*3+[1e-7]*3,
        'counts':[2000,4000,8000],'refinement_ratio':[3.4,4.6],'fine_position_m':'5e-4 initial gyroradius + 1e-5m',
        'fine_velocity_relative':5e-4,'work_residual_relative':1e-12},'cases':[]}
    def persist():receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    persist()
    try:
        for case in fixtures:
            began=time.perf_counter();print(json.dumps({'case':case['id'],'phase':'reference'}),flush=True)
            p,r=case['data']['phase'],case['data']['reading'];model=Snapshot(p,r);trusted=Model(r)
            seed=np.array(model.seed_m);B0=np.array(trusted.field(seed.tolist()));direction=B0/np.linalg.norm(B0)
            axis=np.eye(3)[int(np.argmin(np.abs(direction)))];perpendicular=np.cross(direction,axis);perpendicular/=np.linalg.norm(perpendicular)
            angle=math.radians(case['pitch_deg']);velocity=case['speed_m_s']*(math.sin(angle)*perpendicular+math.cos(angle)*direction)
            q,mass=case['charge_C'],case['mass_kg'];omega=abs(q/mass)*np.linalg.norm(B0);period=2*math.pi/omega;duration=case['periods']*period
            gyroradius=case['speed_m_s']*math.sin(angle)/omega
            rotation=np.array(r['ITRF93_to_J2000' if trusted.name=='IGRF14' else 'SystemIII_to_J2000'])
            selected=next(b for b in p['bodies'] if b['id']==r['body_id']);length=p['physical_scale']['length_unit_m'];unit=p['physical_scale']['nominal_GM_unit_m3_s2']
            offsets=np.array([(np.array(b['position'])-selected['position'])*length for b in p['bodies']]);gms=np.array([b['mass']*unit for b in p['bodies']])
            def rhs(t,y):
                # Integrate displacement to avoid the large absolute coordinate
                # setting DOP853's position tolerance. This RHS never calls Snapshot.
                x=seed+y[:3];delta=rotation@x-offsets;radii=np.linalg.norm(delta,axis=1)
                gravity=rotation.T@np.sum(-gms[:,None]*delta/radii[:,None]**3,axis=0)
                field=np.array(trusted.field(x.tolist()))
                return np.r_[y[3:],gravity+(q/mass)*np.cross(y[3:],field)]
            reference=solve_ivp(rhs,[0.,duration],np.r_[np.zeros(3),velocity],method='DOP853',rtol=1e-11,
                atol=np.array([1e-11]*3+[1e-7]*3),dense_output=True,max_step=period/12)
            assert reference.success,reference.message
            rows=[]
            for count in [2000,4000,8000]:
                state=Phase(tuple(float(x) for x in seed),tuple(float(v) for v in velocity));h=duration/count;positions=[];speeds=[];energies=[];max_residual=0.;max_magnetic_power=0.
                initial=model.evaluate(state.position_m);initial_energy=.5*mass*np.dot(velocity,velocity)+mass*initial['gravity_potential_J_kg']
                initial_scale=.5*mass*np.dot(velocity,velocity)+abs(mass*initial['gravity_potential_J_kg'])
                states=[]
                for step in range(count):
                    old=state;state,d=boris_step(model,state,float(q),float(mass),float(h))
                    scale=.5*mass*sum(v*v for v in old.velocity_m_s)+abs(d['electric_work_J'])+abs(d['gravity_work_J'])
                    residual=abs(d['kinetic_change_J']-d['electric_work_J']-d['gravity_work_J'])/scale
                    max_residual=max(max_residual,residual)
                    if (step+1)%(count//40)==0:
                        truth=reference.sol(state.time_s);dx=np.array(state.position_m)-seed
                        positions.append(float(np.linalg.norm(dx-truth[:3])));speeds.append(float(np.linalg.norm(np.array(state.velocity_m_s)-truth[3:])))
                        reading=model.evaluate(state.position_m);energy=.5*mass*sum(v*v for v in state.velocity_m_s)+mass*reading['gravity_potential_J_kg']
                        stable_delta_K=.5*mass*float(np.dot(np.array(state.velocity_m_s)-velocity,np.array(state.velocity_m_s)+velocity))
                        energies.append(stable_delta_K+mass*model.potential_difference(seed.tolist(),state.position_m));states.append({'time_s':state.time_s,'position_m':state.position_m,'velocity_m_s':state.velocity_m_s,'position_origin_m':state.position_origin_m,'position_offset_m':state.position_offset_m})
                        field=np.array(model.evaluate(d['sample_position_m'])['magnetic_field_T']);average=.5*(np.array(old.velocity_m_s)+state.velocity_m_s)
                        power=float(q*np.dot(np.cross(average,field),average));max_magnetic_power=max(max_magnetic_power,abs(power))
                path=folder/(case['id']+'-'+str(count)+'.json');path.write_text(json.dumps({'states':states,'energy_changes_J':energies},indent=2)+'\n',encoding='utf-8')
                if args.prior:
                    previous=ROOT/('output/is4-body-trajectories-'+args.prior)/(case['id']+'-'+str(count)+'.json')
                    prior_states=json.loads(previous.read_text(encoding='utf-8'))['states']
                    phase_bytes=lambda row:struct.pack('<7d',row['time_s'],*row['position_m'],*row['velocity_m_s'])
                    assert len(prior_states)==len(states) and all(phase_bytes(a)==phase_bytes(b) for a,b in zip(prior_states,states)),'Scientific states changed while fixing diagnostics.'
                row={'steps':count,'maximum_position_error_m':max(positions),'maximum_velocity_error_m_s':max(speeds),
                    'work_residual_relative_max':max_residual,'energy_error_absolute_J':max(abs(x) for x in energies),
                    'energy_error_relative':max(abs(x) for x in energies)/initial_scale,'magnetic_power_abs_max_W':max_magnetic_power,
                    'trajectory':path.relative_to(ROOT).as_posix(),'trajectory_sha256':sha(path)}
                rows.append(row);print(json.dumps({'case':case['id'],**{k:row[k] for k in ['steps','maximum_position_error_m','maximum_velocity_error_m_s','work_residual_relative_max']}}),flush=True)
            ratios=[rows[i]['maximum_position_error_m']/rows[i+1]['maximum_position_error_m'] for i in range(2)]
            result={'id':case['id'],'model':trusted.name,'degree':trusted.degree,'charge_C':q,'mass_kg':mass,'duration_s':float(duration),
                'gyro_periods':case['periods'],'initial_gyroradius_m':float(gyroradius),'refinement':rows,'position_error_ratios':ratios,
                'reference_evaluations':reference.nfev,'reference_endpoint':reference.y[:,-1].tolist(),'seconds':time.perf_counter()-began}
            report['pending_case']=result;persist()
            assert all(3.4<=ratio<=4.6 for ratio in ratios),('convergence',case['id'],ratios)
            assert rows[-1]['maximum_position_error_m']<=5e-4*gyroradius+1e-5,('position',case['id'])
            assert rows[-1]['maximum_velocity_error_m_s']<=5e-4*case['speed_m_s'],('velocity',case['id'])
            assert all(row['work_residual_relative_max']<=1e-12 for row in rows),('work',case['id'])
            if case['id']=='IGRF14-synthetic-balanced':
                energy_ratios=[rows[i]['energy_error_absolute_J']/rows[i+1]['energy_error_absolute_J'] for i in range(2)]
                assert all(3.4<=ratio<=4.6 for ratio in energy_ratios),('energy_convergence',energy_ratios)
                result['energy_error_ratios']=energy_ratios
            report['cases'].append(result);report.pop('pending_case',None);persist()
        assert all(sha(ROOT/name)==value for name,value in hashes.items())
        report.update(accepted=True,completed=True,scope='Static prescribed IGRF/JRM with four-center gravity, ten gyro-period physical signed-charge cases and supplemental one-period synthetic gravity-comparable case, independent DOP853 and refinement/work/energy criteria. No live environment, source reaction, worker/native/persistence/performance acceptance.')
    except Exception:report['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps({'accepted':report['accepted'],'cases':len(report['cases']),'failure':report.get('failure')}),flush=True)
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
