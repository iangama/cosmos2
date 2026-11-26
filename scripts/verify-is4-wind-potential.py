"""Paired-coordinate potential changes against independent Decimal80 arithmetic."""
from pathlib import Path
from decimal import Decimal,localcontext
import argparse
import hashlib
import json
import math
import sys
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/is4-solar-wind-staging';APP=ROOT/'output/is4-body-particle-product0.8.1/app'
sys.path[:0]=[str(STAGE),str(APP)]
from is4_wind_field import DEFAULT,AU_M
from is4_wind_snapshot import Snapshot
from is4_wind_diagnostics import potential_differences
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
D=Decimal.from_float

def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);args=p.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):p.error('Invalid label')
    folder=ROOT/('output/is4-wind-potential-'+args.label);receipt=ROOT/('evidence/is4-wind-potential-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve evidence')
    folder.mkdir();fixture=ROOT/'output/is4-body-snapshot-20261025b/IGRF14-13.json';phase=json.loads(fixture.read_text())['phase']
    files=[*STAGE.glob('*.py'),Path(__file__),fixture,ROOT/'IS-4-VENTO-SOLAR-CONTRATO-PREVIO.md'];hashes={f.relative_to(ROOT).as_posix():sha(f) for f in files}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for f in files:z.write(f,f.relative_to(ROOT).as_posix())
    report=dict(schema=1,accepted=False,completed=False,source_sha256=hashes,cases=[])
    try:
        with localcontext() as ctx:
            ctx.prec=80
            for polarity in [1,-1]:
                m=Snapshot(phase,{**DEFAULT,'polarity':polarity})
                for hemisphere in [1,-1]:
                    origin=[.8*AU_M,.2*AU_M,hemisphere*.5*AU_M]
                    for offset in [1e-7,1e-3,1.,1e5,1e9]:
                        left=[offset*2,-offset,.5*offset];right=[-offset,offset*3,-offset*.75]
                        actual=potential_differences(m,origin,left,right)
                        a=[D(o)+D(x) for o,x in zip(origin,left)];b=[D(o)+D(x) for o,x in zip(origin,right)]
                        radius=lambda x:sum(v*v for v in x).sqrt()
                        cfg=m.field.configuration;c=-D(float(polarity))*D(cfg['rotation_rate_rad_s'])*D(cfg['radial_field_at_AU_T'])*D(AU_M)**2
                        electric=c*(abs(b[2])/radius(b)-abs(a[2])/radius(a));gravity=Decimal(0)
                        for s in m.sources:
                            aa=[x-D(y) for x,y in zip(a,s.position_model_m)];bb=[x-D(y) for x,y in zip(b,s.position_model_m)]
                            gravity+=D(s.GM_m3_s2)*(1/radius(aa)-1/radius(bb))
                        expected=[float(electric),float(gravity)];computed=[actual['electric_potential_change_V'],actual['gravity_potential_change_J_kg']]
                        errors=[abs(x-y) for x,y in zip(computed,expected)]
                        assert all(error<=5e-12*abs(value)+1e-18 for error,value in zip(errors,expected)),(polarity,hemisphere,offset,computed,expected)
                        report['cases'].append(dict(polarity=polarity,hemisphere=hemisphere,offset_scale_m=offset,actual=computed,reference=expected,absolute_errors=errors))
        assert all(sha(ROOT/n)==v for n,v in hashes.items())
        report.update(accepted=True,completed=True,scope='Paired coordinate potential changes down to sub-ULP heliocentric displacement; Decimal80 reference, no trajectories or product acceptance.')
    except Exception:report['failure']=traceback.format_exc()
    receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(accepted=report['accepted'],cases=len(report['cases']),failure=report.get('failure'))))
    return 0 if report['accepted'] else 1

if __name__=='__main__':raise SystemExit(main())
