"""Potential differences from paired SI coordinates; retain sub-ULP displacements."""
import math
from is4_values import vector
from is4_wind_field import AU_M

def potential_differences(model,origin_m,start_offset_m,end_offset_m):
    origin,left,right=vector(origin_m),vector(start_offset_m),vector(end_offset_m)
    a=[math.fsum([origin[k],left[k]]) for k in range(3)]
    b=[math.fsum([origin[k],right[k]]) for k in range(3)]
    if not model.segment_in_domain(a,a) or not model.segment_in_domain(b,b):raise ValueError('Potential endpoint outside retained wind/gravity domain')
    d=[right[k]-left[k] for k in range(3)];d2=math.fsum(v*v for v in d)
    r0,r1=math.hypot(*a),math.hypot(*b)
    dr=math.fsum([2*math.fsum(a[k]*d[k] for k in range(3)),d2])/(r0+r1)
    dz=(1 if a[2]>0 else -1)*d[2] if a[2]*b[2]>0 else abs(b[2])-abs(a[2])
    difference=math.fsum([dz/r1,-abs(a[2])*dr/(r0*r1)])
    cfg=model.field.configuration
    electric=-cfg['polarity']*cfg['rotation_rate_rad_s']*cfg['radial_field_at_AU_T']*AU_M**2*difference
    terms=[]
    for s in model.sources:
        initial=[a[k]-s.position_model_m[k] for k in range(3)]
        final=[b[k]-s.position_model_m[k] for k in range(3)]
        r0,r1=math.hypot(*initial),math.hypot(*final)
        difference=math.fsum([2*math.fsum(initial[k]*d[k] for k in range(3)),d2])
        terms.append(s.GM_m3_s2*difference/(r0*r1*(r0+r1)))
    gravity=math.fsum(terms)
    if not all(math.isfinite(v) for v in [electric,gravity]):raise ValueError('Unrepresentable paired potential difference')
    return dict(electric_potential_change_V=electric,gravity_potential_change_J_kg=gravity)
