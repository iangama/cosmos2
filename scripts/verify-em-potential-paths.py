"""Prove topology/coordinates unchanged by exact-endpoint native path joining."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys
import tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];APP=ROOT/'output/c212-em-potential-product/app';sys.path.insert(0,str(APP))
from em_potential import contours
from em_potential_mesh import connected_paths,prepare_mesh
def key(a,b):return tuple(sorted((tuple(a),tuple(b))))
def audit(segments):
    paths=connected_paths(segments);expected=Counter(key(*p) for _,p in segments);actual=Counter()
    used=[]
    degree=Counter(tuple(p) for _,pair in segments for p in pair)
    for indices,points in paths:
        assert len(points)==len(indices)+1;used+=indices
        for p,q in zip(points,points[1:]):actual[key(p,q)]+=1
        for point in points[1:-1]:assert degree[tuple(point)]==2,'Path fabricated a choice through a junction'
    assert actual==expected and sorted(used)==sorted(i for i,_ in segments)
    return paths
fixtures=[[(0,[[0,0,0],[1,0,0]]),(1,[[1,0,0],[2,0,0]])],
          [(0,[[0,0,0],[1,0,0]]),(1,[[1,0,0],[1,1,0]]),(2,[[1,1,0],[0,0,0]])],
          [(0,[[0,0,0],[1,0,0]]),(1,[[0,0,0],[-1,0,0]]),(2,[[0,0,0],[0,1,0]]),(3,[[0,0,0],[0,-1,0]])],
          [(0,[[0,0,0],[1,0,0]]),(1,[[1+1e-15,0,0],[2,0,0]])]]
counts=[len(audit([(i,np.array(p,dtype=float)) for i,p in case])) for case in fixtures]
assert counts==[1,1,4,2],counts
axis=[-2+i/8 for i in range(33)];grid={'x_m':axis,'y_m':axis,'z_m':.35}
m={'system_id':'test','edit_token':'test','revision':0,'time_s':0.,'frame':'EM_SI_FIXED_INERTIAL',
   'samples':[{'position_m':[x,y,.35],'valid':True,'electric_potential_V':3*x-2*y} for x in axis for y in axis]}
g=contours(grid,m,[-1.,0.,1.],exclusions=[]);layer={'measurement':m,'geometry':g};worst=0.
with tempfile.TemporaryDirectory(prefix='cosmos2-contour-paths-') as temp:
    r=prepare_mesh(layer,Path(temp)/'meshes');curves=0
    for mesh in r['meshes']:
        original=[(i,np.array(g['segments'][i]['points_m'])) for i in mesh['segment_indices']];audit(original)
        rows=Path(mesh['file']).read_text().splitlines();paths=[]
        for i,row in enumerate(rows):
            if row.startswith('mesh '):
                count=int(rows[i+2]);paths.append(np.array([[float(v) for v in s.split()] for s in rows[i+3:i+3+count]],dtype=np.float32).astype(float))
        assert len(paths)==mesh['curve_count'];curves+=len(paths)
        for points,indices in zip(paths,mesh['curve_segment_indices']):
            si=points*mesh['local_unit_model_m']+mesh['center_model_m'];assert len(si)==len(indices)+1
            for j,index in enumerate(indices):
                expected=np.array(g['segments'][index]['points_m']);actual=si[j:j+2]
                error=min(float(np.max(abs(actual-expected))),float(np.max(abs(actual[::-1]-expected))));worst=max(worst,error)
                assert error<=3e-7*mesh['local_unit_model_m'] and np.all(actual[:,2]==.35)
report={'status':'native_potential_path_joining_preserves_every_measured_edge_without_smoothing_or_fabricated_closure',
        'open_cycle_junction_and_nearby_disconnected_path_counts':counts,'uniform_original_segments':len(g['segments']),'native_paths':curves,
        'independent_float32_SI_component_error_m':worst,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (APP/'em_potential.py',APP/'em_potential_mesh.py',Path(__file__))},
        'scope':'Geometry/topology/actual SM files only. Exact endpoints join at degree2; junctions/disconnected endpoints remain separate. Native frame improvement requires a new measured profile.'}
(ROOT/'evidence/em-potential-paths-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
