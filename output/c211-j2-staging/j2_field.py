"""Candidate exterior quadrupole correction in SI; fixed inertial symmetry axis.

Independent vector/tensor differentiation of the J2 potential. This module is
not installed, does not attach a force callback and does not deform materials.
"""
import math

def correction(GM_m3_s2,radius_eq_m,j2,axis,displacement_m,*,tensor=True):
    for value in (GM_m3_s2,radius_eq_m,j2):
        if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Finite SI parameters required')
    if not 0<GM_m3_s2<=1.4e22 or not 0<radius_eq_m<=1e12 or abs(j2)>.1:raise ValueError('Bounded exterior model requires0<GM≤1.4e22,0<R≤1e12,|J2|≤0.1 in SI')
    for vector in (axis,displacement_m):
        if not isinstance(vector,list) or len(vector)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in vector):
            raise ValueError('Three finite components required')
    norm=math.hypot(*axis);r=math.hypot(*displacement_m)
    if not math.isfinite(norm) or norm==0 or not math.isfinite(r) or not radius_eq_m<=r<=1e17:raise ValueError('Nonzero axis and exterior Req≤r≤1e17 required')
    s=[v/norm for v in axis];x=displacement_m
    d=math.fsum(s[k]*x[k] for k in range(3));c=d/r;r2=r*r
    potential=GM_m3_s2*j2*radius_eq_m**2*(3*c*c-1)/(2*r**3)
    coefficient=1.5*GM_m3_s2*j2*radius_eq_m**2/r**5
    acceleration=[coefficient*((5*c*c-1)*x[k]-2*d*s[k]) for k in range(3)]
    tidal=[[coefficient*((5*c*c-1)*(1. if k==l else 0.)-2*s[k]*s[l]
        +(10*d/r2)*(x[k]*s[l]+s[k]*x[l])+(5/r2-35*d*d/r2**2)*x[k]*x[l])
        for l in range(3)] for k in range(3)] if tensor else None
    if not all(math.isfinite(v) for v in [potential,*acceleration,*([v for row in tidal for v in row] if tensor else [])]):
        raise ValueError('Nonfinite exterior field')
    return {'potential_J_kg':potential,'acceleration_m_s2':acceleration,**({'tidal_tensor_s_2':tidal} if tensor else {}),
        'policy':'J2 correction only, exterior region, prescribed inertial symmetry axis; add monopole separately; no material or spin torque evolution'}
