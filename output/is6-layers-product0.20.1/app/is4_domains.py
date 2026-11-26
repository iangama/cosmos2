"""Exact straight-segment geometry for frozen body-domain adapters; no field calls."""
import math
from is4_values import scalar,vector

def outside_ellipsoid(start,end,axes_m):
    a,b=vector(start),vector(end);axes=vector(axes_m)
    if any(v<=0 for v in axes):raise ValueError('Positive ellipsoid axes required')
    u=[a[k]/axes[k] for k in range(3)];d=[b[k]/axes[k]-u[k] for k in range(3)]
    denominator=math.fsum(v*v for v in d)
    if not math.isfinite(denominator):raise ValueError('Unrepresentable domain segment')
    t=max(0.,min(1.,-math.fsum(u[k]*d[k] for k in range(3))/denominator)) if denominator else 0.
    minimum=math.fsum(v*v for v in (u[k]+t*d[k] for k in range(3)))
    if not math.isfinite(minimum):raise ValueError('Unrepresentable ellipsoid distance')
    return minimum>=1.

def inside_sphere(start,end,radius_m):
    radius=scalar(radius_m)
    if radius<=0:raise ValueError('Positive outer radius required')
    # A ball is convex, so its two endpoints bound the complete segment.
    return all(math.hypot(*vector(p))<=radius for p in [start,end])

def shell_segment(start,end,inner_m,outer_m):
    inner,outer=scalar(inner_m),scalar(outer_m)
    if not 0<inner<outer:raise ValueError('Ordered positive shell radii required')
    return inside_sphere(start,end,outer) and outside_ellipsoid(start,end,[inner]*3)
