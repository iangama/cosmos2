"""Candidate J2: independent finite differences, analytic poles and rotations."""
from pathlib import Path
import json
import math
import sys
import numpy as np
from scipy.spatial.transform import Rotation

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'output/c211-j2-staging'))
from j2_field import correction
GM,R,J=4e14,6e6,.002
def sample(x,axis=[0.,0.,1.]):return correction(GM,R,J,[float(v) for v in axis],[float(v) for v in x])
gradient_error=tensor_error=rotation_error=trace_error=0.
for point in ([1.2e7,2e6,3e6],[-1.5e7,1.1e7,-8e6],[0.,0.,1.2e7]):
    x=np.array(point);h=math.hypot(*point)*2e-5;data=sample(x)
    gradient=np.array([-(sample(x+np.eye(3)[k]*h)['potential_J_kg']-sample(x-np.eye(3)[k]*h)['potential_J_kg'])/(2*h) for k in range(3)])
    numeric_tensor=np.column_stack([(np.array(sample(x+np.eye(3)[k]*h)['acceleration_m_s2'])-sample(x-np.eye(3)[k]*h)['acceleration_m_s2'])/(2*h) for k in range(3)])
    g=np.array(data['acceleration_m_s2']);T=np.array(data['tidal_tensor_s_2'])
    gradient_error=max(gradient_error,float(np.linalg.norm(gradient-g)/np.linalg.norm(g)))
    tensor_error=max(tensor_error,float(np.linalg.norm(numeric_tensor-T)/np.linalg.norm(T)))
    trace_error=max(trace_error,abs(float(np.trace(T)))/float(np.linalg.norm(T)))
    assert np.max(np.abs(T-T.T))<1e-22
    Q=Rotation.from_rotvec([.3,-.7,.2]).as_matrix();rotated=sample(Q@x,list(Q@np.array([0.,0.,1.])))
    rotation_error=max(rotation_error,float(np.linalg.norm(np.array(rotated['tidal_tensor_s_2'])-Q@T@Q.T)/np.linalg.norm(T)))
    assert math.isclose(rotated['potential_J_kg'],data['potential_J_kg'],rel_tol=1e-14)
    assert np.allclose(rotated['acceleration_m_s2'],Q@g,rtol=1e-13,atol=0)
assert gradient_error<1e-8 and tensor_error<1e-8 and trace_error<1e-14 and rotation_error<1e-14
r=2*R;k=1.5*GM*J*R**2/r**4
assert np.allclose(sample([r,0.,0.])['acceleration_m_s2'],[-k,0.,0.],rtol=1e-14,atol=0)
assert np.allclose(sample([0.,0.,r])['acceleration_m_s2'],[0.,0.,2*k],rtol=1e-14,atol=0)
zero=correction(GM,R,0.,[0.,0.,1.],[r,0.,0.]);assert zero['potential_J_kg']==0 and not np.any(zero['acceleration_m_s2']) and not np.any(zero['tidal_tensor_s_2'])
rejected=0
for args in [(GM,R,J,[0.,0.,0.],[r,0.,0.]),(GM,R,J,[0.,0.,1.],[R/2,0.,0.]),(GM,R,True,[0.,0.,1.],[r,0.,0.]),(GM,R,float('nan'),[0.,0.,1.],[r,0.,0.])]:
    try:correction(*args)
    except ValueError:rejected+=1
    else:raise AssertionError('Invalid exterior model accepted')
report={'status':'candidate_J2_field_math_only_not_installed','gradient_relative_error_max':gradient_error,
    'tidal_finite_difference_relative_error_max':tensor_error,'rotation_relative_error_max':rotation_error,'normalized_trace_max':trace_error,
    'equatorial_polar_signs_and_zero_coefficient':True,'invalid_domains_rejected':rejected,
    'scope':'Exterior J2 correction only; no force integration, feedback, precession, checkpoint, instruments or UI acceptance'}
(ROOT/'evidence/j2-field-prototype-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
