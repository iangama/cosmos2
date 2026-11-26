"""Check all spatial directions in the actual field evaluator and Session solver."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/('output/c211-cloud-product/app' if '--candidate' in sys.argv else 'app')
sys.path.insert(0,str(SOURCE))
from gravity_field import evaluate
from session import Session
from physics import PHYSICAL_SCALE as U
L=U['length_unit_m'];GM=U['nominal_GM_unit_m3_s2']
axes=np.vstack((np.eye(3),-np.eye(3)))
rng=np.random.default_rng(171026)
directions=rng.normal(size=(1024,3));directions/=np.linalg.norm(directions,axis=1)[:,None]
directions=np.vstack((axes,directions))
worst_angle=worst_magnitude=0.;axis_readings=[]
for center in (np.zeros(3),np.array([3.,-2.,7.])):
    b={'id':'source','mass':1.,'position':center.tolist()}
    for i,d in enumerate(directions):
        point=(center*L+d*2*L).tolist()
        g=np.array(evaluate([b],point)['acceleration_m_s2'])
        expected=-GM*d/(2*L)**2
        err=float(np.linalg.norm(g-expected)/np.linalg.norm(expected));worst_magnitude=max(worst_magnitude,err)
        angle=float(np.linalg.norm(np.cross(d,g))/np.linalg.norm(g));worst_angle=max(worst_angle,angle)
        assert np.dot(d,g)<0 and err<1e-13 and angle<1e-13
        farther=evaluate([b],(center*L+d*4*L).tolist())['acceleration_norm_m_s2']
        assert abs(farther/np.linalg.norm(g)-.25)<1e-14
        if not center.any() and i<6:axis_readings.append({'direction':d.tolist(),'acceleration_m_s2':g.tolist()})

with tempfile.TemporaryDirectory(prefix='cosmos2-gravity3d-') as folder:
    s=Session(folder)
    def guard():
        return {'system_id':s.system_id,'edit_token':s.edit_token,'revision':s.revision,
            'expected_time':s.sim.t,'frame':s.contract()['frame']}
    s.new_system({**guard(),'name':'Fonte central','mass_kg':GM/U['G_m3_kg_s2'],
        'position_m':[0.,0.,0.],'velocity_m_s':[0.,0.,0.]})
    for i,d in enumerate(axes):
        s.create_body({**guard(),'name':'Direção '+str(i),'mass_kg':1e20,
            'position_m':(d*2*L).tolist(),'velocity_m_s':[0.,0.,0.]})
    initial=np.array([[p.x,p.y,p.z] for p in s.sim.particles])
    expected=[]
    for i in range(1,7):
        g=np.zeros(3)
        for j,p in enumerate(s.sim.particles):
            if i!=j:
                delta=initial[j]-initial[i];g+=p.m*delta/np.linalg.norm(delta)**3
        expected.append(g)
    dt=1e-5;s.integrate(dt)
    actual=np.array([[p.vx,p.vy,p.vz] for p in s.sim.particles][1:])/dt
    error=float(np.max(np.linalg.norm(actual-expected,axis=1)/np.linalg.norm(expected,axis=1)))
    assert error<1e-9
    for d,p in zip(axes,list(s.sim.particles)[1:]):
        velocity=np.array([p.vx,p.vy,p.vz]);position=np.array([p.x,p.y,p.z])
        assert np.dot(velocity,d)<0 and np.linalg.norm(position)<2
        assert np.linalg.norm(np.cross(velocity,d))/np.linalg.norm(velocity)<1e-13
    assert np.allclose(actual[:3],-actual[3:],rtol=0,atol=1e-16)

report={'status':'spherical_3d_attraction_verified','source':str(SOURCE.relative_to(ROOT)),
    'sampled_directions':len(directions),'centers_tested':2,'total_field_checks':2*len(directions),
    'all_accelerations_toward_center':True,'equal_magnitude_at_equal_radius':True,
    'doubling_radius_quarters_acceleration':True,'axis_readings':axis_readings,
    'maximum_relative_field_error':worst_magnitude,'maximum_transverse_fraction':worst_angle,
    'Session_actual_7_body_3d_motion_above_below_and_four_sides_inward':True,
    'Session_solver_vs_independent_pair_sum_relative_error':error,
    'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [SOURCE/'gravity_field.py',SOURCE/'session.py',SOURCE/'physics.py']},
    'scope_ptBR':'Monopolo newtoniano exterior: atração radial em toda a esfera, inclusive z positivo e negativo. J2 e maré podem acrescentar componentes não radiais. O interior material do corpo não é modelado por este teste.'}
name='gravity-spherical-candidate-check.json' if '--candidate' in sys.argv else 'gravity-spherical-installed-check.json'
if '--report' in sys.argv:
    name=sys.argv[sys.argv.index('--report')+1]
    assert Path(name).name==name and name.endswith('.json')
(ROOT/'evidence'/name).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
