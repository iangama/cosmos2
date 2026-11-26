"""Batched static SI reference fields and conservative source-domain drifts."""
import numpy as np
from em_fields import Model,K_E,MU_0
from em_particles import DomainExit

MAX_COUNT=10000;POSITION_LIMIT_M=1e17
def dot3(a,b):return (a[:,0]*b[:,0]+a[:,1]*b[:,1])+a[:,2]*b[:,2]
def norm3(a):return np.hypot(np.hypot(a[:,0],a[:,1]),a[:,2])
def refuse(mask,message):
    if np.any(mask):raise DomainExit(message+'; particle indices '+str(np.flatnonzero(mask)[:8].tolist()))
def positions(value):
    a=np.asarray(value,dtype=float)
    if a.ndim!=2 or a.shape[1]!=3 or not 1<=len(a)<=MAX_COUNT or not np.isfinite(a).all() or np.max(abs(a))>POSITION_LIMIT_M:raise DomainExit('Cloud positions outside finite1e17m component domain')
    return a
def model_domain(model):
    if not isinstance(model,Model) or any(max(abs(v) for v in s.position_m)>POSITION_LIMIT_M for s in model.sources):raise ValueError('Static EM model with sources in the declared1e17m component domain required')

def evaluate(model,xyz,*,potential=True):
    model_domain(model);x=positions(xyz);E=np.broadcast_to(model.uniform_E_V_m,x.shape).copy();B=np.broadcast_to(model.uniform_B_T,x.shape).copy()
    Ec=np.zeros_like(E);Bc=np.zeros_like(B);phi=-dot3(x,E) if potential else None;pc=np.zeros(len(x)) if potential else None
    def add(total,comp,term):
        y=term-comp;updated=total+y;return updated,(updated-total)-y
    with np.errstate(all='ignore'):
        for source in model.sources:
            d=x-np.array(source.position_m);r=norm3(d)
            refuse(r<=source.exclusion_radius_m,'Particle reaches excluded source '+source.id)
            direction=d/r[:,None]
            if source.charge_C!=0:
                term=((K_E*source.charge_C/r)/r)[:,None]*direction;E,Ec=add(E,Ec,term)
                if potential:phi,pc=add(phi,pc,K_E*source.charge_C/r)
            if source.magnetic_moment_A_m2!=(0.,0.,0.):
                moment=np.broadcast_to(source.magnetic_moment_A_m2,x.shape)
                term=((MU_0/(4*np.pi)/r)/r/r)[:,None]*(3*direction*dot3(direction,moment)[:,None]-moment);B,Bc=add(B,Bc,term)
    if not np.isfinite(E).all() or not np.isfinite(B).all() or potential and not np.isfinite(phi).all():raise DomainExit('Unrepresentable batched SI field')
    return E,B,phi

def drift_domain(model,start,end):
    model_domain(model);a=positions(start);b=positions(end)
    if a.shape!=b.shape:raise ValueError('Matching cloud drift populations required')
    lo=np.minimum(a,b);hi=np.maximum(a,b);delta=b-a
    for source in model.sources:
        p=np.array(source.position_m);offset=p-a
        # A conservative bounding box avoids unstable closest-point arithmetic
        # for tiny drifts far from a source, and skips most ordinary particles.
        candidate=norm3(p-np.clip(p,lo,hi))<=source.exclusion_radius_m
        if not np.any(candidate):continue
        d=delta[candidate];o=offset[candidate];scale=np.max(abs(d),axis=1);moving=scale>0
        closest=o.copy()
        if np.any(moving):
            with np.errstate(all='ignore'):
                unit=d[moving]/scale[moving,None];scaled=o[moving]/scale[moving,None]
                fraction=dot3(scaled,unit)/dot3(unit,unit)
            if not np.isfinite(fraction).all():raise DomainExit('Unrepresentable source-drift closest point')
            fraction=np.clip(fraction,0,1);closest[moving]=o[moving]-fraction[:,None]*d[moving]
        bad=norm3(closest)<=source.exclusion_radius_m
        if np.any(bad):
            indices=np.flatnonzero(candidate)[bad][:8].tolist();raise DomainExit('Drift crosses excluded source '+source.id+'; particle indices '+str(indices))
