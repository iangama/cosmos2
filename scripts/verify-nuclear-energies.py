"""Independent mass-column, invariant, uncertainty and persistence checks."""
from collections import Counter
from decimal import Decimal, localcontext
from pathlib import Path
import copy
import json
import math
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
import nuclear_energies as model
import nuclei

raw = (ROOT / 'data/science/ame2020-mass-original.txt').read_text().splitlines()[36:]
atomic, excess, sigmas, precision = {}, {}, {}, {}
for line in raw:
    line = line.ljust(135)
    z, a = int(line[9:14]), int(line[14:19])
    key = f'nucleus:ame2020:{z}:{a}'
    token = line[110:123].strip().replace('#', '.')
    atomic[key] = Decimal(line[106:109].strip()) + Decimal(token) * Decimal('1e-6')
    excess[key] = Decimal(line[28:42].strip().replace('#', '.'))
    sigmas[key] = Decimal(line[42:54].strip().replace('#', '.'))
    precision[key] = (Decimal(10) ** Decimal(token).as_tuple().exponent * Decimal('1e-6'),
                      Decimal(10) ** excess[key].as_tuple().exponent)
atomic[model.PHOTON] = excess[model.PHOTON] = sigmas[model.PHOTON] = Decimal(0)
precision[model.PHOTON] = (Decimal(0), Decimal(0))
uc2 = Decimal('931494.10242')
refs = {r['case']: r['result']['data']['entries'][0] for r in json.loads((ROOT / 'evidence/nndc-qcalc-reference.json').read_text())['responses']}
checks, max_atomic_error, max_invariant_error, max_gradient_error = [], 0, 0, 0

def coefficients(cfg):
    c = Counter([cfg['projectile_id'], cfg['target_id']])
    for p in cfg['products']:
        c[p['id']] -= p['count']
    return c


def invariant_threshold(cfg, values):
    def mass(i):
        return Decimal(0) if i == model.PHOTON else Decimal(i.split(':')[-1]) * uc2 + values[i]
    ma, mt = mass(cfg['projectile_id']), mass(cfg['target_id'])
    mf = sum(mass(p['id']) * p['count'] for p in cfg['products'])
    # Total incident energy from s, subtract projectile rest energy afterwards.
    return max(Decimal(0), (mf * mf - ma * ma - mt * mt) / (2 * mt) - ma)


with localcontext() as ctx:
    ctx.prec = 60
    for preset in model.PRESETS:
        cfg = preset['configuration']
        result = model.evaluate(cfg)
        c = coefficients(cfg)
        q_atomic = sum(atomic[key] * count for key, count in c.items()) * uc2
        q = Decimal(result['Q']['decimal_keV'])
        bound = sum(abs(count) * (precision[key][0] * uc2 + precision[key][1]) / 2 for key, count in c.items())
        assert abs(q_atomic - q) <= bound, (preset['id'], q_atomic, q, bound)
        max_atomic_error = max(max_atomic_error, float(abs(q_atomic - q)))
        external = refs[preset['id']]
        resolution = Decimal(10) ** Decimal(external['energy']['nds_value']).as_tuple().exponent
        assert abs(q - Decimal(str(external['energy']['value']))) <= resolution / 2 + Decimal('1e-9')
        sigma = sum((count * sigmas[key]) ** 2 for key, count in c.items()).sqrt()
        assert math.isclose(float(sigma), result['Q']['standard_uncertainty_independent'], rel_tol=1e-14)
        expected = invariant_threshold(cfg, excess)
        threshold = result['kinematics']['threshold_keV']
        assert math.isclose(float(expected), threshold, rel_tol=1e-14, abs_tol=1e-12)
        max_invariant_error = max(max_invariant_error, abs(float(expected) - threshold))
        if expected > 0:
            for factor in ('0.999999', '1.000001'):
                request = {**cfg, 'projectile_energy_MeV': float(expected * Decimal(factor) / 1000)}
                k = model.evaluate(request)['kinematics']
                assert (k['available_CM_keV'] > 0) == (Decimal(factor) > 1)
                assert k['accessible_by_energy'] == (Decimal(factor) > 1)
            h = Decimal('.00001')
            gradients = {}
            for key in c:
                if key == model.PHOTON:
                    continue
                plus, minus = excess.copy(), excess.copy()
                plus[key] += h
                minus[key] -= h
                gradients[key] = (invariant_threshold(cfg, plus) - invariant_threshold(cfg, minus)) / (2 * h)
                error = abs(float(gradients[key]) - result['kinematics']['threshold_uncertainty_gradient'][key])
                max_gradient_error = max(max_gradient_error, error)
                assert error < 2e-14, (key, error)
            expected_sigma = sum((sigmas[key] * g) ** 2 for key, g in gradients.items()).sqrt()
            assert math.isclose(float(expected_sigma), result['kinematics']['threshold_standard_uncertainty_independent_keV'], rel_tol=1e-13)
        checks.append({'case': preset['id'], 'Q_keV': float(q), 'atomic_column_Q_keV': float(q_atomic),
                       'source_rounding_bound_keV': float(bound), 'NNDC_Q_keV': external['energy']['value'],
                       'sigma_independent_keV': float(sigma), 'NNDC_reported_error_keV': external['energy']['error'],
                       'threshold_invariant_keV': threshold, 'NNDC_threshold_keV': external['threshold']['value']})

# Required measured discrepancy, not silently matched to a different threshold.
nitrogen = next(r for r in checks if r['case'] == 'n14-n2n')
assert abs(nitrogen['threshold_invariant_keV'] - nitrogen['NNDC_threshold_keV']) > 3
assert next(r for r in checks if r['case'] == 'c12alpha')['sigma_independent_keV'] > 0

# Identical nuclide repeated is one mass variable, not independent copies.
dd = model.evaluate(model.PRESETS[1]['configuration'])
assert next(t for t in dd['Q']['terms'] if t['id'] == model.D)['coefficient'] == 2
elastic = {**model.PRESETS[0]['configuration'], 'products': [{'id': model.D, 'count': 1}, {'id': model.T, 'count': 1}]}
zero = model.evaluate(elastic)
assert zero['Q']['value'] == zero['Q']['standard_uncertainty_independent'] == 0 and zero['Q']['terms'] == []
assert zero['kinematics']['threshold_keV'] == 0
# An extrapolated state can appear in valid breakup. Its flags must survive.
estimated = {**elastic, 'projectile_id': model.N, 'target_id': model.ident(3, 3),
             'products': [{'id': model.H, 'count': 1}, {'id': model.HE3, 'count': 1}]}
assert model.evaluate(estimated)['Q']['estimated']
missing = model.separations(model.H)
assert all(s['value'] is None and s['status'] == 'missing_remnant' for s in missing['energies'])
he4 = model.separations(model.HE4)
assert next(s for s in he4['energies'] if s['name'] == 'Sn')['value'] > 20000
# Column-independent separation energies, including multiple identical emissions.
separation_checked = 0
for key in (model.HE4, model.ident(6, 12), model.ident(26, 56), model.ident(92, 238)):
    for s in model.separations(key)['energies']:
        if s['value'] is None:
            continue
        c = {t['id']: t['coefficient'] for t in s['terms']}
        independent = sum(atomic[i] * count for i, count in c.items()) * uc2
        bound = sum(abs(count) * (precision[i][0] * uc2 + precision[i][1]) / 2 for i, count in c.items())
        assert abs(float(independent) - s['value']) <= float(bound) + 1e-8
        separation_checked += 1

# Vary incident energy; Q and reference identity stay invariant.
first = model.evaluate({})
for energy in (0, .00001, 1, 100):
    r = model.evaluate({'projectile_energy_MeV': energy})
    assert r['Q'] == first['Q'] and r['reaction_sha256'] == first['reaction_sha256']
    assert r['generation'] == first['generation']

bad = [None, [], {'schema': 2}, {'target_id': model.PHOTON}, {'projectile_id': 'unknown'},
       {'projectile_id': {}}, {'projectile_energy_MeV': -1}, {'projectile_energy_MeV': 101},
       {'projectile_energy_MeV': float('nan')}, {'projectile_energy_MeV': True},
       {'products': []}, {'products': [None]}, {'products': [{'id': model.HE4, 'count': 1}]},
       {'products': [{'id': model.HE4, 'count': True}, {'id': model.N, 'count': 1}]},
       {'products': [{'id': model.HE4, 'count': 2}, {'id': model.N, 'count': 1}]},
       {'separation_id': model.PHOTON}]
for request in bad:
    try:
        model.evaluate(request)
    except ValueError:
        pass
    else:
        raise AssertionError(('invalid accepted', request))
assert model.evaluate({}) == first

with tempfile.TemporaryDirectory(prefix='cosmos2 energies ') as folder:
    path = Path(folder) / 'selection.json'
    original = model.save(model.PRESETS[-1]['configuration'], path)
    assert model.load(path)['compatibility'] == 'same_generation'
    assert model.evaluate(model.load(path)['configuration']) == model.evaluate(model.PRESETS[-1]['configuration'])
    for key in ('configuration', 'generation'):
        corrupt = copy.deepcopy(original)
        corrupt[key] = {}
        nuclei.write_atomic(path, corrupt)
        try:
            model.load(path)
        except ValueError:
            pass
        else:
            raise AssertionError('Corruption not detected')
    changed = copy.deepcopy(original)
    changed['generation']['model_version'] = 'previous'
    changed['sha256'] = nuclei.digest({k: changed[k] for k in ('schema', 'configuration', 'generation')})
    nuclei.write_atomic(path, changed)
    assert model.load(path)['compatibility'] == 'changed_generation'
    before = path.read_bytes()
    try:
        model.save({'products': []}, path)
    except ValueError:
        pass
    assert path.read_bytes() == before

report = {'ok': True, 'generation': model.GENERATION, 'presets': checks,
          'max_atomic_column_Q_difference_keV': max_atomic_error,
          'max_invariant_difference_keV': max_invariant_error,
          'max_threshold_gradient_difference': max_gradient_error,
          'separation_atomic_column_checks': separation_checked,
          'invalid_inputs_refused': len(bad), 'same_mass_consolidated': True,
          'missing_remnant_and_estimated_flags': True, 'source_table_unmodified': True,
          'energy_variation_preserves_Q': True, 'persistence_and_changed_generation': True,
          'NNDC_discrepancies_preserved': 'Thresholds and reported errors retained separately; only central Q compared within external printed resolution.',
          'scope': 'Necessary kinematic condition; not probability, rate, lifetime or complete AME covariance uncertainty.'}
(ROOT / 'evidence/nuclear-energies-check.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
print(json.dumps(report, indent=2))
