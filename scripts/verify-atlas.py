"""JPL state contract, independent Horizons and native geometric translation."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys
import runpy
import urllib.error
import urllib.request
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
import atlas
parser=argparse.ArgumentParser();parser.add_argument('--native',action='store_true');args=parser.parse_args()
epochs=['1950-01-01T00:00:00','2000-01-01T12:00:00','2026-10-11T12:00:00','2030-06-15T18:30:00','2050-12-31T23:59:59']
results=[atlas.states(utc=utc) for utc in epochs];spice=atlas.SPICE
for result in results:
    assert result['frame']=='J2000/ICRF' and result['aberration']=='NONE'
    assert result['center_naif_id']=='0' and result['position_unit']=='m' and result['velocity_unit']=='m/s'
    assert {b['id'] for b in result['bodies']}=={'sol:naif:10','sol:naif:399','sol:naif:301','sol:naif:699'}
    et=result['epoch']['et_tdb_s']
    # A separate relative query must match subtraction of SSB states.
    relative,_=spice.spkezr('301',et,'J2000','NONE','399')
    direct_distance=np.linalg.norm(relative[:3])*1000
    assert abs(direct_distance-result['earth_moon_separation_m'])<.0001
    for body in result['bodies']:
        assert all(math.isfinite(x) for x in body['position_m']+body['velocity_m_s'])
        if body['body_to_j2000'] is not None:
            matrix=np.array(body['body_to_j2000'])
            assert np.max(np.abs(matrix.T@matrix-np.eye(3)))<1e-14
            assert abs(np.linalg.det(matrix)-1)<1e-14
        direct=spice.spkpos(body['naif_id'],et,'GALACTIC','NONE','0')[0]*1000
        assert np.max(np.abs(direct-np.array(body['position_render_m'])))<=.001
        # Independent finite temporal derivative of positions checks km/s -> m/s.
        derivative_et=max(body['coverage_et_s'][0][0]+10,min(body['coverage_et_s'][-1][1]-10,et))
        before=spice.spkpos(body['naif_id'],derivative_et-10,'J2000','NONE','0')[0]
        after=spice.spkpos(body['naif_id'],derivative_et+10,'J2000','NONE','0')[0]
        derivative=(after-before)*1000/20
        expected_velocity=spice.spkezr(body['naif_id'],derivative_et,'J2000','NONE','0')[0][3:]*1000
        assert np.max(np.abs(derivative-expected_velocity))<.01
    json.loads(json.dumps(result,allow_nan=False))
# LSK must preserve the known 2016 leap second, rather than subtract a constant.
a=atlas.states(utc='2016-12-31T23:59:59')['epoch']['et_tdb_s']
b=atlas.states(utc='2017-01-01T00:00:00')['epoch']['et_tdb_s']
assert abs((b-a)-2)<1e-6
rejected=0
for utc in ['1949-12-31T23:59:59','2051-01-01T00:00:00','2026-02-30T00:00:00','2026-01-01T12:00:00+03:00','garbage',True]:
    try:atlas.states(utc=utc)
    except ValueError:rejected+=1
    else:raise AssertionError(utc)
fixture=json.loads((ROOT/'evidence/atlas-horizons-reference.json').read_text());comparison=[]
for query in fixture['queries']:
    assert hashlib.sha256((ROOT/query['response_file']).read_bytes()).hexdigest()==query['response_sha256']
    source=[line.strip() for line in query['header'].splitlines() if 'source:' in line.lower()]
    assert query['query']['VEC_CORR']=="'NONE'" and query['query']['REF_PLANE']=="'FRAME'"
    for case in query['cases']:
        et=float(spice.unitim(case['jd_tdb'],'JDTDB','ET'))
        state,_=spice.spkezr(query['target_naif_id'],et,'J2000','NONE','0')
        pos=float(np.linalg.norm(state[:3]-case['position_km'])*1000)
        vel=float(np.linalg.norm(state[3:]-case['velocity_km_s'])*1000)
        assert pos<=1000,(query['target_naif_id'],pos)
        comparison.append({'target':query['target_naif_id'],'jd_tdb':case['jd_tdb'],'position_difference_m':pos,
                           'velocity_difference_m_s':vel,'horizons_source':source})
native=[]
if args.native:
    execute=runpy.run_path(str(ROOT/'scripts/engine-command.py'))['execute']
    def get():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/atlas/state',timeout=10))
    original=get()['epoch']['utc']
    def post(utc):
        return json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:4700/api/atlas/epoch',
                        data=json.dumps({'utc':utc}).encode(),headers={'Content-Type':'application/json'}),timeout=10))
    try:
        for utc in epochs:
            response=post(utc);assert response['ok'];result=response['atlas']
            assert result['renderer']['paused']
            errors=[max(abs(a-b) for a,b in zip(result['renderer']['positions'][body['scene_node']],body['position_render_m'])) for body in result['bodies']]
            assert max(errors)<=.001
            rotations=execute('return {Earth=openspace.worldRotation("Earth"),Moon=openspace.worldRotation("Moon"),Saturn=openspace.worldRotation("Saturn")}')['payload']['1']
            rotation_error=0
            for body in result['bodies']:
                if not body['body_frame']:continue
                # Native Lua glm matrix is serialized as 1..9 in column order.
                matrix=np.array([rotations[body['scene_node']][str(i)] for i in range(1,10)]).reshape(3,3,order='F')
                expected=np.array(result['j2000_to_render_frame'])@np.array(body['body_to_j2000'])
                rotation_error=max(rotation_error,float(np.max(np.abs(matrix-expected))))
            assert rotation_error<1e-12
            native.append({'utc':utc,'max_component_difference_m':max(errors),'body_rotation_difference_max':rotation_error})
        before=get()['epoch']['et_tdb_s']
        try:post('2051-01-01T00:00:00')
        except urllib.error.HTTPError as error:assert error.code==400
        else:raise AssertionError('Native accepted invalid epoch')
        assert get()['epoch']['et_tdb_s']==before
    finally:post(original)
report={'model':'JPL DE442s','epochs':epochs,'provenance':results[0]['provenance'],
        'coverage_each_body':{b['naif_id']:b['coverage_et_s'] for b in results[0]['bodies']},
        'relative_center_and_velocity_conversion':True,'rotations_orthogonal':True,'leap_second_preserved':True,
        'invalid_epochs_rejected':rejected,'horizons_comparison':comparison,'native_scene_comparison':native,
        'native_invalid_epoch_preserves_state':True if args.native else None,
        'scope':'Pipeline and frame/unit agreement. Different JPL models and source uncertainty do not imply observed accuracy.'}
name='native-atlas-check.json' if args.native else 'atlas-check.json'
(ROOT/'evidence'/name).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('coverage_each_body','provenance')},indent=2))
