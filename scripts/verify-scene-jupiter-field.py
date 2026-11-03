"""Verify the staged JRM33 scene binding and independent full IAU angle construction."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import sys
import traceback
import zipfile
import numpy as np
import spiceypy as spice

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is3-tides-product/app'
STAGING=ROOT/'output/is3-jrm33-staging'
sys.path.insert(0,str(APP));sys.path.insert(0,str(STAGING))
import atlas
import jrm33
import jupiter_magnetism as field
from solar_catalog import states
from solar_import import prepare
from session import Session

LIMITS={'independent_IAU_matrix':1e-10,'orthogonality':2e-14,'position_round_trip_m':.001,
    'field_norm_T':1e-18,'spin_rate_degree_per_day_error':.001}
EPOCHS=['2000-01-01T00:00:00Z','2019-01-01T00:00:00Z','2020-02-29T12:00:00Z',
    '2026-10-11T12:00:00Z','2026-10-23T12:00:00Z','2030-01-01T00:00:00Z']
POINTS=[(1.,0,0),(1.,90,0),(1.,-90,180),(1.5,45,120),(2.5,-30,270),(10.,0,360)]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def independent_rotation(et,parameters):
    """Build inertial basis explicitly from published alpha, delta and W."""
    day=et/86400.;century=day/36525.
    p={key:record['PCK00010'] for key,record in parameters.items()}
    raw=p['BODY5_NUT_PREC_ANGLES'];angles=[math.radians(raw[i]+raw[i+1]*century) for i in range(0,len(raw),2)]
    def polynomial(v,t):return v[0]+v[1]*t+v[2]*t*t
    ra=polynomial(p['BODY599_POLE_RA'],century)+math.fsum(a*math.sin(q) for a,q in zip(p['BODY599_NUT_PREC_RA'],angles))
    dec=polynomial(p['BODY599_POLE_DEC'],century)+math.fsum(a*math.cos(q) for a,q in zip(p['BODY599_NUT_PREC_DEC'],angles))
    w=polynomial(p['BODY599_PM'],day)+math.fsum(a*math.sin(q) for a,q in zip(p['BODY599_NUT_PREC_PM'],angles))
    ra,dec,w=map(math.radians,[ra,dec,w])
    z=np.array([math.cos(dec)*math.cos(ra),math.cos(dec)*math.sin(ra),math.sin(dec)])
    u=np.array([-math.sin(ra),math.cos(ra),0.]);v=np.cross(z,u)
    return np.column_stack((u*math.cos(w)+v*math.sin(w),-u*math.sin(w)+v*math.cos(w),z))


def inventory():return [atlas.SPICE.kdata(i,'ALL')[:3] for i in range(atlas.SPICE.ktotal('ALL'))]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    folder=ROOT/('output/is3-jupiter-field-check-'+args.label);receipt=ROOT/('evidence/is3-jupiter-field-check-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve previous evidence.')
    folder.mkdir()
    files=sorted(p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    files += [STAGING/'jrm33.py',STAGING/'jrm33-coefficients.json',STAGING/'jupiter_magnetism.py',
        ROOT/'IS-3-JRM33-ORIENTACAO-CONTRATO.md',ROOT/'IS-3-JRM33-CONTRATO.md',field.ACQUISITION,
        ROOT/'output/is3-jupiter-orientation-staging/pck00010.tpc',ROOT/'output/is3-jupiter-orientation-staging/CoOrd_systems12.pdf',
        field.PCK,field.LSK,Path(__file__).resolve(),ROOT/'evidence/is3-jrm33-check-20261023a.json']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(folder/'executed-sources-data.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    owner=ROOT/'user/sessions/latest.json';owner_before=sha(owner)
    report={'schema':1,'source_sha256':hashes,'limits_before_execution':LIMITS,'checks':{},
        'completed':False,'accepted':False,'scope':'Scene binding, published IAU angle and SPICE consistency, not independent orientation observations. No API/UI or native geometry acceptance.'}
    def persist():receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    persist()
    try:
        accepted=json.loads((ROOT/'evidence/is3-jrm33-check-20261023a.json').read_text(encoding='utf-8'))
        assert accepted['accepted']
        for name in ['output/is3-jrm33-staging/jrm33.py','output/is3-jrm33-staging/jrm33-coefficients.json']:
            assert accepted['source_sha256'][name]==sha(ROOT/name)
        # Isolated test process only: no product process/pool is affected.
        spice.furnsh(str(field.LSK));spice.furnsh(str(ROOT/'output/is3-jupiter-orientation-staging/pck00010.tpc'))
        old={utc:spice.pxform('IAU_JUPITER','J2000',float(spice.str2et(utc.removesuffix('Z')))).tolist() for utc in EPOCHS}
        spice.kclear()
        atlas.initialize();baseline=inventory();parameters=json.loads(field.ACQUISITION.read_text())['parameter_comparisons']
        matrix_error=orthogonal_error=position_error=norm_error=0.;readings=[]
        et0=float(spice.str2et('2026-10-11T12:00:00'))
        baseline_state=spice.spkezr('399',et0,'J2000','NONE','0')[0].tolist()
        baseline_rotation=spice.pxform('IAU_JUPITER','J2000',et0).tolist()
        for utc in EPOCHS:
            session=Session(folder/'sessions');session.import_atlas(prepare(states(utc)))
            snapshot=session.state();before=copy.deepcopy(snapshot)
            body=next(b for b in snapshot['bodies'] if b['reference_id']=='sol:naif:599')
            for radius,latitude,longitude in POINTS:
                for degree in [13,18]:
                    result=field.read(snapshot,body['id'],radius*jrm33.R,latitude,longitude,degree)
                    rotation=np.array(result['SystemIII_to_J2000']);et=result['epoch']['et_tdb_s']
                    assert result['epoch']['et_tdb_s']==snapshot['atlas_initial']['source']['epoch']['et_tdb_s']
                    assert np.array_equal(rotation,np.array(old[utc]))
                    error=float(np.max(np.abs(rotation-independent_rotation(et,parameters))))
                    matrix_error=max(matrix_error,error);assert error<=LIMITS['independent_IAU_matrix']
                    error=max(float(np.max(np.abs(rotation.T@rotation-np.eye(3)))),abs(float(np.linalg.det(rotation))-1))
                    orthogonal_error=max(orthogonal_error,error);assert error<=LIMITS['orthogonality']
                    relative=np.array(result['point_inertial_m'])-result['jupiter_center_inertial_m']
                    error=float(np.max(np.abs(rotation.T@relative-result['point_SystemIII_m'])))
                    position_error=max(position_error,error);assert error<=LIMITS['position_round_trip_m']
                    expected=jrm33.sample(result['point_SystemIII_m'],degree)
                    assert expected['field_SystemIII_T']==result['field_SystemIII_T']
                    error=abs(expected['field_norm_T']-result['field_norm_T'])
                    norm_error=max(norm_error,error);assert error<=LIMITS['field_norm_T']
                    assert np.allclose(rotation@expected['field_SystemIII_T'],result['field_J2000_T'],rtol=1e-14,atol=1e-20)
                    assert np.allclose(np.array(result['J2000_to_render'])@result['field_J2000_T'],result['field_render_T'],rtol=1e-14,atol=1e-20)
                    assert result['coefficient_epoch_decimal_year']==2019 and not result['secular_variation_applied']
                    assert snapshot==before and inventory()==baseline
                    readings.append(result)
        report['checks']['six_epochs_six_positions_two_degrees']={'cases':len(readings),'complete_PCK10_PCK11_matrices_bit_equal':True,
            'independent_IAU_max_matrix_error':matrix_error,'orthogonality_max_error':orthogonal_error,
            'position_round_trip_max_m':position_error,'B_norm_max_difference_T':norm_error}
        rotation0=np.array(baseline_rotation);rotation1=spice.pxform('IAU_JUPITER','J2000',et0+60)
        inertial=rotation0@np.array([1.,0,0]);local=rotation1.T@inertial
        change=math.degrees(math.atan2(local[1],local[0]));rate=-change*86400/60
        assert change<0 and abs(rate-870.536)<=LIMITS['spin_rate_degree_per_day_error']
        report['checks']['east_longitude_decreases_for_inertial_direction']={'delta_degrees_60s':change,'rate_degrees_per_day':rate}
        session=Session(folder/'sessions');session.import_atlas(prepare(states('2026-10-11T12:00:00Z')))
        first=session.state();body=next(b for b in first['bodies'] if b['reference_id']=='sol:naif:599')
        a=field.read(first,body['id'],2*jrm33.R,30,120)
        session.integrate(21600/first['physical_scale']['time_unit_s']);later=session.state()
        b=field.read(later,body['id'],2*jrm33.R,30,120)
        assert b['field_SystemIII_T']==a['field_SystemIII_T'] and b['field_J2000_T']!=a['field_J2000_T']
        assert b['epoch']['et_tdb_s']-a['epoch']['et_tdb_s']==21600
        assert b['jupiter_center_inertial_m']!=a['jupiter_center_inertial_m']
        shifted=copy.deepcopy(later);shift=[1234.,-5678.,910.]
        shifted_body=next(v for v in shifted['bodies'] if v['id']==body['id'])
        for k in range(3):shifted_body['position'][k]+=shift[k]/later['physical_scale']['length_unit_m']
        c=field.read(shifted,body['id'],2*jrm33.R,30,120)
        assert c['field_J2000_T']==b['field_J2000_T']
        assert max(abs(c['point_inertial_m'][k]-b['point_inertial_m'][k]-shift[k]) for k in range(3))<.001
        for latitude in [-90,0,90]:
            zero=field.read(later,body['id'],jrm33.R,latitude,0)
            full=field.read(later,body['id'],jrm33.R,latitude,360)
            assert np.max(np.abs(np.array(zero['field_J2000_T'])-full['field_J2000_T']))<1e-18
        report['checks']['six_hour_rotation_static_coefficients_translation_poles_and_longitude']=True
        refused=[]
        for label,identifier,radius,latitude,longitude,degree in [
            ('wrong_body',first['bodies'][1]['id'],jrm33.R,0,0,13),('unknown_body','unknown',jrm33.R,0,0,13),
            ('radius_low',body['id'],jrm33.R-1,0,0,13),('radius_high',body['id'],21*jrm33.R,0,0,13),
            ('latitude',body['id'],jrm33.R,91,0,13),('longitude',body['id'],jrm33.R,0,-1,13),
            ('longitude_high',body['id'],jrm33.R,0,361,13),('bool',body['id'],True,0,0,13),
            ('nan',body['id'],jrm33.R,float('nan'),0,13),('infinity',body['id'],jrm33.R,0,float('inf'),13),
            ('degree',body['id'],jrm33.R,0,0,30),('degree_bool',body['id'],jrm33.R,0,0,True)]:
            before=copy.deepcopy(first)
            try:field.read(first,identifier,radius,latitude,longitude,degree)
            except ValueError:pass
            else:raise AssertionError(label)
            assert first==before and inventory()==baseline;refused.append(label)
        for utc in ['1999-12-31T23:59:59Z','2030-01-01T00:00:01Z']:
            session.import_atlas(prepare(states(utc)));snapshot=session.state()
            identifier=next(v['id'] for v in snapshot['bodies'] if v['reference_id']=='sol:naif:599')
            try:field.read(snapshot,identifier,jrm33.R,0,0)
            except ValueError:pass
            else:raise AssertionError('Out-of-range epoch accepted.')
            refused.append('epoch_'+utc)
        original=spice.gdpool('BODY599_PM',0,10).tolist()
        spice.pdpool('BODY599_PM',[284.95,870.5,0.])
        try:
            try:field.read(first,body['id'],jrm33.R,0,0)
            except ValueError as error:assert 'efetivos' in str(error)
            else:raise AssertionError('Shadowed pool parameters accepted.')
        finally:spice.pdpool('BODY599_PM',original)
        refused.append('shadowed_effective_pool')
        report['checks']['transactional_refusals']=refused
        assert spice.spkezr('399',et0,'J2000','NONE','0')[0].tolist()==baseline_state
        assert spice.pxform('IAU_JUPITER','J2000',et0).tolist()==baseline_rotation
        assert inventory()==baseline and sha(owner)==owner_before
        assert all(sha(ROOT/name)==digest for name,digest in hashes.items())
        (folder/'all-readings.json').write_text(json.dumps(readings,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
        report['checks']['sources_pool_reference_states_and_owner_preserved']=True
        report['completed']=report['accepted']=True
    except Exception:report['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps({'receipt':receipt.relative_to(ROOT).as_posix(),'accepted':report['accepted'],
        'failure':report.get('failure'),'checks':report['checks']},ensure_ascii=False))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
