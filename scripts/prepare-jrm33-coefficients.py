"""Parse the original PDS model and cross-check PSH's explicit raw coefficients."""
from pathlib import Path
import hashlib
import json
import math
import re

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'output/is3-jrm33-staging'

def main():
    target=FOLDER/'jrm33-coefficients.json';receipt=ROOT/'evidence/is3-jrm33-coefficients-20261023.json'
    if target.exists() or receipt.exists():raise FileExistsError('Preserve coefficients and provenance.')
    source=FOLDER/'pds-cache/JRM33.MOD';raw=source.read_bytes()
    sha=hashlib.sha256(raw).hexdigest();assert sha=='1960a025ea38d8ee604fb69882b95484df55c31c2e5ba3d1c1ebd011af7170be'
    lines=raw.decode('ascii').splitlines();assert lines[0].split()[:2]==['30','1']
    rows=[]
    pattern=re.compile(r'^\s*(\d+)\s+([-+.\deE]+)\s+\(([-+.\deE]+)\)\s+([gGhH])(.{2})(.{2})(?:\s+(.*))?$')
    for line in lines[1:]:
        m=pattern.fullmatch(line.rstrip());assert m,line
        index,value,resolution,kind,n,order,amplitude=m.groups()
        value=float(value);resolution=float(resolution);n=int(n);order=int(order)
        assert int(index)==len(rows)+1 and all(math.isfinite(v) for v in [value,resolution])
        assert 1<=n<=(30 if kind.islower() else 1) and 0<=order<=n and (kind.lower()!='h' or order>0)
        rows.append({'kind':kind,'n':n,'m':order,'value_nT':value,'resolution_diagonal':resolution,
                     'normalized_Lowes_amplitude':float(amplitude) if amplitude else None})
    internal=[r for r in rows if r['kind'].islower()];external=[r for r in rows if r['kind'].isupper()]
    assert len(internal)==960 and len(external)==3 and len({(r['kind'],r['n'],r['m']) for r in rows})==963
    mapping={(r['kind'],r['n'],r['m']):r['value_nT'] for r in internal}
    checks={}
    for degree in [13,18]:
        path=FOLDER/('upstream-PSH/Jupiter/Python/jovian_jrm33_order'+str(degree)+'_internal_rtp.py')
        entries=re.findall(r'([gh])\[\s*(\d+),\s*(\d+)\]\s*=\s*([-+]?\d+(?:\.\d+)?)',path.read_text())
        table={(kind,int(n),int(m)):float(value) for kind,n,m,value in entries}
        expected={key:value for key,value in mapping.items() if key[1]<=degree}
        assert table==expected and len(table)==degree*(degree+2)
        checks[str(degree)]={'raw_coefficients_bit_equal':len(table),'PSH_source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    result={'schema':1,'model':'JRM33','source_url':'https://pds-ppi.igpp.ucla.edu/data/JNO-J-3-FGM-CAL-V1.0/DATA/MODEL/JRM33.MOD',
        'source_sha256':sha,'reference_radius_m':71492000.,'coordinate_frame':'right_handed_System_III_1965',
        'longitude':'east','normalization':'Schmidt semi-normalized without Condon-Shortley phase',
        'coefficient_unit':'nT','coefficient_epoch_decimal_year':2019.,'secular_variation_adopted':False,
        'source_header':lines[0],'internal_coefficients':internal,'separate_external_coefficients':external}
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    report={'schema':1,'accepted_for_candidate_data':True,'source_sha256':sha,'internal_count':960,'external_count':3,
        'PSH_crosschecks':checks,'derived_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'scope':'Exact parsed coefficients and community-source cross-checks; no field computation or scene acceptance.'}
    receipt.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
