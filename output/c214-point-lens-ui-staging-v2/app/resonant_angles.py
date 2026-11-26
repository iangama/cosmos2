"""Isolated read-only prograde planar first-order critical-angle candidate.

Wrapped instantaneous angles and finite circular coverage are measurements,
not an automatic declaration of libration, resonance or permanent capture.
"""
import math
import numpy as np
from physics import PHYSICAL_SCALE as U

TAU=2*math.pi


def vector(value):
    if not isinstance(value,list) or len(value)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>1e17 for x in value):raise ValueError('Finite bounded three-vector required')
    return np.asarray(value,dtype=float)


def basis(normal,reference):
    z=vector(normal);x=vector(reference)
    if np.linalg.norm(z)<1e-12:raise ValueError('Nonzero plane normal required')
    z=z/np.linalg.norm(z);x=x-z*float(x@z)
    if np.linalg.norm(x)<1e-12:raise ValueError('Plane reference parallel to normal')
    x=x/np.linalg.norm(x);y=np.cross(z,x)
    return x,y,z


def elements(primary,body,normal,reference):
    xaxis,yaxis,zaxis=basis(normal,reference)
    if primary.get('id')==body.get('id'):raise ValueError('Distinct primary and orbiter required')
    masses=[]
    for b in (primary,body):
        m=b.get('mass')
        if type(m) not in (int,float) or not math.isfinite(m) or not 1e-12<=m<=100:raise ValueError('Positive bounded canonical masses required')
        masses.append(m)
    r=vector(body['position'])-vector(primary['position']);v=vector(body['velocity'])-vector(primary['velocity'])
    radius=float(np.linalg.norm(r));mu=math.fsum(masses)
    if not 1e-12<=radius<=2e8:raise ValueError('Pair separation outside candidate domain')
    h=np.cross(r,v);hn=float(np.linalg.norm(h))
    if hn<1e-12*math.sqrt(mu*radius):raise ValueError('Radial orbit has no plane')
    if float(h@zaxis)<=0 or np.linalg.norm(np.cross(h/hn,zaxis))>1e-7:raise ValueError('Prograde orbit in the selected plane required')
    if abs(float(r@zaxis))/radius>1e-7:raise ValueError('Position outside selected orbital plane')
    v2=float(v@v);rv=float(r@v);energy=.5*v2-mu/radius
    if energy>=-1e-12*mu/radius:raise ValueError('Bound elliptic orbit away from parabola required')
    a=-mu/(2*energy);evec=((v2-mu/radius)*r-rv*v)/mu;e=float(np.linalg.norm(evec))
    if not e<1-1e-8:raise ValueError('Eccentricity outside elliptic candidate domain')
    longitude=math.atan2(float(r@yaxis),float(r@xaxis))
    periapsis=math.atan2(float(evec@yaxis),float(evec@xaxis))
    if e>1e-12:
        f=math.atan2(float(np.cross(evec,r)@(h/hn)),float(evec@r))
        E=math.atan2(math.sqrt(1-e*e)*math.sin(f),e+math.cos(f))
        longitude+=math.remainder(E-f,TAU)-e*math.sin(E)
    else:periapsis=None
    return {'semimajor_axis_m':a*U['length_unit_m'],'eccentricity':e,
        'mean_motion_rad_s':math.sqrt(mu/a**3)/U['time_unit_s'],
        'mean_longitude_rad':longitude%TAU,'longitude_periapsis_rad':periapsis%TAU if e>1e-8 else None,
        'periapsis_undefined_reason':'Near-circular orbit; no defined apsidal direction' if e<=1e-8 else None,
        'frame_policy':'Selected fixed inertial plane; explicit primary-relative two-body osculating elements, not default Jacobi elements'}


def instantaneous(bodies,primary_id,inner_id,outer_id,j,normal,reference):
    if type(j) is not int or not 2<=j<=9:raise ValueError('First-order resonance integer2–9 required')
    ids=[b.get('id') for b in bodies]
    if len(set(ids))!=len(ids) or len({primary_id,inner_id,outer_id})!=3 or any(i not in ids for i in (primary_id,inner_id,outer_id)):raise ValueError('Three distinct active identities required')
    primary=bodies[ids.index(primary_id)]
    inner=elements(primary,bodies[ids.index(inner_id)],normal,reference)
    outer=elements(primary,bodies[ids.index(outer_id)],normal,reference)
    if inner['semimajor_axis_m']>=outer['semimajor_axis_m']:raise ValueError('Selected inner/outer ordering changed; do not silently swap identities')
    phase=j*outer['mean_longitude_rad']-(j-1)*inner['mean_longitude_rad']
    angles=[]
    for identifier,orbit in ((inner_id,inner),(outer_id,outer)):
        peri=orbit['longitude_periapsis_rad']
        angles.append({'periapsis_body_id':identifier,'angle_rad':None if peri is None else (phase-peri)%TAU,
            'unavailable_reason':orbit['periapsis_undefined_reason'] if peri is None else None})
    ratio=inner['mean_motion_rad_s']/outer['mean_motion_rad_s']
    return {'primary_id':primary_id,'inner_id':inner_id,'outer_id':outer_id,'j':j,'inner':inner,'outer':outer,
        'outer_to_inner_period_ratio':ratio,'nominal_period_ratio':j/(j-1),
        'relative_offset_from_nominal':ratio/(j/(j-1))-1,'critical_angles':angles,
        'classification':None,'policy':'Instantaneous commensurability and wrapped critical angles only; no libration/capture inference from a single snapshot'}


def circular_coverage(angles):
    if not isinstance(angles,list) or not 2<=len(angles)<=4096 or any(type(a) not in (int,float) or not math.isfinite(a) for a in angles):raise ValueError('Finite continuous segment with2–4096angles required')
    values=sorted(a%TAU for a in angles)
    gaps=[b-a for a,b in zip(values,values[1:])]+[values[0]+TAU-values[-1]]
    occupied=TAU-max(gaps)
    c=math.fsum(math.cos(a) for a in values);s=math.fsum(math.sin(a) for a in values);strength=math.hypot(c,s)/len(values)
    return {'minimum_occupied_arc_rad':occupied,'circular_mean_rad':math.atan2(s,c)%TAU if strength>1e-12 else None,
        'resultant_strength':strength,'classification':None,
        'policy':'Finite sampled circular coverage only; a short arc may also be an incomplete circulation. No angular unwrapping, frequency or permanent-capture claim.'}
