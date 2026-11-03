"""Immutable association of one isolated spherical reference to a paused body."""
from pathlib import Path
import copy
import hashlib
import json
import math
import sys

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
HERE=Path(__file__).resolve().parent
APP=ROOT/'output/is5-compression-product0.17.2/app'
sys.path[:0]=[str(ROOT/'output/is6-spatial-staging-b'),str(APP)]
import is6_spatial as spatial
import is5_solar_source as solar
from physics import PHYSICAL_SCALE

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
FILES=[Path(__file__),HERE/'body-reference-radii.json',ROOT/'scripts/prepare-is6-body-radii.py',
       ROOT/'IS-6-FONTE-CORPOS-CONTRATO-PREVIO.md',ROOT/'data/spice/pck00011.tpc',
       ROOT/'evidence/is6-spatial-20261101c.json',APP.parent/'build-manifest.json',
       ROOT/'evidence/is5-native-compression-20261101c.json',
       ROOT/'evidence/is5-compression-visual-review-20261101c.json',
       ROOT/'evidence/is5-compression-profile-audit-20261101a.json']
IMPORTED={p.relative_to(ROOT).as_posix():sha(p) for p in FILES}
APP_IMPORTED=json.loads((APP.parent/'build-manifest.json').read_text())['files_sha256']
CATALOG=json.loads((HERE/'body-reference-radii.json').read_text(encoding='utf-8'))


def generation():
    if any(sha(ROOT/n)!=v for n,v in IMPORTED.items()) or any(sha(APP/n)!=v for n,v in APP_IMPORTED.items()):
        raise ValueError('Restart after spatial-body source changes')
    science=json.loads((ROOT/'evidence/is6-spatial-20261101c.json').read_text())
    gen=spatial.generation()
    if not science['accepted'] or science['generation']!=gen:raise ValueError('Accepted spatial scientific generation required')
    for p in FILES[-3:]:
        if not json.loads(p.read_text())['accepted']:raise ValueError('Accepted underlying product required')
    provenance=CATALOG['provenance']
    if sha(ROOT/provenance['file'])!=provenance['sha256']:raise ValueError('Adopted boundary kernel differs')
    return dict(schema=1,id='cosmos2:is6-paused-four-center-spherical-reference',version='0.1.0',
                source_sha256=dict(IMPORTED),underlying_app_sha256=dict(APP_IMPORTED),spatial=gen)


def guard(phase):
    return {k:phase[k] for k in ['system_id','edit_token','revision','time']}|{'frame':phase['contract']['frame']}


def bind(phase,request):
    if not isinstance(request,dict) or set(request)!={'body_id','source_guard'}:raise ValueError('Exact body-reference selection required')
    if not isinstance(phase,dict):raise ValueError('Explicit paused phase required')
    p=copy.deepcopy(phase);selected=copy.deepcopy(request);g=selected['source_guard']
    if not isinstance(g,dict) or set(g)!={'system_id','edit_token','revision','time','frame'} or type(g.get('revision')) is not int:
        raise ValueError('Exact paused source guard required')
    spatial.number(g.get('time'))
    common=solar.bind(p)
    if g!=guard(p):raise ValueError('The selected body phase changed')
    identity=selected['body_id']
    if not isinstance(identity,str):raise ValueError('Explicit body identity required')
    matches=[b for b in p['bodies'] if b['id']==identity]
    if len(matches)!=1:raise ValueError('Selected body unavailable in this phase')
    body=matches[0];rows=[r for r in CATALOG['bodies'] if r['reference_id']==body['reference_id']]
    if len(rows)!=1:raise ValueError('Spherical reference boundary unavailable')
    row=copy.deepcopy(rows[0]);provenance=copy.deepcopy(CATALOG['provenance'])
    if common['kernels_sha256'].get(provenance['file'])!=provenance['sha256']:
        raise ValueError('Scene and spherical-reference PCK differ')
    gm=spatial.number(body['mass'])*PHYSICAL_SCALE['nominal_GM_unit_m3_s2']
    if gm<=0:raise ValueError('Positive body-reference GM required')
    configuration=spatial.source(dict(GM_m3_s2=gm,material_radius_m=row['exterior_boundary_m']))
    spatial.sample(configuration,row['exterior_boundary_m'])
    center=[x*PHYSICAL_SCALE['length_unit_m'] for x in solar.vector(body['position'])]
    velocity=[x*PHYSICAL_SCALE['velocity_unit_m_s'] for x in solar.vector(body['velocity'])]
    rotation=common['J2000_to_render'];render=[math.fsum(rotation[j][i]*center[i] for i in range(3)) for j in range(3)]
    if any(not math.isfinite(x) or abs(x)>1e20 for x in [*center,*velocity,*render]):raise ValueError('Unrepresentable body reference')
    gen=generation()
    descriptor=dict(schema=1,kind='is6_isolated_spherical_body_reference',body_id=identity,
        body_reference_id=body['reference_id'],name=row['name'],scene_phase=guard(p),scene_phase_sha256=solar.digest(p),
        source_frame=solar.FRAME,render_frame='GALACTIC',epoch=common['epoch'],
        center_inertial_m=center,velocity_inertial_m_s=velocity,J2000_to_render=rotation,center_render_m=render,
        source_configuration=configuration,GM_origin='Current scenario mass times adopted GM unit; archived reference, not applied orbital force.',
        boundary=row,boundary_provenance=provenance,scientific_generation=gen,
        clock='Static supported observers in a single-source vacuum reference; not the moving body clock.',
        source_feedback=False,scope='Spherical isolated exterior reference; excludes rotation,J2,other sources and plasma. PCK boundary is adopted, not an observed exact surface or graphical/collision radius.')
    return {**descriptor,'binding_sha256':solar.digest(descriptor)}


def validate(phase,descriptor):
    if not isinstance(descriptor,dict):raise ValueError('Complete spherical body descriptor required')
    expected=bind(phase,dict(body_id=descriptor.get('body_id'),source_guard=descriptor.get('scene_phase')))
    if solar.digest(expected)!=solar.digest(descriptor):raise ValueError('Spherical body reference differs from its archived phase')
    return expected


def evaluate(phase,descriptor,radius_m):
    validated=validate(phase,descriptor)
    return spatial.sample(validated['source_configuration'],radius_m)
