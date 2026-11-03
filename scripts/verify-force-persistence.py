"""Configuration migrations, provenance drift and complete envelope integrity."""
from pathlib import Path
import copy
import hashlib
import json
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from forces import SCENARIOS,normalize,evaluate,save_configuration,load_configuration,load_configuration_record

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',', ':'),allow_nan=False).encode()).hexdigest()
def envelope(record):
    record['sha256']=digest(record['configuration'])
    record['generation_sha256']=digest(record['scientific_generation'])
    record['manifest_sha256']=digest({k:v for k,v in record.items() if k!='manifest_sha256'})
    return record

with tempfile.TemporaryDirectory(prefix='cosmos2-provenance-') as folder:
    path=Path(folder)/'latest.json';checked=[]
    for key in SCENARIOS:
        request={'scenario':key}
        record=save_configuration(request,folder)
        loaded=load_configuration_record(folder)
        assert record['schema']==3 and record['manifest_sha256']==digest({k:v for k,v in record.items() if k!='manifest_sha256'})
        assert loaded['configuration']==normalize(request)==load_configuration(folder)
        assert loaded['restoration']['status']=='same_generation'
        assert not loaded['restoration']['differences']
        for group in ('code_sha256','data_sha256'):
            for name,sha in record['scientific_generation'][group].items():
                assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha
        checked.append(key)
    record=save_configuration({'scenario':'weak','controls':{'weak':{'acting':False}}},folder)
    assert evaluate(record['configuration'])==evaluate(load_configuration(folder))
    corrupted=0
    for mutate in (
        lambda r:r['configuration']['controls']['weak'].update(acting=True),
        lambda r:r['scientific_generation']['code_sha256'].update({'app/forces.py':'0'*64}),
        lambda r:r['scientific_generation']['runtime'].update(scipy='0.0.0'),
        lambda r:r.update(generation_sha256='0'*64),
        lambda r:r.update(manifest_sha256='0'*64),
    ):
        changed=copy.deepcopy(record);mutate(changed);path.write_text(json.dumps(changed))
        try:load_configuration_record(folder)
        except ValueError:corrupted+=1
        else:raise AssertionError('Accepted corrupt configuration/generation')
    changed=copy.deepcopy(record)
    changed['scientific_generation']['code_sha256']['app/forces.py']='a'*64
    changed['scientific_generation']['runtime']['scipy']='0.0.0'
    path.write_text(json.dumps(envelope(changed)))
    loaded=load_configuration_record(folder)
    assert loaded['configuration']==record['configuration']
    assert loaded['restoration']['status']=='changed_generation'
    assert {(d['kind'],d['name']) for d in loaded['restoration']['differences']}=={('code','app/forces.py'),('runtime','scipy')}
    changed=save_configuration({'scenario':'geomagnetic'},folder)
    changed['scientific_generation']['data_sha256']['data/science/igrf14coeffs.txt']='b'*64
    path.write_text(json.dumps(envelope(changed)))
    assert load_configuration_record(folder)['restoration']['differences'][0]['kind']=='data'
    legacy=[]
    for schema in (1,2):
        config={'scenario':'weak','parameters':{'initial_population':1000},'controls':{'weak':{'acting':False,'visible':True}}}
        path.write_text(json.dumps({'schema':schema,'configuration':config,'sha256':digest(config)}))
        loaded=load_configuration_record(folder)
        assert loaded['restoration']['status']=='unknown_generation'
        assert loaded['restoration']['saved_generation'] is None
        assert loaded['configuration']==normalize(config)
        legacy.append(schema)
    record=save_configuration({'scenario':'weak'},folder);before=path.read_bytes()
    try:save_configuration({'scenario':'invalid'},folder)
    except ValueError:pass
    else:raise AssertionError('Invalid configuration accepted')
    assert path.read_bytes()==before
report={'schema':3,'roundtrip_models':checked,'same_generation':True,'configuration_and_provenance_corruptions_rejected':corrupted,
        'changed_code_data_runtime_reported':True,'conditions_preserved_across_generation_change':True,
        'legacy_schemas_unknown_generation':legacy,'invalid_save_preserves_previous_file':True,
        'weak_recalculation_identical_in_current_generation':True,
        'scope':'Configuration provenance; not a solver state checkpoint or a guarantee of cross-machine bit identity'}
(ROOT/'evidence/force-persistence-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
