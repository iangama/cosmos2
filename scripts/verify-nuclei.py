"""Independent table/token checks, binding identities, extract and persistence."""
from decimal import Decimal
from pathlib import Path
import copy
import hashlib
import json
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from nuclei import DATA, EXPECTED_SHA256, GENERATION, catalog, parse_table, export, export_file, save, load, digest

data = catalog()
records = data['records']
index = {(r['Z'], r['A']): r for r in records}
assert len(records) == len(index) == 3558
assert all(r['N'] + r['Z'] == r['A'] for r in records)
assert hashlib.sha256(DATA.read_bytes()).hexdigest() == EXPECTED_SHA256

# Read the whole original independently by whitespace and B- delimiter,
# rather than reuse the published column slices used by the implementation.
original = DATA.read_text(encoding='ascii').splitlines()
def decimal(token):
    return None if token in ('', '*') else Decimal(token.replace('#', '.'))
numeric = re.compile(r'[+-]?\d+(?:[.#]\d*)?\Z')
flags = missing = fields = 0
for r in records:
    row = original[r['source_line'] - 1]
    before, after = row[1:].split('B-')
    tokens = before.split()
    assert [int(x) for x in tokens[:4]] == [r['N'] - r['Z'], r['N'], r['Z'], r['A']]
    values = [t for t in tokens[5:] if numeric.fullmatch(t) or t == '*']
    assert len(values) == 4
    tail = after.split()
    atomic_integer, atomic, atomic_sigma = tail[-3:]
    beta = tail[:-3]
    assert len(beta) in (1, 2)
    expected = {
        'mass_excess': values[:2], 'binding_per_nucleon': values[2:],
        'beta_minus_energy': [beta[0], beta[1] if len(beta) == 2 else ''],
        'atomic_mass': [atomic, atomic_sigma],
    }
    for name, (value, sigma) in expected.items():
        q = r['quantities'][name]
        assert q['raw_value'] == value and q['raw_uncertainty'] == sigma
        v, s = decimal(value), decimal(sigma)
        if name == 'atomic_mass':
            v = Decimal(atomic_integer) + v / Decimal(1000000)
            s /= Decimal(1000000)
        assert q['value'] == (None if v is None else float(v))
        assert q['uncertainty'] == (None if s is None else float(s))
        assert q['estimated'] == ('#' in value)
        assert q['uncertainty_estimated'] == ('#' in sigma)
        flags += q['estimated']
        missing += q['value'] is None
        fields += 1
assert missing == 295
assert data['coverage']['estimated_binding_states'] == 1008

# Fixed checks are copied from the original table; no runtime oracle.
anchors = {(0, 1): ('1.00866491590', '8071.31806', '0.0'),
           (1, 1): ('1.007825031898', '7288.971064', '0.0'),
           (1, 2): ('2.014101777844', '13135.722895', '1112.2831'),
           (1, 3): ('3.01604928132', '14949.81090', '2827.2654'),
           (2, 4): ('4.00260325413', '2424.91587', '7073.9156'),
           (6, 12): ('12', '0', '7680.1446'),
           (26, 56): ('55.934935537', '-60607.163', '8790.3563'),
           (28, 62): ('61.928344753', '-66746.440', '8794.5555'),
           (92, 238): ('238.050786936', '47307.732', '7570.1262')}
anchor_results = []
for key, values in anchors.items():
    r = index[key]
    for name, expected in zip(('atomic_mass', 'mass_excess', 'binding_per_nucleon'), values):
        assert r['quantities'][name]['value'] == float(expected), (r['label'], name)
    anchor_results.append({'id': r['id'], 'label': r['label'], 'verified': True})

# Algebraic binding relation from mass excesses, with each field's printed
# rounding resolution. This tests separate properties throughout the table.
h = Decimal(index[1, 1]['quantities']['mass_excess']['raw_value'])
n = Decimal(index[0, 1]['quantities']['mass_excess']['raw_value'])
hres = Decimal(str(index[1, 1]['quantities']['mass_excess']['source_resolution']))
nres = Decimal(str(index[0, 1]['quantities']['mass_excess']['source_resolution']))
max_binding = 0
for r in records:
    q = r['quantities']; a, z, count = Decimal(r['A']), Decimal(r['Z']), Decimal(r['N'])
    expected = (z * h + count * n - decimal(q['mass_excess']['raw_value'])) / a
    residual = abs(expected - decimal(q['binding_per_nucleon']['raw_value']))
    tolerance = (Decimal(str(q['binding_per_nucleon']['source_resolution'])) +
                 (z * hres + count * nres + Decimal(str(q['mass_excess']['source_resolution']))) / a) / 2 + Decimal('1e-8')
    assert residual <= tolerance, (r['label'], residual, tolerance)
    max_binding = max(max_binding, float(residual))

# Independently use atomic masses and AME-era u*c^2, not mass excesses.
def atom(r):
    return Decimal(r['atomic_mass_integer_u']) + decimal(r['quantities']['atomic_mass']['raw_value']) / Decimal(1000000)
mh, mn = atom(index[1, 1]), atom(index[0, 1])
mass_binding = []
for key in anchors:
    r = index[key]
    calculated = (Decimal(r['Z']) * mh + Decimal(r['N']) * mn - atom(r)) * Decimal('931494.10242') / Decimal(r['A'])
    residual = abs(calculated - decimal(r['quantities']['binding_per_nucleon']['raw_value']))
    assert residual < Decimal('0.00006')
    mass_binding.append({'label': r['label'], 'residual_keV_per_nucleon': float(residual)})

# The preexisting pynucastro extract lacks uncertainty/flags. It is a check
# of mass excess central values only; tolerate its own decimal rounding.
extract = ROOT / '.tooling/python/Lib/site-packages/pynucastro/nucdata/AtomicMassEvaluation/mass_excess2020.txt'
compared = 0; max_mass_difference = 0; rounding_exceptions = []
for line in extract.read_text().splitlines():
    tokens = line.split()
    if len(tokens) != 3 or not tokens[0].isdigit():
        continue
    a, z = map(int, tokens[:2]); value = Decimal(tokens[2]) * 1000
    if (z, a) not in index:
        continue
    q = index[z, a]['quantities']['mass_excess']
    diff = abs(value - decimal(q['raw_value']))
    rounding = Decimal(10) ** Decimal(tokens[2]).as_tuple().exponent * 1000 / 2
    tolerance = rounding + Decimal(str(q['source_resolution'])) / 2 + Decimal('1e-8')
    if diff > tolerance:
        # The installed extract comes from NUBASE2020, not this original
        # mass file. Record O16's final-digit discrepancy instead of concealing
        # it. It is less than the original tabulated standard uncertainty.
        assert (z, a) == (8, 16) and diff == Decimal('0.0000700')
        assert diff < Decimal(str(q['uncertainty']))
        rounding_exceptions.append({'label': index[z, a]['label'], 'difference_keV': float(diff),
                                    'original_keV': q['value'], 'extract_keV': float(value),
                                    'original_uncertainty_keV': q['uncertainty'],
                                    'note': 'NUBASE-derived extract differs beyond last-digit rounding; original AME value remains authoritative.'})
    compared += 1; max_mass_difference = max(max_mass_difference, float(diff))
assert compared == 3558

# Parser must not skip malformed or duplicate data rows.
raw = DATA.read_bytes()
bad = [raw + b'\nunknown data row', raw + b'\n' + original[36].encode(),
       raw.replace(b'8071.31806', b'not_a_num!', 1)]
for broken in bad:
    try:
        parse_table(broken)
    except ValueError:
        pass
    else:
        raise AssertionError('Malformed row was accepted')

cfg = {'selected_ids': [index[26, 56]['id'], index[28, 62]['id']], 'view': 'binding', 'include_estimates': False}
payload = export(cfg)
assert len(payload['records']) == 2
assert json.loads(json.dumps(payload, allow_nan=False)) == payload
hidden = export({**cfg, 'view': 'chart', 'include_estimates': True})
assert hidden['selection_sha256'] == payload['selection_sha256']
assert hidden['records'] == payload['records']
with tempfile.TemporaryDirectory() as folder:
    written = export_file(cfg, folder)
    assert Path(written['export_file']).exists()
    assert json.loads(Path(written['export_file']).read_text(encoding='utf-8')) == written
    path = Path(folder) / 'selection.json'
    saved = save(cfg, path)
    assert load(path)['configuration'] == cfg | {'schema': 1}
    assert load(path)['compatibility'] == 'same_generation'
    changed = copy.deepcopy(saved)
    changed['generation']['data_sha256']['data/science/ame2020-mass-original.txt'] = '0' * 64
    changed['sha256'] = digest({k: changed[k] for k in ('schema', 'configuration', 'generation')})
    path.write_text(json.dumps(changed))
    assert load(path)['compatibility'] == 'changed_generation'
    saved['configuration']['selected_ids'] = ['nucleus:ame2020:999:999']
    path.write_text(json.dumps(saved))
    try:
        load(path)
    except ValueError:
        pass
    else:
        raise AssertionError('Corrupt selection accepted')
report = {'states': len(records), 'independently_tokenized_property_fields': fields,
          'estimated_property_fields': flags, 'estimated_binding_states': 1008,
          'missing_beta_values': missing, 'original_sha256': EXPECTED_SHA256,
          'anchor_checks': anchor_results, 'binding_from_atomic_masses': mass_binding,
          'all_binding_mass_excess_identity_max_residual_keV_per_nucleon': max_binding,
          'rounding_tolerance_passed': True, 'upstream_extract_common_ids': compared,
          'upstream_max_difference_keV': max_mass_difference,
          'upstream_rounding_exceptions': rounding_exceptions,
          'upstream_extract_sha256': hashlib.sha256(extract.read_bytes()).hexdigest(),
          'malformed_duplicate_rows_rejected': True, 'export_roundtrip': True,
          'presentation_preserves_selection_identity': True, 'save_load_integrity_generation': True,
          'scope': 'Evaluated reference states; rounding consistency is not observational accuracy or proof of stability.'}
(ROOT / 'evidence/nuclei-check.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
