"""Extend the pinned reference model with six moons while retaining the ten prior records."""
import argparse
import copy
import hashlib
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is6-planet-navigation-product0.24.0/app'
BASE=ROOT/'output/is6-planet-catalog-model-20261110a/catalog-data.json'
sys.path.insert(0,str(APP))
helpers=SourceFileLoader('moons_printed_parameter',str(ROOT/'scripts/prepare-is6-planet-catalog.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ROWS=[('501','Io','Io','5','jup365'),('502','Europa','Europa','5','jup365'),
      ('503','Ganymede','Ganimedes','5','jup365'),('504','Callisto','Calisto','5','jup365'),
      ('602','Enceladus','Encélado','6','sat441'),('606','Titan','Titã','6','sat441')]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True)
    parser.add_argument('--data-label',required=True);parser.add_argument('--acquisition-label',required=True)
    args=parser.parse_args();label=args.label
    for value in [label,args.data_label,args.acquisition_label]:
        if not value or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in value):parser.error('Invalid label')
    data_path=ROOT/f'evidence/is6-principal-moons-data-{args.data_label}.json'
    acquired_path=ROOT/f'evidence/is6-principal-moons-acquisition-{args.acquisition_label}.json'
    acquired=json.loads(acquired_path.read_text())
    data=json.loads(data_path.read_text());assert data['accepted'] and data['completed'] and acquired['completed']
    folder=ROOT/f'output/is6-principal-moons-model-{label}';folder.mkdir(exist_ok=False)
    model=copy.deepcopy(json.loads(BASE.read_text()))
    assert sha(BASE)==data['old_model_sha256']
    previous=copy.deepcopy(model['bodies']);assert len(previous)==10
    for name,seal in model['runtime_sha256'].items():assert sha(ROOT/name)==seal
    by_target={str(row['target']):row for row in data['centers']}
    for target,node,name,parent,family in ROWS:
        entry=by_target[target];comments=ROOT/acquired['files'][family+'.cmt']['path']
        assert sha(comments)==acquired['files'][family+'.cmt']['sha256']
        assert sha(ROOT/entry['file'])==entry['sha256']
        parameter=helpers.printed_parameter(comments,r'^\s*'+node+r'\s+'+target+r'\s+(\S+)\s+\d+\s+\d+\s+',
            acquired['files'][family+'.cmt']['url'])
        model['bodies'].append(dict(id='sol:naif:'+target,naif_id=target,name=name,node=node,
            entity_kind='physical_body',body_kind='moon',chain_naif_ids=[target,parent,'0'],
            relative_kernel=entry['file'],rotation_frame='IAU_'+node.upper(),GM=parameter))
        model['extra_spk'].append(entry['file'])
        model['runtime_sha256'][entry['file']]=entry['sha256']
        model['runtime_sha256'][comments.relative_to(ROOT).as_posix()]=sha(comments)
    assert model['bodies'][:10]==previous
    model.update(kind='eight_planets_and_principal_moons_reference_data',version='0.3.0',
        source_data_receipt=data_path.relative_to(ROOT).as_posix(),source_data_sha256=sha(data_path),
        parent_model=dict(path=BASE.relative_to(ROOT).as_posix(),sha256=sha(BASE)),
        recipe_sha256=sha(Path(__file__)),
        scope='Isolated reference model: Sun, eight physical planets and seven moons. No new native scene or coupled dynamics acceptance.')
    path=folder/'catalog-data.json';path.write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    code=(APP/'is6_planet_catalog_v2.py').read_text()
    code=code.replace('eight physical planets, Sun and Moon.','eight physical planets, Sun and seven moons.')
    code=code.replace("DATA = ROOT / 'output/is6-planet-catalog-model-20261110a/catalog-data.json'",
                      'DATA = ROOT / '+repr(path.relative_to(ROOT).as_posix()))
    code=code.replace("DATA_SHA256 = 'fd040559c9e35ccb7a5a154241a20e6a912968284bef8db44f3a0182c1fb13c2'",
                      'DATA_SHA256 = '+repr(sha(path)))
    assert "'899': 'NEP097'}" in code
    code=code.replace("'899': 'NEP097'}", "'899': 'NEP097', '501': 'JUP365', '502': 'JUP365', '503': 'JUP365',\n          '504': 'JUP365', '602': 'SAT441', '606': 'SAT441'}")
    code=code.replace("kind='eight_planet_geometric_reference', version='0.2.0'",
                      "kind='eight_planets_and_principal_moons_geometric_reference', version='0.3.0'")
    module=folder/'is6_principal_moons_catalog.py';module.write_text(code,encoding='utf8')
    compile(code,str(module),'exec')
    receipt=ROOT/f'evidence/is6-principal-moons-catalog-prepared-{label}.json';assert not receipt.exists()
    result=dict(prepared=True,accepted=False,bodies=len(model['bodies']),moons=7,prior_records_unchanged=True,
        model=dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path)),
        module=dict(path=module.relative_to(ROOT).as_posix(),sha256=sha(module)),
        acquisition=dict(path=acquired_path.relative_to(ROOT).as_posix(),sha256=sha(acquired_path)),
        script_sha256=sha(Path(__file__)),contract_sha256=sha(ROOT/'IS-6-LUAS-PRINCIPAIS-CONTRATO.md'),
        scope='Prepared CPU model only. Five-epoch/refusal/reopen verification, independent comparison, native UI and own profiles pending.')
    receipt.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(prepared=True,bodies=16,module=result['module'])),flush=True)


if __name__=='__main__':main()
