"""K4 filesystem checks with real scientific reconstruction and forced I/O failure."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import subprocess
import sys
import traceback
import zipfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/is6-layers-persistence-staging'
APP=ROOT/'output/is6-layers-product0.19.1/app'
sys.path[:0]=[str(STAGE),str(APP)]
import is6_layers_checkpoint_v2 as checkpoint
import is6_layers_store as storage
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/('output/is6-layers-store-check-'+args.label);out=ROOT/('evidence/is6-layers-store-'+args.label+'.json')
    if folder.exists() or out.exists():raise FileExistsError('Preserve store evidence')
    anchor=ROOT/'evidence/is6-layers-native-20261103b.json';a=json.loads(anchor.read_text());assert a['accepted']
    sources=dict(a['source_sha256'])
    for path in [Path(__file__),Path(checkpoint.__file__),Path(storage.__file__),anchor,ROOT/'IS-6-COEXISTENCIA-PERSISTENCIA-K4-CONTRATO.md',ROOT/'IS-6-COEXISTENCIA-PERSISTENCIA-K4-REVISAO-B.md']:
        sources[path.relative_to(ROOT).as_posix()]=sha(path)
    assert all(sha(ROOT/p)==seal for p,seal in sources.items())
    folder.mkdir()
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sources:z.write(ROOT/p,p)
    store=storage.Store(folder/'store')
    r=dict(accepted=False,completed=False,source_sha256=sources,roundtrips=[],refusals=[],branches=[],exports=[],
           scope='CPU/file-store only. Real archived models revalidated; native scene, actor/UI restoration, process restart and migration remain separate requirements.')
    def refuse(name,operation):
        before=store.path.read_bytes() if store.path.exists() else None
        try:operation()
        except (ValueError,OSError) as error:r['refusals'].append(dict(name=name,error=str(error)))
        else:raise AssertionError('Invalid store operation accepted: '+name)
        assert (store.path.read_bytes() if store.path.exists() else None)==before
    try:
        for case in a['cases']:
            scientific=case['artifact']
            for spatial in [False,True]:
                for magnetic in [False,True]:
                    visible=dict(spatial=spatial,magnetic=magnetic)
                    saved=store.save(scientific,visible)
                    got,flags,record=store.load();assert got==scientific and flags==visible
                    assert sha(store.path)==saved['sha256'] and record['scientific_sha256']==checkpoint.contract.digest(scientific)
                    r['roundtrips'].append(dict(body=case['body'],visible=visible,sha256=saved['sha256']))
            branch=store.branch(scientific,visible,record_name='Referência '+case['body'])
            child=store.branch(scientific,dict(spatial=False,magnetic=True),record_name='Variação '+case['body'],parent=branch['record']['id'])
            got,flags,record=store.load(child['record']['id']);assert got==scientific and flags==dict(spatial=False,magnetic=True) and record['parent']==branch['record']['id']
            r['branches'] += [branch,child]
            exported=store.export(scientific,flags,parent=record['id']);decoded=json.loads(Path(exported['path']).read_text());assert storage.decode(decoded)==(scientific,flags) and sha(Path(exported['path']))==exported['sha256'];r['exports'].append(exported)
        pristine=store.path.read_bytes();baseline=json.loads(pristine);scientific=a['cases'][0]['artifact'];visible=dict(spatial=True,magnetic=True)
        refuse('invalid-science-preserves-latest',lambda:store.save({**scientific,'kind':'combined_field'},visible))
        refuse('numeric-visibility-preserves-latest',lambda:store.save(scientific,dict(spatial=1,magnetic=True)))
        for bad in ['../latest','..','f'*31,'g'*32,True,0]:
            refuse('branch-id-'+str(bad),lambda bad=bad:store.load(bad))
        for bad in ['', 'x'*81, 'linha\nnova', None]:
            refuse('branch-name-'+str(bad),lambda bad=bad:store.branch(scientific,visible,record_name=bad))
        with patch.object(storage.os,'replace',side_effect=OSError('Injected atomic replacement failure')):
            refuse('atomic-replacement-failure-preserves-latest',lambda:store.save(scientific,dict(spatial=False,magnetic=False)))
        assert not list(store.folder.rglob('*.tmp'))
        for label,mutate in [('schema-bool',lambda v:v.update(schema=True)),('old-kind',lambda v:v.update(kind='spatial_save')),
                             ('wrong-record-hash',lambda v:v.update(record_sha256='0'*64)),('wrong-science',lambda v:v['checkpoint']['scientific'].update(kind='combined_field')),
                             ('extra-metadata',lambda v:v.update(extra=1)),('non-UTC',lambda v:v.update(created_utc='2026-01-01T00:00:00'))]:
            bad=copy.deepcopy(baseline);mutate(bad)
            if label!='wrong-record-hash':bad['record_sha256']=checkpoint.contract.digest({k:v for k,v in bad.items() if k!='record_sha256'})
            store.path.write_text(json.dumps(bad,allow_nan=False),encoding='utf8');refuse('load-'+label,store.load);store.path.write_bytes(pristine)
        for label,text in [('duplicate-key','{"schema":1,'+pristine.decode().lstrip()[1:]),('non-finite','{"invalid":NaN}'),('broken-JSON','{')]:
            store.path.write_text(text,encoding='utf8');refuse('load-'+label,store.load);store.path.write_bytes(pristine)
        for label,mutate in [('resigned-magnetic-norm',lambda v:v['magnetic'].update(field_norm_T=v['magnetic']['field_norm_T']*2)),
                             ('resigned-magnetic-epoch',lambda v:v['magnetic']['epoch'].update(utc='2000-01-01T00:00:00Z')),
                             ('resigned-false-coupling',lambda v:v['admission'].update(physical_coupling=True))]:
            bad=copy.deepcopy(baseline);envelope=bad['checkpoint'];mutate(envelope['scientific'])
            envelope['scientific_sha256']=checkpoint.contract.digest(envelope['scientific'])
            envelope['checkpoint_sha256']=checkpoint.contract.digest({k:v for k,v in envelope.items() if k!='checkpoint_sha256'})
            bad['record_sha256']=checkpoint.contract.digest({k:v for k,v in bad.items() if k!='record_sha256'})
            store.path.write_text(json.dumps(bad,allow_nan=False),encoding='utf8');refuse(label,store.load);store.path.write_bytes(pristine)
        branch_path=Path(r['branches'][0]['path']);branch_bytes=branch_path.read_bytes();wrong=json.loads(branch_bytes);wrong['id']='b'*32
        wrong['record_sha256']=checkpoint.contract.digest({k:v for k,v in wrong.items() if k!='record_sha256'})
        branch_path.write_text(json.dumps(wrong),encoding='utf8');refuse('branch-file-identity-mismatch',lambda:store.load(r['branches'][0]['record']['id']));branch_path.write_bytes(branch_bytes)
        with patch.object(storage,'MAX_BYTES',128):refuse('oversized-record',store.load)
        invalid=store.branches/('a'*32+'.json');invalid.write_text('{',encoding='utf8')
        catalog=store.catalog();assert len([v for v in catalog if v['valid']])==4 and len([v for v in catalog if not v['valid']])==1
        r['catalog']=catalog
        # Validator relocation keeps logical source hashes while reading exactly
        # the same bytecode sources and scientific data in a fresh interpreter.
        relocated=folder/'relocated';relocated.mkdir()
        for source in [Path(checkpoint.__file__),Path(checkpoint.contract.__file__)]:
            target=relocated/source.name;target.write_bytes(source.read_bytes())
        payload=folder/'checkpoint.json';payload.write_text(json.dumps(baseline['checkpoint']),encoding='utf8')
        child_code='import sys,json;sys.path[:0]=[sys.argv[1],sys.argv[2]];import is6_layers_checkpoint_v2 as c;p=json.load(open(sys.argv[3],encoding="utf8"));s,v=c.restore(p);print(json.dumps({"sha256":c.contract.digest(s),"visible":v}))'
        child=subprocess.run([sys.executable,'-Xutf8','-c',child_code,str(relocated),str(APP),str(payload)],capture_output=True,text=True,encoding='utf8',check=True)
        r['relocated_validator']=json.loads(child.stdout);assert r['relocated_validator']['sha256']==baseline['checkpoint']['scientific_sha256']
        old=copy.deepcopy(baseline['checkpoint']);old['generation']['version']='0.1.0';old['checkpoint_sha256']=checkpoint.contract.digest({k:v for k,v in old.items() if k!='checkpoint_sha256'})
        refuse('no-implicit-v1-envelope-migration',lambda:checkpoint.restore(old))
        assert store.path.read_bytes()==pristine and all(sha(ROOT/p)==seal for p,seal in sources.items())
        r.update(accepted=True,completed=True,atomic_failure_preserved_previous_record=True,temporary_files_cleaned=True)
    except Exception:r['failure']=traceback.format_exc()
    out.write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(dict(accepted=r['accepted'],roundtrips=len(r['roundtrips']),refusals=len(r['refusals']),failure=r.get('failure','').splitlines()[-1:])),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
