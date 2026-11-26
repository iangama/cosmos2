"""Verify staged tide request guards without touching the active renderer."""
from pathlib import Path
import ast
import copy
import hashlib
import json
import sys
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'output/is3-solar-staging'))
from solar_tides import evaluate,guarded_read
receipt=ROOT/'evidence/is3-tide-guards-20261023a.json'
folder=ROOT/'output/is3-tide-guards-20261023a'
if receipt.exists() or folder.exists():raise FileExistsError('Preserve earlier evidence.')
folder.mkdir()
module=ROOT/'output/is3-solar-staging/solar_tides.py'
fixture=ROOT/'output/is12-native-20261023d/initial-snapshot.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=[Path(__file__).resolve(),module,fixture,ROOT/'IS-3-MARES-VALIDACAO-PREVIA.md']
with zipfile.ZipFile(folder/'sources-fixture.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
report={'schema':1,'accepted':False,'sources_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in paths},
        'refusals':[],'scope':'Staged function/request guards only; no API/worker/native integration acceptance.'}
receipt.write_text(json.dumps(report,indent=2)+'\n')
try:
    def scientific_ast(text):
        return ast.dump(next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='evaluate'))
    with zipfile.ZipFile(ROOT/'output/is3-tides-check-20261023a/sources-fixture-recipe.zip') as z:
        previous=z.read('output/is3-solar-staging/solar_tides.py').decode('utf-8')
    assert scientific_ast(previous)==scientific_ast(module.read_text(encoding='utf-8'))
    report['scientific_function_AST_unchanged_from_72_Decimal_cases']=True
    state=json.loads(fixture.read_text(encoding='utf-8'));original=copy.deepcopy(state)
    body=state['bodies'][1]
    request={k:state[k] for k in ['system_id','edit_token','revision']}
    request.update(expected_time=state['time'],frame=state['contract']['frame'],body_id=body['id'],offset_m=[6378137.,0,0])
    assert guarded_read(state,request)==evaluate(state,body['id'],request['offset_m'])
    variants=[]
    for key in request:
        bad=copy.deepcopy(request);del bad[key];variants.append(('missing_'+key,state,bad))
    for key,value in [('extra',1),('system_id','stale'),('edit_token','stale'),('revision',1),('revision',True),
                      ('expected_time',1),('expected_time',True),('expected_time',float('nan')),
                      ('frame','SSB'),('body_id','unknown'),('offset_m',[True,0,0]),('offset_m',[0,0]),
                      ('offset_m',[float('inf'),0,0]),('offset_m',[1e13,0,0])]:
        bad=copy.deepcopy(request);bad[key]=value;variants.append((key+'_'+str(value),state,bad))
    for key,value in [('gravity_effects',{'test':1}),('material_tides',{'test':1})]:
        bad=copy.deepcopy(state);bad[key]=value;variants.append((key,bad,request))
    bad=copy.deepcopy(state);bad['contract']['model']='unsupported';variants.append(('unsupported_model',bad,request))
    other=state['bodies'][2];length=state['physical_scale']['length_unit_m']
    bad=copy.deepcopy(request);bad['offset_m']=[(other['position'][k]-body['position'][k])*length for k in range(3)]
    variants.append(('external_source_singularity',state,bad))
    for label,snapshot,payload in variants:
        before=copy.deepcopy(snapshot)
        try:guarded_read(snapshot,payload)
        except ValueError:pass
        else:raise AssertionError('Invalid request accepted: '+label)
        assert snapshot==before,label
        report['refusals'].append(label)
    assert state==original
    report.update(accepted=True,read_only=True,positive_guarded_reading=True)
except Exception:report['failure']=traceback.format_exc()
receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'accepted':report['accepted'],'refusals':len(report['refusals']),'failure':report.get('failure')}))
raise SystemExit(0 if report['accepted'] else 1)
