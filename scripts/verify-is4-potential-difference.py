"""Check the stable four-center potential difference against Decimal60 arithmetic."""
from pathlib import Path
from decimal import Decimal,localcontext
import hashlib
import json
import sys
import traceback
import zipfile
ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/is4-body-particle-staging';APP=ROOT/'output/is3-body-points-product/app'
sys.path[:0]=[str(STAGE),str(APP)]
from is4_body_snapshot import Snapshot
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    folder=ROOT/'output/is4-potential-difference-20261025a';receipt=ROOT/'evidence/is4-potential-difference-20261025a.json'
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve potential evidence.')
    folder.mkdir();fixtures=[ROOT/('output/is4-body-snapshot-20261025b/'+name+'.json') for name in ['IGRF14-13','JRM33-13']]
    files=[*STAGE.glob('*.py'),Path(__file__),*fixtures];hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    report={'schema':1,'accepted':False,'completed':False,'source_sha256':hashes,'cases':[]}
    try:
        for path in fixtures:
            fixture=json.loads(path.read_text(encoding='utf-8'));model=Snapshot(fixture['phase'],fixture['reading']);start=list(model.seed_m)
            for delta in [[0.,0.,0.],[1e-6,0.,0.],[1e-6,-2e-6,3e-6],[50.,-20.,10.]]:
                end=[start[k]+delta[k] for k in range(3)];calls=model.magnetic_evaluations
                actual=model.potential_difference(start,end);opposite=model.potential_difference(end,start)
                with localcontext() as context:
                    context.prec=60;reference=Decimal(0)
                    for source in model.sources:
                        radii=[]
                        for point in [start,end]:
                            r2=sum((Decimal.from_float(point[k])-Decimal.from_float(source.position_model_m[k]))**2 for k in range(3))
                            radii.append(r2.sqrt())
                        reference+=Decimal.from_float(source.GM_m3_s2)*(1/radii[0]-1/radii[1])
                expected=float(reference);error=abs(actual-expected)
                assert error<=1e-12*abs(expected)+1e-13,(path.name,delta,actual,expected)
                assert abs(actual+opposite)<=1e-12*abs(expected)+1e-13
                assert calls==model.magnetic_evaluations
                report['cases'].append({'fixture':path.name,'requested_displacement_m':delta,'actual_difference_J_kg':actual,'Decimal60_difference_J_kg':expected,'absolute_error_J_kg':error})
        assert all(sha(ROOT/name)==value for name,value in hashes.items())
        report.update(accepted=True,completed=True,scope='Stable static monopole potential differences, zero/antisymmetry and no B calls, against Decimal60. Absolute field/trajectory/native acceptance is separate.')
    except Exception:report['failure']=traceback.format_exc()
    receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'accepted':report['accepted'],'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
