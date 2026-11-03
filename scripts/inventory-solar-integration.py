"""Read-only inventory for the first integrated Sun/Earth/Moon/Jupiter slice."""
from pathlib import Path
import hashlib
import json
import sys
import spiceypy as spice

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
import atlas

atlas.initialize()
epoch = '2026-10-11T12:00:00'
et = spice.str2et(epoch)
inventory = []
for name in atlas.KERNELS:
    path = ROOT / 'data/spice' / name
    record = {'path': 'data/spice/' + name, 'bytes': path.stat().st_size,
              'sha256': hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()}
    if path.suffix == '.bsp':
        records = []
        for target in spice.spkobj(str(path)):
            coverage = spice.spkcov(str(path), int(target))
            records.append({'naif_id': int(target), 'coverage_et_tdb_s':
                            [list(spice.wnfetd(coverage, i)) for i in range(spice.wncard(coverage))]})
        record['targets'] = records
    inventory.append(record)
states = []
for target, label in [('10', 'Sol'), ('399', 'Terra'), ('301', 'Lua'),
                       ('5', 'baricentro do sistema de Jupiter'), ('599', 'centro de Jupiter')]:
    item = {'naif_id': target, 'label': label}
    try:
        state, _ = spice.spkezr(target, et, 'J2000', 'NONE', '0')
        item.update(available=True, position_m=(state[:3] * 1000).tolist(),
                    velocity_m_s=(state[3:] * 1000).tolist())
    except spice.utils.exceptions.SpiceyError as error:
        item.update(available=False, spice_error=str(error))
    states.append(item)
rotation = spice.pxform('IAU_JUPITER', 'J2000', et).tolist()
report = {
    'schema': 1, 'scope': 'IS-1 data inventory only; no API or physical model changed.',
    'epoch_utc': epoch, 'epoch_et_tdb_s': et,
    'frame': 'J2000/ICRF', 'center_naif_id': '0', 'aberration': 'NONE',
    'kernels': inventory, 'queried_states': states,
    'jupiter_general_PCK_orientation_available': True,
    'jupiter_body_to_J2000': rotation,
    'center_and_barycenter_interchangeable': False,
    'all_four_body_centers_available': all(s['available'] for s in states if s['naif_id'] != '5'),
    'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
}
destination = ROOT / 'evidence/solar-integration-kernel-inventory-20261023.json'
assert not destination.exists()
destination.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps({'states': [{k: s[k] for k in ['naif_id', 'available']} for s in states],
                  'all_four_body_centers_available': report['all_four_body_centers_available']}))
