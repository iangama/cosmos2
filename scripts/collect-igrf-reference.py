"""Deterministic fixtures from original BGS Fortran; run under Linux after build."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parents[1]
cases=[]
positions=[(-90,0),(-23.55,-46.63),(0,180),(67,120),(90,-180)]
for year in [1900,1945,1994.999,1995,1997.5,2000,2020,2025,2026.75,2030]:
    for (lat,lon),alt in zip(positions,[0,1,500,1000,42]):
        cases.append(dict(year=year,latitude_deg=lat,longitude_deg=lon,altitude_km=alt,itype=1,isv=0))
for lat,lon in [(-90,0),(0,0),(90,120),(45,-30)]:
    cases.append(dict(year=2026,latitude_deg=lat,longitude_deg=lon,radius_km=6371.2,itype=2,isv=0))
for year in [1900,1997.5,2026,2030]:
    cases.append(dict(year=year,latitude_deg=-23.55,longitude_deg=-46.63,altitude_km=300,itype=1,isv=1))
source=ROOT/'.upstream/igrf14/igrf14.f';exe=ROOT/'.tooling/fortran/igrf-reference'
lines=''.join(f"{c['isv']} {c['year']} {c['itype']} {c.get('altitude_km',c.get('radius_km'))} {90-c['latitude_deg']} {c['longitude_deg']%360}\n" for c in cases)
result=subprocess.run([str(exe)],input=lines,text=True,capture_output=True,check=True)
rows=result.stdout.strip().splitlines()
if len(rows)!=len(cases):raise RuntimeError('Unexpected reference warnings/row count: '+result.stdout)
for case,row in zip(cases,rows):
    values=[float(value) for value in row.split()]
    if len(values)!=4:raise RuntimeError(row)
    case['reference_ned_nT']=values[:3]
report={'reference':'Original BGS igrf14syn Fortran, local GNU13.3 build, unmodified routine',
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),
        'coefficient_sha256':hashlib.sha256((ROOT/'data/science/igrf14coeffs.txt').read_bytes()).hexdigest(),
        'cases':cases,'scope':'Reference fixtures, not measured Earth field; geodetic BGS uses rounded WGS84 constants, geocentric tests avoid that difference'}
output=ROOT/'evidence/igrf-reference.json'
output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'cases':len(cases),'fixture_sha256':hashlib.sha256(output.read_bytes()).hexdigest()}))
