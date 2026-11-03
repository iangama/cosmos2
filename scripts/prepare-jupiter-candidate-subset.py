"""Extract the original 599/5 records into isolated IS-1 staging, with no refit."""
from pathlib import Path
import hashlib
import json
import numpy as np
import spiceypy as spice

ROOT = Path(__file__).resolve().parents[1]
receipt = json.loads((ROOT / 'evidence/jupiter-acquisition-20261023.json').read_text())
entry = receipt['files']['jup348.bsp']
source = ROOT / entry['file']
assert hashlib.sha256(source.read_bytes()).hexdigest() == entry['sha256']
directory = ROOT / 'output/solar-integration-staging'
directory.mkdir(exist_ok=True)
destination = directory / 'jupiter-center-jup365-from-jup348.bsp'
report_path = ROOT / 'evidence/jupiter-candidate-subset-20261023.json'
assert not destination.exists() and not report_path.exists()
spice.furnsh(str(ROOT / 'data/spice/naif0012.tls'))
start, end = [spice.str2et(t) for t in ['1949-12-30T00:00:00', '2051-01-03T00:00:00']]
input_handle = spice.dafopr(str(source))
output_handle = spice.spkopn(str(destination), 'COSMOS2_CANDIDATE_JUPITER_599_ONLY', 2048)
segments = []
try:
    spice.dafac(output_handle, ['Cosmos2 IS-1 candidate: target599 relative to5 only.',
                              'JUP365 original records included in official JUP348.',
                              'Source SHA256: ' + entry['sha256'],
                              'CSPICE spksub; no resampling or fit. Candidate, not installed.'])
    spice.dafbfs(input_handle)
    while spice.daffna():
        summary = spice.dafgs(5)
        dc, ic = spice.dafus(summary, 2, 6)
        if int(ic[0]) != 599 or dc[1] < start or dc[0] > end:
            continue
        assert int(ic[1]) == 5 and int(ic[2]) == 1
        lo, hi = max(float(dc[0]), start), min(float(dc[1]), end)
        ident = spice.dafgn()
        spice.spksub(input_handle, summary, ident, lo, hi, output_handle)
        segments.append({'body': 599, 'center': 5, 'frame_id': 1, 'SPK_type': int(ic[3]),
                         'segment_id': ident, 'source_et': dc.tolist(), 'subset_et': [lo, hi]})
finally:
    spice.dafcls(input_handle)
    spice.spkcls(output_handle)
assert segments
epochs = np.linspace(start, end, 201)
spice.kclear()
spice.furnsh(str(source))
original = np.array([spice.spkezr('599', t, 'J2000', 'NONE', '5')[0] for t in epochs])
spice.kclear()
spice.furnsh(str(destination))
copied = np.array([spice.spkezr('599', t, 'J2000', 'NONE', '5')[0] for t in epochs])
assert np.array_equal(original, copied)
assert list(spice.spkobj(str(destination))) == [599]
coverage = spice.spkcov(str(destination), 599)
assert any(spice.wnfetd(coverage, i)[0] <= start and spice.wnfetd(coverage, i)[1] >= end
           for i in range(spice.wncard(coverage)))
spice.kclear()
spice.furnsh(str(ROOT / 'data/spice/de442s.bsp'))
old = {target: np.array([spice.spkezr(target, t, 'J2000', 'NONE', '0')[0] for t in epochs])
       for target in ['10', '399', '301', '5']}
spice.furnsh(str(destination))
for target, expected in old.items():
    assert np.array_equal(expected, np.array([spice.spkezr(target, t, 'J2000', 'NONE', '0')[0] for t in epochs]))
center = np.array([spice.spkezr('599', t, 'J2000', 'NONE', '0')[0] for t in epochs])
center_minus_barycenter_m = np.linalg.norm((center[:, :3] - old['5'][:, :3]) * 1000, axis=1)
spice.kclear()
report = {'schema': 1, 'source': entry, 'derived_file': destination.relative_to(ROOT).as_posix(),
          'bytes': destination.stat().st_size, 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
          'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'segments': segments,
          'method': 'CSPICE spksub; original polynomial records, no fit or resampling',
          'comparison_epochs': len(epochs), 'subset_relative_states_bit_identical': True,
          'old_DE442s_states_bit_identical': True, 'only_target_599': True,
          'jupiter_center_barycenter_separation_range_m': [float(center_minus_barycenter_m.min()), float(center_minus_barycenter_m.max())],
          'scope': 'Candidate data preparation only; GM, independent Horizons and application integration still pending.',
          'sources': [entry['url'], 'https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spksub_c.html']}
report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: report[k] for k in ['bytes', 'comparison_epochs', 'subset_relative_states_bit_identical',
                                        'old_DE442s_states_bit_identical', 'jupiter_center_barycenter_separation_range_m']}))
