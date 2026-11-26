"""I: evaluate identical exclusion masks by source, pruning only exact lower bounds."""
from pathlib import Path
import ast
import hashlib
import json
ROOT=Path(__file__).resolve().parents[1];I=ROOT/'output/c212-em-framing-product'
dest=ROOT/'evidence/em-framing-geometry-prepared.json';assert not dest.exists()
path=I/'app/em_potential.py';before=path.read_bytes();source=before.decode()
old="""    triangles=[];ny=len(ys)
    for i in range(len(xs)-1):
        for j in range(ny-1):
            a=i*ny+j;b=(i+1)*ny+j;c=b+1;d=a+1
            unsafe=any(math.hypot(p[0]-min(xs[i+1],max(xs[i],p[0])),p[1]-min(ys[j+1],max(ys[j],p[1])),p[2]-z)<=radius for p,radius in sources)
            triangles.extend((((a,b,c),unsafe),((a,c,d),unsafe)))"""
new="""    triangles=[];ny=len(ys)
    # Exact same closed-sphere/rectangle distance as before. Axis distances
    # are lower bounds: they only skip spheres that cannot touch a cell.
    # Every declared source remains in the receipt and in the field solver.
    unsafe_cells=[[False]*(ny-1) for _ in range(len(xs)-1)]
    for p,radius in sources:
        dz=p[2]-z
        if abs(dz)>radius:continue
        for i in range(len(xs)-1):
            dx=p[0]-min(xs[i+1],max(xs[i],p[0]))
            if abs(dx)>radius:continue
            for j in range(ny-1):
                if unsafe_cells[i][j]:continue
                dy=p[1]-min(ys[j+1],max(ys[j],p[1]))
                if abs(dy)<=radius and math.hypot(dx,dy,dz)<=radius:unsafe_cells[i][j]=True
    for i in range(len(xs)-1):
        for j in range(ny-1):
            a=i*ny+j;b=(i+1)*ny+j;c=b+1;d=a+1
            unsafe=unsafe_cells[i][j]
            triangles.extend((((a,b,c),unsafe),((a,c,d),unsafe)))"""
assert source.count(old)==1 and source.count("VERSION='0.1.0'")==1
source=source.replace(old,new).replace("VERSION='0.1.0'","VERSION='0.1.1'");ast.parse(source)
path.write_text(source)
report={'status':'I_exact_exclusion_mask_loop_prepared_awaiting_equivalence_and_live_checks',
        'before_sha256':hashlib.sha256(before).hexdigest(),'source_sha256':{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()},
        'scope':'App geometry only; same math.hypot distance and inclusive boundary, fewer repeated axis calculations. No source removed from field evaluation, no change to2s/33grid/128sources/scientific core or worker.'}
dest.write_text(json.dumps(report,indent=2)+'\n');print(report['status'],flush=True)
