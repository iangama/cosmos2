"""Audit preserved Horizons moon vectors at the exact decimal epochs originally sent."""
import argparse
import csv
from decimal import Decimal
import hashlib
import io
import json
import math
from pathlib import Path
import traceback
import spiceypy as spice

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
TARGETS={'501','502','503','504','602','606'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True)
    label=parser.parse_args().label
    if not label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):parser.error('Invalid label')
    source=ROOT/'evidence/is6-principal-moons-horizons-20261111a.json'
    out=ROOT/f'evidence/is6-principal-moons-horizons-{label}.json'
    if out.exists():raise FileExistsError('Preserve prior service agreement receipt')
    previous=json.loads(source.read_text(encoding='utf8'))
    result=dict(accepted=False,completed=False,queries=[],source=source.relative_to(ROOT).as_posix(),
        source_sha256=sha(source),script_sha256=sha(Path(__file__)),
        contract_sha256=sha(ROOT/'IS-6-LUAS-HORIZONS-TEMPO-20261111.md'),
        position_limit_m=1.,velocity_limit_m_s=1e-5,
        timestamp_basis='Exact sent TLIST decimal JD minus J2000, times86400; rounded response epochs retained',
        scope='Numerical agreement with pinned complete kernels; service source labels remain explicit and are not declared identical packages.')
    try:
        assert previous['completed'] and not previous.get('failure')
        assert {q['target'] for q in previous['queries']}==TARGETS and len(previous['queries'])==6
        for q in previous['queries']:
            response_path=ROOT/q['response'];assert sha(response_path)==q['response_sha256']
            kernel=ROOT/q['comparison_kernel']['path']
            with kernel.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==q['comparison_kernel']['sha256']
            params=q['query'];assert params['VEC_CORR']=="'NONE'" and params['OUT_UNITS']=="'KM-S'" and params['REF_SYSTEM']=="'ICRF'"
            text=json.loads(response_path.read_text())['result']
            rows=list(csv.reader(io.StringIO(text.split('$$SOE')[1].split('$$EOE')[0].strip())))
            epochs=params['TLIST'].strip("'").split(',');assert len(rows)==len(epochs)==5
            spice.kclear();spice.furnsh(str(ROOT/'data/spice/naif0012.tls'));spice.furnsh(str(kernel))
            entry=dict(target=q['target'],center=q['center'],local_model=q['local_model'],
                horizons_model=q['horizons_model'],response=q['response'],response_sha256=sha(response_path),
                comparison_kernel=q['comparison_kernel'],cases=[])
            for exact,row in zip(epochs,rows,strict=True):
                et=float((Decimal(exact)-Decimal('2451545.0'))*Decimal(86400))
                printed=spice.unitim(float(row[0]),'JDTDB','ET')
                state,_=spice.spkezr(q['target'],et,'J2000','NONE',q['center'])
                position=math.dist(state[:3],[float(x) for x in row[2:5]])*1000
                velocity=math.dist(state[3:],[float(x) for x in row[5:8]])*1000
                case=dict(requested_jd_tdb=exact,et_tdb_s=et,printed_jd_tdb=row[0],printed_calendar_tdb=row[1],
                    printed_epoch_difference_s=printed-et,position_difference_m=position,velocity_difference_m_s=velocity,
                    passed=position<=1 and velocity<=1e-5)
                entry['cases'].append(case)
            result['queries'].append(entry)
        assert all(c['passed'] for q in result['queries'] for c in q['cases'])
        result.update(accepted=True,completed=True,cases=30,
            maximum_position_difference_m=max(c['position_difference_m'] for q in result['queries'] for c in q['cases']),
            maximum_velocity_difference_m_s=max(c['velocity_difference_m_s'] for q in result['queries'] for c in q['cases']))
    except Exception:result['failure']=traceback.format_exc()
    finally:
        spice.kclear();out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(accepted=result['accepted'],queries=len(result['queries']),failure=result.get('failure'))))
    return 0 if result['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
