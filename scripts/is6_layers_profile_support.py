"""K3 profile transport and scientific checks; no collector starts on import."""
import copy
import is6_pair_profile_support as resources

LIMITS = dict(resources.LIMITS)
WINDOWS = list(resources.WINDOWS)
COMBINATIONS = copy.deepcopy(resources.COMBINATIONS)


def recipe(kind):
    if kind not in {'static', 'visibility'}:
        raise ValueError('Unknown K3 profile window')
    return ([] if kind == 'static' else
            [dict(tick=tick, offset_s=tick*.5, visible=copy.deepcopy(COMBINATIONS[tick % 4])) for tick in range(120)])


def settings(phase, reference_id):
    if reference_id not in {'sol:naif:399', 'sol:naif:599'}:
        raise ValueError('Unprofiled body')
    body = next(b for b in phase['bodies'] if b['reference_id'] == reference_id)
    magnetic = (dict(model='IGRF14', latitude_deg=-23.55, longitude_deg=-46.63, altitude_m=1000.)
                if reference_id == 'sol:naif:399' else
                dict(model='JRM33', radius_m=1.5*71492000., latitude_deg=0., longitude_east_deg=0., degree=13))
    return dict(body_id=body['id'], magnetic=magnetic,
                configuration=dict(inner_radius_boundary_units=1., outer_radius_boundary_units=3.,
                    radial_count=65, azimuth_sectors=96, orientation=[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]], vertical_amplification=200.))


def phase_fields(value):
    return {k:value[k] for k in ['system_id','edit_token','revision','time','bodies','atlas_initial','interventions']}


def verify_scientific(contract, scientific, phase, reference_id):
    if not isinstance(scientific,dict) or set(scientific) != {'schema','kind','spatial','magnetic','admission'}:
        raise ValueError('Complete scientific pair required')
    if type(scientific['schema']) is not int or scientific['schema'] != 1 or scientific['kind'] != 'independent_frozen_layer_pair':
        raise ValueError('Unsupported scientific pair')
    run = contract.artifact.Run.restore(scientific['spatial'])
    if phase_fields(run.payload['phase']) != phase_fields(phase):
        raise ValueError('Profile source phase differs')
    expected = settings(phase,reference_id)
    if run.payload['configuration'] != expected['configuration'] or run.payload['binding']['body_reference_id'] != reference_id:
        raise ValueError('Unprofiled configuration')
    reading = contract.magnetic(phase,scientific['magnetic'])
    coordinates = reading['coordinates']
    adopted = expected['magnetic']
    if reference_id == 'sol:naif:399':
        actual = {k:coordinates[k] for k in ['latitude_deg','longitude_deg','altitude_m']}
        expected_coordinates = {k:v for k,v in adopted.items() if k != 'model'}
    else:
        actual = dict(radius_m=coordinates['radius_m'],latitude_deg=coordinates['latitude_planetocentric_deg'],
                      longitude_east_deg=coordinates['longitude_east_deg'],degree=reading['degree'])
        expected_coordinates = {k:v for k,v in adopted.items() if k != 'model'}
    if actual != expected_coordinates:
        raise ValueError('Unprofiled magnetic sample')
    admission = contract.compose(phase,run.payload,reading,dict(spatial=True,magnetic=True))
    if contract.encoded(admission) != contract.encoded(scientific['admission']):
        raise ValueError('Pair admission differs')
    return contract.digest(scientific)


def confirm_response(snapshot, artifact_id, digest, visible):
    if not snapshot['active'] or snapshot['busy'] or snapshot['error'] or snapshot['recovery_required']:
        raise ValueError('Profile layer state is not stable')
    artifact = snapshot['artifact']
    if artifact['id'] != artifact_id or artifact['sha256'] != digest or artifact['visible'] != visible:
        raise ValueError('Profile layer response differs')
    if type(snapshot['guard']['revision']) is not int or snapshot['guard']['artifact_id'] != artifact_id:
        raise ValueError('Profile layer guard differs')


def flag_script(lua, scene):
    return ('local m={};for _,n in ipairs('+lua(scene['magnetic_nodes'])+') do '
            'm[n]=openspace.propertyValue("Scene."..n..".Renderable.DrawElements") end;'
            'return {spatial=openspace.propertyValue("Scene.'+scene['spatial_wire']+'.Renderable.DrawElements"),magnetic=m}')


def verify_flags(flags, scene, visible):
    if flags['spatial'] is not visible['spatial'] or set(flags['magnetic']) != set(scene['magnetic_nodes']):
        raise ValueError('Profile native layer set differs')
    if any(v is not visible['magnetic'] for v in flags['magnetic'].values()):
        raise ValueError('Profile native magnetic visibility differs')
