"""Passive solar-zone binding, SI coordinates and stale/corrupt source refusals."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import sys
import traceback
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/is5-solar-core-staging';APP=ROOT/'output/is4-solar-wind-product0.9.1/app'
sys.path[:0]=[str(STAGE),str(APP)]
from is5_solar_source import bind,validate,digest
import atlas
from is5_core import integrate_zone,DEFAULT_PARAMETERS
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/('output/is5-solar-source-'+args.label);path=ROOT/('evidence/is5-solar-source-'+args.label+'.json')
    if folder.exists() or path.exists():raise FileExistsError('Preserve binding evidence')
    folder.mkdir();fixture=ROOT/'output/is4-body-snapshot-20261025b/IGRF14-13.json';phase=json.loads(fixture.read_text())['phase'];before=copy.deepcopy(phase)
    files=[*STAGE.glob('*.py'),APP/'atlas.py',APP/'physics.py',fixture,Path(__file__),ROOT/'IS-5-NUCLEO-SOLAR-CONTRATO-PREVIO.md'];hashes={f.relative_to(ROOT).as_posix():sha(f) for f in files}
    with zipfile.ZipFile(folder/'executed-sources-and-fixture.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(schema=1,accepted=False,completed=False,source_sha256=hashes,refusals=0)
    try:
        source=bind(phase);assert validate(phase,source)==source and phase==before
        sun=next(b for b in phase['bodies'] if b['reference_id']=='sol:naif:10');scale=phase['physical_scale']
        assert source['GM_m3_s2']==sun['mass']*scale['nominal_GM_unit_m3_s2'] and source['center_inertial_m']==[v*scale['length_unit_m'] for v in sun['position']]
        assert source['velocity_inertial_m_s']==[v*scale['velocity_unit_m_s'] for v in sun['velocity']]
        with atlas.LOCK:
            atlas.initialize();spice=atlas.SPICE;et=spice.str2et(source['epoch']['utc']);matrix=spice.pxform('J2000','GALACTIC',et)
        assert abs(et-source['epoch']['et_tdb_s'])<=1e-6
        assert np.allclose(source['center_render_m'],matrix@source['center_inertial_m'],rtol=1e-14,atol=1e-5)
        output=integrate_zone({**DEFAULT_PARAMETERS,'duration_s':1.});assert phase==before and bind(phase)==source
        assert output['parameters']['duration_s']==1. and source['scene_phase']['time']==0.
        for key,value in [('paused',False),('time',True),('revision',True),('edit_token','bad'),('fixture_sha256','bad'),('physical_scale',{}),('bodies',phase['bodies'][:-1])]:
            bad={**copy.deepcopy(phase),key:value};prior=copy.deepcopy(bad)
            try:bind(bad)
            except ValueError:r['refusals']+=1
            else:raise AssertionError(key)
            assert bad==prior
        for key in ['time','revision','body_id','GM_m3_s2','center_inertial_m','epoch','binding_sha256']:
            bad=copy.deepcopy(source)
            if key in ['time','revision']:bad['scene_phase'][key]+=1
            elif key=='body_id':bad[key]='other'
            elif key=='GM_m3_s2':bad[key]*=2
            elif key=='center_inertial_m':bad[key][0]+=1
            elif key=='epoch':bad[key]['et_tdb_s']+=1
            else:bad[key]='0'*64
            try:validate(phase,bad)
            except ValueError:r['refusals']+=1
            else:raise AssertionError(key)
        bad=copy.deepcopy(phase);bad['atlas_initial']['source']['epoch']['utc']='2020-01-01T00:00:00.000Z'
        try:bind(bad)
        except ValueError:r['refusals']+=1
        else:raise AssertionError('Contradictory UTC/TDB accepted')
        assert phase==before and all(sha(ROOT/n)==v for n,v in hashes.items())
        r.update(accepted=True,completed=True,source=source,independent_nuclear_duration_s=1.,scope='Passive four-center Sun association, SI frame/GM/epoch, immutable source and corrupt/stale binding refusals only; no hydrostatic/interior gravity, worker, UI or luminosity acceptance.')
    except Exception:r['failure']=traceback.format_exc()
    path.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');print(json.dumps(dict(accepted=r['accepted'],refusals=r['refusals'],failure=r.get('failure'))));return 0 if r['accepted'] else 1

if __name__=='__main__':raise SystemExit(main())
