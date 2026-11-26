"""Read-only, bounded grid sampling under a caller-owned worker command lock.

No native/UI changes occur here. A caller may publish the returned layer only
after success; failures leave its previous frozen layer intact.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import math
import time
from em_potential import contours,finite

KEYS=('system_id','edit_token','revision','frame','time_s')
CRITICAL=(*KEYS,'paused','experiment','scientific_generation')
def sample_slice(read_state,query,command_lock,grid,levels_V,*,maximum_segments=4096,budget_s=2.):
    budget=finite(budget_s)
    if not 0<budget<=2:raise ValueError('Sampling wall budget must be positive and<=2s')
    with command_lock:
        began=time.monotonic();initial=deepcopy(read_state())
        grid=deepcopy(grid);levels_V=deepcopy(levels_V)
        if initial.get('paused') is not True:raise ValueError('Pause before measuring an electric potential slice')
        # Validate shape/bounds before allocating or contacting the worker.
        if not isinstance(grid,dict) or set(grid)!={'x_m','y_m','z_m'}:raise ValueError('Explicit Cartesian grid required')
        for key in ('x_m','y_m'):
            a=grid[key]
            if not isinstance(a,(list,tuple)) or not 2<=len(a)<=65:raise ValueError('Grid axes need2..65 samples')
            axis=list(map(finite,a))
            if any(abs(v)>1e9 for v in axis) or any(a>=b for a,b in zip(axis,axis[1:])):raise ValueError('Strictly increasing bounded grid axes required')
        z=finite(grid['z_m'])
        if abs(z)>1e9:raise ValueError('Slice outside supported domain')
        points=[[finite(x),finite(y),z] for x in grid['x_m'] for y in grid['y_m']]
        metadata={k:deepcopy(initial[k]) for k in KEYS};ex=initial['experiment']
        if ex['mode']=='test_particle':
            exclusions=[{'id':s['id'],'position_m':s['position_m'],'radius_m':s['exclusion_radius_m']} for s in ex['model']['sources']]
        elif ex['mode']=='mutual_electrostatic':
            exclusions=[{'id':sid,'position_m':p,'radius_m':r} for sid,p,r in zip(ex['system']['ids'],ex['phase']['position_m'],ex['system']['exclusion_radius_m'])]
        else:raise ValueError('Unsupported EM potential regime')
        dummy={**metadata,'samples':[{'position_m':p,'valid':False} for p in points]}
        contours(grid,dummy,levels_V,exclusions=exclusions,maximum_segments=maximum_segments)
        guard={k:initial[k] for k in ('system_id','edit_token','revision','frame')}|{'expected_time_s':initial['time_s']}
        samples=[];batches=[]
        def unchanged():
            now=read_state()
            if any(now.get(k)!=initial[k] for k in CRITICAL):raise ValueError('EM snapshot changed during slice measurement; discard every batch')
        for offset in range(0,len(points),128):
            unchanged()
            if time.monotonic()-began>budget:raise TimeoutError('Potential slice sampling budget exceeded; no partial layer published')
            batch=points[offset:offset+128];ack=query({'command':'field_map',**guard,'points_m':batch})
            result=ack.get('result')
            if ack.get('type')!='ack' or ack.get('paused') is not True or ack.get('time_s')!=initial['time_s'] or not isinstance(result,dict):raise ValueError('Unconfirmed potential batch')
            if {k:result.get(k) for k in KEYS}!=metadata or not isinstance(result.get('samples'),list) or len(result['samples'])!=len(batch):raise ValueError('Potential batch identity/count mismatch')
            for point,sample in zip(batch,result['samples']):
                if sample.get('position_m')!=point:raise ValueError('Potential batch positions changed order')
            samples.extend(deepcopy(result['samples']));batches.append({'offset':offset,'samples':len(batch)})
        unchanged()
        if time.monotonic()-began>budget:raise TimeoutError('Potential slice sampling budget exceeded; no partial layer published')
        measured={**metadata,'samples':samples}
        layer=contours(grid,measured,levels_V,exclusions=exclusions,maximum_segments=maximum_segments)
        unchanged();elapsed=time.monotonic()-began
        if elapsed>budget:raise TimeoutError('Potential slice geometry budget exceeded; no partial layer published')
        return {'measurement':measured,'geometry':layer,'source_snapshot':deepcopy(ex),
                'scientific_generation':deepcopy(initial['scientific_generation']),
                'batch_protocol':{'maximum_points_per_request':128,'batches':batches,'all_same_confirmed_snapshot':True,
                                  'elapsed_wall_ms':elapsed*1000,'budget_s':budget,
                                  'budget_policy':'Checked before/after synchronous queries and geometry; this is not an interrupt guarantee for a stalled query.',
                                  'assembler_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}}
