"""A passive SI Parker reading bound to one paused four-center scene."""
from pathlib import Path
import copy
import hashlib
import math
from is4_wind_field import AU_M
from is4_wind_snapshot import Snapshot,product,digest,FRAME
from is4_values import scalar

KIND='scene_Sun_Parker_prescribed_point'

def read(phase,coordinates,configuration=None):
    if not isinstance(coordinates,dict) or set(coordinates)!={'radius_m','latitude_deg','east_longitude_deg'}:raise ValueError('Complete heliographic SI coordinates required')
    c={k:scalar(v) for k,v in coordinates.items()}
    if not -90<=c['latitude_deg']<=90 or not -180<=c['east_longitude_deg']<=180:raise ValueError('Heliographic angles outside declared limits')
    model=Snapshot(phase,configuration);description=model.descriptor
    lat,lon=math.radians(c['latitude_deg']),math.radians(c['east_longitude_deg']);radius=c['radius_m']
    point=[radius*math.cos(lat)*math.cos(lon),radius*math.cos(lat)*math.sin(lon),radius*math.sin(lat)]
    if abs(c['latitude_deg'])==90.:point=[0.,0.,math.copysign(radius,c['latitude_deg'])]
    field=model.evaluate(point);rotation=description['model_to_J2000'];render=description['J2000_to_render'];center=description['origin_inertial_m']
    relative=product(rotation,point);inertial=[center[k]+relative[k] for k in range(3)]
    return dict(schema=1,kind=KIND,**{k:copy.deepcopy(phase[k]) for k in ['system_id','edit_token','revision','time','scientific_generation']},
        frame=FRAME,body_id=description['source_body_id'],body_reference_id='sol:naif:10',epoch=description['epoch'],
        coordinates=c,wind_parameters=model.field.configuration,point_model_m=point,sun_center_inertial_m=center,
        point_inertial_m=inertial,point_render_m=list(product(render,inertial)),model_to_J2000=rotation,J2000_to_render=render,
        field_model_T=field['magnetic_field_T'],field_J2000_T=list(product(rotation,field['magnetic_field_T'])),
        electric_field_model_V_m=field['electric_field_V_m'],wind_velocity_model_m_s=field['wind_velocity_m_s'],
        electric_potential_V=field['electric_potential_V'],gravity_potential_J_kg=field['gravity_potential_J_kg'],
        configuration_sha256=model.configuration_sha256,electric_policy='SI E=-u cross B prescribed; no Gaussian1/c factor.',
        provenance=dict(model='Parker prescrito, duas polaridades',reading_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),snapshot=description),
        uncertainty=None,uncertainty_reason='Didactic prescribed parameters; no fit, measurement uncertainty or model discrepancy propagated.',
        scope='Vento radial e campos prescritos, duas polaridades; folha equatorial±5° e proximidades dos planetas excluídas. Sem MHD, CME, espalhamento ou resposta do plasma.')

def validate(phase,reading):
    if not isinstance(reading,dict) or reading.get('kind')!=KIND:raise ValueError('Prescribed Parker reading required')
    expected=read(phase,reading.get('coordinates'),reading.get('wind_parameters'))
    if digest(expected)!=digest(reading):raise ValueError('Prescribed wind reading and paused source differ')
    return Snapshot(phase,reading['wind_parameters'])
