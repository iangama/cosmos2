"""Isolated sixteen-center Newtonian import; legacy three/four formats remain separate."""
import copy
import math
from pathlib import Path
import platform
import re
import uuid

import rebound
import atlas_import
import physics
import is6_principal_moons_catalog as catalog

ROOT = catalog.ROOT
KIND = 'solar_sixteen_physical_centers'
VERSION = '0.1.0'
IDS = ['10','199','299','399','301','499','599','699','799','899','501','502','503','504','602','606']
EXCLUDED = ['general_relativity', 'multipoles', 'tidal_dissipation', 'unlisted_moons',
            'asteroids', 'plasma', 'nongravitational_forces']
U = physics.PHYSICAL_SCALE
digest = atlas_import.digest


def sha(path):
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def typed_equal(actual, expected):
    if type(expected) in (int, float):
        return type(actual) in (int, float) and math.isfinite(actual) and actual == expected
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(typed_equal(actual[k], v) for k,v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(typed_equal(a,b) for a,b in zip(actual,expected))
    return actual == expected


def generation():
    files = [Path(__file__), Path(catalog.__file__), Path(physics.__file__), Path(atlas_import.__file__)]
    return dict(schema=1, model_id='cosmos2:sixteen-physical-centers-newton', model_version=VERSION,
                source_sha256={p.name:sha(p) for p in files},
                canonical_units_sha256=sha(ROOT/'data/science/canonical-units.json'),
                catalog_data_sha256=catalog.DATA_SHA256,
                runtime=dict(python=platform.python_version(), rebound=rebound.__version__))


def validate_catalog(value):
    if not isinstance(value, dict) or value.get('kind') != 'eight_planets_and_principal_moons_geometric_reference':
        raise ValueError('É necessário o catálogo geométrico dos16centros físicos.')
    epoch = value.get('epoch')
    if not isinstance(epoch, dict) or type(epoch.get('et_tdb_s')) not in (int,float) or not math.isfinite(epoch['et_tdb_s']):
        raise ValueError('Época ET/TDB inválida.')
    expected = catalog.states(et=epoch['et_tdb_s'])
    if [b['naif_id'] for b in expected['bodies']] != IDS or not typed_equal(value, expected):
        raise ValueError('Catálogo difere dos estados, centros físicos ou fontes fixados.')
    if any(type(b['GM']['value']) not in (int,float) or not math.isfinite(b['GM']['value']) or b['GM']['value'] <= 0 for b in expected['bodies']):
        raise ValueError('Parâmetro gravitacional físico inválido.')
    return copy.deepcopy(expected)


def assemble(reference, branch, scientific_generation):
    total = math.fsum(b['GM']['value'] for b in reference['bodies'])
    center = [math.fsum(b['GM']['value']*b['position_m'][k] for b in reference['bodies'])/total for k in range(3)]
    velocity = [math.fsum(b['GM']['value']*b['velocity_m_s'][k] for b in reference['bodies'])/total for k in range(3)]
    bodies = []
    for source in reference['bodies']:
        target = source['naif_id']
        bodies.append(dict(id=f'exp:{branch}:naif:{target}', reference_id=source['id'], naif_id=target,
            name=source['name'], entity_kind='physical_body', source_GM=copy.deepcopy(source['GM']),
            source_position_m=list(source['position_m']), source_velocity_m_s=list(source['velocity_m_s']),
            source_uncertainty=dict(position_m=None, velocity_m_s=None),
            shape_reference=None, reference_properties=[],
            mass=source['GM']['value']/U['nominal_GM_unit_m3_s2'],
            position=[(x-c)/U['length_unit_m'] for x,c in zip(source['position_m'],center)],
            velocity=[(x-c)/U['velocity_unit_m_s'] for x,c in zip(source['velocity_m_s'],velocity)]))
    return dict(schema=3, kind=KIND, version=VERSION, branch_id=branch,
        contract=dict(schema=3, frame='initial_subset_barycenter_inertial_axes_J2000',
            units=dict(system='canonical',G=1.0), model='newtonian_point_masses',
            collisions='disabled', softening_m=0.0, integrator='IAS15', epsilon=1e-9,
            epoch=copy.deepcopy(reference['epoch']),
            time='elapsed model time; epoch_et_tdb_s + t*time_unit_s; not a replacement for ephemerides',
            centers='physical body centers and individual body GMs; no separate system barycenter particles',
            excluded_influences=list(EXCLUDED), electromagnetic_coupling=False, nuclear_coupling=False),
        physical_scale=copy.deepcopy(U), reference_catalog=copy.deepcopy(reference),
        source=dict(model=reference['kind']+'/'+reference['version'],
                    **{k:copy.deepcopy(reference[k]) for k in ['epoch','frame','center_naif_id','aberration','provenance']}),
        initial_ssb_origin_m=center, inertial_origin_velocity_m_s=velocity,
        render_frame=reference['render_frame'], j2000_to_render_frame=copy.deepcopy(reference['j2000_to_render_frame']),
        generation=copy.deepcopy(scientific_generation), bodies=bodies)


def prepare(reference):
    reference = validate_catalog(reference)
    result = assemble(reference, uuid.uuid4().hex, generation())
    result['initial_state_sha256'] = digest(result)
    return validate(result)


def validate(value):
    if not isinstance(value, dict) or type(value.get('schema')) is not int or value['schema'] != 3 or value.get('kind') != KIND or value.get('version') != VERSION:
        raise ValueError('Formato da cópia de16centros incompatível.')
    body = {k:v for k,v in value.items() if k != 'initial_state_sha256'}
    if digest(body) != value.get('initial_state_sha256'):
        raise ValueError('Integridade da cópia de16centros inválida.')
    branch = value.get('branch_id')
    if not isinstance(branch,str) or not re.fullmatch('[0-9a-f]{32}',branch):
        raise ValueError('Identidade de ramo inválida.')
    reference = validate_catalog(value.get('reference_catalog'))
    current_generation = generation()
    if not typed_equal(value.get('generation'),current_generation):
        raise ValueError('Geração científica diferente desta revisão isolada.')
    expected = assemble(reference,branch,current_generation)
    if not typed_equal(body,expected):
        raise ValueError('Cópia não corresponde aos estados, GM, unidades ou operadores declarados.')
    for row in expected['bodies']:
        for key,scale,origin,original,limit in [
            ('position',U['length_unit_m'],'initial_ssb_origin_m','source_position_m',.001),
            ('velocity',U['velocity_unit_m_s'],'inertial_origin_velocity_m_s','source_velocity_m_s',1e-8)]:
            if max(abs(x*scale+c-y) for x,c,y in zip(row[key],value[origin],row[original])) > limit:
                raise ValueError('Conversão SI/canônica inconsistente.')
    return copy.deepcopy(value)


def simulation(initial, epsilon=1e-9):
    initial = validate(initial)
    if type(epsilon) not in (int,float) or not math.isfinite(epsilon) or not 1e-15 <= epsilon <= 1e-3:
        raise ValueError('Tolerância IAS15 inválida.')
    sim = rebound.Simulation()
    sim.G = 1.0
    sim.integrator = 'ias15'
    sim.integrator.epsilon = epsilon
    sim.collision = 'none'
    sim.softening = 0.0
    for b in initial['bodies']:
        sim.add(m=b['mass'],x=b['position'][0],y=b['position'][1],z=b['position'][2],
                vx=b['velocity'][0],vy=b['velocity'][1],vz=b['velocity'][2])
    return sim
