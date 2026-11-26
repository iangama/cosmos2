"""Exterior J2 in SI; one array kernel shared by force and field readings."""
import math
import numpy as np

POLICY='J2 correction only, exterior region, prescribed inertial symmetry axis; add monopole separately; no material or spin torque evolution'

def _parameters(GM,radius,j2,axis):
    for v in (GM,radius,j2):
        if type(v) not in (int,float) or not math.isfinite(v):raise ValueError('Finite SI parameters required')
    if not 0<GM<=1.4e22 or not 0<radius<=1e12 or abs(j2)>.1:raise ValueError('Bounded exterior model requires0<GM≤1.4e22,0<R≤1e12,|J2|≤0.1 in SI')
    if not isinstance(axis,list) or len(axis)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in axis):raise ValueError('Three finite axis components required')
    norm=math.hypot(*axis)
    if not math.isfinite(norm) or norm==0:raise ValueError('Nonzero finite axis required')
    return [v/norm for v in axis]

def corrections(GM_m3_s2,radius_eq_m,j2,axis,displacements_m,*,tensor=False):
    """Bounded batch of independent exterior points; no softening or interior fill."""
    s=_parameters(GM_m3_s2,radius_eq_m,j2,axis)
    return _evaluate(GM_m3_s2,radius_eq_m,j2,np.asarray(s),displacements_m,tensor=tensor)

def _evaluate(GM_m3_s2,radius_eq_m,j2,s,displacements_m,*,tensor=False):
    """Array algebra for already validated scalar or per-point source parameters."""
    x=np.asarray(displacements_m,dtype=np.float64)
    if x.ndim!=2 or x.shape[1]!=3 or not 1<=x.shape[0]<=16384 or not np.isfinite(x).all():raise ValueError('Finite N×3 SI displacements required')
    r=np.sqrt(np.sum(x*x,axis=1))
    if not np.all((r>=radius_eq_m)&(r<=1e17)):raise ValueError('J2 exterior requires Req≤r≤1e17')
    d=np.sum(x*s,axis=1);c=d/r;r2=r*r
    potential=GM_m3_s2*j2*radius_eq_m**2*(3*c*c-1)/(2*r**3)
    coefficient=1.5*GM_m3_s2*j2*radius_eq_m**2/r**5
    acceleration=coefficient[:,None]*((5*c*c-1)[:,None]*x-2*d[:,None]*np.asarray(s))
    tidal=None
    if tensor:
        tidal=np.empty((len(x),3,3))
        for k in range(3):
            for l in range(3):
                sk=s[k] if s.ndim==1 else s[:,k];sl=s[l] if s.ndim==1 else s[:,l]
                tidal[:,k,l]=coefficient*((5*c*c-1)*(1. if k==l else 0.)-2*sk*sl
                    +(10*d/r2)*(x[:,k]*sl+sk*x[:,l])+(5/r2-35*d*d/r2**2)*x[:,k]*x[:,l])
    if not np.isfinite(potential).all() or not np.isfinite(acceleration).all() or (tensor and not np.isfinite(tidal).all()):raise ValueError('Nonfinite exterior field')
    return potential,acceleration,tidal

def correction(GM_m3_s2,radius_eq_m,j2,axis,displacement_m,*,tensor=True):
    if not isinstance(displacement_m,list) or len(displacement_m)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in displacement_m):raise ValueError('Three finite components required')
    phi,g,T=corrections(GM_m3_s2,radius_eq_m,j2,axis,[displacement_m],tensor=tensor)
    return {'potential_J_kg':float(phi[0]),'acceleration_m_s2':g[0].tolist(),
            **({'tidal_tensor_s_2':T[0].tolist()} if tensor else {}),'policy':POLICY}
