"""Independent 70-digit Decimal reference for the staged differential field."""
from pathlib import Path
from decimal import Decimal, localcontext
import copy
import hashlib
import json
import math
import sys
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'output/is3-solar-staging'))
from solar_tides import evaluate

receipt=ROOT/'evidence/is3-tides-staging-20261023a.json'
folder=ROOT/'output/is3-tides-check-20261023a'
if receipt.exists() or folder.exists():raise FileExistsError('Preserve prior evidence.')
folder.mkdir()
fixture=ROOT/'output/is12-native-20261023d/initial-snapshot.json'
files=[Path(__file__).resolve(),ROOT/'IS-3-MARES-VALIDACAO-PREVIA.md',ROOT/'output/is3-solar-staging/solar_tides.py',fixture]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
with zipfile.ZipFile(folder/'sources-fixture-recipe.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in files:z.write(p,p.relative_to(ROOT).as_posix())
report={'schema':1,'source_sha256':hashes,'limits_before_execution':{'absolute_component_m_s2':2e-15,'relative_component':1e-10},
        'accepted':False,'cases':[],'scope':'Staged passive calculation only, without API/UI integration or IS-3 acceptance.'}
receipt.write_text(json.dumps(report,indent=2)+'\n')
try:
    state=json.loads(fixture.read_text(encoding='utf-8'));unchanged=copy.deepcopy(state)
    for body in state['bodies']:
        zero=evaluate(state,body['id'],[0,0,0]);assert zero['exact_m_s2']==[0.,0.,0.]
        for axis in range(3):
            for sign in [-1,1]:
                for length in [100,100000,6378137]:
                    offset=[0.,0.,0.];offset[axis]=sign*length
                    result=evaluate(state,body['id'],offset)
                    errors=[]
                    for row in result['sources']:
                        source=next(b for b in state['bodies'] if b['id']==row['id'])
                        with localcontext() as context:
                            context.prec=70
                            D=Decimal.from_float
                            scale=D(state['physical_scale']['length_unit_m'])
                            d=[(D(source['position'][k])-D(body['position'][k]))*scale for k in range(3)]
                            q=[d[k]-D(offset[k]) for k in range(3)]
                            r=sum(x*x for x in d).sqrt();rq=sum(x*x for x in q).sqrt()
                            gm=D(source['mass'])*D(state['physical_scale']['nominal_GM_unit_m3_s2'])
                            expected=[float(gm*(q[k]/rq**3-d[k]/r**3)) for k in range(3)]
                        for a,b in zip(row['exact_m_s2'],expected):
                            assert abs(a-b)<=2e-15,(a,b)
                            if abs(b)>1e-12:assert abs(a-b)/abs(b)<=1e-10,(a,b)
                            errors.append(abs(a-b))
                    assert len(result['sources'])==3 and body['id'] not in [r['id'] for r in result['sources']]
                    report['cases'].append({'body':body['reference_id'],'offset_m':offset,'max_component_error_m_s2':max(errors)})
        residuals=[]
        for length in [1000.,100.]:
            result=evaluate(state,body['id'],[length,0,0])
            residuals.append(max(math.hypot(*r['nonlinear_residual_m_s2']) for r in result['sources']))
        assert residuals[1]<=residuals[0]*.02+1e-24,residuals
    invalid=[[True,0,0],[float('nan'),0,0],[float('inf'),0,0],[0,0],[1e13,0,0]]
    for offset in invalid:
        try:evaluate(state,state['bodies'][1]['id'],offset)
        except ValueError:pass
        else:raise AssertionError('Invalid offset accepted.')
    assert state==unchanged and len(report['cases'])==72
    assert all(sha(ROOT/name)==digest for name,digest in hashes.items())
    report.update(accepted=True,read_only=True,zero_offset_exact=True,linear_refinement_passed=True,invalid_offsets_refused=5)
except Exception:report['failure']=traceback.format_exc()
receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
print(json.dumps({'accepted':report['accepted'],'cases':len(report['cases']),'failure':report.get('failure')}))
raise SystemExit(0 if report['accepted'] else 1)
