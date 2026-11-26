"""Passive IGRF14 point bound to the evolved Earth center and a pinned EOP frame."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import math

import atlas
import geomagnetism as igrf

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
NAME='earth_000101_270118_261022'
PCK=ROOT/'output/is3-earth-orientation-staging'/(NAME+'.bpc')
ACQUISITION=ROOT/'evidence/is3-earth-orientation-acquisition-20261023.json'
PCK_SHA='0d7b251eacf1f3136aa9d9dd7d5f7c9b060a97bc1ab07de5635f9445d0fa923b'
ACQUISITION_SHA='5b1b663eb37c5c7ed64e78f92c6a1f117d90f54a4b06c119988bb49489d77792'
FRAME='initial_subset_barycenter_inertial_axes_J2000'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decimal_year(utc):
    if utc[17:19]=='60':
        raise ValueError('Amostra em segundo intercalar sem convenção de ano decimal adotada.')
    date=dt.datetime.fromisoformat(utc.removesuffix('Z')).replace(tzinfo=dt.timezone.utc)
    start=dt.datetime(date.year,1,1,tzinfo=dt.timezone.utc)
    end=dt.datetime(date.year+1,1,1,tzinfo=dt.timezone.utc)
    return date.year+(date-start).total_seconds()/(end-start).total_seconds()


def product(matrix, vector):
    return [math.fsum(row[k]*vector[k] for k in range(3)) for row in matrix]


def read(snapshot, body_id, latitude_deg, longitude_deg, altitude_m):
    initial=snapshot.get('atlas_initial')
    if not initial or initial.get('kind')!='solar_four_physical_centers' or snapshot['contract']['frame']!=FRAME:
        raise ValueError('Abra a cópia de quatro centros no referencial adotado.')
    earth=next((b for b in snapshot['bodies'] if b['id']==body_id),None)
    if earth is None or earth.get('reference_id')!='sol:naif:399':
        raise ValueError('O IGRF14 deste instrumento está associado somente à Terra399 ativa.')
    for value in [latitude_deg,longitude_deg,altitude_m]:
        if type(value) not in (int,float) or not math.isfinite(value):
            raise ValueError('Posição geodética deve usar números SI finitos.')
    if not -90<=latitude_deg<=90 or not -180<=longitude_deg<=180 or not 0<=altitude_m<=1e6:
        raise ValueError('Use latitude±90°, longitude±180° e altura de0 a1000km.')
    elapsed=snapshot['time']*snapshot['physical_scale']['time_unit_s']
    et=initial['source']['epoch']['et_tdb_s']+elapsed
    if not math.isfinite(et):raise ValueError('Época não finita.')
    if sha(ACQUISITION)!=ACQUISITION_SHA or sha(PCK)!=PCK_SHA:
        raise ValueError('A orientação terrestre difere da fonte fixada.')
    acquisition=json.loads(ACQUISITION.read_text(encoding='utf-8'))
    assert acquisition['accepted_for_data'] and acquisition['completed']
    if not any(a<=et<=b for a,b in acquisition['coverage']['intervals_et_tdb_s']):
        raise ValueError('Época fora da cobertura do PCK terrestre fixado; sem fallback de rotação.')
    if sha(igrf.COEFFICIENT_PATH)!=igrf.EXPECTED_SHA:
        raise ValueError('Coeficientes IGRF14 alterados.')
    lsk=ROOT/'data/spice/naif0012.tls'
    if sha(lsk)!=acquisition['lsk_sha256']:raise ValueError('LSK diferente do adotado na orientação.')
    with atlas.LOCK:
        atlas.initialize();spice=atlas.SPICE
        loaded=[]
        for i in range(spice.ktotal('ALL')):
            item=spice.kdata(i,'ALL')
            if item[1]=='PCK':loaded.append(Path(item[0]).resolve())
        if any(p!=PCK.resolve() for p in loaded):
            raise ValueError('Outro PCK binário está ativo; autoridade de orientação não confirmada.')
        already_loaded=PCK.resolve() in loaded
        if not already_loaded:spice.furnsh(str(PCK))
        try:
            utc=spice.et2utc(et,'ISOC',6)+'Z';year=decimal_year(utc)
            if not 1900<=year<=2030:raise ValueError('Época fora do domínio IGRF14.')
            rotation=spice.pxform('ITRF93','J2000',et).tolist()
            render_rotation=spice.pxform('J2000','GALACTIC',et).tolist()
            value=igrf.field_at(year,latitude_deg,longitude_deg,altitude_m)
        finally:
            if not already_loaded:spice.unload(str(PCK))
    relative=product(rotation,value['position_ecef_m'])
    center=[v*snapshot['physical_scale']['length_unit_m'] for v in earth['position']]
    point=[center[k]+relative[k] for k in range(3)]
    field=product(rotation,value['field_ecef_T'])
    status='prediction' if et>acquisition['coverage']['last_datum_et_tdb_s'] else 'EOP_supported_region'
    return {'schema':1,'kind':'scene_Earth_IGRF14_passive_point','body_id':body_id,'body_reference_id':'sol:naif:399',
        **{k:snapshot[k] for k in ['system_id','edit_token','revision','time']},'frame':FRAME,
        'epoch':{'et_tdb_s':et,'utc':utc,'decimal_UTC_year':year,'UTC_rounding_s':1e-6},
        'coordinates':{'latitude_deg':latitude_deg,'longitude_deg':longitude_deg,'altitude_m':altitude_m,
            'definition':'Constructed WGS84 ellipsoid point in ITRF93 axes; not a transformed measured station.'},
        'point_ITRF93_m':value['position_ecef_m'],'earth_center_inertial_m':center,
        'point_inertial_m':point,'relative_point_J2000_m':relative,
        'point_render_m':product(render_rotation,point),'field_ITRF93_T':value['field_ecef_T'],
        'field_J2000_T':field,'field_render_T':product(render_rotation,field),
        'field_NED_nT':value['field_ned_nT'],'field_norm_T':math.hypot(*field),
        'ITRF93_to_J2000':rotation,'J2000_to_render':render_rotation,
        'orientation':{'frame':'ITRF93','frame_id':3000,'status':status,
            'last_datum_utc':acquisition['coverage']['last_datum_utc'],
            'coverage_et_tdb_s':acquisition['coverage']['intervals_et_tdb_s'],
            'precise_station_motion_included':False,'display_spin_does_not_change_provider':True},
        'provenance':{'model':'IGRF14','coefficient_sha256':igrf.EXPECTED_SHA,'PCK_sha256':PCK_SHA,
            'PCK_acquisition_sha256':ACQUISITION_SHA,'LSK_sha256':acquisition['lsk_sha256'],
            'code_sha256':{'earth_magnetism.py':sha(Path(__file__)),
                'geomagnetism.py':sha(Path(igrf.__file__)),'atlas.py':sha(Path(atlas.__file__))}},
        'uncertainty':None,'uncertainty_reason':'Field and EOP uncertainty not propagated locally; not zero.',
        'scope':'Prescribed internal Earth field at one confirmed phase; no external space-weather component or force on neutral centers.'}
