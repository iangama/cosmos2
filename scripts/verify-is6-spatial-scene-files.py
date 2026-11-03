"""Independently parse all static wire vertices, topology and float32 conversion."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import re
import sys
import traceback
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/is6-spatial-scene-staging'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/f'output/is6-spatial-scene-files-{args.label}';receipt=ROOT/f'evidence/is6-spatial-scene-files-{args.label}.json'
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve static scene evidence')
    anchor=ROOT/'evidence/is6-spatial-artifact-20261101a.json';accepted=json.loads(anchor.read_text());assert accepted['accepted']
    files=[Path(__file__),STAGE/'is6_spatial_scene.py',ROOT/'IS-6-CENA-PROTOTIPO-CONTRATO.md',anchor,
           ROOT/'.upstream/openspace/modules/space/rendering/renderableconstellationlines.cpp',
           ROOT/'.upstream/openspace/modules/space/rendering/renderableconstellationlines.h',
           ROOT/'evidence/built-runtime-is4-stream.json']
    hashes=dict(accepted['source_sha256']);hashes.update({p.relative_to(ROOT).as_posix():sha(p) for p in files})
    assert all(sha(ROOT/n)==v for n,v in hashes.items());folder.mkdir();archive=folder/'executed-sources.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=hashes,archive_sha256=sha(archive),cases=[],
           limit_before_execution=dict(predicted_float32_vector_error_normalized=2e-6),
           scope='Static normalized SPECK topology and predicted quantization only; not native/GPU readback/visual/UI/performance acceptance.')
    def persist():receipt.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    persist()
    try:
        sys.path.insert(0,str(STAGE));import is6_spatial_scene as scene
        generation=scene.generation();r['generation']=generation
        fixture=json.loads((ROOT/'output/is6-body-fixtures-20261101a/fixtures-before-execution.json').read_text())
        phase=fixture['phases'][0];before=copy.deepcopy(phase)
        for body in phase['bodies']:
            for nr in [65,257]:
                config={**copy.deepcopy(scene.artifact.DEFAULT_CONFIGURATION),'radial_count':nr}
                run=scene.artifact.Run.create(phase,dict(body_id=body['id'],source_guard=scene.artifact.body.guard(phase)),config)
                payload=run.payload;held=scene.artifact.digest(payload)
                target=folder/(body['reference_id'].split(':')[-1]+'-'+str(nr));record=scene.prepare(run,target)
                rows=(target/'wire.speck').read_text().splitlines();parsed=[];cursor=0
                while cursor<len(rows):
                    header=re.fullmatch(r'mesh -c ([12]) \{',rows[cursor]);assert header
                    identifier=rows[cursor+1].removeprefix('id ');count=int(rows[cursor+2]);assert count>0
                    points=np.array([[float(v) for v in line.split()] for line in rows[cursor+3:cursor+3+count]])
                    assert points.shape==(count,3) and np.isfinite(points).all() and rows[cursor+3+count]=='}'
                    parsed.append((identifier,int(header.group(1)),points));cursor+=count+4
                geometry=np.array(payload['mesh']['display_vertices_relative_m']).reshape(nr,97,3)
                unit=payload['binding']['source_configuration']['material_radius_m'];normalized=geometry/unit
                references=[('ring_'+str(i),1,normalized[i]) for i in range(nr)]
                references += [('meridian_'+str(j),2,normalized[:,:96,:].transpose(1,0,2)[j]) for j in range(96)]
                assert len(parsed)==nr+96==record['line_count']
                error=0.;vertices=0
                for actual,expected in zip(parsed,references):
                    assert actual[:2]==expected[:2] and np.array_equal(actual[2],expected[2])
                    if actual[1]==1:assert np.array_equal(actual[2][0],actual[2][-1])
                    error=max(error,float(np.linalg.norm(actual[2].astype(np.float32).astype(np.float64)-expected[2],axis=1).max()))
                    vertices+=len(actual[2])
                assert error<=2e-6 and abs(error-record['maximum_predicted_float32_error_normalized'])<=1e-20
                assert vertices==record['vertex_instances'] and sha(target/'wire.speck')==record['wire_sha256']
                assert (target/'wire.names').read_text().splitlines()==[x[0]+' '+x[0] for x in parsed]
                assert scene.artifact.digest(run.payload)==held and phase==before
                r['cases'].append(dict(body=body['reference_id'],radial_count=nr,lines=len(parsed),vertex_instances=vertices,
                    maximum_predicted_float32_error_normalized=error,maximum_predicted_float32_error_m=error*unit,
                    folder=target.relative_to(ROOT).as_posix(),binding_sha256=sha(target/'binding.json')))
                persist();print(json.dumps(r['cases'][-1]),flush=True)
        assert scene.generation()==generation and all(sha(ROOT/n)==v for n,v in hashes.items())
        r.update(accepted=True,completed=True)
    except Exception:r['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps(dict(accepted=r['accepted'],cases=len(r['cases']),failure=r.get('failure'))),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
