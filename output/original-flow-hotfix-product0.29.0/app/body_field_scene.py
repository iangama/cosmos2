"""Prepare normalized native line meshes for one frozen SI magnetic point reading."""
from pathlib import Path
import hashlib
import json
import math
import uuid
import numpy as np

from body_attributes import rotation_euler
from body_field_geometry import build,product,arrow
from body_field_lines import bundle,Model
from body_field_maps import build as build_maps
from body_field_points import batches
from body_field_map_geometry import build as map_geometry,view as map_view

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())


def prepare(reading,representation='vector'):
    if representation not in ('vector','lines','shell','cut'):raise ValueError('Representação magnética não adotada.')
    geometry=build(reading);token=uuid.uuid4().hex
    geometry['representation']=representation
    if representation in ('shell','cut'):
        geometry['field_maps']=build_maps(reading)
        geometry['map_display']=map_geometry(geometry['field_maps'],representation)
        geometry['view']=map_view(geometry['field_maps'],geometry['map_display'])
        geometry['policy']='Frozen discrete internal magnetic sample map; eight |B| color bins, graphic sample glyphs, unavailable domain masked, no interpolation into unsampled points or force on neutral centers.'
    if representation=='lines':
        geometry['field_lines']=bundle(reading)
        geometry['policy']='Frozen confirmed internal-model field lines; domain and arc stops recorded, no inferred closure, plasma trajectory or force on neutral centers.'
    folder=ROOT/'output/body-field-previews'/token;folder.mkdir(parents=True)
    scale=geometry['reference_radius_m'];matrix=geometry['body_to_render']
    angles=rotation_euler([1.,0.,0.,0.],matrix)
    frame='LabBodyFieldFrame_'+token
    lua=lambda value:json.dumps(value,ensure_ascii=False)
    vec=lambda values:'{'+','.join(format(float(v),'.17g') for v in values)+'}'
    center=geometry['center_render_m']
    code='openspace.addSceneGraphNode({Identifier='+lua(frame)+',Parent="LabRoot",Transform={Translation={Type="StaticTranslation",Position='+vec(center)+'}},GUI={Name="Amostra magnetica fixa"}});'
    nodes=[frame];meshes=[]
    def mesh(name,curves,color,width):
        nonlocal code
        if not curves:return
        node='LabBodyField_'+name+'_'+token
        file,names=folder/(name+'.speck'),folder/(name+'.names')
        content=['# Frozen model-frame geometry normalized by reference radius; SI reading in receipt.'];name_lines=[]
        maximum=0.;vertices=0
        for i,curve in enumerate(curves):
            normalized=np.array(curve,dtype=np.float64)/scale
            error=float(np.max(np.abs(normalized.astype(np.float32).astype(np.float64)-normalized)))*scale
            maximum=max(maximum,error);vertices+=len(curve)
            if error>1e-6*scale:raise ValueError('Quantização da malha fora do limite gráfico adotado.')
            content += ['mesh -c 1 {','id '+name+str(i),str(len(curve)),
                *[' '.join(format(float(v),'.17g') for v in row) for row in normalized],'}']
            name_lines.append(name+str(i)+' '+name+str(i))
        file.write_text('\n'.join(content)+'\n',encoding='utf-8');names.write_text('\n'.join(name_lines)+'\n',encoding='utf-8')
        code+='openspace.addSceneGraphNode({Identifier='+lua(node)+',Parent='+lua(frame)+',Transform={Rotation={Type="StaticRotation",Rotation='+vec(angles)+'},Scale={Type="StaticScale",Scale='+format(scale,'.17g')+'}},Renderable={Type="RenderableConstellationLines",File='+lua(file.as_posix())+',NamesFile='+lua(names.as_posix())+',Unit="m",Colors={'+vec(color)+'},LineWidth='+str(width)+'},GUI={Name='+lua(name)+',Focusable=false}});'
        nodes.append(node);meshes.append({'node':node,'quantity':name,'file':file.as_posix(),'names_file':names.as_posix(),
            'file_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'names_sha256':hashlib.sha256(names.read_bytes()).hexdigest(),
            'curves':len(curves),'vertices':vertices,'color_rgb':color,'scale_m':scale,
            'rotation_euler_rad':angles,'float32_vertex_max_component_error_m':maximum,
            'conservative_display_position_error_bound_m':3*maximum+4e-6*max(scale,geometry['view']['distance_m'])+.1})
    mesh('reference_grid',geometry['reference_curves_m'],[.23,.46,.53],1)
    if representation=='lines':
        traced=geometry['field_lines'];model=Model(reading)
        mesh('field_lines',[line['points_m'] for line in traced['lines'] if len(line['points_m'])>1],[.3,.83,.95],2)
        directions=[]
        for line in traced['lines']:
            point=line['points_m'][len(line['points_m'])//2]
            direction=arrow(point,model.field(point),.07*scale)
            if direction['drawn']:directions.extend(direction['segments_m'])
        mesh('field_line_directions',directions,[.35,1.,.62],3)
    if representation in ('shell','cut'):
        points_code,points_meshes=batches(geometry,folder,frame,token,angles)
        code+=points_code;meshes.extend(points_meshes);nodes.extend(m['node'] for m in points_meshes)
    if geometry['arrow']['drawn']:mesh('magnetic_vector',geometry['arrow']['segments_m'],[.35,1.,.62],3)
    mesh('sample_point',geometry['point_cross_segments_m'],[1.,.79,.28],3)
    label='LabBodyFieldLabel_'+token
    local=product(matrix,geometry['point_model_m'])
    label_text='' if representation in ('shell','cut') else 'B · amostra fixa'
    code+='openspace.addSceneGraphNode({Identifier='+lua(label)+',Parent='+lua(frame)+',Transform={Translation={Type="StaticTranslation",Position='+vec(local)+'}},Renderable={Type="RenderableLabel",Text='+lua(label_text)+',FontSize=50,Size='+format(math.log10(geometry['view']['distance_m']*.002),'.17g')+',MinMaxSize={14,20},OrientationOption="Camera View Direction",EnableFading=false},GUI={Name="Ponto da amostra magnetica",Focusable=false}});'
    nodes.append(label)
    render={'id':token,'nodes':nodes,'frame_node':frame,'meshes':meshes,'frame_position_render_m':center,
        'view':geometry['view'],'label_node':label,'label_position_render_relative_m':local,
        'model_to_render_rotation_euler_rad':angles,'policy':geometry['policy'],'representation':representation}
    record={'schema':1,'geometry':geometry,'render':render,'source_sha256':{
        'body_field_scene.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'body_field_geometry.py':hashlib.sha256(Path(__file__).with_name('body_field_geometry.py').read_bytes()).hexdigest()}}
    receipt=folder/'receipt.json';receipt.write_text(json.dumps(record,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    render['receipt']=receipt.as_posix();render['receipt_sha256']=hashlib.sha256(receipt.read_bytes()).hexdigest()
    return code,{'geometry':geometry,'render':render}
