"""Five independent Horizons queries for 599 relative to 5; no product changes."""
from pathlib import Path
import csv
import datetime
import hashlib
import io
import json
import math
import urllib.parse
import urllib.request
import spiceypy as spice

ROOT = Path(__file__).resolve().parents[1]
destination = ROOT / 'evidence/jupiter-candidate-reference-20261023.json'
raw_path = ROOT / 'evidence/horizons-jupiter599-relative5-20261023.json'
assert not destination.exists() and not raw_path.exists()
# Fixed before acquiring the comparison; mismatches must remain failures.
position_limit_m, velocity_limit_m_s = 1.0, 1e-5
receipt = json.loads((ROOT / 'evidence/jupiter-candidate-subset-20261023.json').read_text())
subset = ROOT / receipt['derived_file']
assert hashlib.sha256(subset.read_bytes()).hexdigest() == receipt['sha256']
spice.furnsh(str(ROOT / 'data/spice/naif0012.tls'))
spice.furnsh(str(subset))
epochs = ['1950-01-01T00:00:00', '2000-01-01T12:00:00', '2026-10-11T12:00:00',
          '2030-06-15T18:30:00', '2050-12-31T23:59:59']
jds = [spice.unitim(spice.str2et(t), 'ET', 'JDTDB') for t in epochs]
params = {'format': 'json', 'COMMAND': "'599'", 'OBJ_DATA': "'YES'", 'MAKE_EPHEM': "'YES'",
          'EPHEM_TYPE': "'VECTORS'", 'CENTER': "'500@5'", 'REF_PLANE': "'FRAME'",
          'REF_SYSTEM': "'ICRF'", 'VEC_CORR': "'NONE'", 'OUT_UNITS': "'KM-S'",
          'VEC_TABLE': "'2'", 'CSV_FORMAT': "'YES'", 'TIME_TYPE': "'TDB'",
          'TIME_DIGITS': "'FRACSEC'", 'TLIST_TYPE': "'JD'",
          'TLIST': "'" + ','.join(f'{jd:.16f}' for jd in jds) + "'"}
url = 'https://ssd.jpl.nasa.gov/api/horizons.api?' + urllib.parse.urlencode(params)
with urllib.request.urlopen(url, timeout=45) as response:
    raw = response.read()
raw_path.write_bytes(raw)
value = json.loads(raw)
if value.get('error'):
    raise RuntimeError(value['error'])
text = value['result']
rows = list(csv.reader(io.StringIO(text.split('$$SOE')[1].split('$$EOE')[0].strip())))
assert len(rows) == len(epochs)
checks = []
for utc, row in zip(epochs, rows):
    et = spice.unitim(float(row[0]), 'JDTDB', 'ET')
    expected_p, expected_v = [float(x) for x in row[2:5]], [float(x) for x in row[5:8]]
    actual, _ = spice.spkezr('599', et, 'J2000', 'NONE', '5')
    pe = math.dist(actual[:3], expected_p) * 1000
    ve = math.dist(actual[3:], expected_v) * 1000
    checks.append({'input_utc': utc, 'jd_tdb': float(row[0]), 'position_difference_m': pe,
                   'velocity_difference_m_s': ve, 'passed': pe <= position_limit_m and ve <= velocity_limit_m_s})
report = {'schema': 1, 'acquired_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'query': params, 'url': url, 'header': text.split('$$SOE')[0],
          'raw_response': raw_path.relative_to(ROOT).as_posix(), 'response_sha256': hashlib.sha256(raw).hexdigest(),
          'candidate_sha256': receipt['sha256'], 'cases': checks,
          'position_limit_m': position_limit_m, 'velocity_limit_m_s': velocity_limit_m_s,
          'accepted': all(c['passed'] for c in checks),
          'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'scope': 'Independent service/pipeline comparison of 599/5; same ephemeris family may underlie both. Not observational accuracy or full four-body acceptance.'}
destination.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'accepted': report['accepted'], 'cases': checks}), flush=True)
raise SystemExit(0 if report['accepted'] else 1)
