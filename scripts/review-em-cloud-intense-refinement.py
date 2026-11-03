"""Independent stdlib checks of stored intense-source endpoints and energies."""
from pathlib import Path
import hashlib
import json
import math
import sys

ROOT=Path(__file__).resolve().parents[1];label=sys.argv[1]
assert label.isalnum() and len(label)<=20
path=ROOT/f'evidence/em-cloud-native-source128-intense-{label}.json'
r=json.loads(path.read_bytes());assert r['completed'] and r['accepted'] and not r['criteria_failures']
assert r['endpoint_error_normalizing_scales']=={'position_m':1.,'velocity_m_s':1.}
for group in ('source_sha256','reference_implementation_sha256'):
    for name,digest in r[group].items():assert hashlib.sha256((ROOT/name.replace('\\','/')).read_bytes()).hexdigest()==digest,name
original=json.loads((ROOT/'evidence/em-cloud-source128-strong-fixture-rejection.json').read_bytes())
assert r['model']==original['model'] and r['particle_indices_in_10k_fixture']==original['particle_indices_in_10k_fixture']
assert r['q_C']==r['mass_kg']==1. and r['DOP853_reference_refinement_max_component_change']<1e-8
constants=json.loads((ROOT/'output/c212-em-cloud-native-staging/constants.json').read_bytes())
ke=1/(4*math.pi*constants['vacuum_electric_permittivity_F_m']['value'])
def energy(position,velocity):
    kinetic=.5*math.fsum(v*v for v in velocity)
    potential=math.fsum(ke*source['charge_C']/math.dist(position,source['position_m'])for source in r['model']['sources'])
    return kinetic+potential,kinetic
initial=[]
for index in r['particle_indices_in_10k_fixture']:
    theta=index*math.pi*(3-math.sqrt(5));x=[.4*math.cos(theta),.4*math.sin(theta),.4*(index+.5)/10000-.2];v=[1.,.1*math.sin(theta),0.]
    initial.append(energy(x,v))
records=[]
for run in r['runs']:
    assert abs(run['time_s']-20*math.pi)<1e-6 and math.isclose(run['dt_s']*run['steps'],20*math.pi,rel_tol=1e-15)
    phase_error=energy_error=0.
    assert len(run['endpoint_position_m'])==len(run['endpoint_velocity_m_s'])==len(run['reference_position_m'])==len(run['reference_velocity_m_s'])==4
    for i,(x,v,rx,rv) in enumerate(zip(run['endpoint_position_m'],run['endpoint_velocity_m_s'],run['reference_position_m'],run['reference_velocity_m_s'])):
        assert all(math.isfinite(c)for row in (x,v,rx,rv)for c in row)
        assert all(math.dist(x,s['position_m'])>s['exclusion_radius_m']for s in r['model']['sources'])
        phase_error=max(phase_error,math.dist(x,rx),math.dist(v,rv))
        actual,_=energy(x,v);before,kinetic=initial[i]
        energy_error=max(energy_error,abs(actual-before)/max(abs(before),kinetic))
        assert math.isclose(run['initial_energy_J'][i],before,rel_tol=1e-13,abs_tol=1e-13)
        assert math.isclose(run['endpoint_energy_J'][i],actual,rel_tol=1e-13,abs_tol=1e-13)
    assert phase_error<1e-3 and energy_error<1e-6
    assert math.isclose(run['phase_error_over_initial_Larmor_scale_max'],phase_error,rel_tol=1e-10,abs_tol=1e-13)
    assert math.isclose(run['static_energy_relative_error'],energy_error,rel_tol=1e-4,abs_tol=1e-13)
    records.append({'steps':run['steps'],'dt_s':run['dt_s'],'phase_error':phase_error,'energy_error':energy_error})
assert len(records)==3 and [x['steps']for x in records]==[1280000,2560000,5120000]
ratios=[a['phase_error']/b['phase_error']for a,b in zip(records,records[1:])];assert min(ratios)>3.8
result={'accepted':True,'source':str(path.relative_to(ROOT)),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'auditor_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'runs':records,'convergence_ratios':ratios,
        'scope':'Independent arithmetic/source-integrity audit of stored endpoints, SI static energies and original fixed tolerances. '
                'DOP853 solve provenance is checked but not rerun here. Four particles only; no dt.002,10k intense-source throughput, installation or full C2-12 approval.'}
destination=path.with_name(path.stem+'-review.json');assert not destination.exists()
destination.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
