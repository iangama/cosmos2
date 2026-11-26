"""Independent straight/radial/dipole invariants and refinement of EM field lines."""
from pathlib import Path
import hashlib
import json
import math
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1];CANDIDATE=ROOT/'output/c212-em-product'
sys.path.insert(0,str(CANDIDATE/'app'));sys.path.insert(0,str(CANDIDATE/'em'))
from em_trace import trace
from em_fields import Model,Source,MU_0
cases=[]
uniform=Model(uniform_E_V_m=(2,-1,3),uniform_B_T=(-1,4,2));result=trace(uniform,[[.2,.3,.4]],['electric','magnetic'],2.,max_wall_s=10)
for curve in result['curves']:
    v=np.array(uniform.uniform_E_V_m if curve['quantity']=='electric' else uniform.uniform_B_T);v=v/math.hypot(*v)*curve['orientation']
    points=np.array(curve['points_m']);relative=points-points[0]
    assert np.max(abs(np.cross(relative,v)))<3e-13
    assert np.all(np.diff(relative@v)>0) and curve['termination']=='outer_boundary'
cases.append({'kind':'uniform E/B','curves':len(result['curves']),'straight_and_oriented':True})

radial=Model((Source('positive',(0,0,0),.2,1e-9),));seed=[1.,.7,-.3];result=trace(radial,[seed],['electric'],2.,max_wall_s=10)
for curve in result['curves']:
    points=np.array(curve['points_m']);radii=np.linalg.norm(points,axis=1)
    assert np.max(abs(np.cross(points,np.array(seed)/math.hypot(*seed))))<3e-13
    assert np.all(radii>.2)
    assert np.all(np.diff(radii)*curve['orientation']>0)
assert result['curves'][0]['termination']=='domain_boundary'
cases.append({'kind':'positive point charge','inward_stops_before_exclusion':True,'radial_orientation_exact':True})
negative=Model((Source('negative',(0,0,0),.2,-1e-9),));minus=trace(negative,[seed],['electric'],2.,max_wall_s=10)
for curve,opposite in zip(result['curves'],reversed(minus['curves'])):assert curve['points_m']==opposite['points_m']

dipole=Model((Source('dipole',(0,0,0),.35,0,(0,0,4*math.pi/MU_0)),))
# Derived independently: Br/Btheta=2cot(theta), so r/sin²(theta) is
# constant along every meridian of an ideal dipole outside its exclusion.
errors=[]
for tolerance in (1e-4,1e-6,1e-8):
    out=trace(dipole,[[1.4,0,.8]],['magnetic'],2.,max_wall_s=10,max_steps=512,tolerance_fraction=tolerance)
    maximum=0.
    for curve in out['curves']:
        points=np.array(curve['points_m']);radius=np.linalg.norm(points,axis=1);invariant=radius**3/(points[:,0]**2+points[:,1]**2)
        maximum=max(maximum,float(np.max(abs(invariant/invariant[0]-1))))
        assert np.max(abs(points[:,1]))==0 and np.all(radius>.35)
        assert curve['termination']=='domain_boundary',curve['termination']
    errors.append(maximum)
assert errors[-1]<2e-6 and errors[1]<errors[0]/3 and errors[2]<errors[1]/3,errors
cases.append({'kind':'ideal dipole','r_over_sin2_theta_relative_errors':errors,'refinement_confirmed':True})
null=trace(Model(),[[1,0,0]],['electric','magnetic'],1.,max_wall_s=10)
assert all(len(c['points_m'])==1 and c['termination']=='null_or_cancellation_direction' for c in null['curves'])
excluded=trace(radial,[[0,0,0]],['electric'],1.,max_wall_s=10)
assert all(len(c['points_m'])==1 and c['termination']=='domain_boundary' for c in excluded['curves'])
budget=trace(dipole,[[1.4,0,.8]]*12,['electric','magnetic'],2.,max_wall_s=1e-6)
assert len(budget['curves'])==48 and all(c['termination']=='budget_limit' for c in budget['curves'])
cases.append({'kind':'null/exclusion/budget','explicit_stop_without_invented_segments':True})
report={'status':'candidate_EM_field_line_invariants_orientation_refinement_and_bounded_stops_verified','cases':cases,
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (CANDIDATE/'app/em_trace.py',CANDIDATE/'em/em_fields.py',CANDIDATE/'em/em_particles.py',Path(__file__))},
        'scope':'Normalized reference E/B integral curves only; no particle trajectory, native scene, body model or formal performance approval.'}
(ROOT/'evidence/em-trace-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
