"""Pin a dated, proportional EOP-based Earth PCK without changing the product."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import re
import sys
import traceback
import urllib.error
import urllib.request
import spiceypy as spice
from spiceypy.utils.support_types import SPICEINT_CELL

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'output/is3-earth-orientation-staging'
NAME='earth_000101_270118_261022'
BASE='https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/'


def main():
    receipt=ROOT/'evidence/is3-earth-orientation-acquisition-20261023.json'
    if DEST.exists() or receipt.exists():raise FileExistsError('Preserve prior acquisition.')
    DEST.mkdir()
    report={'schema':1,'started_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
            'files':{},'completed':False,'accepted_for_data':False,
            'scope':'Pinned candidate orientation data only; no product/IGRF integration acceptance.'}
    def persist():receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    persist()
    try:
        for name in [NAME+'.cmt','aareadme.txt',NAME+'.bpc']:
            url=BASE+name;partial=DEST/(name+'.partial');digest=hashlib.sha256();md5=hashlib.md5();size=0
            with urllib.request.urlopen(url,timeout=45) as response,partial.open('xb') as output:
                headers=dict(response.headers)
                while True:
                    chunk=response.read(1024*1024)
                    if not chunk:break
                    output.write(chunk);digest.update(chunk);md5.update(chunk);size+=len(chunk)
            if headers.get('Content-Length'):assert size==int(headers['Content-Length'])
            partial.rename(DEST/name)
            report['files'][name]={'url':url,'bytes':size,'sha256':digest.hexdigest(),'md5':md5.hexdigest(),
                                  'Last-Modified':headers.get('Last-Modified'),'ETag':headers.get('ETag')}
            persist()
        kernel=DEST/(NAME+'.bpc')
        assert kernel.read_bytes()[:8]==b'DAF/PCK '
        assert 4*1024**2<kernel.stat().st_size<8*1024**2
        alias_digest=hashlib.sha256();alias_bytes=0
        with urllib.request.urlopen(BASE+'earth_latest_high_prec.bpc',timeout=45) as response:
            while True:
                chunk=response.read(1024*1024)
                if not chunk:break
                alias_digest.update(chunk);alias_bytes+=len(chunk)
        assert alias_digest.hexdigest()==report['files'][NAME+'.bpc']['sha256']
        report['official_alias_comparison']={'url':BASE+'earth_latest_high_prec.bpc',
            'bytes':alias_bytes,'sha256':alias_digest.hexdigest(),'identical_to_dated_file':True}
        checksum_url=BASE+'aa_checksums.txt'
        try:
            with urllib.request.urlopen(checksum_url,timeout=15) as response:raw=response.read()
            (DEST/'aa_checksums.txt').write_bytes(raw)
            pairs=[line.split() for line in raw.decode('ascii').splitlines() if len(line.split())>=2]
            found=next((row[0] for row in pairs if row[-1].split('/')[-1]==NAME+'.bpc'),None)
            if found is not None:assert found.lower()==report['files'][NAME+'.bpc']['md5']
            report['provider_checksum']={'url':checksum_url,'available_for_dated_file':found is not None,
                                         'md5':found,'sha256_of_listing':hashlib.sha256(raw).hexdigest()}
        except (urllib.error.HTTPError,urllib.error.URLError) as error:
            report['provider_checksum']={'url':checksum_url,'available_for_dated_file':False,'reason':str(error),
                'note':'Own SHA256 and dated/official-alias identity are recorded; no published checksum is invented.'}
        lsk=ROOT/'data/spice/naif0012.tls';spice.furnsh(str(lsk))
        ids=SPICEINT_CELL(10);spice.pckfrm(str(kernel),ids);assert list(ids)==[3000]
        coverage=spice.pckcov(str(kernel),3000)
        segments=[list(spice.wnfetd(coverage,i)) for i in range(spice.wncard(coverage))]
        comments=(DEST/(NAME+'.cmt')).read_text(encoding='ascii')
        match=re.search(r'UTC Epoch of last datum:\s*([^\n]+)',comments);assert match
        datum=match.group(1).strip();datum_et=float(spice.str2et(datum))
        et=float(spice.str2et('2026-10-11T12:00:00'))
        assert any(a<=et and b>=et+30*86400 for a,b in segments)
        report['coverage']={'frame':'ITRF93','frame_id':3000,'intervals_et_tdb_s':segments,
            'intervals_utc':[[spice.et2utc(x,'ISOC',6)+'Z' for x in row] for row in segments],
            'last_datum_utc':spice.et2utc(datum_et,'ISOC',6)+'Z','last_datum_et_tdb_s':datum_et,
            'after_last_datum_is_prediction':True}
        report['lsk_sha256']=hashlib.sha256(lsk.read_bytes()).hexdigest()
        report['contract_sha256']=hashlib.sha256((ROOT/'IS-3-IGRF-CONTRATO.md').read_bytes()).hexdigest()
        report['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        spice.unload(str(lsk))
        report['completed']=report['accepted_for_data']=True
    except Exception:report['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps(report,ensure_ascii=False))
    return 0 if report['accepted_for_data'] else 1

if __name__=='__main__':raise SystemExit(main())
