"""Prepare an isolated four-center SI fixture and explain initial contributions."""
from pathlib import Path
import hashlib
import json
import math
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
import atlas
from atlas_import import gm_data

destination = ROOT / 'output/solar-integration-staging/four-body-initial-si.json'
assert not destination.exists()
source = atlas.states(utc='2026-10-11T12:00:00')
subset_receipt = json.loads((ROOT / 'evidence/jupiter-candidate-subset-20261023.json').read_text())
subset = ROOT / subset_receipt['derived_file']
assert hashlib.sha256(subset.read_bytes()).hexdigest() == subset_receipt['sha256']
gm_receipt = json.loads((ROOT / 'evidence/jupiter-candidate-gm-20261023.json').read_text())
gm = gm_data()
bodies = []
for target, name, key in [('10', 'Sol', 'GMS'), ('399', 'Terra', 'GM3'), ('301', 'Lua', 'GMM')]:
    b = next(b for b in source['bodies'] if b['naif_id'] == target)
    bodies.append({'id': 'sol:naif:' + target, 'naif_id': target, 'name': name,
                   'GM_m3_s2': gm[key]['value'], 'position_m': b['position_m'],
                   'velocity_m_s': b['velocity_m_s'], 'GM_source': gm[key]})
atlas.SPICE.furnsh(str(subset))
try:
    state, _ = atlas.SPICE.spkezr('599', source['epoch']['et_tdb_s'], 'J2000', 'NONE', '0')
finally:
    atlas.SPICE.unload(str(subset))
bodies.append({'id': 'sol:naif:599', 'naif_id': '599', 'name': 'Jupiter',
               'GM_m3_s2': gm_receipt['candidate_parameter']['GM_m3_s2'],
               'position_m': (state[:3] * 1000).tolist(), 'velocity_m_s': (state[3:] * 1000).tolist(),
               'GM_source_receipt': 'evidence/jupiter-candidate-gm-20261023.json'})
for b in bodies:
    terms = []
    for other in bodies:
        if other is b:
            continue
        delta = [other['position_m'][i] - b['position_m'][i] for i in range(3)]
        distance = math.hypot(*delta)
        acceleration = [other['GM_m3_s2'] * value / distance**3 for value in delta]
        terms.append({'source_id': other['id'], 'distance_m': distance,
                      'acceleration_m_s2': acceleration, 'acceleration_norm_m_s2': math.hypot(*acceleration)})
    b['initial_gravitational_contributions'] = terms
    b['initial_acceleration_m_s2'] = [math.fsum(t['acceleration_m_s2'][i] for t in terms) for i in range(3)]
total = math.fsum(b['GM_m3_s2'] for b in bodies)
origin = [math.fsum(b['GM_m3_s2'] * b['position_m'][i] for b in bodies) / total for i in range(3)]
velocity = [math.fsum(b['GM_m3_s2'] * b['velocity_m_s'][i] for b in bodies) / total for i in range(3)]
for b in bodies:
    b['subset_barycentric_position_m'] = [b['position_m'][i] - origin[i] for i in range(3)]
    b['subset_barycentric_velocity_m_s'] = [b['velocity_m_s'][i] - velocity[i] for i in range(3)]
report = {'schema': 1, 'kind': 'candidate_four_body_SI_fixture_not_product_session',
          'epoch': source['epoch'], 'frame': 'J2000/ICRF', 'center_naif_id': '0', 'aberration': 'NONE',
          'model': 'reduced Newtonian point centers; no jovian moons, multipoles, tides, EM or stellar feedback',
          'bodies': bodies, 'subset_barycenter_SSB_position_m': origin,
          'subset_barycenter_SSB_velocity_m_s': velocity, 'provenance': source['provenance'],
          'jupiter_subset_sha256': subset_receipt['sha256'],
          'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'integrated_in_product': False, 'propagation_validated': False}
destination.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')
earth = next(b for b in bodies if b['naif_id'] == '399')
print(json.dumps({'fixture': destination.relative_to(ROOT).as_posix(),
                  'earth_initial_contributions_m_s2': {t['source_id']: t['acceleration_norm_m_s2']
                      for t in earth['initial_gravitational_contributions']}}))
