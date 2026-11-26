"""Compare the read-only adapter with every row of the accepted reference data."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/is5-solar-reference-browser-staging'
sys.path.insert(0,str(STAGE))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/f'output/is5-solar-reference-browser-{args.label}'
    path=ROOT/f'evidence/is5-solar-reference-browser-{args.label}.json'
    if folder.exists() or path.exists():raise FileExistsError('Preserve browser evidence')
    from is5_reference_browser import Library
    from is5_reference_manifest import FILES,MODELS
    originals=ROOT/'evidence/is5-solar-reference-20261027a.json'
    brackets=ROOT/'evidence/is5-solar-reference-audit-20261027b.json'
    previous=[json.loads(p.read_text()) for p in [originals,brackets]]
    hashes={}
    for receipt in previous:
        assert receipt['accepted']
        for n,v in receipt['source_sha256'].items():
            assert sha(ROOT/n)==v,n
            hashes[n]=v
    files=[Path(__file__),originals,brackets,ROOT/'scripts/prepare-is5-solar-reference-browser.py',
           ROOT/'IS-5-REFERENCIAS-SOLARES-PRODUTO-CONTRATO.md',*STAGE.glob('*.py'),
           *(STAGE/'references'/name for name in FILES),
           *(ROOT/row['path'] for receipt in previous for row in receipt.get('models',[])+receipt.get('comparison',[]))]
    hashes.update({p.relative_to(ROOT).as_posix():sha(p) for p in files})
    folder.mkdir()
    archive=folder/'executed-sources.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=hashes,archive_sha256=sha(archive),
           rows_checked=0,ideal_brackets_checked=0,refusals=0,models=[])
    try:
        library=Library()
        assert library.catalog()['models']==list(MODELS) and library.catalog()['interpolation'] is False
        for entry in previous[0]['models']:
            name=entry['model'];original=json.loads((ROOT/entry['path']).read_text())
            series=library.query('series','model='+name)
            assert series['r_over_Rsun']==[v[0] for v in original['raw_values']]
            for field in ['temperature_K','density_kg_m3','pressure_Pa','electron_density_m3']:
                assert series[field]==[v[field] for v in original['derived']]
            for index in range(2001):
                sample=library.sample(name,index)
                assert sample==library.query('sample',f'model={name}&index={index}')
                assert sample['structure']==original['derived'][index]
                assert sample['r_over_Rsun']==original['raw_values'][index][0]
                assert sample['abundances']==dict(zip(original['columns'][18:],original['raw_values'][index][18:]))
                assert sample['quality_flags']==original['flags'][index]
                assert sample['interpolation'] is False
                if index<3:assert not sample['structure']['eligible']
                r['rows_checked']+=1
            bracket=next((row for row in previous[1]['comparison'] if row['model']==name),None)
            if bracket:
                rows=json.loads((ROOT/bracket['path']).read_text());expected={row['index']:row for row in rows}
                for index in range(2001):
                    assert library.sample(name,index)['ideal_comparison']==expected.get(index)
                r['ideal_brackets_checked']+=len(rows)
            else:assert all(library.sample(name,i)['ideal_comparison'] is None for i in range(2001))
            # Returned structures must not allow a caller to edit cached scientific data.
            sample=library.sample(name,3);sample['structure']['temperature_K']=-1
            sample['abundances'].clear();sample['quality_flags'].append('invented')
            series['temperature_K'][3]=-1
            assert library.sample(name,3)['structure']==original['derived'][3]
            assert library.series(name)['temperature_K'][3]==original['derived'][3]['temperature_K']
            r['models'].append(name)
        invalid=[('catalog','x=1'),('sample','model=GS98'),('sample','model=GS98&index=true'),
                 ('sample','model=GS98&index=1.0'),('sample','model=GS98&index=2001'),
                 ('sample','model=GS98&index=-1'),('sample','model=GS98&index=%2B1'),
                 ('sample','model=GS98&index=3&index=4'),('sample','model=GS98&index=3&x=1'),
                 ('series','model=../GS98'),('series','model=unknown'),('series','model=GS98&model=AGSS09'),
                 ('unknown',''),('catalog','orphan')]
        for operation,query in invalid:
            try:library.query(operation,query)
            except ValueError:r['refusals']+=1
            else:raise AssertionError((operation,query))
        for index in [True,False,3.,'3',None,-1,2001]:
            try:library.sample('GS98',index)
            except ValueError:r['refusals']+=1
            else:raise AssertionError(index)
        with tempfile.TemporaryDirectory(dir=folder) as temporary:
            tmp=Path(temporary)
            for name in FILES:shutil.copy2(STAGE/'references'/name,tmp/name)
            target=tmp/'GS98.json';target.write_bytes(target.read_bytes()+b' ')
            try:Library(tmp)
            except ValueError:r['refusals']+=1
            else:raise AssertionError('Changed data accepted')
            target.unlink()
            try:Library(tmp)
            except FileNotFoundError:r['refusals']+=1
            else:raise AssertionError('Missing data accepted')
        assert r['rows_checked']==12006 and r['ideal_brackets_checked']==713
        assert all(sha(ROOT/n)==v for n,v in hashes.items())
        r.update(accepted=True,completed=True,scope='Lossless read-only adapter over accepted B23 data; no new EOS or solar evolution.')
    except Exception:r['failure']=traceback.format_exc()
    path.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in r.items() if k!='source_sha256'}),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
