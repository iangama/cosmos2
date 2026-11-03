"""Magnified native plot of a paused, paired-position particle phase; no forces."""
from pathlib import Path
from dataclasses import asdict
import copy
import hashlib
import json
import math
import uuid
import numpy as np
from body_attributes import rotation_euler
from is4_values import scalar,vector
from is4_experiment import phase_record

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
GRAPHIC_UNIT_M=1e7


def identity(value,length=32):
    if not isinstance(value,str) or len(value)!=length or any(c not in '0123456789abcdef' for c in value):raise ValueError('Particle view identity invalid')
    return value


def matrix(value):
    if not isinstance(value,list) or len(value)!=3:raise ValueError('Three matrix rows required')
    result=np.array([vector(row) for row in value])
    if np.max(np.abs(result.T@result-np.eye(3)))>2e-12 or abs(np.linalg.det(result)-1)>2e-12:raise ValueError('Proper orthonormal frame required')
    return result


def geometry(state,physical_unit_m,initial_field_T,*,require_paused=True):
    if not isinstance(state,dict) or type(state.get('paused')) is not bool or require_paused and not state['paused'] or state.get('frame')!='is4_frozen_body_snapshot_axes_m':raise ValueError('Confirmed particle state required; pause for a static preview')
    identity(state.get('worker_id'))
    if type(state.get('sequence')) is not int or state['sequence']<1:raise ValueError('Positive publication sequence required')
    exp=state.get('experiment')
    if not isinstance(exp,dict):raise ValueError('Active particle required')
    for key in ['id','edit_token']:identity(exp.get(key))
    identity(exp.get('snapshot_configuration_sha256'),64)
    if type(exp.get('revision')) is not int or exp['revision']<0:raise ValueError('Particle revision invalid')
    unit=scalar(physical_unit_m)
    if not 1e-12<=unit<=1e12:raise ValueError('Physical plotting unit outside adopted range')
    phase=phase_record(exp['phase']);origin=vector(exp['parameters']['initial_position_m'])
    if phase.position_origin_m!=origin:raise ValueError('Particle launch origin differs')
    trail=exp.get('recent_trajectory')
    if not isinstance(trail,list) or not 1<=len(trail)<=129:raise ValueError('Bounded actual trajectory required')
    parsed=[phase_record(row) for row in trail]
    if asdict(parsed[-1])!=asdict(phase):raise ValueError('Trajectory endpoint and marker differ')
    if any(row.position_origin_m!=origin or row.time_s>phase.time_s for row in parsed):raise ValueError('Trajectory origin/time differs')
    if any(a.time_s>=b.time_s for a,b in zip(parsed,parsed[1:])):raise ValueError('Trajectory times not increasing')
    body_to_J2000=matrix(exp['model_to_J2000']);J2000_to_render=matrix(exp['J2000_to_render']);rotation=J2000_to_render@body_to_J2000
    center=np.array(vector(exp['body_center_inertial_m']));anchor=J2000_to_render@(center+body_to_J2000@origin)
    points=np.array([row.position_offset_m for row in parsed])/unit;marker=np.array(phase.position_offset_m)/unit
    if not np.isfinite(points).all():raise ValueError('Unrepresentable plotting positions')
    float_error=float(np.max(np.linalg.norm(points.astype(np.float32).astype(float)-points,axis=1)))*unit
    extent=max(1.,float(np.max(np.linalg.norm(points,axis=1))))
    world_scale=1e14+max(abs(float(v)) for v in anchor)+GRAPHIC_UNIT_M*extent
    frame_error=128*math.ulp(world_scale)/GRAPHIC_UNIT_M*unit
    if float_error+frame_error>1e-6*unit*extent:raise ValueError('Native plot quantization exceeds adopted bound')
    field=np.array(vector(initial_field_T));norm=np.linalg.norm(field);direction=field/norm if norm else np.array([0.,0.,1.])
    axis=np.eye(3)[int(np.argmin(abs(direction)))];side=np.cross(direction,axis);side/=np.linalg.norm(side)
    look=.65*direction+side;look/=np.linalg.norm(look);up=np.cross(direction,side);up/=np.linalg.norm(up)
    return {'schema':1,'identity':{k:state[k] for k in ['worker_id','sequence']}|{k:exp[k] for k in ['id','edit_token','revision','snapshot_configuration_sha256']},
        'phase':asdict(phase),'source_epoch':copy.deepcopy(exp['snapshot_epoch']),'model':exp['model'],'degree':exp['degree'],
        'physical_unit_m':unit,'graphic_unit_m':GRAPHIC_UNIT_M,'magnification':GRAPHIC_UNIT_M/unit,
        'plot_origin_model_m':list(origin),'anchor_relative_LabRoot_m':anchor.tolist(),'model_to_render':rotation.tolist(),
        'rotation_euler_rad':rotation_euler([1.,0.,0.,0.],rotation.tolist()),'vertices_normalized':points.tolist(),
        'sample_times_s':[row.time_s for row in parsed],'marker_normalized':marker.tolist(),'float32_error_m':float_error,
        'global_frame_conservative_error_m':frame_error,'adopted_total_error_bound_m':1e-6*unit*extent,
        'camera_offset_render_m':(rotation@(look*6*GRAPHIC_UNIT_M)).tolist(),'camera_up_render':(rotation@up).tolist(),
        'policy':'Magnified local plot, not a physical-size astronomical trajectory. Actual worker samples, normalized by declared SI length; geometry alone does not confirm native GPU upload.'}


def prepare(state,physical_unit_m,initial_field_T):
    g=geometry(state,physical_unit_m,initial_field_T);token=uuid.uuid4().hex;folder=ROOT/'output/is4-particle-previews'/token;folder.mkdir(parents=True)
    frame='LabIS4Frame_'+token;marker='LabIS4Marker_'+token;trail='LabIS4Trail_'+token;axes='LabIS4Axes_'+token
    file=folder/'trajectory.speck';names=folder/'trajectory.names';points=g['vertices_normalized']
    file.write_text('# Actual normalized paused particle samples\nmesh -c 1 {\nid trajectory\n'+str(len(points))+'\n'+'\n'.join(' '.join(format(v,'.17g') for v in p) for p in points)+'\n}\n',encoding='utf-8')
    names.write_text('trajectory trajectory\n',encoding='utf-8')
    lua=lambda v:json.dumps(v,ensure_ascii=True);vec=lambda v:'{'+','.join(format(float(x),'.17g') for x in v)+'}'
    code='openspace.addSceneGraphNode({Identifier='+lua(frame)+',Parent="LabRoot",Transform={Translation={Type="StaticTranslation",Position='+vec(g['anchor_relative_LabRoot_m'])+'},Rotation={Type="StaticRotation",Rotation='+vec(g['rotation_euler_rad'])+'},Scale={Type="StaticScale",Scale='+format(GRAPHIC_UNIT_M,'.17g')+'}},GUI={Name="Vista local ampliada da particula",Focusable=false}});'
    code+='openspace.addSceneGraphNode({Identifier='+lua(trail)+',Parent='+lua(frame)+',Renderable={Type="RenderableConstellationLines",File='+lua(file.as_posix())+',NamesFile='+lua(names.as_posix())+',Unit="m",Colors={{0.3,0.9,1.0}},LineWidth=3},GUI={Name="Trajetoria recente",Focusable=false}});'
    code+='openspace.addSceneGraphNode({Identifier='+lua(marker)+',Parent='+lua(frame)+',Transform={Translation={Type="StaticTranslation",Position='+vec(g['marker_normalized'])+'}},Renderable={Type="RenderableSphereImageLocal",Size=0.035,Segments=24,Texture=openspace.absPath("${COSMOS2}/data/markers/orbiter.ppm")},GUI={Name="Particula de teste"}});'
    code+='openspace.addSceneGraphNode({Identifier='+lua(axes)+',Parent='+lua(frame)+',Transform={Scale={Type="StaticScale",Scale=0.6}},Renderable={Type="RenderableCartesianAxes"},GUI={Name="Eixos do modelo congelado",Focusable=false}});'
    code+='openspace.navigation.setNavigationState({Anchor='+lua(marker)+',ReferenceFrame="LabRoot",Position='+vec(g['camera_offset_render_m'])+',Up='+vec(g['camera_up_render'])+'});'
    render={'id':token,'nodes':[frame,trail,marker,axes],'frame_node':frame,'marker_node':marker,'trajectory_node':trail,
        'file':file.as_posix(),'file_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'names_file':names.as_posix(),
        'names_sha256':hashlib.sha256(names.read_bytes()).hexdigest(),'identity':g['identity'],'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    receipt=folder/'receipt.json';receipt.write_text(json.dumps({'geometry':g,'render':render},indent=2)+'\n',encoding='utf-8')
    render['receipt']=receipt.as_posix();render['receipt_sha256']=hashlib.sha256(receipt.read_bytes()).hexdigest()
    code+='local p=openspace.propertyValue("Scene.'+marker+'.Translation.Position");local e='+vec(g['marker_normalized'])+';for k=1,3 do if math.abs(p[k]-e[k])>2e-12*math.max(1,math.abs(e[k])) then error("Particle marker coordinates not confirmed") end end;return {ready=true,sequence='+str(g['identity']['sequence'])+',position_normalized=p}'
    return code,{'geometry':g,'render':render}
