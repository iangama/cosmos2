"""Audit revision B incremental reference and split inertial origins from archived series."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import traceback
import zipfile

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
IDS=['10','199','299','399','301','499','599','699','799','899','501','502','503','504','602','606']
LIMITS=dict(position_component_m=10.,velocity_component_m_s=1e-5,refinement_position_component_m=1.,
            relative_energy_drift=1e-9,normalized_linear_momentum_drift=1e-10,
            normalized_angular_momentum_drift=1e-10,inverse_position_m=.001,inverse_velocity_m_s=1e-8,
            acceleration_component_m_s2=1e-10)


def conserved(values,masses):
    energies=[];momenta=[];angular=[]
    for state in values:
        energy=math.fsum(float(m*np.dot(row[3:],row[3:]))/2 for m,row in zip(masses,state))
        energy-=math.fsum(float(masses[i]*masses[j])/math.dist(state[i,:3],state[j,:3])
                          for i,j in itertools.combinations(range(16),2))
        energies.append(energy)
        momenta.append([math.fsum(float(m*row[k+3]) for m,row in zip(masses,state)) for k in range(3)])
        angular.append([math.fsum(float(m*np.cross(row[:3],row[3:])[k]) for m,row in zip(masses,state)) for k in range(3)])
    pscale=math.fsum(float(m*np.linalg.norm(row[3:])) for m,row in zip(masses,values[0]))
    lscale=math.fsum(float(m*np.linalg.norm(np.cross(row[:3],row[3:]))) for m,row in zip(masses,values[0]))
    assert energies[0] != 0 and pscale>0 and lscale>0
    return dict(relative_energy_drift=max(abs((x-energies[0])/energies[0]) for x in energies),
                normalized_linear_momentum_drift=max(math.dist(x,momenta[0]) for x in momenta)/pscale,
                normalized_angular_momentum_drift=max(math.dist(x,angular[0]) for x in angular)/lscale)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True)
    label=parser.parse_args().label
    if not label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):parser.error('Invalid label')
    source=ROOT/f'evidence/is6-dynamics16-verification-{label}.json'
    out=ROOT/f'evidence/is6-dynamics16-audit-{label}.json'
    if out.exists():raise FileExistsError('Preserve numerical audit')
    result=dict(accepted=False,completed=False,source=source.relative_to(ROOT).as_posix(),
                source_sha256=sha(source),auditor_sha256=sha(Path(__file__)))
    try:
        r=json.loads(source.read_text());assert r['accepted'] and r['completed'] and not r.get('failure') and not r.get('cleanup_failure')
        assert r['limits_before_execution']==LIMITS and len(r['epochs'])==5 and len(r['refusals'])==25
        assert r['frame_checks']==dict(independent_simulations=True,independent_inputs_outputs=True,JSON_roundtrip=True,refused=4)
        assert r['protected_unchanged'] and all(sha(ROOT/p)==v for p,v in r['protected_sha256'].items())
        assert all(sha(ROOT/p)==v for p,v in r['source_sha256'].items())
        archive=ROOT/r['source_archive'];assert sha(archive)==r['source_archive_sha256']
        with zipfile.ZipFile(archive) as z:
            assert set(z.namelist())==set(r['source_sha256']) and len(z.namelist())==len(set(z.namelist()))
            assert all(hashlib.sha256(z.read(p)).hexdigest()==v for p,v in r['source_sha256'].items())
        fixture=ROOT/r['fixture']['path'];assert sha(fixture)==r['fixture']['sha256']
        initial=json.loads(fixture.read_text());bodies=initial['bodies'];reference=initial['reference_catalog']['bodies']
        assert [b['naif_id'] for b in bodies]==[b['naif_id'] for b in reference]==IDS
        assert initial['schema']==3 and initial['kind']=='solar_sixteen_physical_centers'
        assert initial['contract']['model']=='newtonian_point_masses' and initial['contract']['softening_m']==0
        U=initial['physical_scale'];L,V,T=[U[k] for k in ['length_unit_m','velocity_unit_m_s','time_unit_s']]
        masses=np.array([b['mass'] for b in bodies])
        assert all(m>0 and math.isfinite(m) for m in masses)
        for row in r['epochs']:
            assert row['body_count']==16 and row['inverse_errors']['position']<=.001 and row['inverse_errors']['velocity']<=1e-8
        pairs=list(itertools.combinations(range(16),2));assert len(r['reciprocal_pairs'])==len(pairs)==120
        pair_peak=0
        for raw,(i,j) in zip(r['reciprocal_pairs'],pairs,strict=True):
            assert raw['targets']==[IDS[i],IDS[j]]
            extrapolated=(4*np.array(raw['half_step_m_s2'])-raw['full_step_m_s2'])/3
            assert np.array_equal(extrapolated,raw['extrapolated_m_s2'])
            for k,(target,other) in enumerate([(i,j),(j,i)]):
                delta=np.array(reference[other]['position_m'])-reference[target]['position_m']
                acceleration=reference[other]['GM']['value']*delta/math.sqrt(float(np.dot(delta,delta)))**3
                assert np.max(np.abs(acceleration-raw['expected_m_s2'][k]))<=1e-14
                error=float(np.max(np.abs(extrapolated[k]-acceleration)))
                assert error<=LIMITS['acceleration_component_m_s2'];pair_peak=max(pair_peak,error)
        p=r['propagation'];path=ROOT/p['series_file'];assert sha(path)==p['series_sha256']
        data=json.loads(path.read_text());seconds=np.array(data['seconds'])
        assert np.array_equal(seconds,np.arange(0,30*86400+1,21600,dtype=float))
        arrays={key:np.array(data[key]) for key in ['canonical_IAS15','canonical_IAS15_refined','canonical_DOP853','canonical_transformed']}
        assert all(x.shape==(121,16,6) and np.all(np.isfinite(x)) for x in arrays.values())
        baseline=arrays['canonical_IAS15'];independent=arrays['canonical_DOP853']
        initial_state=np.array([b['position']+b['velocity'] for b in bodies]);assert np.array_equal(baseline[0],initial_state)
        pos=np.abs(baseline[:,:,:3]-independent[:,:,:3])*L
        vel=np.abs(baseline[:,:,3:]-independent[:,:,3:])*V
        assert np.array_equal(pos,data['absolute_position_component_errors_m']) and np.array_equal(vel,data['absolute_velocity_component_errors_m_s'])
        refinement=float(np.max(np.abs(baseline[:,:,:3]-arrays['canonical_IAS15_refined'][:,:,:3]))*L)
        transformed=arrays['canonical_transformed'].copy();recipe=r['recipe_before_execution']
        shift=np.array(recipe['translation_m'])/L;boost=np.array(recipe['boost_m_s'])/V
        assert recipe['translation_m']==[3e12,-4e12,5e12] and recipe['boost_m_s']==[1000.,-2000.,3000.]
        assert r['coordinate_encoding']=='split_inertial_origin' and recipe['reference_formulation']=='incremental_SI'
        assert len(data['inertial_origins'])==121
        for t,origin in zip(seconds,data['inertial_origins'],strict=True):
            assert origin['encoding']=='split_inertial_origin' and abs(origin['elapsed_s']-t)<1e-8
            assert origin['origin_velocity_m_s']==recipe['boost_m_s']
            assert np.max(np.abs(np.array(origin['origin_m'])-(np.array(recipe['translation_m'])+t*np.array(recipe['boost_m_s']))))<=.001
        translation_pos=float(np.max(np.abs(baseline[:,:,:3]-transformed[:,:,:3]))*L)
        translation_vel=float(np.max(np.abs(baseline[:,:,3:]-transformed[:,:,3:]))*V)
        assert pos.max()<=10 and vel.max()<=1e-5 and refinement<=1 and translation_pos<=10 and translation_vel<=1e-5
        for key in ['canonical_IAS15','canonical_IAS15_refined','canonical_DOP853']:
            metrics=conserved(arrays[key],masses)
            assert all(value<=LIMITS[name] for name,value in metrics.items()),(key,metrics)
            result.setdefault('conservation',{})[key]=metrics
        assert p['DOP853']['largest_step_s']<=3600+2*math.ulp(float(seconds[-1])) and p['samples']==121 and p['horizon_days']==30
        result.update(accepted=True,completed=True,positions=1936,reciprocal_pairs=120,pair_acceleration_peak_m_s2=pair_peak,
                      position_component_max_m=float(pos.max()),velocity_component_max_m_s=float(vel.max()),
                      refinement_position_component_max_m=refinement,translation_position_component_max_m=translation_pos,
                      translation_velocity_component_max_m_s=translation_vel,scope=r['scope'])
    except Exception:result['failure']=traceback.format_exc()
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(result,ensure_ascii=False),flush=True)
    return 0 if result['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
