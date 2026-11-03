"""Passive binding to the Sun in one confirmed paused four-center scene."""
from pathlib import Path
import copy
import hashlib
import json
import math

FRAME='initial_subset_barycenter_inertial_axes_J2000'
REFERENCES={'sol:naif:10','sol:naif:399','sol:naif:301','sol:naif:599'}

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False).encode()).hexdigest()

def number(value):
    if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Finite numeric source SI value required')
    return float(value)

def vector(value):
    if not isinstance(value,(list,tuple)) or len(value)!=3:raise ValueError('Three source vector components required')
    return [number(v) for v in value]

def bind(phase):
    import atlas
    from physics import PHYSICAL_SCALE
    if not isinstance(phase,dict):raise ValueError('Explicit paused solar phase required')
    p=copy.deepcopy(phase)
    if p.get('paused') is not True or p.get('contract',{}).get('frame')!=FRAME or p['contract'].get('model')!='newtonian_point_masses':raise ValueError('Adopted paused solar experiment required')
    if digest(p.get('physical_scale'))!=digest(PHYSICAL_SCALE):raise ValueError('Adopted source scale required')
    for key in ['system_id','edit_token']:
        value=p.get(key)
        if not isinstance(value,str) or len(value)!=32 or any(c not in '0123456789abcdef' for c in value):raise ValueError('Source identity differs')
    if type(p.get('revision')) is not int or p['revision']<0 or number(p.get('time'))<0:raise ValueError('Nonnegative source revision/time required')
    if p.get('scientific_generation',{}).get('candidate_extension',{}).get('id')!='is3-body-fields':raise ValueError('Adopted solar source generation required')
    fixture=p.get('fixture_sha256')
    if not isinstance(fixture,str) or len(fixture)!=64 or any(c not in '0123456789abcdef' for c in fixture):raise ValueError('Source fixture identity required')
    initial=p.get('atlas_initial',{})
    if initial.get('kind')!='solar_four_physical_centers':raise ValueError('Four-center imported solar source required')
    bodies=p.get('bodies')
    if not isinstance(bodies,list) or len(bodies)!=4 or any(not isinstance(b,dict) for b in bodies) or {b.get('reference_id') for b in bodies}!=REFERENCES:raise ValueError('Exactly four source centers required')
    if any(not isinstance(b.get('id'),str) or not b['id'] for b in bodies) or len({b['id'] for b in bodies})!=4:raise ValueError('Unique source body identities required')
    sun=next(b for b in bodies if b['reference_id']=='sol:naif:10');mass=number(sun.get('mass'))
    if not 0<mass<=100:raise ValueError('Source solar GM outside adopted editor range')
    center=[v*PHYSICAL_SCALE['length_unit_m'] for v in vector(sun.get('position'))]
    velocity=[v*PHYSICAL_SCALE['velocity_unit_m_s'] for v in vector(sun.get('velocity'))]
    if math.hypot(*center)>1e17 or not all(math.isfinite(v) for v in [*center,*velocity]):raise ValueError('Unrepresentable solar source coordinates')
    t0=number(initial['source']['epoch']['et_tdb_s']);et=t0+p['time']*PHYSICAL_SCALE['time_unit_s']
    if not math.isfinite(et):raise ValueError('Unrepresentable source epoch')
    with atlas.LOCK:
        atlas.initialize();spice=atlas.SPICE
        origin_utc=initial['source']['epoch'].get('utc')
        if not isinstance(origin_utc,str) or abs(float(spice.str2et(origin_utc))-t0)>.001+8*math.ulp(t0):raise ValueError('Initial source UTC and TDB differ')
        utc=spice.et2utc(et,'ISOC',6)+'Z';atlas.normalize_epoch(utc[:19]);rotation=spice.pxform('J2000','GALACTIC',et).tolist()
        kernels=copy.deepcopy(atlas.PROVENANCE['kernels_sha256'])
    descriptor=dict(schema=1,kind='passive_solar_zone_source',body_id=sun['id'],body_reference_id='sol:naif:10',source_frame=FRAME,
        scene_phase={k:p[k] for k in ['system_id','edit_token','revision','time','fixture_sha256']},scene_phase_sha256=digest(p),
        epoch=dict(et_tdb_s=et,utc=utc,UTC_rounding_s=1e-6),center_inertial_m=center,velocity_inertial_m_s=velocity,
        GM_m3_s2=mass*PHYSICAL_SCALE['nominal_GM_unit_m3_s2'],J2000_to_render=rotation,
        center_render_m=[math.fsum(row[k]*center[k] for k in range(3)) for row in rotation],kernels_sha256=kernels,
        implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        clock='Nuclear duration starts at zero independently; scene epoch/orbit remain fixed.',source_feedback=False,
        scope='Instrument associated with the selected Sun; no measured core location, point-mass interior field, hydrostatic structure, luminosity or orbital feedback inferred.')
    return {**descriptor,'binding_sha256':digest(descriptor)}

def validate(phase,descriptor):
    expected=bind(phase)
    if digest(expected)!=digest(descriptor):raise ValueError('Solar-zone binding and paused phase differ')
    return expected
