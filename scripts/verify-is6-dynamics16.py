"""Own sixteen-body conversion, refusals and independent 30-day Newtonian verification."""
import argparse
import copy
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import traceback
import zipfile

import numpy as np
import rebound
import scipy
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT/'output/is6-principal-moons-navigation-product0.25.1/app'
STAGE = ROOT/'output/is6-dynamics16-staging'
sys.path[:0] = [str(STAGE), str(APP)]
import system16_import as product
import is6_principal_moons_catalog as catalog

U = product.U
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
EPOCHS = ['1995-01-01T00:00:00Z','2000-01-01T12:00:00Z','2026-10-11T12:00:00Z',
          '2030-06-15T18:30:00Z','2049-12-30T23:59:59Z']
LIMITS = dict(position_component_m=10., velocity_component_m_s=1e-5,
              refinement_position_component_m=1., relative_energy_drift=1e-9,
              normalized_linear_momentum_drift=1e-10, normalized_angular_momentum_drift=1e-10,
              inverse_position_m=.001, inverse_velocity_m_s=1e-8, acceleration_component_m_s2=1e-10)


def phase(sim):
    return np.array([[p.x,p.y,p.z,p.vx,p.vy,p.vz] for p in sim.particles])


def balances(series, masses, seconds):
    r,v = series[:,:,:3],series[:,:,3:]
    energy = .5*np.sum(masses[None,:]*np.sum(v*v,axis=2),axis=1)
    for i in range(len(masses)):
        for j in range(i+1,len(masses)):
            energy -= masses[i]*masses[j]/np.linalg.norm(r[:,i]-r[:,j],axis=1)
    momentum = np.sum(masses[None,:,None]*v,axis=1)
    angular = np.sum(masses[None,:,None]*np.cross(r,v),axis=1)
    pscale = float(np.sum(masses*np.linalg.norm(v[0],axis=1)))
    lscale = float(np.sum(masses*np.linalg.norm(np.cross(r[0],v[0]),axis=1)))
    assert energy[0] != 0 and pscale > 0 and lscale > 0
    center = np.sum(masses[None,:,None]*r,axis=1)/masses.sum()
    initial_velocity = np.sum(masses[:,None]*v[0],axis=0)/masses.sum()
    expected = center[0]+seconds[:,None]/U['time_unit_s']*initial_velocity
    return dict(relative_energy_drift=float(np.max(np.abs((energy-energy[0])/energy[0]))),
                normalized_linear_momentum_drift=float(np.max(np.linalg.norm(momentum-momentum[0],axis=1))/pscale),
                normalized_angular_momentum_drift=float(np.max(np.linalg.norm(angular-angular[0],axis=1))/lscale),
                momentum_scale_canonical=pscale,angular_scale_canonical=lscale,
                barycenter_inertial_drift_m=float(np.max(np.linalg.norm(center-expected,axis=1))*U['length_unit_m']),
                normalization='Initial nonzero total energy; sum m|v| and sum m|r cross v| in the same inertial origin.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label',required=True)
    label = parser.parse_args().label
    if not label or len(label)>20 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
        parser.error('Invalid label')
    folder = ROOT/f'output/is6-dynamics16-verification-{label}'
    out = ROOT/f'evidence/is6-dynamics16-verification-{label}.json'
    if folder.exists() or out.exists():raise FileExistsError('Preserve sixteen-body verification')
    # Keep the native performance measurement free of another numerical workload.
    profile = json.loads((ROOT/'evidence/is6-moons-layers-profile-20261112a.json').read_text())
    assert profile['completed'] and profile.get('processes') and profile.get('owner_app_kept_open')
    folder.mkdir()
    files = [Path(__file__),Path(product.__file__),Path(catalog.__file__),ROOT/'IS-6-DINAMICA16-CONTRATO.md',
             APP/'physics.py',APP/'atlas_import.py',APP/'solar_import.py',APP/'import_dispatch.py',catalog.DATA,
             ROOT/'data/science/canonical-units.json',ROOT/'scripts/audit-is6-dynamics16.py']
    files += [p for p in APP.glob('*.py')]
    files += [ROOT/name for name in catalog._data()['runtime_sha256']]
    sources = {p.relative_to(ROOT).as_posix():sha(p) for p in files}
    archive = folder/'executed-sources.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name in sources:z.write(ROOT/name,name)
    protected = {name:sha(ROOT/name) for name in ['user/sessions/latest.json','Iniciar-Cosmos2.cmd']}
    r = dict(accepted=False,completed=False,source_sha256=sources,source_archive=archive.relative_to(ROOT).as_posix(),
             source_archive_sha256=sha(archive),protected_sha256=protected,epochs=[],refusals=[],
             limits_before_execution=LIMITS,runtime=dict(python=sys.version,rebound=rebound.__version__,scipy=scipy.__version__,numpy=np.__version__),
             recipe_before_execution=dict(days=30,sample_interval_s=21600,IAS15_epsilon=1e-9,
                IAS15_refined_epsilon=1e-12,refined_intermediate_output_s=10800,DOP853_rtol=2e-13,
                DOP853_position_atol_m=.001,DOP853_velocity_atol_m_s=1e-9,DOP853_max_step_s=3600,
                pair_difference_steps_s=[1.,.5],pair_extrapolation='(4*a_half-a_full)/3',
                translation_m=[3e12,-4e12,5e12],boost_m_s=[1000.,-2000.,3000.]),
             started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
             scope='Isolated CPU foundation only. Sixteen physical point masses, no new UI, field coupling, performance or promotion acceptance.')

    def persist():
        out.write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')

    def refused(name, call):
        try:call()
        except (ValueError,TypeError) as error:r['refusals'].append(dict(name=name,error=str(error)))
        else:raise AssertionError('Invalid input admitted: '+name)

    persist()
    try:
        initial = reference = None
        for utc in EPOCHS:
            source = catalog.states(utc=utc)
            packet = product.prepare(source)
            assert [b['naif_id'] for b in packet['bodies']] == product.IDS
            errors = {}
            for key,scale,origin,original,limit in [
                ('position',U['length_unit_m'],'initial_ssb_origin_m','source_position_m',LIMITS['inverse_position_m']),
                ('velocity',U['velocity_unit_m_s'],'inertial_origin_velocity_m_s','source_velocity_m_s',LIMITS['inverse_velocity_m_s'])]:
                error = max(abs(x*scale+c-y) for b in packet['bodies'] for x,c,y in zip(b[key],packet[origin],b[original]))
                assert error <= limit
                errors[key] = error
            assert all(b['mass']*U['nominal_GM_unit_m3_s2'] == b['source_GM']['value'] or
                       abs(b['mass']*U['nominal_GM_unit_m3_s2']-b['source_GM']['value']) <= math.ulp(b['source_GM']['value'])
                       for b in packet['bodies'])
            assert product.validate(json.loads(json.dumps(packet))) == packet
            r['epochs'].append(dict(utc=utc,et=source['epoch']['et_tdb_s'],body_count=16,inverse_errors=errors))
            if utc == EPOCHS[2]:initial,reference = packet,source
        assert initial is not None
        fixture = folder/'initial-sixteen-centers.json'
        fixture.write_text(json.dumps(initial,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
        r['fixture'] = dict(path=fixture.relative_to(ROOT).as_posix(),sha256=sha(fixture))
        original = copy.deepcopy(initial)
        mutations = {
            'catalog_missing_body':lambda x:x['bodies'].pop(),
            'catalog_duplicate_body':lambda x:x['bodies'].__setitem__(1,copy.deepcopy(x['bodies'][2])),
            'catalog_jupiter_barycenter':lambda x:x['bodies'][6].__setitem__('naif_id','5'),
            'catalog_saturn_barycenter':lambda x:x['bodies'][7].__setitem__('naif_id','6'),
            'catalog_GM_changed':lambda x:x['bodies'][-1]['GM'].__setitem__('value',1.),
            'catalog_boolean_GM':lambda x:x['bodies'][0]['GM'].__setitem__('value',True),
            'catalog_nan_position':lambda x:x['bodies'][0]['position_m'].__setitem__(0,float('nan')),
            'catalog_infinite_velocity':lambda x:x['bodies'][1]['velocity_m_s'].__setitem__(0,float('inf')),
            'catalog_wrong_frame':lambda x:x.__setitem__('frame','GALACTIC'),
            'catalog_wrong_units':lambda x:x.__setitem__('position_unit','km'),
            'catalog_light_time':lambda x:x.__setitem__('aberration','LT'),
            'catalog_false_epoch':lambda x:x['epoch'].__setitem__('et_tdb_s',True),
            'catalog_inconsistent_epoch':lambda x:x['epoch'].__setitem__('et_tdb_s',x['epoch']['et_tdb_s']+1),
            'catalog_extra_field':lambda x:x.__setitem__('assume_valid',True),
        }
        for name,mutate in mutations.items():
            bad = copy.deepcopy(reference);mutate(bad)
            refused(name,lambda:product.prepare(bad))
        mutations = {
            'packet_boolean_mass':lambda x:x['bodies'][0].__setitem__('mass',True),
            'packet_changed_phase':lambda x:x['bodies'][-1]['position'].__setitem__(0,0.),
            'packet_changed_GM':lambda x:x['bodies'][6]['source_GM'].__setitem__('value',1.),
            'packet_changed_origin':lambda x:x['initial_ssb_origin_m'].__setitem__(0,0.),
            'packet_changed_units':lambda x:x['physical_scale'].__setitem__('length_unit_m',1.),
            'packet_changed_operator':lambda x:x['contract'].__setitem__('softening_m',1.),
            'packet_changed_tolerance':lambda x:x['contract'].__setitem__('epsilon',1e-3),
            'packet_changed_generation':lambda x:x['generation'].__setitem__('model_version','unknown'),
            'packet_bad_branch':lambda x:x.__setitem__('branch_id','../latest'),
            'packet_extra_field':lambda x:x.__setitem__('accepted',True),
        }
        for name,mutate in mutations.items():
            bad = copy.deepcopy(initial);mutate(bad)
            bad['initial_state_sha256'] = product.digest({k:v for k,v in bad.items() if k != 'initial_state_sha256'})
            refused(name,lambda:product.validate(bad))
        bad = copy.deepcopy(initial);bad['initial_state_sha256'] = '0'*64
        refused('packet_bad_hash',lambda:product.validate(bad))
        assert initial == original
        r['reciprocal_pairs'] = []
        for i in range(16):
            for j in range(i+1,16):
                sim = rebound.Simulation();sim.G=1.;sim.integrator='ias15';sim.integrator.epsilon=1e-12
                for index in [i,j]:
                    b=initial['bodies'][index]
                    sim.add(m=b['mass'],x=b['position'][0],y=b['position'][1],z=b['position'][2],vx=b['velocity'][0],vy=b['velocity'][1],vz=b['velocity'][2])
                estimates=[]
                for step in [1.,.5]:
                    forward,backward=sim.copy(),sim.copy()
                    forward.integrate(step/U['time_unit_s']);backward.integrate(-step/U['time_unit_s'])
                    estimates.append((phase(forward)[:,3:]-phase(backward)[:,3:])*U['velocity_unit_m_s']/(2*step))
                actual=(4*estimates[1]-estimates[0])/3
                errors=[];expected_vectors=[]
                for local,(target,source) in enumerate([(i,j),(j,i)]):
                    delta=np.array(reference['bodies'][source]['position_m'])-reference['bodies'][target]['position_m']
                    expected=reference['bodies'][source]['GM']['value']*delta/np.linalg.norm(delta)**3
                    expected_vectors.append(expected.tolist())
                    errors.append(float(np.max(np.abs(actual[local]-expected))))
                r['reciprocal_pairs'].append(dict(targets=[product.IDS[i],product.IDS[j]],component_errors_m_s2=errors,
                    full_step_m_s2=estimates[0].tolist(),half_step_m_s2=estimates[1].tolist(),
                    extrapolated_m_s2=actual.tolist(),expected_m_s2=expected_vectors))
        persist()
        assert max(max(x['component_errors_m_s2']) for x in r['reciprocal_pairs']) <= LIMITS['acceleration_component_m_s2']
        print(json.dumps(dict(stage='conversion-refusals-pairs',epochs=5,refusals=len(r['refusals']),pairs=120)),flush=True)
        seconds=np.arange(0,30*86400+1,21600,dtype=float)
        production=product.simulation(initial);refined=product.simulation(initial,epsilon=1e-12)
        transformed=production.copy()
        shift=np.array(r['recipe_before_execution']['translation_m'])/U['length_unit_m']
        boost=np.array(r['recipe_before_execution']['boost_m_s'])/U['velocity_unit_m_s']
        for p in transformed.particles:
            p.x+=shift[0];p.y+=shift[1];p.z+=shift[2]
            p.vx+=boost[0];p.vy+=boost[1];p.vz+=boost[2]
        series=[];fine=[];translated=[]
        start=time.perf_counter()
        for t in seconds:
            production.integrate(t/U['time_unit_s'])
            if t:refined.integrate((t-10800)/U['time_unit_s'])
            refined.integrate(t/U['time_unit_s']);transformed.integrate(t/U['time_unit_s'])
            series.append(phase(production));fine.append(phase(refined));translated.append(phase(transformed))
        series,fine,translated=map(np.array,[series,fine,translated])
        rebound_wall=time.perf_counter()-start
        n=16;components=3*n
        gm=np.array([b['GM']['value'] for b in reference['bodies']])
        positions=np.array([b['position_m'] for b in reference['bodies']])-initial['initial_ssb_origin_m']
        velocities=np.array([b['velocity_m_s'] for b in reference['bodies']])-initial['inertial_origin_velocity_m_s']
        def equations(t,state):
            position=state[:components].reshape(n,3)
            delta=position[None,:,:]-position[:,None,:]
            distance=np.linalg.norm(delta,axis=2);np.fill_diagonal(distance,np.inf)
            acceleration=np.sum(delta*(gm[None,:]/distance**3)[:,:,None],axis=1)
            return np.concatenate((state[components:],acceleration.ravel()))
        start=time.perf_counter()
        solution=solve_ivp(equations,(0,seconds[-1]),np.concatenate((positions.ravel(),velocities.ravel())),
            method='DOP853',rtol=2e-13,atol=np.array([.001]*components+[1e-9]*components),max_step=3600,dense_output=True)
        assert solution.success and solution.t[-1] == seconds[-1],solution.message
        sampled=solution.sol(seconds)
        independent=np.concatenate((sampled[:components].T.reshape(-1,n,3)/U['length_unit_m'],sampled[components:].T.reshape(-1,n,3)/U['velocity_unit_m_s']),axis=2)
        dop_wall=time.perf_counter()-start
        corrected=translated.copy();corrected[:,:,:3]-=shift[None,None,:]+seconds[:,None,None]/U['time_unit_s']*boost[None,None,:]
        corrected[:,:,3:]-=boost[None,None,:]
        pdiff=np.abs(series[:,:,:3]-independent[:,:,:3])*U['length_unit_m']
        vdiff=np.abs(series[:,:,3:]-independent[:,:,3:])*U['velocity_unit_m_s']
        refinements=np.abs(series[:,:,:3]-fine[:,:,:3])*U['length_unit_m']
        translation_position=np.abs(series[:,:,:3]-corrected[:,:,:3])*U['length_unit_m']
        translation_velocity=np.abs(series[:,:,3:]-corrected[:,:,3:])*U['velocity_unit_m_s']
        assert all(np.all(np.isfinite(x)) for x in [series,fine,independent,translated])
        masses=np.array([b['mass'] for b in initial['bodies']])
        data=dict(seconds=seconds.tolist(),canonical_IAS15=series.tolist(),canonical_IAS15_refined=fine.tolist(),
                  canonical_DOP853=independent.tolist(),canonical_transformed=translated.tolist(),
                  absolute_position_component_errors_m=pdiff.tolist(),absolute_velocity_component_errors_m_s=vdiff.tolist())
        series_path=folder/'30-day-series.json';series_path.write_text(json.dumps(data,allow_nan=False)+'\n',encoding='utf8')
        r['propagation']=dict(samples=121,horizon_days=30,position_component_max_m=float(pdiff.max()),
            velocity_component_max_m_s=float(vdiff.max()),refinement_position_component_max_m=float(refinements.max()),
            translation_position_component_max_m=float(translation_position.max()),translation_velocity_component_max_m_s=float(translation_velocity.max()),
            per_body_position_max_m={body:float(pdiff[:,i].max()) for i,body in enumerate(product.IDS)},
            production_balances=balances(series,masses,seconds),refined_balances=balances(fine,masses,seconds),independent_balances=balances(independent,masses,seconds),
            IAS15=dict(production_steps=production.steps_done,refined_steps=refined.steps_done,transformed_steps=transformed.steps_done,wall_s=rebound_wall),
            DOP853=dict(nfev=solution.nfev,accepted_steps=len(solution.t)-1,largest_step_s=float(np.diff(solution.t).max()),wall_s=dop_wall),
            series_file=series_path.relative_to(ROOT).as_posix(),series_sha256=sha(series_path))
        persist()
        assert pdiff.max() <= LIMITS['position_component_m'] and vdiff.max() <= LIMITS['velocity_component_m_s']
        assert refinements.max() <= LIMITS['refinement_position_component_m']
        assert translation_position.max() <= LIMITS['position_component_m'] and translation_velocity.max() <= LIMITS['velocity_component_m_s']
        for name in ['production_balances','refined_balances','independent_balances']:
            for key in ['relative_energy_drift','normalized_linear_momentum_drift','normalized_angular_momentum_drift']:
                assert r['propagation'][name][key] <= LIMITS[key],(name,key,r['propagation'][name][key])
        r.update(accepted=True,completed=True)
    except Exception:r['failure']=traceback.format_exc()
    finally:
        try:
            assert all(sha(ROOT/name)==seal for name,seal in sources.items())
            assert all(sha(ROOT/name)==seal for name,seal in protected.items())
            r['protected_unchanged']=True
        except Exception:r['cleanup_failure']=traceback.format_exc();r['accepted']=False
        persist()
    print(json.dumps(dict(accepted=r['accepted'],epochs=len(r['epochs']),refusals=len(r['refusals']),
                          failure=r.get('failure'),cleanup_failure=r.get('cleanup_failure')),ensure_ascii=False),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
