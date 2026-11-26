"""Frozen model-frame geometry from a trusted scene-bound magnetic point reading."""
import copy
import hashlib
import json
import math


def vector(value):
    if not isinstance(value,(list,tuple)) or len(value)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in value):
        raise ValueError('Vetor gráfico deve ter três componentes finitas.')
    return list(value)


def product(matrix,value):return [math.fsum(row[k]*value[k] for k in range(3)) for row in matrix]


def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]


def rotation(value):
    if not isinstance(value,list) or len(value)!=3:raise ValueError('Matriz gráfica3×3 ausente.')
    rows=[vector(row) for row in value]
    error=max(abs(math.fsum(rows[i][k]*rows[j][k] for k in range(3))-(i==j)) for i in range(3) for j in range(3))
    determinant=math.fsum(rows[0][i]*cross(rows[1],rows[2])[i] for i in range(3))
    if error>2e-12 or abs(determinant-1)>2e-12:raise ValueError('Transformação gráfica deve ser uma rotação própria.')
    return rows


def arrow(point,field,length):
    point,field=vector(point),vector(field)
    if type(length) not in (int,float) or not math.isfinite(length) or length<=0:raise ValueError('Comprimento gráfico inválido.')
    norm=math.hypot(*field)
    if not math.isfinite(norm):raise ValueError('Norma de B não finita.')
    if norm==0:return {'drawn':False,'reason':'Norma de B nula; direção indefinida.','field_norm_T':0.}
    direction=[v/norm for v in field]
    axis=min(range(3),key=lambda k:abs(direction[k]));side=cross(direction,[float(k==axis) for k in range(3)])
    side_norm=math.hypot(*side);side=[v/side_norm for v in side]
    tip=[point[k]+length*direction[k] for k in range(3)]
    base=[tip[k]-.25*length*direction[k] for k in range(3)]
    left=[base[k]+.12*length*side[k] for k in range(3)];right=[base[k]-.12*length*side[k] for k in range(3)]
    return {'drawn':True,'direction':direction,'field_norm_T':norm,'length_m':length,
        'segments_m':[[point,tip],[left,tip,right]],'scale':'Uniform graphic length; magnitude remains an SI readout, not an arrow-length scale.'}


def reference_grid(a,b):
    curves=[];steps=96
    for latitude_deg in [-60,-30,0,30,60]:
        latitude=math.radians(latitude_deg)
        curves.append([[a*math.cos(latitude)*math.cos(2*math.pi*i/steps),
            a*math.cos(latitude)*math.sin(2*math.pi*i/steps),b*math.sin(latitude)] for i in range(steps+1)])
    for longitude_deg in range(0,180,30):
        longitude=math.radians(longitude_deg)
        curves.append([[a*math.cos(2*math.pi*i/steps)*math.cos(longitude),
            a*math.cos(2*math.pi*i/steps)*math.sin(longitude),b*math.sin(2*math.pi*i/steps)] for i in range(steps+1)])
    return curves


def build(reading):
    kind=reading.get('kind')
    if kind=='scene_Earth_IGRF14_passive_point':
        point=vector(reading['point_ITRF93_m']);field=vector(reading['field_ITRF93_T'])
        center=vector(reading['earth_center_inertial_m']);body_rotation=rotation(reading['ITRF93_to_J2000'])
        a=6378137.;b=a*(1-1/298.257223563);model='IGRF14';body_frame='ITRF93'
        reference={'kind':'WGS84_reference_ellipsoid','semiaxes_m':[a,a,b],
            'scope':'Model ellipsoid only; parametric graticule, no topography or measured station transformation.'}
    elif kind=='scene_Jupiter_JRM33_passive_point':
        point=vector(reading['point_SystemIII_m']);field=vector(reading['field_SystemIII_T'])
        center=vector(reading['jupiter_center_inertial_m']);body_rotation=rotation(reading['SystemIII_to_J2000'])
        a=b=71492000.;model='JRM33';body_frame='right_handed_System_III_1965'
        reference={'kind':'JRM33_reference_sphere','semiaxes_m':[a,a,b],
            'scope':'Harmonic reference sphere only; not an adopted solid or oblate Jovian surface.'}
    else:raise ValueError('Leitura magnética corporal confirmada ausente.')
    render_rotation=rotation(reading['J2000_to_render'])
    model_to_render=[[math.fsum(render_rotation[i][k]*body_rotation[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    center_render=product(render_rotation,center)
    point_render=[center_render[k]+product(model_to_render,point)[k] for k in range(3)]
    # Relative comparison avoids falsely rejecting normal large-origin rounding.
    if max(abs(x-y) for x,y in zip(point_render,reading['point_render_m']))>.001:
        raise ValueError('Ponto gráfico não corresponde à leituraSI.')
    magnetic_arrow=arrow(point,field,.3*a)
    marker=[]
    for axis in range(3):
        first=list(point);last=list(point);first[axis]-=.025*a;last[axis]+=.025*a;marker.append([first,last])
    normalized=[v/math.hypot(*point) for v in point]
    tangent_axis=min(range(3),key=lambda k:abs(normalized[k]));tangent=cross(normalized,[float(k==tangent_axis) for k in range(3)])
    tangent=[v/math.hypot(*tangent) for v in tangent]
    viewing=[normalized[k]+.65*tangent[k] for k in range(3)];viewing=[v/math.hypot(*viewing) for v in viewing]
    up=cross(viewing,tangent);up=[v/math.hypot(*up) for v in up]
    extent=max(a,math.hypot(*point)+.3*a);distance=3.4*extent
    encoded=json.dumps(reading,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    return {'schema':1,'kind':'frozen_body_magnetic_vector','model':model,
        'metadata':{k:copy.deepcopy(reading[k]) for k in ['system_id','body_id','edit_token','revision','time','epoch']},
        'reading_sha256':hashlib.sha256(encoded).hexdigest(),'reading':copy.deepcopy(reading),
        'body_frame':body_frame,'reference':reference,'reference_radius_m':a,
        'center_inertial_m':center,'center_render_m':center_render,'body_to_render':model_to_render,
        'point_model_m':point,'field_model_T':field,'point_render_m':point_render,
        'reference_curves_m':reference_grid(a,b),'arrow':magnetic_arrow,'point_cross_segments_m':marker,
        'view':{'distance_m':distance,'position_render_relative_m':product(model_to_render,[v*distance for v in viewing]),
            'up_render':product(model_to_render,up)},
        'policy':'Frozen confirmed inertial sample, graphic uniform arrow length, no force on neutral centers or field-line inference.'}
