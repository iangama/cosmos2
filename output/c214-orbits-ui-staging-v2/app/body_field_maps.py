"""A sampled shell and masked meridional cut from the same frozen field provider."""
import math

from body_field_geometry import build as geometry, product
from body_field_lines import Model, vector
import geomagnetism as igrf


def build(reading):
    frame=geometry(reading);model=Model(reading)
    point=vector(frame['point_model_m']);expected=vector(frame['field_model_T'])
    actual=model.field(point)
    if max(abs(a-b) for a,b in zip(actual,expected))>2e-18:
        raise ValueError('Sonda e mapa magnético não compartilham a mesma solução.')
    earth=model.name=='IGRF14';coordinates=reading['coordinates']
    if earth:
        height=coordinates['altitude_m']
        values=[coordinates['latitude_deg'],coordinates['longitude_deg'],height]
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in values):raise ValueError('Coordenadas geodéticas inválidas.')
        declared=list(igrf.geodetic_position(*values))
        longitudes=list(range(-180,181,10));longitude=coordinates['longitude_deg']
        shell_definition={'latitude':'geodetic_WGS84','altitude_m':height,'longitude':'east_positive_minus180_to180'}
        extent=igrf.WGS_A+1e6
    else:
        radius=coordinates['radius_m']
        if type(radius) not in (int,float) or not math.isfinite(radius) or not model.radius<=radius<=20*model.radius:
            raise ValueError('Raio da casca joviana fora do domínio adotado.')
        lat,lon=coordinates['latitude_planetocentric_deg'],coordinates['longitude_east_deg']
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in [lat,lon]) or not -90<=lat<=90 or not 0<=lon<=360:
            raise ValueError('Ângulos jovianos fora do domínio adotado.')
        phi,lam=math.radians(lat),math.radians(lon)
        declared=[radius*math.cos(phi)*math.cos(lam),radius*math.cos(phi)*math.sin(lam),radius*math.sin(phi)]
        longitudes=list(range(0,361,10));longitude=coordinates['longitude_east_deg']
        shell_definition={'latitude':'planetocentric','radius_m':radius,'longitude':'east_positive_0_to360'}
        extent=max(3*model.radius,radius)
    if max(abs(x-y) for x,y in zip(point,declared))>.001:raise ValueError('Sonda e coordenadas declaradas divergiram.')
    latitudes=list(range(-90,91,10));calls=0
    def sample(position,allow_mask=False):
        nonlocal calls
        if model.clearance(position)<0:
            if allow_mask:return None
            raise ValueError('Casca fora do domínio magnético adotado.')
        calls+=1
        if calls>5000:raise ValueError('Orçamento de células magnéticas excedido.')
        b=model.field(position);render_field=product(frame['body_to_render'],b)
        return {'position_model_m':position,'field_model_T':b,'field_render_T':render_field,'field_norm_T':math.hypot(*b)}
    shell=[]
    for latitude in latitudes:
        row=[]
        for east in longitudes:
            if earth:position=list(igrf.geodetic_position(float(latitude),float(east),height))
            else:
                phi,lam=math.radians(latitude),math.radians(east)
                position=[radius*math.cos(phi)*math.cos(lam),radius*math.cos(phi)*math.sin(lam),radius*math.sin(phi)]
            row.append(sample(position))
        shell.append(row)
    lam=math.radians(longitude);axis=[math.cos(lam),math.sin(lam),0.]
    steps=65;grid=[-extent+2*extent*i/(steps-1) for i in range(steps)]
    cut=[[sample([u*axis[0],u*axis[1],z],allow_mask=True) for u in grid] for z in grid]
    return {'schema':1,'kind':'frozen_body_internal_magnetic_maps','model':model.name,'degree':model.degree,
        'reading':reading,'reading_sha256':frame['reading_sha256'],'epoch':reading['epoch'],
        'frame':frame['body_frame'],'body_to_render':frame['body_to_render'],'center_render_m':frame['center_render_m'],
        'shell':{'definition':shell_definition,'latitude_deg':latitudes,'east_longitude_deg':longitudes,'samples':shell,
            'seam':'First/last columns are the same meridian; repeated display boundary, not independent area samples.'},
        'cut':{'u_m':grid,'z_m':grid,'u_axis_model':axis,'z_axis_model':[0.,0.,1.],
            'samples':cut,'masked_cells':sum(p is None for row in cut for p in row),
            'definition':'Cartesian meridional slice through the model axis; outside adopted internal-field domain is masked, never zero.'},
        'probe':sample(point),'field_evaluations':calls,
        'units':{'position':'m','B':'T'},'observational_uncertainty':None,
        'policy':'Frozen adopted internal component only; no observational error bar, external magnetosphere, particle dynamics, native-map integration or unproven global extrema.'}
