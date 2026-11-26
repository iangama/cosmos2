"""Exercise the I audit with a real layer and deliberately resealed corruptions."""
from pathlib import Path
from copy import deepcopy
import ast
import hashlib
import json
import subprocess
import sys
from em_viewport_profile_audit import audit_dependencies,audit_potential,digest,BASE

ROOT=Path(__file__).resolve().parents[1];I=ROOT/BASE
destination=ROOT/'evidence/em-viewport-profile-support-check.json';assert not destination.exists()
sources=[p for folder in ('em','app','em-cloud') for p in (I/folder).rglob('*')
         if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py','.dll','.cpp','.json','.txt')]
sources += [ROOT/'scripts/build-em-cloud-kernel.ps1',ROOT/'scripts/em_viewport_profile_audit.py',ROOT/'evidence/em-framing-static-sampler-release2-check.json']
configuration={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
layer_file=None
for p in (ROOT/'output/c212-em-framing-product/native-potential').glob('*/layer-receipt.json'):
    v=json.loads(p.read_bytes());layer=v['layer'];ex=layer['source_snapshot']
    if len(layer['measurement']['samples'])==1089 and ex.get('mode')=='mutual_electrostatic' and len(ex['system']['ids'])==128:
        layer_file=p;break
assert layer_file
report={'configuration_sha256':configuration,'fixture':ex,'scientific_generation':layer['scientific_generation'],
        'viewport_profile':True,'framing_profile':True,'cloud_editor_profile':True,'integration_profile':True,
        'session':{'emViewportCandidate':True,'emFramingCandidate':True,'emCloudEditorCandidate':True},
        'potential_numeric_sampling_ms':[layer['batch_protocol']['elapsed_wall_ms']]}
run={'run':1,'frozen_potential_layer':layer,'frozen_potential_render':v['render'],
     'initial':{'system_id':layer['measurement']['system_id']}}
constants=json.loads((I/'em/constants.json').read_bytes());ke=1/(4*__import__('math').pi*constants['vacuum_electric_permittivity_F_m']['value'])
deps=audit_dependencies(report,lambda path:(ROOT/path).read_bytes())
valid=audit_potential(report,run,ke);rejected=[]
for kind in ('unsealed_values','resealed_values','exclusion','provider_hash','worker_attribution','batches','budget','layer_id','source_snapshot'):
    broken=deepcopy(run);l=broken['frozen_potential_layer']
    sample=next(s for s in l['measurement']['samples'] if s['valid'])
    if kind in ('unsealed_values','resealed_values'):sample['electric_potential_V']+=1.
    elif kind=='exclusion':l['geometry']['exclusions'][0]['radius_m']*=2
    elif kind=='provider_hash':l['batch_protocol']['provider']['files_sha256']['app/em_static_sampler.py']='0'*64
    elif kind=='worker_attribution':l['batch_protocol']['provider']['field_queries_in_worker']=True
    elif kind=='batches':l['batch_protocol']['batches'][-1]['samples']-=1
    elif kind=='budget':l['batch_protocol']['budget_s']=3
    elif kind=='layer_id':broken['frozen_potential_render']['layer_id']='0'*64
    elif kind=='source_snapshot':l['source_snapshot']['system']['charge_C'][0]*=2
    if kind=='resealed_values':
        l['geometry']['measurement_sha256']=digest(l['measurement'])
        broken['frozen_potential_render']['layer_id']=digest(l['geometry'])
    try:audit_potential(report,broken,ke)
    except AssertionError:rejected.append(kind)
    else:raise AssertionError('Corrupted layer accepted: '+kind)
for name in ('review-em128-new-runtime-benchmark.py','review-em-cloud-source128-benchmark.py'):
    tree=ast.parse((ROOT/'scripts'/name).read_text())
    guards=[node for node in ast.walk(tree) if isinstance(node,ast.Assert) and 'prefix' in ast.unparse(node.test) and any(flag in ast.unparse(node.test) for flag in ('integration_profile','cloud_editor_profile','framing_profile','viewport_profile'))]
    assert len(guards)==4
    for suffix,flags in (('integration',(True,False,False,False)),('cloud-editor',(True,True,False,False)),('framing',(True,True,True,False)),('viewport',(True,True,True,True)),('time',(False,False,False,False))):
        prefix='output/c212-em-'+suffix+'-product/'+('em-cloud/' if 'cloud-source' in name else 'em/')
        for mask in range(16):
            r=dict(zip(('integration_profile','cloud_editor_profile','framing_profile','viewport_profile'),(bool(mask&8),bool(mask&4),bool(mask&2),bool(mask&1))))
            actual=all(eval(compile(ast.Expression(g.test),'<prefix-guard>','eval'),{'r':r,'prefix':prefix}) for g in guards)
            assert actual==(tuple(r.values())==flags),(name,prefix,r)
for name in ('benchmark-em128-new-runtime-native.py','benchmark-em128-potential-native.py','benchmark-em-cloud-source128-native.py'):
    p=ROOT/'scripts'/name
    help_result=subprocess.run([sys.executable,str(p),'--help'],capture_output=True,text=True)
    assert help_result.returncode==0 and '--viewport' in help_result.stdout
    refusal=subprocess.run([sys.executable,str(p),'--label','invalid','--viewport'],capture_output=True,text=True)
    assert refusal.returncode!=0 and 'assert not args.viewport or args.framing' in refusal.stderr
result={'completed':True,'real_layer':str(layer_file.relative_to(ROOT)),
        'real_layer_sha256':hashlib.sha256(layer_file.read_bytes()).hexdigest(),
        'dependency_check':deps,'raw_layer_audit':valid,'corruptions_rejected':rejected,
        'prefix_guard_combinations_checked':160,'runner_flag_guards_checked':3,
        'source_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),ROOT/'scripts/em_viewport_profile_audit.py')},
        'scope':'Audit/runner preparation only; no J formal frame/throughput acceptance.'}
destination.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
