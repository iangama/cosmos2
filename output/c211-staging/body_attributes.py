"""Geometric radii and uncoupled inertial kinematic spin; no internal-energy model."""
import copy
import math
from physics import PHYSICAL_SCALE

C=299792458.

def defaults(meta,initial=None):
    radius=None;origin={'kind':'unknown'}
    source=next((b for b in initial['bodies'] if b['id']==meta['id']),None) if initial else None
    shape=source.get('shape_reference') if source else None
    if isinstance(shape,dict):
        axes=shape.get('radii_m')
        if isinstance(axes,list) and len(axes)==3 and all(type(x) in (int,float) and math.isfinite(x) and x>0 for x in axes):
            radius=math.cbrt(math.prod(axes));origin={'kind':'reference_volume_equivalent_sphere','reference_id':meta['reference_id'],'reference_shape':copy.deepcopy(shape),'formula':'(a*b*c)^(1/3)'}
        elif type(shape.get('radius_m')) in (int,float) and math.isfinite(shape['radius_m']) and shape['radius_m']>0:
            radius=shape['radius_m'];origin={'kind':'adopted_reference_sphere','reference_id':meta['reference_id'],'reference_shape':copy.deepcopy(shape)}
    return {'radius_m':radius,'radius_origin':origin,'angular_velocity_rad_s':None,'spin_origin':{'kind':'unknown'},
            'orientation_reference_wxyz':[1.,0.,0.,0.],'orientation_epoch_model_time':0.}

def inputs(radius,omega):
    if radius is not None and (type(radius) not in (int,float) or not math.isfinite(radius) or not 0<=radius<=1e12):raise ValueError('Raio deve ser desconhecido ou estar entre0 e1e12m.')
    if omega is not None and (not isinstance(omega,list) or len(omega)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in omega) or math.hypot(*omega)>1e3):raise ValueError('Spin exige três componentes finitas e norma até1e3rad/s, ou desconhecido.')
    if radius and omega and radius*math.hypot(*omega)>.01*C:raise ValueError('Velocidade de superfície supera0,01c, fora do domínio clássico adotado.')

def multiply(a,b):
    w,x,y,z=a;v,i,j,k=b
    return [w*v-x*i-y*j-z*k,w*i+x*v+y*k-z*j,w*j-x*k+y*v+z*i,w*k+x*j-y*i+z*v]

def orientation(value,time):
    omega=value['angular_velocity_rad_s'];q=value['orientation_reference_wxyz'];speed=math.hypot(*omega) if omega else 0
    if not speed:return list(q)
    elapsed=time-value['orientation_epoch_model_time'];period=2*math.pi/(speed*PHYSICAL_SCALE['time_unit_s'])
    angle=(math.remainder(elapsed,period)*speed*PHYSICAL_SCALE['time_unit_s']) if math.isfinite(period) else speed*elapsed*PHYSICAL_SCALE['time_unit_s']
    half=angle/2
    result=multiply([math.cos(half),*[x/speed*math.sin(half) for x in omega]],q);norm=math.hypot(*result)
    return [v/norm for v in result]

def rotation_euler(q,frame=None):
    w,x,y,z=q
    matrix=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
            [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
            [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
    if frame:matrix=[[sum(row[k]*matrix[k][j] for k in range(3)) for j in range(3)] for row in frame]
    sy=math.hypot(matrix[0][0],matrix[1][0])
    return [math.atan2(matrix[2][1],matrix[2][2]) if sy>=1e-8 else math.atan2(-matrix[1][2],matrix[1][1]),
            math.atan2(-matrix[2][0],sy),math.atan2(matrix[1][0],matrix[0][0]) if sy>=1e-8 else 0.]

def proposed(old,request,time):
    if 'radius_m' not in request or 'angular_velocity_rad_s' not in request:raise ValueError('Informe raio e spin explicitamente; null significa não definido.')
    radius,omega=request['radius_m'],request['angular_velocity_rad_s'];inputs(radius,omega)
    result=copy.deepcopy(old)
    if radius!=old['radius_m']:result.update(radius_m=radius,radius_origin={'kind':'user_model'})
    if omega!=old['angular_velocity_rad_s']:
        result.update(angular_velocity_rad_s=copy.deepcopy(omega),spin_origin={'kind':'user_model'},orientation_reference_wxyz=orientation(old,time),orientation_epoch_model_time=time)
    return result

def validate(value,meta,initial,time):
    expected=defaults(meta,initial)
    if not isinstance(value,dict) or set(value)!=set(expected):raise ValueError('Atributos geométricos/cinemáticos inválidos.')
    inputs(value['radius_m'],value['angular_velocity_rad_s'])
    for field in ('radius_origin','spin_origin'):
        origin=value[field]
        if origin not in ({'kind':'unknown'},{'kind':'user_model'}):
            if field!='radius_origin' or origin!=expected[field] or value['radius_m']!=expected['radius_m']:raise ValueError('Procedência dos atributos inválida.')
        if origin=={'kind':'unknown'} and value['radius_m' if field=='radius_origin' else 'angular_velocity_rad_s'] is not None:raise ValueError('Valor definido sem procedência.')
    epoch=value['orientation_epoch_model_time'];q=value['orientation_reference_wxyz']
    if type(epoch) not in (int,float) or not math.isfinite(epoch) or not 0<=epoch<=time:raise ValueError('Época cinemática inválida.')
    if not isinstance(q,list) or len(q)!=4 or any(type(x) not in (int,float) or not math.isfinite(x) for x in q) or abs(math.hypot(*q)-1)>1e-12:raise ValueError('Quaternion de orientação inválido.')
    return copy.deepcopy(value)

def restore(manifest,original_registry,events,registry,initial,time):
    modern=manifest['saved_generation']['model_version'] in ('3.1.0','3.2.0','3.3.0','3.4.0','3.5.0')
    active={b['id']:defaults(b,initial) for b in original_registry}
    for event in events:
        identifier=event['body'];kind=event['type']
        if kind=='create_body':active[identifier]=defaults(event['metadata'],initial)
        elif kind=='remove_body':
            if modern and event.get('removed_attributes')!=active[identifier]:raise ValueError('Atributos removidos não correspondem ao histórico.')
            active.pop(identifier)
        elif kind=='set_attributes':
            if not modern or event.get('old_attributes')!=active[identifier]:raise ValueError('Histórico de atributos incompatível.')
            new=event.get('new_attributes');meta=next((b for b in registry if b['id']==identifier),None)
            # Metadata also survives in the eventual removal event for deleted bodies.
            if meta is None:meta=next(e['metadata'] for e in events if e['type']=='remove_body' and e['body']==identifier)
            new=validate(new,meta,initial,event['time'])
            expected=proposed(active[identifier],new,event['time'])
            if new!=expected:raise ValueError('Edição de atributos não preserva orientação/procedência.')
            active[identifier]=new
    if modern:
        supplied=manifest.get('body_attributes')
        if not isinstance(supplied,dict) or supplied!=active:raise ValueError('Cadastro de atributos difere do histórico.')
    elif 'body_attributes' in manifest:raise ValueError('Geração antiga não declara atributos.')
    return {b['id']:validate(active[b['id']],b,initial,time) for b in registry}
