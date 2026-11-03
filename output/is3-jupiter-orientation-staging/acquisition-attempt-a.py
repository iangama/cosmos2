"""Preserve LASP System III definitions and compare the complete adopted PCK terms."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import re
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'output/is3-jupiter-orientation-staging'
SOURCES={
    'CoOrd_systems12.pdf':'https://lasp.colorado.edu/mop/files/2015/02/CoOrd_systems12.pdf',
    'pck00010.tpc':'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00010.tpc',
}
KEYS=['BODY599_POLE_RA','BODY599_POLE_DEC','BODY599_PM','BODY599_LONG_AXIS',
    'BODY599_NUT_PREC_RA','BODY599_NUT_PREC_DEC','BODY599_NUT_PREC_PM','BODY5_NUT_PREC_ANGLES']


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def values(text,key):
    matches=re.findall(r'(?m)^\s*'+re.escape(key)+r'\s*=\s*\(([^)]*)\)',text)
    if len(matches)!=1:raise ValueError('Expected one assignment: '+key)
    return [float(v.replace('D','E').replace('d','e')) for v in matches[0].split()]


def main():
    receipt=ROOT/'evidence/is3-jupiter-orientation-acquisition-20261023.json'
    if DEST.exists() or receipt.exists():raise FileExistsError('Preserve previous acquisition.')
    DEST.mkdir()
    report={'schema':1,'started_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'files':{},'completed':False,'accepted_for_candidate_data':False,
        'scope':'Documented right-handed System III (1965) convention and exact full Jupiter parameter equality between PCK00010 and local PCK00011; not independent observational accuracy.'}
    def persist():receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    persist()
    for name,url in SOURCES.items():
        with urllib.request.urlopen(url,timeout=30) as response:raw=response.read()
        assert 0<len(raw)<5*1024*1024
        target=DEST/name;target.write_bytes(raw)
        report['files'][name]={'url':url,'bytes':len(raw),'sha256':sha(target)};persist()
    local=ROOT/'data/spice/pck00011.tpc'
    old=(DEST/'pck00010.tpc').read_text(encoding='ascii')
    new=local.read_text(encoding='ascii')
    report['local_PCK00011']={'path':local.relative_to(ROOT).as_posix(),'sha256':sha(local)}
    report['parameter_comparisons']={key:{'PCK00010':values(old,key),'PCK00011':values(new,key),
        'exactly_equal':values(old,key)==values(new,key)} for key in KEYS}
    assert all(v['exactly_equal'] for v in report['parameter_comparisons'].values())
    report['convention_source']={'pages_one_based':[1,2,3,4],
        'convention':'S3RH maps to IAU_JUPITER; east longitude = 360 degrees minus traditional west longitude; X on equatorial prime meridian, Y=Z cross X, Z north spin axis.',
        'model_radius_m':71492000.,'full_nutation_precession_terms_required':True,
        'document_date':'2016-10-20','document_version':12}
    report['completed']=report['accepted_for_candidate_data']=True
    report['script_sha256']=sha(Path(__file__));persist()
    print(json.dumps({'receipt':receipt.relative_to(ROOT).as_posix(),'accepted_for_candidate_data':True,
        'complete_parameter_groups_equal':len(KEYS),'files':report['files']}))


if __name__=='__main__':main()
