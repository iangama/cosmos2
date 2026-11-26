"""Fix the physical-599 GM source for the reduced candidate, retaining differences."""
from pathlib import Path
from decimal import Decimal
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
receipt = json.loads((ROOT / 'evidence/jupiter-acquisition-20261023.json').read_text())
path = ROOT / receipt['files']['jup365.cmt']['file']
raw = path.read_bytes()
assert hashlib.sha256(raw).hexdigest() == receipt['files']['jup365.cmt']['sha256']
lines = raw.decode('ascii').splitlines()
matches = [(i, line, re.match(r'^\s+Jupiter\s+599\s+(\S+)\s+', line))
           for i, line in enumerate(lines, 1)]
matches = [(i, line, m.group(1)) for i, line, m in matches if m]
assert matches and len({Decimal(value) for _, _, value in matches}) == 1
value = Decimal(matches[0][2])
jup348 = ROOT / receipt['files']['jup348.cmt']['file']
other = []
for i, line in enumerate(jup348.read_text().splitlines(), 1):
    m = re.search(r'\b500GM\s+([\d.E+-]+)', line)
    if m:
        other.append({'line': i, 'raw': line, 'additional_constant_500GM_km3_s2': m.group(1)})
de442 = ROOT / 'data/spice/de442_tech-comments.txt'
de_line = next((i, line) for i, line in enumerate(de442.read_text().splitlines(), 1)
               if re.match(r'^\s+GM5\s+', line))
system_gm = Decimal(de_line[1].split()[-1])
report = {
    'schema': 1, 'naif_id': '599', 'entity_kind': 'physical_body',
    'candidate_parameter': {'GM_m3_s2': float(value * Decimal(10)**9),
                          'GM_m3_s2_decimal': str(value * Decimal(10)**9),
                          'original_km3_s2': matches[0][2], 'uncertainty': None,
                          'uncertainty_reason': 'No standard uncertainty adopted from this printed table.'},
    'source': receipt['files']['jup365.cmt'],
    'matching_source_rows': [{'line': i, 'raw': line} for i, line, _ in matches],
    'comparison_only': {'JUP348_additional_500GM_rows': other,
                        'DE442_system5': {'source': de442.relative_to(ROOT).as_posix(),
                            'sha256': hashlib.sha256(de442.read_bytes()).hexdigest(),
                            'line': de_line[0], 'raw': de_line[1],
                            'system_GM_km3_s2': str(system_gm)},
                        'system5_minus_candidate599_km3_s2': str(system_gm - value)},
    'adoption_scope': 'Physical599 GM from JUP365 paired with inherited 599/5 trajectory, for the declared reduced four-center candidate. Other jovian moons omitted; not a complete JPL dynamical fit.',
    'not_used_in_product_yet': True,
    'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
}
destination = ROOT / 'evidence/jupiter-candidate-gm-20261023.json'
assert not destination.exists()
destination.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'GM_m3_s2_decimal': report['candidate_parameter']['GM_m3_s2_decimal'],
                  'source_rows': len(matches), 'alternative_constant_rows': len(other)}))
