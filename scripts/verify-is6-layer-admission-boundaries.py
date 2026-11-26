"""Complement K0 with valid cross-body pairs and non-finite input refusals."""
from pathlib import Path
import copy
import hashlib
import json
import math
import sys
import traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'output/is6-layer-coordination-staging'),str(ROOT/'output/is6-spatial-product0.18.5/app')]
import is6_layer_contract as c
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out=ROOT/'evidence/is6-layer-admission-boundaries-20261102a.json'
    if out.exists():raise FileExistsError('Preserve boundary evidence')
    anchor=ROOT/'evidence/is6-layer-admission-20261102a.json';a=json.loads(anchor.read_text())
    assert a['accepted'] and a['completed']
    hashes=dict(a['source_sha256'])
    for p in [Path(__file__),anchor]:hashes[p.relative_to(ROOT).as_posix()]=sha(p)
    assert all(sha(ROOT/n)==v for n,v in hashes.items())
    r=dict(accepted=False,completed=False,source_sha256=hashes,refusals=[],native_coexistence_confirmed=False,scope='Additional K0 cross-body and non-finite CPU refusal audit only.')
    def persist():out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    def refuse(name,phase,payload,reading,visible):
        before=json.dumps([phase,payload,reading,visible],sort_keys=True,allow_nan=True)
        try:c.compose(phase,payload,reading,visible)
        except ValueError as error:r['refusals'].append(dict(case=name,error=str(error)))
        else:raise AssertionError('Invalid pair admitted: '+name)
        assert json.dumps([phase,payload,reading,visible],sort_keys=True,allow_nan=True)==before
    persist()
    try:
        phase=json.loads((ROOT/'output/is6-spatial-profile-20261102c/artifact-1.json').read_text())['phase'];items={}
        for target in ['399','599']:
            body=next(b for b in phase['bodies'] if b['reference_id']=='sol:naif:'+target)
            run=c.artifact.Run.create(phase,dict(body_id=body['id'],source_guard=c.artifact.body.guard(phase)),c.artifact.DEFAULT_CONFIGURATION)
            reading=c.earth_magnetism.read(phase,body['id'],-23.55,-46.63,1000.) if target=='399' else c.jupiter_magnetism.read(phase,body['id'],1.5*71492000.,0.,0.,13)
            items[target]=(run.payload,reading)
        visible=dict(spatial=True,magnetic=True)
        for target,other in [('399','599'),('599','399')]:
            payload,reading=items[target];refuse(target+'_valid_other_body',phase,payload,items[other][1],visible)
            assert 'same body' in r['refusals'][-1]['error']
            for label,value in [('nan',math.nan),('positive_infinity',math.inf),('negative_infinity',-math.inf)]:
                bad=copy.deepcopy(reading);bad['coordinates'][next(iter(bad['coordinates']))]=value
                refuse(target+'_coordinate_'+label,phase,payload,bad,visible)
                bad=copy.deepcopy(reading);bad['field_render_T'][0]=value
                refuse(target+'_field_'+label,phase,payload,bad,visible)
                bad_phase=copy.deepcopy(phase);bad_phase['time']=value
                refuse(target+'_phase_'+label,bad_phase,payload,reading,visible)
        assert all(sha(ROOT/n)==v for n,v in hashes.items())
        r.update(accepted=True,completed=True)
    except Exception:r['failure']=traceback.format_exc()
    persist();print(json.dumps(dict(accepted=r['accepted'],refusals=len(r['refusals']),failure=r.get('failure','').splitlines()[-1:])))
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
