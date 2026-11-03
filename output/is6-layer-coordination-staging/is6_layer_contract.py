"""Admission plan for independent frozen references; no native scene ownership."""
import copy
import hashlib
import json
import math

from is6_product_scene import artifact
import earth_magnetism
import jupiter_magnetism


def encoded(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def magnetic(phase,reading):
    if not isinstance(reading,dict):
        raise ValueError('Explicit frozen magnetic reading required')
    try:
        body=reading['body_id'];coords=reading['coordinates']
        if reading['body_reference_id']=='sol:naif:399':
            actual=earth_magnetism.read(phase,body,coords['latitude_deg'],coords['longitude_deg'],coords['altitude_m'])
        elif reading['body_reference_id']=='sol:naif:599':
            actual=jupiter_magnetism.read(phase,body,coords['radius_m'],coords['latitude_planetocentric_deg'],coords['longitude_east_deg'],reading['degree'])
        else:
            raise ValueError('No adopted internal magnetic layer for this body')
        if encoded(actual)!=encoded(reading):
            raise ValueError('Recomputed frozen magnetic reading differs')
    except (KeyError,TypeError,OverflowError) as error:
        raise ValueError('Incomplete magnetic reading') from error
    return actual


def compose(phase,spatial_payload,magnetic_reading,visible):
    """Recompute both references and admit only an identical source and epoch."""
    if not isinstance(visible,dict) or set(visible)!={'spatial','magnetic'} or any(type(v) is not bool for v in visible.values()):
        raise ValueError('Two explicit boolean visibilities required')
    phase=copy.deepcopy(phase)
    run=artifact.Run.restore(copy.deepcopy(spatial_payload))
    payload=run.payload
    if encoded(payload['phase'])!=encoded(phase):
        raise ValueError('Spatial reference belongs to another source phase')
    b=payload['binding'];r=magnetic(phase,copy.deepcopy(magnetic_reading))
    guard=artifact.body.guard(phase)
    if any(r[k]!=guard[k] for k in guard if k!='frame') or r['frame']!=guard['frame']:
        raise ValueError('Magnetic phase or frame differs')
    if r['body_id']!=b['body_id'] or r['body_reference_id']!=b['body_reference_id']:
        raise ValueError('Both references must describe the same body')
    if r['epoch']['et_tdb_s']!=b['epoch']['et_tdb_s'] or r['J2000_to_render']!=b['J2000_to_render']:
        raise ValueError('Reference epoch or render orientation differs')
    center_key='earth_center_inertial_m' if r['body_reference_id']=='sol:naif:399' else 'jupiter_center_inertial_m'
    if any(not math.isclose(x,y,rel_tol=0,abs_tol=.001) for x,y in zip(r[center_key],b['center_inertial_m'],strict=True)):
        raise ValueError('Reference SI centers differ by more than1mm')
    result=dict(schema=1,kind='is6_independent_layer_admission_plan',source_guard=guard,
        source_phase_sha256=digest(phase),body_id=b['body_id'],body_reference_id=b['body_reference_id'],
        epoch=copy.deepcopy(b['epoch']),source_frame=b['source_frame'],render_frame='GALACTIC',
        position_unit='m',center_render_m=list(b['center_render_m']),J2000_to_render=copy.deepcopy(b['J2000_to_render']),
        layers=[dict(id='spatial',model='Schwarzschild isolated exterior spatial slice',visible=visible['spatial'],
                     solution_sha256=artifact.digest(payload),artifact_id=run.id,quantity_units=dict(curvature='m^-4',clock_ratio='1'),
                     display_vertical_amplification=payload['configuration']['vertical_amplification']),
                dict(id='magnetic',model=r['provenance']['model'],visible=visible['magnetic'],solution_sha256=digest(r),
                     quantity_units=dict(magnetic_field='T'),provenance=copy.deepcopy(r['provenance']),
                     uncertainty=r['uncertainty'],uncertainty_reason=r['uncertainty_reason'])],
        camera_owner='future_composite_scene_owner',native_coexistence_confirmed=False,
        physical_coupling=False,scope='Admission only; independent models, no combined field, native view, persistence or performance acceptance.')
    return {**result,'plan_sha256':digest(result)}
