"""Isolated J2: recoil/energy, independent DOP853, secular rates and restart."""
from pathlib import Path
import copy
import ctypes
import hashlib
import json
import math
import sys
import struct
import tempfile
import warnings

import numpy as np
import rebound
from scipy.integrate import solve_ivp
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'output/c211-j2-staging'), str(ROOT/'app')]
from j2_dynamics import Driver, digest, phase, reset_pointers
from physics import PHYSICAL_SCALE

LENGTH = PHYSICAL_SCALE['length_unit_m']
A, E, INC, R, J2, MASS = .4, .13, .7, .12, .002, 1e-4
MU = 1.+MASS
PERIOD = 2*math.pi*math.sqrt(A**3/MU)
IDS = ['synthetic-primary', 'synthetic-companion']
CONFIG = [{'body_id': IDS[0], 'j2': J2, 'radius_eq_m': R*LENGTH,
           'axis': [0.,0.,1.], 'provenance': 'Synthetic verification parameters; no observed planet'}]


def initial(epsilon=1e-12):
    sim = rebound.Simulation()
    sim.G = 1.
    sim.integrator = 'ias15'
    sim.integrator.epsilon = epsilon
    sim.add(m=1.)
    sim.add(m=MASS, a=A, e=E, inc=INC, Omega=.2, omega=.5, f=.3)
    sim.move_to_com()
    return sim


def relative(sim):
    p, q = sim.particles
    return np.array([q.x-p.x,q.y-p.y,q.z-p.z,q.vx-p.vx,q.vy-p.vy,q.vz-p.vz])


def integrals(driver):
    ps = driver.sim.particles
    momentum = np.array([math.fsum(p.m*getattr(p,k) for p in ps) for k in ('vx','vy','vz')])
    angular = sum((p.m*np.cross([p.x,p.y,p.z],[p.vx,p.vy,p.vz]) for p in ps), start=np.zeros(3))
    return driver.energy(), momentum, angular


def angles(sim):
    rv = relative(sim); r,v = rv[:3],rv[3:]
    h = np.cross(r,v); node=np.cross([0.,0.,1.],h)
    ecc = np.cross(v,h)/MU-r/np.linalg.norm(r)
    return [math.atan2(node[1],node[0]),
            math.atan2(np.dot(np.cross(node,ecc),h)/np.linalg.norm(h),np.dot(node,ecc))]


def oracle_rhs(t, y):
    # Independent Cartesian form for an axis aligned with z. It does not call
    # the candidate field, driver or REBOUND force routines.
    x,yc,z,vx,vy,vz = y
    r2 = x*x+yc*yc+z*z; r=math.sqrt(r2); z2=z*z/r2
    c=1.5*MU*J2*R**2/r**5
    return [vx,vy,vz,-MU*x/r**3+c*x*(5*z2-1),
            -MU*yc/r**3+c*yc*(5*z2-1),-MU*z/r**3+c*z*(5*z2-3)]


def scientific_binary(sim):
    """Compare every serialized field except measured timing and owner pointers.

    REBOUND5.2.2 binarydata.c explicitly treats particles specially because
    their serialized _sim pointer belongs to each process allocation. No
    integrator field, compensation term, derivative or physical byte is masked.
    """
    data=bytearray(sim.__reduce__()[1][0]);index=64
    while index+16<=len(data):
        name_size,payload_size=struct.unpack_from('<QQ',data,index);index+=16
        assert 0<name_size<=256 and index+name_size+payload_size<=len(data)
        name=bytes(data[index:index+name_size]).rstrip(b'\0').decode('ascii');index+=name_size
        if name.startswith('walltime'):
            data[index:index+payload_size]=b'\0'*payload_size
        elif name=='particles':
            size=ctypes.sizeof(rebound.Particle);offset=rebound.Particle._sim.offset
            assert payload_size==sim.N*size
            for number in range(sim.N):
                begin=index+number*size+offset
                data[begin:begin+ctypes.sizeof(ctypes.c_void_p)]=b'\0'*ctypes.sizeof(ctypes.c_void_p)
        index+=payload_size
        if name=='end':break
    return bytes(data)


driver = Driver(initial(), IDS, CONFIG)
energy0, p0, angular0 = integrals(driver)
maximum = {'energy_relative_error':0., 'momentum_normalized_error':0., 'axial_angular_relative_error':0.}
times = np.linspace(0.,60*PERIOD,721)
observed = [angles(driver.sim)]
for t in times[1:]:
    driver.advance(float(t))
    energy, momentum, angular = integrals(driver)
    maximum['energy_relative_error']=max(maximum['energy_relative_error'],abs((energy-energy0)/energy0))
    maximum['momentum_normalized_error']=max(maximum['momentum_normalized_error'],float(np.linalg.norm(momentum-p0))/(MASS*math.sqrt(MU/A)))
    maximum['axial_angular_relative_error']=max(maximum['axial_angular_relative_error'],abs(float((angular[2]-angular0[2])/angular0[2])))
    observed.append(angles(driver.sim))
assert maximum['energy_relative_error']<1e-10 and maximum['momentum_normalized_error']<1e-10 and maximum['axial_angular_relative_error']<1e-10, maximum
full_angular_change=float(np.linalg.norm(integrals(driver)[2]-angular0)/np.linalg.norm(angular0))
assert full_angular_change>1e-3  # The imposed axis exchanges torque with the orbit.
unwrapped=np.unwrap(np.array(observed),axis=0)
fitted=[float(np.polyfit(times,unwrapped[:,k],1)[0]) for k in range(2)]
mean_motion=math.sqrt(MU/A**3);p=A*(1-E**2)
analytic=[-1.5*mean_motion*J2*(R/p)**2*math.cos(INC),
          .75*mean_motion*J2*(R/p)**2*(5*math.cos(INC)**2-1)]
rates_error=[abs(a-b)/abs(b) for a,b in zip(fitted,analytic)]
assert max(rates_error)<.02, (fitted,analytic,rates_error)

# Independent integrator comparison and tighter IAS15 tolerance convergence.
target=4*PERIOD;y0=relative(initial())
oracle=solve_ivp(oracle_rhs,(0.,target),y0,method='DOP853',rtol=2.3e-14,atol=1e-15,max_step=PERIOD/80)
assert oracle.success
refined_oracle=solve_ivp(oracle_rhs,(0.,target),y0,method='DOP853',rtol=2.3e-14,atol=1e-15,max_step=PERIOD/160)
assert refined_oracle.success
oracle_refinement=float(np.linalg.norm(np.r_[(oracle.y[:3,-1]-refined_oracle.y[:3,-1])/A,
    (oracle.y[3:,-1]-refined_oracle.y[3:,-1])/math.sqrt(MU/A)]))
assert oracle_refinement<1e-11,oracle_refinement
oracle_errors=[]
for epsilon in (1e-9,1e-12):
    trial=Driver(initial(epsilon),IDS,CONFIG);trial.advance(target)
    difference=relative(trial.sim)-oracle.y[:,-1]
    oracle_errors.append(float(np.linalg.norm(np.r_[difference[:3]/A,difference[3:]/math.sqrt(MU/A)])))
assert max(oracle_errors)<2e-9,oracle_errors
# At the float64/oracle floor a strict monotonic-error assertion is false:
# two solutions differing by1e-13 can exchange order under coordinate rounding.
oracle_floor=max(1e-12,5*oracle_refinement)
assert oracle_errors[1]<oracle_errors[0] or max(oracle_errors)<oracle_floor,oracle_errors

# Field, callback and finite-mass recoil use identical acceleration values.
probe=Driver(initial(),IDS,CONFIG)
acceleration,extra_energy=probe._terms(probe.sim)
point=[getattr(probe.sim.particles[1],k)*LENGTH for k in ('x','y','z')]
field=probe.field_correction(IDS[0],point)
unit=PHYSICAL_SCALE['nominal_GM_unit_m3_s2']/LENGTH**2
assert all(field['acceleration_m_s2'][k]/unit==acceleration[1][k] for k in range(3))
assert max(abs(acceleration[0][k]+MASS*acceleration[1][k]) for k in range(3))<1e-20

# Translate, boost and rotate the complete two-body problem, including axis.
Q=Rotation.from_rotvec([.3,-.7,.2]).as_matrix(); transformed=initial()
for particle in transformed.particles:
    pos=Q@np.array([particle.x,particle.y,particle.z])+[.7,-.4,.2]
    vel=Q@np.array([particle.vx,particle.vy,particle.vz])+[.03,.02,-.01]
    particle.x,particle.y,particle.z=pos;particle.vx,particle.vy,particle.vz=vel
rotated_config=copy.deepcopy(CONFIG);rotated_config[0]['axis']=(Q@np.array([0.,0.,1.])).tolist()
rotated=Driver(transformed,IDS,rotated_config);rotated.advance(target)
rotation_error=float(np.linalg.norm(relative(rotated.sim)-np.r_[Q@relative(trial.sim)[:3],Q@relative(trial.sim)[3:]]))
assert rotation_error<2e-10,rotation_error

# Archive/reconnect does not restart IAS15 or silently omit the callback.
with tempfile.TemporaryDirectory() as directory:
    probe.advance(PERIOD*1.17)
    before=phase(probe.sim);record=probe.save(directory)
    binary=Path(directory)/record['binary'];original_bytes=binary.read_bytes()
    restored=Driver.load(directory)
    assert phase(restored.sim)==before and bool(restored.sim._additional_forces)
    # Read-only tensor/potential queries preserve the complete binary cache.
    probe.field_correction(IDS[0],point)
    second=probe.save(directory)
    assert (Path(directory)/second['binary']).read_bytes()==original_bytes
    restored.advance(PERIOD*2.31);probe.advance(PERIOD*2.31)
    assert phase(restored.sim)==phase(probe.sim)
    assert restored.energy()==probe.energy() and restored.reference_energy==probe.reference_energy
    after=probe.save(directory);another=restored.save(directory)
    assert probe.sim==restored.sim  # REBOUND documents exclusion of walltime.
    assert scientific_binary(probe.sim)==scientific_binary(restored.sim)
    pointer=Path(directory)/'latest.json';baseline=json.loads(pointer.read_text())
    corruptions=[]
    for field,value in [('configuration',[]),('sha256','0'*64),('policy','invented'),('rebound','wrong'),
                        ('binary','../arbitrary.bin'),('reference_energy',float('inf'))]:
        changed=copy.deepcopy(baseline);changed[field]=value
        if field!='configuration' and field!='reference_energy':
            changed['receipt']=digest({k:v for k,v in changed.items() if k!='receipt'})
        pointer.write_text(json.dumps(changed))
        try:Driver.load(directory)
        except (ValueError,OSError):corruptions.append(field)
        else:raise AssertionError('Invalid checkpoint accepted: '+field)
    assert phase(probe.sim)==phase(restored.sim)

# Domain failure during an adaptive trial must retain last confirmed phase.
infall=rebound.Simulation();infall.G=1.;infall.integrator='ias15';infall.integrator.epsilon=1e-12
infall.add(m=1.);infall.add(m=MASS,x=.13,vx=-3.);infall.move_to_com()
boundary=Driver(infall,IDS,CONFIG);confirmed=phase(boundary.sim)
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter('always')
    try:boundary.advance(.02)
    except ValueError as error:assert 'exterior' in str(error)
    else:raise AssertionError('Interior trial committed')
assert phase(boundary.sim)==confirmed and not caught,[str(w.message) for w in caught]

report={'status':'candidate_J2_dynamics_verified_not_installed','rebound':rebound.__version__,
        'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'output/c211-j2-staging').glob('*.py')},
        'conservation_over60_periods':maximum,'full_orbital_angular_change_expected':full_angular_change,
        'secular_node_pericenter_rad_per_canonical_time':{'fit':fitted,'first_order':analytic,'relative_error':rates_error},
        'dop853_relative_phase_errors_epsilon1e9_and1e12':oracle_errors,
        'dop853_step_refinement_phase_difference':oracle_refinement,
        'epsilon_tightening_policy':'Error decreases or both solutions are below the independently refined oracle/float64 floor',
        'translation_boost_rotation_absolute_phase_error':rotation_error,
        'identical_field_force_and_linear_reaction':True,
        'same_integrator_binary_unchanged_by_readonly_fields':True,
        'checkpoint_continued_phase_exact_and_serialized_cache_exact_except_walltime_and_particle_owner_pointers':True,
        'corruptions_rejected':corruptions,'interior_substage_rolls_back_confirmed_phase':True,
        'scope':'Isolated exterior fixed-axis J2; no installed Session/worker/UI or spin/material acceptance'}
(ROOT/'evidence/j2-dynamics-prototype-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
