"""Two-body, two-epoch geometric ICRF Horizons fixtures; retain full responses."""
from pathlib import Path
import csv
import datetime
import hashlib
import io
import json
import sys
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
import atlas
atlas.states(utc='2000-01-01T12:00:00')
epochs=['2000-01-01T12:00:00','2026-10-11T12:00:00']
jds=[float(atlas.SPICE.unitim(atlas.states(utc=utc)['epoch']['et_tdb_s'],'ET','JDTDB')) for utc in epochs]
records=[]
for target in ('399','301'):
    params={'format':'json','COMMAND':"'"+target+"'",'OBJ_DATA':"'YES'",'MAKE_EPHEM':"'YES'",'EPHEM_TYPE':"'VECTORS'",
            'CENTER':"'500@0'",'REF_PLANE':"'FRAME'",'REF_SYSTEM':"'ICRF'",'VEC_CORR':"'NONE'",'OUT_UNITS':"'KM-S'",
            'VEC_TABLE':"'2'",'CSV_FORMAT':"'YES'",'TIME_TYPE':"'TDB'",'TIME_DIGITS':"'FRACSEC'",
            'TLIST_TYPE':"'JD'",'TLIST':"'"+','.join(f'{jd:.16f}' for jd in jds)+"'"}
    url='https://ssd.jpl.nasa.gov/api/horizons.api?'+urllib.parse.urlencode(params)
    with urllib.request.urlopen(url,timeout=45) as response:raw=response.read()
    value=json.loads(raw)
    if value.get('error'):raise RuntimeError(value['error'])
    text=value['result'];rows=list(csv.reader(io.StringIO(text.split('$$SOE')[1].split('$$EOE')[0].strip())))
    if len(rows)!=len(epochs):raise RuntimeError(text)
    path=ROOT/'evidence'/('horizons-atlas-'+target+'.json');path.write_bytes(raw)
    cases=[]
    for utc,row in zip(epochs,rows):
        cases.append({'input_utc':utc,'jd_tdb':float(row[0]),'position_km':[float(x) for x in row[2:5]],'velocity_km_s':[float(x) for x in row[5:8]]})
    records.append({'target_naif_id':target,'query':params,'url':url,'response_file':str(path.relative_to(ROOT)).replace('\\','/'),
                    'response_sha256':hashlib.sha256(raw).hexdigest(),'header':text.split('$$SOE')[0],'cases':cases})
fixture={'acquired_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'queries':records,
         'scope':'JPL Horizons geometric ICRF SSB fixture; model name retained in response/header; distinct from observational accuracy.'}
(ROOT/'evidence/atlas-horizons-reference.json').write_text(json.dumps(fixture,indent=2)+'\n')
print(json.dumps({'queries':len(records),'cases':sum(len(r['cases']) for r in records)},indent=2))
