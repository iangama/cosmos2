"""Original Fortran fixtures, geodesy, degree1 and instantaneous operator checks."""
from pathlib import Path
import hashlib
import itertools
import json
import math
import sys

import numpy as np
from scipy.constants import elementary_charge

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from geomagnetism import field_at,spherical,geodetic_position,coefficients,WGS_A,WGS_B,REFERENCE_RADIUS_M
from forces import evaluate,normalize

fixture=json.loads((ROOT/'evidence/igrf-reference.json').read_text())
assert hashlib.sha256((ROOT/'data/science/igrf14coeffs.txt').read_bytes()).hexdigest()==fixture['coefficient_sha256']
assert hashlib.sha256((ROOT/'.upstream/igrf14/igrf14.f').read_bytes()).hexdigest()==fixture['source_sha256']
differences=[]
for case in fixture['cases']:
    if case['itype']==1:
        value=field_at(case['year'],case['latitude_deg'],case['longitude_deg'],case['altitude_km']*1000,secular=bool(case['isv']))['field_ned_nT']
    else:
        br,bt,bp=spherical(case['year'],case['radius_km']*1000,math.radians(90-case['latitude_deg']),math.radians(case['longitude_deg']))
        value=[-bt,bp,-br]
    error=max(abs(a-b) for a,b in zip(value,case['reference_ned_nT']))
    assert error<=1.,(case,error,value)
    differences.append({'year':case['year'],'itype':case['itype'],'isv':case['isv'],'latitude':case['latitude_deg'],'max_component_error_nT':error})
assert len(differences)>=20
assert np.allclose(geodetic_position(0,0,0),[WGS_A,0,0],rtol=0,atol=1e-9)
assert np.allclose(geodetic_position(0,90,1000),[0,WGS_A+1000,0],rtol=0,atol=1e-9)
assert np.allclose(geodetic_position(90,0,0),[0,0,WGS_B],rtol=0,atol=1e-9)
for latitude in (-90,90):
    a=field_at(2026,latitude,0,0)['field_ecef_T']
    for longitude in (-180,-90,90,180):
        b=field_at(2026,latitude,longitude,0)['field_ecef_T']
        assert np.allclose(a,b,rtol=1e-13,atol=1e-19)
assert np.allclose(field_at(2026,12,-180,0)['field_ecef_T'],field_at(2026,12,180,0)['field_ecef_T'],rtol=1e-14)
degree1_errors=[]
for latitude,longitude,height in [(-23,40,0),(0,0,1000),(90,180,1e6),(-90,0,0),(67,-90,500000)]:
    a=field_at(2026,latitude,longitude,height,degree=1)
    pos=np.array(a['position_ecef_m']);r=np.linalg.norm(pos);unit=pos/r;cf=coefficients(2026)
    vector=np.array([cf['g',1,1],cf['h',1,1],cf['g',1,0]])*1e-9
    ref=(REFERENCE_RADIUS_M/r)**3*(3*np.dot(vector,unit)*unit-vector)
    error=float(np.linalg.norm(ref-a['field_ecef_T'])/np.linalg.norm(ref));assert error<1e-14;degree1_errors.append(error)

baseline=evaluate({'scenario':'geomagnetic'});ref=baseline['result']['reference']
for charge,master,effect in itertools.product((-1,1),(False,True),(False,True)):
    request={'scenario':'geomagnetic','parameters':{'charge_sign':charge,'velocity_north_km_s':200,'velocity_east_km_s':-30,'velocity_down_km_s':75},
             'controls':{'electromagnetic':{'acting':master,'effects':{'magnetic_deflection':effect}}}}
    out=evaluate(request);g=out['result']['geomagnetic'];b=np.array(g['full']['field_ned_T']);v=np.array(g['velocity_ned_m_s'])
    force=charge*elementary_charge*np.cross(v,b)*(master and effect)
    assert np.allclose(force,g['full']['magnetic_force_ned_N'],rtol=1e-14,atol=1e-32)
    assert out['result']['reference']==ref
    assert abs(np.dot(force,v))<=1e-14*np.linalg.norm(force)*np.linalg.norm(v)+1e-100
    assert out['scientific_contract']['sampling']['kind']=='spatial_snapshot'
    assert out['result']['time_s']==[]
hidden=evaluate({'scenario':'geomagnetic','controls':{'electromagnetic':{'visible':False}}})
assert hidden['result']==baseline['result'] and hidden['physics_sha256']==baseline['physics_sha256']
assert len(baseline['result']['geomagnetic']['grid'])==703
for parameters in ({'year':1899.9},{'year':2030.001},{'altitude_km':-1},{'altitude_km':1000.01},{'latitude_deg':90.01},{'charge_sign':0}):
    try:normalize({'scenario':'geomagnetic','parameters':parameters})
    except ValueError:pass
    else:raise AssertionError(parameters)
assert json.loads(json.dumps(baseline,allow_nan=False))==baseline
report={'model_id':baseline['scientific_contract']['model_id'],'scientific_contract':baseline['scientific_contract'],
        'original_fortran_cases':len(differences),'max_component_difference_nT':max(x['max_component_error_nT'] for x in differences),
        'geocentric_max_difference_nT':max(x['max_component_error_nT'] for x in differences if x['itype']==2),
        'geodetic_difference_scope':'Own exact WGS84 a/f versus BGS rounded squared axes and angle constants; retained, not fitted.',
        'degree1_cartesian_relative_error_max':max(degree1_errors),'geodesy_known_vectors':True,
        'pole_ecef_invariant':True,'meridian_periodic':True,'operator_cases':8,'force_power_ledger':True,
        'visibility_preserves_physics':True,'out_of_domain_rejected':True,'snapshot_not_time_evolution':True,
        'reference_sha256':hashlib.sha256((ROOT/'evidence/igrf-reference.json').read_bytes()).hexdigest(),
        'scope':'Numerical IGRF14 synthesis agreement; not observational magnetic-field accuracy','cases':differences}
(ROOT/'evidence/igrf-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('scientific_contract','cases')},indent=2))
