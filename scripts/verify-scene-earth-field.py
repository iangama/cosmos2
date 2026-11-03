"""Validate the staged Earth field binding, pinned synthesis and rotation transport."""
from pathlib import Path
import argparse
import ast
import calendar
import copy
import hashlib
import json
import math
import sys
import traceback
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is3-tides-product/app'
STAGING=ROOT/'output/is3-earth-field-staging'
sys.path.insert(0,str(APP));sys.path.insert(0,str(STAGING))
import atlas
import geomagnetism as igrf
import earth_magnetism as earth_field
from solar_catalog import states
from solar_import import prepare
from session import Session

LIMITS={'BGS_component_nT':1.,'rotation_matrix_error':2e-14,'B_norm_error_T':1e-18,'round_trip_position_m':.001}


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def inventory():
    return [atlas.SPICE.kdata(i,'ALL')[:3] for i in range(atlas.SPICE.ktotal('ALL'))]


def calendar_year(utc):
    year,month,day=int(utc[:4]),int(utc[5:7]),int(utc[8:10])
    days=sum(calendar.monthrange(year,m)[1] for m in range(1,month))+day-1
    seconds=int(utc[11:13])*3600+int(utc[14:16])*60+float(utc[17:].removesuffix('Z'))
    return year+(days+seconds/86400)/(366 if calendar.isleap(year) else 365)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    folder=ROOT/('output/is3-earth-field-check-'+args.label);receipt=ROOT/('evidence/is3-earth-field-check-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve previous evidence.')
    folder.mkdir()
    files=sorted(p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    files += [STAGING/'earth_magnetism.py',STAGING/'geomagnetism.py',Path(__file__).resolve(),
        ROOT/'IS-3-IGRF-CONTRATO.md',earth_field.ACQUISITION,earth_field.PCK,ROOT/'data/spice/naif0012.tls',
        ROOT/'data/science/igrf14coeffs.txt',ROOT/'evidence/igrf-reference.json',ROOT/'.upstream/igrf14/igrf14.f']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    archive=folder/'executed-sources-data-fixtures.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    owner=ROOT/'user/sessions/latest.json';owner_before=sha(owner)
    report={'schema':1,'source_sha256':hashes,'source_archive_sha256':sha(archive),
        'limits_before_execution':LIMITS,'checks':{},'completed':False,'accepted':False,
        'scope':'Pinned IGRF synthesis and scene-time/EOP vector/position binding. Rotation checks are consistency tests of the SPICE provider, not independent EOP observations; no API/UI acceptance.'}
    def persist():receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    persist()
    try:
        def functions(text):return [ast.dump(n) for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
        assert functions((ROOT/'app/geomagnetism.py').read_text(encoding='utf-8'))==functions((STAGING/'geomagnetism.py').read_text(encoding='utf-8'))
        reference=json.loads((ROOT/'evidence/igrf-reference.json').read_text(encoding='utf-8'))
        assert reference['coefficient_sha256']==igrf.EXPECTED_SHA
        assert reference['source_sha256']==sha(ROOT/'.upstream/igrf14/igrf14.f')
        errors=[]
        for case in reference['cases']:
            if case['itype']==1:
                result=igrf.field_at(case['year'],case['latitude_deg'],case['longitude_deg'],case['altitude_km']*1000,secular=bool(case['isv']))['field_ned_nT']
            else:
                br,bt,bp=igrf.spherical(case['year'],case['radius_km']*1000,math.radians(90-case['latitude_deg']),math.radians(case['longitude_deg']))
                result=[-bt,bp,-br]
            error=max(abs(a-b) for a,b in zip(result,case['reference_ned_nT']));assert error<=LIMITS['BGS_component_nT'];errors.append(error)
        report['checks']['pinned_BGS_fixtures']={'cases':len(errors),'max_component_nT':max(errors),'synthesis_function_AST_unchanged':True}
        atlas.initialize();spice=atlas.SPICE;baseline=inventory()
        reference_et=float(spice.str2et('2026-10-11T12:00:00'))
        before_state=spice.spkezr('399',reference_et,'J2000','NONE','0')[0].tolist()
        before_IAU=spice.pxform('IAU_EARTH','J2000',reference_et).tolist()
        geodetic=[(-90,0,0),(90,180,1e6),(0,0,0),(-23.55,-46.63,1000),(45,120,300000),(0,-180,500000)]
        epochs=['2000-01-02T00:00:00Z','2004-02-29T12:00:00Z','2020-12-31T23:59:59Z','2026-10-11T12:00:00Z','2026-11-10T12:00:00Z']
        readings=[];matrix_error=position_error=norm_error=0.
        for utc in epochs:
            session=Session(folder/'sessions');session.import_atlas(prepare(states(utc)))
            snapshot=session.state();original=copy.deepcopy(snapshot)
            body=next(b for b in snapshot['bodies'] if b['reference_id']=='sol:naif:399')
            for lat,lon,height in geodetic:
                result=earth_field.read(snapshot,body['id'],lat,lon,height)
                assert snapshot==original and inventory()==baseline
                assert result['epoch']['decimal_UTC_year']==calendar_year(result['epoch']['utc'])
                rotation=np.array(result['ITRF93_to_J2000'])
                error=max(float(np.max(np.abs(rotation.T@rotation-np.eye(3)))),abs(float(np.linalg.det(rotation))-1))
                matrix_error=max(matrix_error,error);assert error<=LIMITS['rotation_matrix_error']
                vector=np.array(result['point_inertial_m'])-result['earth_center_inertial_m']
                inverse=rotation.T@vector
                error=float(np.max(np.abs(inverse-result['point_ITRF93_m'])))
                position_error=max(position_error,error);assert error<=LIMITS['round_trip_position_m']
                error=abs(math.hypot(*result['field_ITRF93_T'])-result['field_norm_T'])
                norm_error=max(norm_error,error);assert error<=LIMITS['B_norm_error_T']
                assert np.allclose(np.array(result['J2000_to_render'])@result['field_J2000_T'],result['field_render_T'],rtol=1e-14,atol=1e-19)
                expected_status='prediction' if utc.startswith('2026-11') else 'EOP_supported_region'
                assert result['orientation']['status']==expected_status
                readings.append(result)
        report['checks']['five_epochs_six_points']={'cases':len(readings),'matrix_max_error':matrix_error,
            'position_round_trip_max_m':position_error,'B_norm_max_difference_T':norm_error,'calendar_years_and_prediction_labels':True}
        # Explicit inverse/sxform API route agrees with the stored coordinate matrix.
        spice.furnsh(str(earth_field.PCK))
        try:
            rotation=np.array(readings[-1]['ITRF93_to_J2000'])
            sx=np.array(spice.sxform('ITRF93','J2000',readings[-1]['epoch']['et_tdb_s']))[:3,:3]
            assert float(np.max(np.abs(rotation-sx)))<=LIMITS['rotation_matrix_error']
            preloaded_inventory=inventory()
            earth_field.read(snapshot,body['id'],-23.55,-46.63,1000)
            assert inventory()==preloaded_inventory
        finally:spice.unload(str(earth_field.PCK))
        assert inventory()==baseline
        report['checks']['preloaded_provider_preserved']=True

        session=Session(folder/'sessions');session.import_atlas(prepare(states('2026-10-11T12:00:00Z')))
        start=session.state();body=next(b for b in start['bodies'] if b['reference_id']=='sol:naif:399')
        first=earth_field.read(start,body['id'],-23.55,-46.63,1000)
        session.integrate(21600/start['physical_scale']['time_unit_s']);later=session.state()
        second=earth_field.read(later,body['id'],-23.55,-46.63,1000)
        assert np.linalg.norm(np.array(second['field_J2000_T'])-first['field_J2000_T'])>1e-6
        assert np.linalg.norm(np.array(second['relative_point_J2000_m'])-first['relative_point_J2000_m'])>1e6
        assert second['epoch']['et_tdb_s']-first['epoch']['et_tdb_s']==21600
        shifted=copy.deepcopy(later);earth=next(b for b in shifted['bodies'] if b['id']==body['id'])
        shift=[1234.,-5678.,910.]
        for k in range(3):earth['position'][k]+=shift[k]/shifted['physical_scale']['length_unit_m']
        transported=earth_field.read(shifted,body['id'],-23.55,-46.63,1000)
        assert transported['field_J2000_T']==second['field_J2000_T']
        assert max(abs(transported['point_inertial_m'][k]-second['point_inertial_m'][k]-shift[k]) for k in range(3))<.001
        report['checks']['six_hour_rotation_and_evolved_center_binding']=True

        refused=[]
        for label,identifier,lat,lon,height in [('wrong_body',start['bodies'][2]['id'],0,0,0),('unknown_body','unknown',0,0,0),
            ('latitude',body['id'],91,0,0),('longitude',body['id'],0,181,0),('negative_height',body['id'],0,0,-1),
            ('high_height',body['id'],0,0,1000001),('bool',body['id'],True,0,0),('NaN',body['id'],float('nan'),0,0),
            ('infinite',body['id'],0,float('inf'),0)]:
            original=copy.deepcopy(start)
            try:earth_field.read(start,identifier,lat,lon,height)
            except ValueError:pass
            else:raise AssertionError(label)
            assert start==original and inventory()==baseline;refused.append(label)
        for utc in ['1999-12-31T00:00:00Z','2027-01-19T00:00:00Z']:
            session.import_atlas(prepare(states(utc)));outside=session.state()
            identifier=next(b['id'] for b in outside['bodies'] if b['reference_id']=='sol:naif:399')
            try:earth_field.read(outside,identifier,0,0,0)
            except ValueError:pass
            else:raise AssertionError('Orientation outside coverage accepted.')
            refused.append('coverage_'+utc)
        session.import_atlas(prepare(states('2016-12-31T23:59:59Z')))
        session.integrate(1/session.state()['physical_scale']['time_unit_s']);leap=session.state()
        identifier=next(b['id'] for b in leap['bodies'] if b['reference_id']=='sol:naif:399')
        try:earth_field.read(leap,identifier,0,0,0)
        except ValueError as error:assert 'intercalar' in str(error)
        else:raise AssertionError('Undeclared leap second accepted.')
        refused.append('leap_second_without_decimal_year_convention')
        report['checks']['transactional_refusals']=refused
        assert spice.spkezr('399',reference_et,'J2000','NONE','0')[0].tolist()==before_state
        assert spice.pxform('IAU_EARTH','J2000',reference_et).tolist()==before_IAU
        assert inventory()==baseline and sha(owner)==owner_before
        assert all(sha(ROOT/name)==digest for name,digest in hashes.items())
        result_path=folder/'all-field-readings.json';result_path.write_text(json.dumps(readings,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
        report['readings_sha256']=sha(result_path)
        report['checks']['SPICE_pool_reference_states_IAU_and_owner_preserved']=True
        report['completed']=report['accepted']=True
    except Exception:report['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps({'receipt':receipt.relative_to(ROOT).as_posix(),'accepted':report['accepted'],'failure':report.get('failure'),'checks':report['checks']},ensure_ascii=False))
    return 0 if report['accepted'] else 1

if __name__=='__main__':raise SystemExit(main())
