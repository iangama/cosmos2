"""Passive static JRM33 bound to the evolved planet599 and the adopted IAU frame."""
from pathlib import Path
import hashlib
import json
import math

import atlas
import jrm33

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
ACQUISITION=ROOT/'evidence/is3-jupiter-orientation-acquisition-20261023b.json'
ACQUISITION_SHA='28f5d074258b3c0b2d749afb2d0f950976765745508b022bbe5580e3ab133312'
PCK=ROOT/'data/spice/pck00011.tpc'
PCK_SHA='3dff7b1dbeceaa01f25467767d3fa25816051c85d162d1edf04acb310ee28bb1'
LSK=ROOT/'data/spice/naif0012.tls'
LSK_SHA='678e32bdb5a744117a467cd9601cd6b373f0e9bc9bbde1371d5eee39600a039b'
FRAME='initial_subset_barycenter_inertial_axes_J2000'
APPLICATION_UTC=['2000-01-01T00:00:00Z','2030-01-01T00:00:00Z']


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def product(matrix,vector):
    return [math.fsum(row[k]*vector[k] for k in range(3)) for row in matrix]


def read(snapshot,body_id,radius_m,latitude_deg,east_longitude_deg,degree=13):
    initial=snapshot.get('atlas_initial')
    if not initial or initial.get('kind')!='solar_four_physical_centers' or snapshot['contract']['frame']!=FRAME:
        raise ValueError('Abra a cópia de quatro centros no referencial adotado.')
    body=next((b for b in snapshot['bodies'] if b['id']==body_id),None)
    if body is None or body.get('reference_id')!='sol:naif:599':
        raise ValueError('O JRM33 deste instrumento está associado somente a Júpiter599 ativo.')
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in [radius_m,latitude_deg,east_longitude_deg]):
        raise ValueError('Coordenadas devem ser números SI finitos.')
    if not -90<=latitude_deg<=90 or not 0<=east_longitude_deg<=360:
        raise ValueError('Use latitude planetocêntrica±90° e longitude leste0..360°.')
    # Validate the raw request before Cartesian conversion, including radius and degree.
    jrm33.validate(radius_m,math.radians(90-latitude_deg),math.radians(east_longitude_deg),degree)
    for path,expected in [(ACQUISITION,ACQUISITION_SHA),(PCK,PCK_SHA),(LSK,LSK_SHA),(jrm33.DATA_PATH,jrm33.DATA_SHA)]:
        if sha(path)!=expected:raise ValueError('Fonte magnética/orientação joviana diferente da adotada.')
    acquisition=json.loads(ACQUISITION.read_text(encoding='utf-8'))
    if not acquisition.get('accepted_for_candidate_data') or not acquisition.get('completed'):
        raise ValueError('Aquisição da orientação não foi aceita.')
    et=initial['source']['epoch']['et_tdb_s']+snapshot['time']*snapshot['physical_scale']['time_unit_s']
    if not math.isfinite(et):raise ValueError('Época não finita.')
    latitude,longitude=math.radians(latitude_deg),math.radians(east_longitude_deg)
    local=[radius_m*math.cos(latitude)*math.cos(longitude),radius_m*math.cos(latitude)*math.sin(longitude),radius_m*math.sin(latitude)]
    value=jrm33.sample(local,degree)
    with atlas.LOCK:
        atlas.initialize();spice=atlas.SPICE
        bounds=[float(spice.str2et(utc.removesuffix('Z'))) for utc in APPLICATION_UTC]
        if not bounds[0]<=et<=bounds[1]:raise ValueError('Época fora da faixa de aplicação JRM33:2000–2030; sem extrapolação automática.')
        if spice.namfrm('IAU_JUPITER')!=10015 or spice.frinfo(10015)!=(599,2,599):
            raise ValueError('Identidade do frame joviano diferente da adotada.')
        for i in range(spice.ktotal('ALL')):
            if spice.kdata(i,'ALL')[1]=='PCK':
                raise ValueError('PCK binário concorrente; autoridade da orientação joviana não confirmada.')
        for key,record in acquisition['parameter_comparisons'].items():
            if spice.gdpool(key,0,100).tolist()!=record['PCK00011']:
                raise ValueError('Parâmetros efetivos da orientação joviana diferentes da fonte fixada.')
        rotation=spice.pxform('IAU_JUPITER','J2000',et).tolist()
        render_rotation=spice.pxform('J2000','GALACTIC',et).tolist()
        utc=spice.et2utc(et,'ISOC',6)+'Z'
    relative=product(rotation,local)
    center=[v*snapshot['physical_scale']['length_unit_m'] for v in body['position']]
    point=[center[k]+relative[k] for k in range(3)]
    field=product(rotation,value['field_SystemIII_T'])
    return {'schema':1,'kind':'scene_Jupiter_JRM33_passive_point','body_id':body_id,'body_reference_id':'sol:naif:599',
        **{k:snapshot[k] for k in ['system_id','edit_token','revision','time']},'frame':FRAME,
        'epoch':{'et_tdb_s':et,'utc':utc,'UTC_rounding_s':1e-6},
        'coordinates':{'radius_m':radius_m,'latitude_planetocentric_deg':latitude_deg,
            'longitude_east_deg':east_longitude_deg,'definition':'Spherical geocentric radius, not ellipsoidal altitude; right-handed System III (1965).'},
        'degree':degree,'degree_status':'exploratory_truncation' if degree==18 else 'analytic_dipole_reference' if degree==1 else 'adopted_default_truncation',
        'point_SystemIII_m':local,'jupiter_center_inertial_m':center,'relative_point_J2000_m':relative,
        'point_inertial_m':point,'point_render_m':product(render_rotation,point),
        'field_SystemIII_T':value['field_SystemIII_T'],'field_spherical_T':value['field_spherical_T'],
        'field_J2000_T':field,'field_render_T':product(render_rotation,field),'field_norm_T':math.hypot(*field),
        'scalar_potential_T_m':value['scalar_potential_T_m'],'reference_radius_m':jrm33.R,
        'SystemIII_to_J2000':rotation,'J2000_to_render':render_rotation,
        'orientation':{'frame':'IAU_JUPITER','frame_id':10015,'convention':'right_handed_System_III_1965',
            'provider':'PCK00011; all eight Jovian parameter groups exactly equal to LASP-adopted PCK00010',
            'application_UTC':APPLICATION_UTC,'nutation_precession_included':True,'display_spin_does_not_change_provider':True},
        'coefficient_epoch_decimal_year':2019.,'secular_variation_applied':False,'external_current_component_included':False,
        'provenance':{'model':'JRM33 internal','coefficients_sha256':jrm33.DATA_SHA,'PCK_sha256':PCK_SHA,
            'orientation_acquisition_sha256':ACQUISITION_SHA,'LSK_sha256':LSK_SHA,
            'code_sha256':{'jupiter_magnetism.py':sha(Path(__file__)),'jrm33.py':sha(Path(jrm33.__file__)),
                'atlas.py':sha(Path(atlas.__file__))}},
        'uncertainty':None,'uncertainty_reason':'Local field and orientation uncertainty not propagated; truncation difference is not an uncertainty estimate.',
        'scope':'Static prescribed 2019 internal component at one scene epoch; no secular forecast, external currents, plasma or force on neutral centers.'}
