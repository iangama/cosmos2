"""Independent analytic references for the isolated equipotential geometry."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import math
import sys
ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/c212-em-potential-staging';sys.path.insert(0,str(STAGE))
from em_potential import contours
def measurement(xs,ys,function,*,z=0.):
    return {'system_id':'reference','edit_token':'reference','revision':0,'time_s':0.,'frame':'EM_SI_FIXED_INERTIAL',
            'samples':[{'position_m':[x,y,z],'valid':(v:=function(x,y)) is not None,**({'electric_potential_V':v} if v is not None else {})} for x in xs for y in ys]}
def grid(axis,z=0.):return {'x_m':axis,'y_m':axis,'z_m':z}
xs=[-2+i/4 for i in range(17)];ys=[-2+i/4 for i in range(17)]
m=measurement(xs,ys,lambda x,y:3*x-2*y+5);original=deepcopy(m)
r=contours(grid(xs),m,[-1.,0.,3.,6.,10.],exclusions=[])
assert r['complete'] and r['segments'] and m==original
uniform_error=max(abs(3*p[0]-2*p[1]+5-s['level_V']) for s in r['segments'] for p in s['points_m']);assert uniform_error<1e-13
errors=[];counts=[]
for n in (7,13,25,49,65):
    axis=[-2+4*i/(n-1) for i in range(n)]
    m=measurement(axis,axis,lambda x,y:1/math.hypot(x,y) if math.hypot(x,y)>.08 else None)
    exclusion=[{'id':'positive','position_m':[0.,0.,0.],'radius_m':.08}]
    r=contours(grid(axis),m,[1.],exclusions=exclusion,maximum_segments=8192);assert r['complete']
    points=[]
    for segment in r['segments']:
        a,b=segment['points_m'];points.extend((a,b,tuple((x+y)/2 for x,y in zip(a,b))))
        assert all(m['samples'][i]['valid'] for i in segment['sample_indices'])
    error=max(abs(math.hypot(p[0],p[1])-1) for p in points);errors.append(error);counts.append(len(r['segments']))
assert errors[0]/errors[1]>2.5 and errors[1]/errors[2]>2.5 and errors[2]/errors[3]>2.5 and errors[3]/errors[4]>1.4,errors
assert errors[-1]<.003,errors
# Opposite signed sources must produce the same geometric level set for -V.
axis=[-2+i/4 for i in range(17)]
positive=measurement(axis,axis,lambda x,y:1/math.hypot(x,y) if math.hypot(x,y)>.08 else None)
negative=measurement(axis,axis,lambda x,y:-1/math.hypot(x,y) if math.hypot(x,y)>.08 else None)
a=contours(grid(axis),positive,[1.],exclusions=exclusion);b=contours(grid(axis),negative,[-1.],exclusions=exclusion)
assert {tuple(s['points_m']) for s in a['segments']}=={tuple(s['points_m']) for s in b['segments']}
# A source wholly between valid samples still blocks its enclosing cells.
axis=[-1.,1.];m=measurement(axis,axis,lambda x,y:x)
hole=[{'id':'hidden-between-samples','position_m':[0.,0.,0.],'radius_m':.1}]
r=contours(grid(axis),m,[0.],exclusions=hole);assert not r['segments'] and r['source_exclusion_triangle_levels']==2
above=deepcopy(hole);above[0]['position_m'][2]=1.
r=contours(grid(axis),m,[0.],exclusions=above);assert r['segments'] and r['source_exclusion_triangle_levels']==0
flat=contours(grid(axis),measurement(axis,axis,lambda x,y:0.),[0.],exclusions=[])
assert not flat['segments'] and flat['constant_level_triangle_regions']==2
budget=contours(grid(xs),measurement(xs,xs,lambda x,y:x),[-1.,0.,1.],exclusions=[],maximum_segments=1)
assert len(budget['segments'])==1 and not budget['complete'] and budget['unprocessed_triangle_levels']>0 and budget['termination']=='segment_budget'
# Finite large signed potentials must interpolate without an overflowing deltaV.
huge=contours(grid(axis),measurement(axis,axis,lambda x,y:x*1e308),[0.],exclusions=[])
assert huge['segments'] and all(p[0]==0. for s in huge['segments'] for p in s['points_m'])
refusals=0
for action in (lambda:contours(grid(axis),m,[True],exclusions=[]),lambda:contours(grid([1.,-1.]),m,[0.],exclusions=[]),
               lambda:contours(grid(axis),m,[0.],exclusions=[],maximum_segments=0),lambda:contours(grid(axis),m,[0.],exclusions=hole*2),
               lambda:contours(grid(axis),{**m,'frame':'OTHER'},[0.],exclusions=[])):
    try:action()
    except ValueError:refusals+=1
    else:raise AssertionError('Invalid contour input accepted')
bad=deepcopy(m);bad['samples'][0]['position_m'][0]+=.1
try:contours(grid(axis),bad,[0.],exclusions=[])
except ValueError:refusals+=1
else:raise AssertionError('Reordered grid positions accepted')
report={'status':'isolated_electric_equipotential_geometry_analytic_refinement_and_domain_verified',
        'uniform_linear_potential_absolute_residual_V':uniform_error,'Coulomb_grid_axis_counts':[7,13,25,49,65],
        'Coulomb_unit_radius_max_error_m':errors,'Coulomb_segment_counts':counts,
        'signed_geometry_equivalent':True,'unsampled_source_exclusion_between_valid_vertices_omits_cell':True,
        'off_slice_source_does_not_mask_without_intersection':True,'constant_level_regions_not_fabricated_as_lines':True,
        'segment_budget_partial_explicit':True,'finite_large_signed_potential_interpolation_verified':True,'invalid_inputs_refused':refusals,
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (STAGE/'em_potential.py',Path(__file__))},
        'scope':'Isolated geometry from analytic frozen SI scalar samples; not a worker batch protocol, persistence, native/CEF integration or performance/visual acceptance.'}
(ROOT/'evidence/em-potential-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
