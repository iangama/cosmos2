"""Full geometry equivalence to preserved H, independent closed-box masks and cost."""
from pathlib import Path
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
import random
import time
ROOT=Path(__file__).resolve().parents[1];I=ROOT/'output/c212-em-framing-product';H=ROOT/'output/c212-em-cloud-editor-product'
dest=ROOT/'evidence/em-framing-geometry-check.json';assert not dest.exists()
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
old=module(H/'app/em_potential.py','old_contours');new=module(I/'app/em_potential.py','new_contours')
rng=random.Random(212012);checks=[]
def run(grid,sources,levels,name,constant=False,limit=4096):
    points=[[x,y,grid['z_m']] for x in grid['x_m'] for y in grid['y_m']]
    measurement={'system_id':'same-model','edit_token':'same-phase','revision':2,'frame':old.FRAME,'time_s':1.25,
                 'samples':[{'position_m':p,'valid':True,'electric_potential_V':0. if constant else 2*p[0]-3*p[1]+.1*p[2]} for p in points]}
    initial=deepcopy((grid,sources,levels,measurement));a=old.contours(grid,measurement,levels,exclusions=sources,maximum_segments=limit);b=new.contours(grid,measurement,levels,exclusions=sources,maximum_segments=limit)
    a.pop('algorithm');b.pop('algorithm');assert a==b,name
    assert (grid,sources,levels,measurement)==initial
    if a['complete']:
        unsafe=0
        for x0,x1 in zip(grid['x_m'],grid['x_m'][1:]):
            for y0,y1 in zip(grid['y_m'],grid['y_m'][1:]):
                def touches(s):
                    x,y,z=s['position_m'];dx=max(x0-x,0.,x-x1);dy=max(y0-y,0.,y-y1)
                    return math.hypot(dx,dy,z-grid['z_m'])<=s['radius_m']
                unsafe+=any(touches(s) for s in sources)
        assert a['source_exclusion_triangle_levels']==2*unsafe*len(levels),(name,a['source_exclusion_triangle_levels'],unsafe)
    checks.append({'case':name,'segments':len(a['segments']),'source_exclusion_triangle_levels':a['source_exclusion_triangle_levels'],'full_geometry_identical':True})
    return measurement
grid={'x_m':[-1.,0.,1.],'y_m':[-1.,0.,1.],'z_m':0.}
for r in (1.,math.nextafter(1.,0.),math.nextafter(1.,math.inf)):
    for p in ([2.,0.,0.],[0.,0.,1.],[1.,1.,1.],[-2.,0.,0.]):
        run(grid,[{'id':'edge','position_m':p,'radius_m':r}],[-1.,0.,1.],str((p,r)))
run(grid,[],[0.],'empty constant',True)
run(grid,[{'id':'all','position_m':[0.,0.,0.],'radius_m':1e200}],[0.],'all excluded',True)
run(grid,[{'id':'remote','position_m':[1e200,-1e200,1e200],'radius_m':1e-200}],[0.],'remote huge position')
for index in range(50):
    n=rng.choice((3,9,17));axis=[-4+8*i/(n-1) for i in range(n)];g={'x_m':axis,'y_m':axis,'z_m':rng.uniform(-2,2)}
    sources=[{'id':str(i),'position_m':[rng.uniform(-8,8) for _ in range(3)],'radius_m':10**rng.uniform(-6,1)} for i in range(rng.choice((0,1,8,128)))]
    run(g,sources,[-.5,0.,.5],'random'+str(index),index%9==0,16 if index%7==0 else 4096)
raw=json.loads((ROOT/'evidence/native-em128-c212hpotb.json').read_bytes());fixture=raw['fixture'];s=fixture['system']
sources=[{'id':sid,'position_m':p,'radius_m':r} for sid,p,r in zip(s['ids'],fixture['phase']['position_m'],s['exclusion_radius_m'])]
axis=[-3+6*i/32 for i in range(33)];g={'x_m':axis,'y_m':axis,'z_m':0.};measurement=run(g,sources,[-1.,0.,1.],'formal128geometry')
timings=[]
for repeat in range(4):
    for label,m in ([('old',old),('new',new)] if repeat%2==0 else [('new',new),('old',old)]):
        start=time.perf_counter();m.contours(g,measurement,[-1.,0.,1.],exclusions=sources)
        timings.append({'repeat':repeat+1,'version':label,'wall_ms':(time.perf_counter()-start)*1000})
report={'status':'I_exact_potential_geometry_equivalence_and_independent_masks_verified','checks':checks,'timings':timings,
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),H/'app/em_potential.py',I/'app/em_potential.py')},
        'scope':'Geometry unchanged except algorithm version/hash; tangency/ULP/random128/segment-budget and independent rectangle masks. Timings geometry only, not live2s sampler or native performance approval.'}
dest.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'cases':len(checks),'timings':timings}),flush=True)
