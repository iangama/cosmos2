"""Copy only699 SPK polynomial records; preserve DE442s planetary authority."""
from pathlib import Path
import hashlib
import json
import os

import numpy as np
import spiceypy as spice

ROOT = Path(__file__).resolve().parents[1]
receipt = json.loads((ROOT / 'evidence/saturn-acquisition.json').read_text())
source = ROOT / receipt['files']['sat459.bsp']['file']
assert hashlib.sha256(source.read_bytes()).hexdigest() == receipt['files']['sat459.bsp']['sha256']
spice.furnsh(str(ROOT / 'data/spice/naif0012.tls'))
start, end = (spice.str2et(t) for t in ('1949-12-30T00:00:00', '2051-01-03T00:00:00'))
destination = ROOT / 'data/spice/saturn-center-sat441.bsp'
temporary = ROOT / 'output/saturn-acquisition/saturn-center.tmp.bsp'
if temporary.exists(): temporary.unlink()
input_handle = spice.dafopr(str(source))
output_handle = spice.spkopn(str(temporary), 'COSMOS2_SATURN_699_ONLY', 2048)
segments = []
try:
    spice.dafac(output_handle, ['Cosmos2 subset of official NAIF SAT459, target699 only.',
                              'Original SHA256: '+receipt['files']['sat459.bsp']['sha256'],
                              'Source699: SAT441/SAT441xl; center6; no polynomial refit.',
                              'See evidence/saturn-subset.json and original NAIF comments.'])
    spice.dafbfs(input_handle)
    while spice.daffna():
        summary = spice.dafgs(5)
        dc, ic = spice.dafus(summary, 2, 6)
        if int(ic[0]) != 699 or dc[1] < start or dc[0] > end:
            continue
        assert int(ic[1]) == 6 and int(ic[2]) == 1
        lo, hi = max(float(dc[0]), start), min(float(dc[1]), end)
        ident = spice.dafgn()
        spice.spksub(input_handle, summary, ident, lo, hi, output_handle)
        segments.append({'body': int(ic[0]), 'center': int(ic[1]), 'frame_id': int(ic[2]),
                         'SPK_type': int(ic[3]), 'id': ident, 'source_et': dc.tolist(), 'subset_et': [lo,hi]})
finally:
    spice.dafcls(input_handle)
    spice.spkcls(output_handle)
assert segments
spice.kclear();spice.furnsh(str(source))
epochs = np.linspace(start, end, 201)
original = np.array([spice.spkezr('699', t, 'J2000', 'NONE', '6')[0] for t in epochs])
spice.kclear();spice.furnsh(str(temporary))
copied = np.array([spice.spkezr('699', t, 'J2000', 'NONE', '6')[0] for t in epochs])
error = np.max(np.abs(original-copied), axis=0)
assert np.max(error[:3]) <= 1e-9 and np.max(error[3:]) <= 1e-12
assert list(spice.spkobj(str(temporary))) == [699]
coverage = spice.spkcov(str(temporary), 699)
assert any(spice.wnfetd(coverage,i)[0] <= start and spice.wnfetd(coverage,i)[1] >= end for i in range(spice.wncard(coverage)))
# Adding the production subset must leave all old model states identical.
spice.kclear();spice.furnsh(str(ROOT / 'data/spice/de442s.bsp'))
old = {target: np.array([spice.spkezr(target,t,'J2000','NONE','0')[0] for t in epochs]) for target in ('10','399','301')}
spice.furnsh(str(temporary))
for target, expected in old.items():
    current = np.array([spice.spkezr(target,t,'J2000','NONE','0')[0] for t in epochs])
    assert np.array_equal(current, expected)
spice.kclear()
os.replace(temporary,destination)
report = {'schema':1,'source':receipt['files']['sat459.bsp'],
          'derived_file': destination.relative_to(ROOT).as_posix(), 'bytes':destination.stat().st_size,
          'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),
          'method':'CSPICE spksub, existing polynomial records copied for699 only; no resampling or orbit fit',
          'recipe_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'segments':segments,'time_scale':'ET/TDB, UTC boundaries converted using naif0012',
          'comparison_epochs':len(epochs),'maximum_component_difference_km_kms':error.tolist(),
          'old_planet_states_bit_identical':True,'production_target_ids':[699],
          'sources':['https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/sat459.mrg',
                     'https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spksub_c.html']}
(ROOT / 'evidence/saturn-subset.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('source','segments','sources')},indent=2))
