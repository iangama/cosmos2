"""Prepare native SM files from frozen electric equipotential segments.

No engine calls or scene mutations. Coordinates remain in the measured slice;
local centering limits float32 loss. Width/color are graphic choices.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import math
import uuid
import numpy as np

DISPLAY_SCALE=1e9
def prepare_mesh(layer,destination,*,enabled=True):
    if type(enabled) is not bool:raise ValueError('Explicit potential visibility required')
    geometry=layer['geometry'];measurement=layer['measurement']
    if geometry.get('schema')!=1 or geometry.get('kind')!='electric_equipotential_slice':raise ValueError('Electric equipotential layer required')
    if geometry['metadata']!={k:measurement[k] for k in ('system_id','edit_token','revision','frame','time_s')}:raise ValueError('Potential geometry and measurement stamps differ')
    canonical=json.dumps(measurement,sort_keys=True,allow_nan=False,separators=(',',':')).encode()
    if hashlib.sha256(canonical).hexdigest()!=geometry['measurement_sha256']:raise ValueError('Potential geometry belongs to another measurement')
    grid=geometry['grid'];center=np.array([(grid['x_m'][0]+grid['x_m'][-1])/2,(grid['y_m'][0]+grid['y_m'][-1])/2,grid['z_m']],dtype=float)
    unit=max(grid['x_m'][-1]-grid['x_m'][0],grid['y_m'][-1]-grid['y_m'][0])/2
    if not np.isfinite(center).all() or not math.isfinite(unit) or not 1e-12<=unit<=1e9:raise ValueError('Potential mesh outside native display scale domain')
    if not isinstance(geometry['segments'],list) or len(geometry['segments'])>8192:raise ValueError('Bounded potential segments required')
    grouped={level:[] for level in geometry['levels_V']}
    for index,segment in enumerate(geometry['segments']):
        points=np.array(segment['points_m'],dtype=float);level=segment['level_V']
        if points.shape!=(2,3) or not np.isfinite(points).all() or level not in grouped or not np.all(points[:,2]==grid['z_m']):raise ValueError('Invalid electric slice segment')
        grouped[level].append((index,points))
    folder=Path(destination)
    if folder.exists():raise ValueError('Native potential assets need a new directory')
    folder.mkdir(parents=True);token=uuid.uuid4().hex;meshes=[];nodes=[]
    for i,(level,segments) in enumerate(grouped.items()):
        if not segments:continue
        file=folder/f'level-{i}.speck';names=folder/f'level-{i}.names'
        rows=['# Frozen electric equipotential slice; SI voltage, no height warp'];local_error=reconstruction_error=0.
        for index,points in segments:
            local=(points-center)/unit;actual=local.astype(np.float32).astype(float)
            local_error=max(local_error,float(np.max(abs(actual-local)))*unit)
            reconstruction_error=max(reconstruction_error,float(np.max(abs(actual*unit+center-points))))
            rows+=['mesh -c 1 {','id potential'+str(index),'2',*[' '.join(format(v,'.17g') for v in p) for p in local],'}']
        if local_error>3e-7*unit:raise ValueError('Native potential vertex precision budget exceeded')
        file.write_text('\n'.join(rows)+'\n');names.write_text(''.join('potential'+str(index)+' level'+str(i)+'\n' for index,_ in segments))
        node='C2EMPotential_'+str(i)+'_'+token;color=[1.,.65,.25] if level>0 else [.35,.55,1.] if level<0 else [.85,.9,.95]
        nodes.append({'Identifier':node,'Parent':'C2EMRoot',
                      'Transform':{'Translation':{'Type':'StaticTranslation','Position':(center*DISPLAY_SCALE).tolist()},'Scale':{'Type':'StaticScale','Scale':unit*DISPLAY_SCALE}},
                      'Renderable':{'Type':'RenderableConstellationLines','File':file.as_posix(),'NamesFile':names.as_posix(),'Unit':'m','Colors':[color],'LineWidth':1.5,'Enabled':enabled},
                      'GUI':{'Name':'Potencial elétrico '+format(level,'.6g')+' V · congelado','Focusable':False}})
        meshes.append({'node':node,'level_V':level,'segment_indices':[index for index,_ in segments],
                       'file':file.as_posix(),'file_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
                       'names_file':names.as_posix(),'names_sha256':hashlib.sha256(names.read_bytes()).hexdigest(),
                       'center_model_m':center.tolist(),'local_unit_model_m':unit,'vertex_count':2*len(segments),
                       'float32_local_component_error_model_m':local_error,'SI_reconstruction_component_error_m':reconstruction_error})
    report={'schema':1,'metadata':deepcopy(geometry['metadata']),'meshes':meshes,'nodes':nodes,
            'complete':geometry['complete'],'termination':geometry['termination'],'graphic_render_m_per_model_m':DISPLAY_SCALE,
            'policy':'Uniform graphic width, colors distinguish voltage sign; each level retains its numeric SI voltage. Centered local vertices stay on the actual measured slice, no height warp.',
            'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (folder/'receipt.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');return report
