"""Real-model K4 CPU round trips and resigned corruption; no native or product save."""
from pathlib import Path
import argparse
import copy
import hashlib
import itertools
import json
import sys
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'output/is6-layers-persistence-staging'),str(ROOT/'output/is6-layers-product0.19.1/app')]
import is6_layers_checkpoint as checkpoint
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    out=ROOT/('evidence/is6-layers-checkpoint-'+args.label+'.json');folder=ROOT/('output/is6-layers-checkpoint-'+args.label)
    if out.exists() or folder.exists():raise FileExistsError('Preserve checkpoint evidence')
    anchor=ROOT/'evidence/is6-layers-native-20261103a.json';a=json.loads(anchor.read_text());assert a['accepted']
    hashes=dict(a['source_sha256'])
    for p in [anchor,Path(__file__),Path(checkpoint.__file__),ROOT/'IS-6-COEXISTENCIA-PERSISTENCIA-K4-CONTRATO.md']:
        hashes[p.relative_to(ROOT).as_posix()]=sha(p)
    assert all(sha(ROOT/p)==seal for p,seal in hashes.items())
    folder.mkdir()
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in hashes:z.write(ROOT/p,p)
    r=dict(accepted=False,completed=False,source_sha256=hashes,roundtrips=[],refusals=[],
           scope='CPU envelope only; actual IGRF/JRM33 and spatial reconstruction. No file-store replacement, native restore, service save, branch, migration, UI or performance acceptance.')
    def resign(value):
        value['checkpoint_sha256']=checkpoint.contract.digest({k:v for k,v in value.items() if k!='checkpoint_sha256'})
        return value
    def refuse(name,value):
        try:checkpoint.restore(value)
        except (ValueError,TypeError) as error:r['refusals'].append(dict(name=name,error=str(error)))
        else:raise AssertionError('Corruption accepted: '+name)
    try:
        for case in a['cases']:
            scientific=case['artifact']
            for spatial,magnetic in itertools.product([False,True],repeat=2):
                visible=dict(spatial=spatial,magnetic=magnetic)
                encoded=checkpoint.create(scientific,visible)
                decoded=json.loads(json.dumps(encoded,allow_nan=False))
                restored,flags=checkpoint.restore(decoded)
                assert restored==scientific and flags==visible
                r['roundtrips'].append(dict(body=case['body'],visible=visible,sha256=encoded['checkpoint_sha256']))
            base=checkpoint.create(scientific,dict(spatial=True,magnetic=True))
            for name,mutate in [
                ('schema-bool',lambda v:v.update(schema=True)),
                ('legacy-kind',lambda v:v.update(kind='spatial_checkpoint')),
                ('extra',lambda v:v.update(extra=1)),
                ('generation',lambda v:v['generation'].update(version='old')),
                ('scientific-digest',lambda v:v.update(scientific_sha256='0'*64)),
                ('visible-number',lambda v:v['visible'].update(magnetic=1)),
                ('visible-missing',lambda v:v['visible'].pop('magnetic')),
                ('scientific-kind',lambda v:v['scientific'].update(kind='coupled_field')),
                ('scientific-schema-bool',lambda v:v['scientific'].update(schema=True)),
                ('magnetic-body',lambda v:v['scientific']['magnetic'].update(body_id='another-body')),
                ('magnetic-epoch',lambda v:v['scientific']['magnetic']['epoch'].update(utc='2000-01-01T00:00:00Z')),
                ('admission-visible',lambda v:v['scientific']['admission']['layers'][0].update(visible=False)),
                ('admission-coupling',lambda v:v['scientific']['admission'].update(physical_coupling=True))]:
                value=copy.deepcopy(base);mutate(value);refuse(case['body']+'-'+name,resign(value))
            refuse(case['body']+'-missing-envelope',scientific)
            value=copy.deepcopy(base);value['checkpoint_sha256']='0'*64;refuse(case['body']+'-bad-checksum',value)
            value=copy.deepcopy(base);value['visible']['spatial']=float('nan');refuse(case['body']+'-NaN',value)
        assert all(sha(ROOT/p)==seal for p,seal in hashes.items())
        r.update(accepted=True,completed=True)
    except Exception:r['failure']=traceback.format_exc()
    out.write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(dict(accepted=r['accepted'],roundtrips=len(r['roundtrips']),refusals=len(r['refusals']),failure=r.get('failure','').splitlines()[-1:])))
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
