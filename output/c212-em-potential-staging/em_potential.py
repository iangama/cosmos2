"""Frozen SI electric equipotentials on an explicit Cartesian slice.

Piecewise linear triangles, fixed diagonal00→11. No invented potential at
excluded samples, no scalar magnetic potential and no graphic height warp.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import math

VERSION='0.1.0'
FRAME='EM_SI_FIXED_INERTIAL'
def finite(value):
    if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Finite real SI values required')
    return float(value)

def contours(grid,measurement,levels_V,*,exclusions,maximum_segments=4096):
    if not isinstance(grid,dict) or set(grid)!={'x_m','y_m','z_m'}:raise ValueError('Explicit Cartesian SI grid required')
    axes=[]
    for key in ('x_m','y_m'):
        raw=grid[key]
        if not isinstance(raw,(list,tuple)) or not 2<=len(raw)<=65:raise ValueError('Grid axes need2..65 samples')
        axis=list(map(finite,raw))
        if any(abs(v)>1e9 for v in axis) or any(a>=b for a,b in zip(axis,axis[1:])):raise ValueError('Strictly increasing bounded grid axes required')
        axes.append(axis)
    xs,ys=axes;z=finite(grid['z_m'])
    if abs(z)>1e9:raise ValueError('Slice outside supported SI domain')
    if not isinstance(levels_V,(list,tuple)) or not 1<=len(levels_V)<=16:raise ValueError('Declare1..16 SI contour levels')
    levels=list(map(finite,levels_V))
    if any(a>=b for a,b in zip(levels,levels[1:])):raise ValueError('Distinct increasing levels required')
    if type(maximum_segments) is not int or not 1<=maximum_segments<=8192:raise ValueError('Bounded segment budget required')
    if not isinstance(exclusions,list) or len(exclusions)>128:raise ValueError('Explicit source exclusions required, including an empty list when none')
    sources=[];ids=set()
    for source in exclusions:
        if not isinstance(source,dict) or set(source)!={'id','position_m','radius_m'}:raise ValueError('Exact source exclusion declaration required')
        sid=source['id'];p=source['position_m'];radius=finite(source['radius_m'])
        if not isinstance(sid,str) or not 1<=len(sid)<=128 or sid in ids or not isinstance(p,(list,tuple)) or len(p)!=3 or radius<=0:raise ValueError('Valid unique exclusion identity/geometry required')
        ids.add(sid);sources.append((tuple(map(finite,p)),radius))
    metadata={k:measurement[k] for k in ('system_id','edit_token','revision','frame','time_s')}
    if metadata['frame']!=FRAME or type(metadata['revision']) is not int or metadata['revision']<0 or finite(metadata['time_s'])<0:raise ValueError('Confirmed EM slice metadata required')
    if any(not isinstance(metadata[k],str) or not 1<=len(metadata[k])<=128 for k in ('system_id','edit_token')):raise ValueError('Bounded system identity required')
    expected=[(x,y,z) for x in xs for y in ys];samples=measurement['samples']
    if not isinstance(samples,list) or len(samples)!=len(expected):raise ValueError('Complete explicitly ordered grid measurement required')
    values=[]
    for point,sample in zip(expected,samples):
        position=sample['position_m']
        if not isinstance(position,(list,tuple)) or len(position)!=3 or tuple(map(finite,position))!=point or type(sample['valid']) is not bool:raise ValueError('Grid/sample position or validity mismatch')
        values.append(finite(sample['electric_potential_V']) if sample['valid'] else None)
    triangles=[];ny=len(ys)
    for i in range(len(xs)-1):
        for j in range(ny-1):
            a=i*ny+j;b=(i+1)*ny+j;c=b+1;d=a+1
            unsafe=any(math.hypot(p[0]-min(xs[i+1],max(xs[i],p[0])),p[1]-min(ys[j+1],max(ys[j],p[1])),p[2]-z)<=radius for p,radius in sources)
            triangles.extend((((a,b,c),unsafe),((a,c,d),unsafe)))
    segments=[];seen=set();processed=masked=flat=safety=0;complete=True
    def edge(a,b,level):
        # Canonical endpoint order gives identical shared-edge coordinates.
        if a>b:a,b=b,a
        va,vb=values[a],values[b]
        if va==level:return expected[a]
        if vb==level:return expected[b]
        scale=max(abs(va),abs(vb),abs(level))
        fraction=(level/scale-va/scale)/(vb/scale-va/scale)
        return tuple(x+fraction*(y-x) for x,y in zip(expected[a],expected[b]))
    for level in levels:
        for triangle,unsafe in triangles:
            if len(segments)>=maximum_segments:complete=False;break
            processed+=1;vs=[values[index] for index in triangle]
            if unsafe:safety+=1;continue
            if None in vs:masked+=1;continue
            if all(v==level for v in vs):flat+=1;continue
            crossings=[]
            for a,b in zip(triangle,triangle[1:]+triangle[:1]):
                if (values[a]>=level)!=(values[b]>=level):crossings.append(edge(a,b,level))
            if len(crossings)!=2 or crossings[0]==crossings[1]:continue
            endpoints=tuple(sorted(crossings));key=(level,endpoints)
            if key in seen:continue
            seen.add(key);segments.append({'level_V':level,'points_m':endpoints,'sample_indices':triangle})
        if not complete:break
    total=len(triangles)*len(levels)
    return {'schema':1,'kind':'electric_equipotential_slice','metadata':deepcopy(metadata),
            'grid':{'x_m':xs,'y_m':ys,'z_m':z},'levels_V':levels,'segments':segments,
            'complete':complete,'termination':'complete' if complete else 'segment_budget',
            'triangle_level_combinations':total,'processed_triangle_levels':processed,
            'unprocessed_triangle_levels':total-processed,'excluded_triangle_levels':masked,
            'source_exclusion_triangle_levels':safety,'exclusions':deepcopy(exclusions),
            'constant_level_triangle_regions':flat,'maximum_segments':maximum_segments,
            'units':{'position_m':'m','level_V':'V'},
            'algorithm':{'version':VERSION,'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                         'method':'Linear triangles with fixed00-to11 diagonal; interpolation of measured SI values, no accuracy bound without refinement.'},
            'measurement_sha256':hashlib.sha256(json.dumps(measurement,sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest(),
            'scope':'Frozen electric scalar potential in the measurement gauge. Constant-level regions are reported rather than represented by arbitrary lines. Invalid samples remove adjacent triangles; cells whose3D boxes touch a declared sphere are conservatively omitted. This slice does not replace the3D field.'}
