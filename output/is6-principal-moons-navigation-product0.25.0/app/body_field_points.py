"""Native batches of exact frozen magnetic sample positions, at most eight VBOs."""
from pathlib import Path
import hashlib
import json
import math
import numpy as np


def batches(geometry,folder,frame,token,angles):
    display=geometry['map_display'];source=geometry['field_maps'][display['representation']]
    scale=geometry['reference_radius_m']
    # Billboard diameter is a display quantity in world meters; the pointcloud
    # shader transforms positions by the model matrix but not billboard size.
    diameter=.018*display['view_radius_m']
    lua=lambda value:json.dumps(value,ensure_ascii=False)
    vec=lambda values:'{'+','.join(format(float(v),'.17g') for v in values)+'}'
    code='';meshes=[]
    for index,item in enumerate(display['bins']):
        if not item['cells']:continue
        points=[source['samples'][r][c]['position_model_m'] for r,c in item['cells']]
        normalized=np.asarray(points,dtype=np.float64)/scale
        error=float(np.max(np.abs(normalized.astype(np.float32).astype(np.float64)-normalized)))*scale
        if error>1e-6*scale:raise ValueError('Quantização do lote magnético fora do limite gráfico.')
        name='field_map_bin_'+str(index);node='LabBodyField_'+name+'_'+token
        path=Path(folder)/(name+'.csv')
        path.write_text('x,y,z\n'+'\n'.join(','.join(format(float(v),'.17g') for v in p) for p in normalized)+'\n',encoding='utf-8')
        code+='openspace.addSceneGraphNode({Identifier='+lua(node)+',Parent='+lua(frame)+',Transform={Rotation={Type="StaticRotation",Rotation='+vec(angles)+'},Scale={Type="StaticScale",Scale='+format(scale,'.17g')+'}},Renderable={Type="RenderablePointCloud",File='+lua(path.as_posix())+',Unit="m",UseCaching=false,UseAdditiveBlending=false,Texture={Enabled=false},Coloring={FixedColor='+vec(item['color_rgb'])+'},SizeSettings={ScaleExponent='+format(math.log10(diameter),'.17g')+',ScaleFactor=1,EnableMaxSizeControl=true,MaxSize=0.18}},GUI={Name='+lua(name)+',Focusable=false}});'
        meshes.append({'node':node,'quantity':name,'file':path.as_posix(),
            'file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'renderer':'RenderablePointCloud','points':len(points),'vertices':len(points),
            'cells':item['cells'],'color_rgb':item['color_rgb'],'scale_m':scale,
            'rotation_euler_rad':angles,'graphic_point_diameter_m':diameter,
            'maximum_angular_diameter_degrees':.18,'float32_vertex_max_component_error_m':error,
            'conservative_display_position_error_bound_m':3*error+4e-6*max(scale,geometry['view']['distance_m'])+.1})
    assert sum(m['points'] for m in meshes)==display['drawn_symbols']
    return code,meshes
