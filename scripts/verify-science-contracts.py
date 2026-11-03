"""Unit/time/provenance and view-independent scientific identity checks."""
from pathlib import Path
import copy
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from forces import evaluate,SCENARIOS

models=[]
for name in SCENARIOS:
    result=evaluate({'scenario':name});c=result['scientific_contract']
    assert c['schema']==1 and c['model_id'].startswith('cosmos2:')
    if name=='geomagnetic':
        assert c['sampling']['kind']=='spatial_snapshot' and c['sampling']['states']==704
        assert result['result']['time_s']==[] and c['quantities']['epoch']['value']==2026
    else:
        assert c['sampling']['states']==241
        assert c['sampling']['end_s']==result['result']['time_s'][-1]
        assert c['quantities']['time_s']['epoch'] is None
    for category in ('code_sha256','data_sha256'):
        for path,digest in c['provenance'][category].items():
            assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
    request=copy.deepcopy(result['configuration'])
    for control in request['controls'].values():control['visible']=False
    hidden=evaluate(request)
    assert hidden['scientific_contract']==c
    assert hidden['physics_sha256']==result['physics_sha256']
    assert hidden['configuration_sha256']!=result['configuration_sha256']
    assert hidden['result']==result['result']
    assert json.loads(json.dumps(result,allow_nan=False))==result
    if name=='relativity':
        assert c['quantities']['time_s']['kind']=='normalized_affine_parameter'
        assert 'photon proper time' in c['quantities']['time_s']['normalization']
    if name=='binary':assert c['coordinate_frame']=='barycentric_corotating'
    if name in ('cno','stellar'):assert c['quantities']['curves']['definition']=='X_i=A_i n_i/(rho/m_u)'
    request['controls'][SCENARIOS[name]['force']]['acting']=False
    assert evaluate(request)['physics_sha256']!=hidden['physics_sha256']
    models.append({'scenario':name,'model_id':c['model_id'],'frame':c['coordinate_frame'],
                   'data_files':len(c['provenance']['data_sha256'])})
report={'models':models,'hashes_verified':True,'visibility_preserves_science_identity':True,
        'affine_time_separate':True,'json_round_trip':True,
        'scope':'bounded force export contracts; Atlas epochs and general session contracts remain pending'}
(ROOT/'evidence/science-contracts-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
