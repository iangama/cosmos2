"""Concrete SI examples accompanying the requested four-force test review."""
from pathlib import Path
import hashlib
import json
import math
import sys
from scipy.constants import elementary_charge, proton_mass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from atlas_import import gm_data
from forces import evaluate
from nuclear_energies import evaluate as energy, PRESETS

gm = gm_data()
r = 384400e3
au = 149597870700.0
gravity = {
    'kind': 'illustrative reference distances, not a queried orbital epoch',
    'earth_moon_distance_m': r,
    'sun_earth_distance_m': au,
    'earth_acceleration_at_moon_m_s2': gm['GM3']['value'] / r**2,
    'moon_acceleration_at_earth_m_s2': gm['GMM']['value'] / r**2,
    'sun_acceleration_at_earth_m_s2': gm['GMS']['value'] / au**2,
    'isolated_source_acceleration_ratio_at_double_distance': .25,
    'solar_lunar_linear_tidal_amplitude_ratio': gm['GMS']['value'] / gm['GMM']['value'] * (r / au)**3,
    'source_GM': gm,
}
em = {
    'kind': 'analytic uniform-field example; not the local IGRF value',
    'particle': 'proton', 'B_T': 50e-6, 'E_V_m': 0,
    'perpendicular_speed_m_s': 1e5,
    'larmor_radius_m': proton_mass * 1e5 / (elementary_charge * 50e-6),
    'period_s': 2 * math.pi * proton_mass / (elementary_charge * 50e-6),
    'magnetic_power_W': 0,
}
dt_preset = next(p for p in PRESETS if p['id'] == 'dt')
dt_result = energy(dt_preset['configuration'])
request = {'scenario': 'decays', 'parameters': {'parent_case': 'c14', 'initial_population': 1000}}
decay = evaluate(request)['result']
hidden = evaluate({**request, 'controls': {'weak': {'visible': False}}})['result']
off = evaluate({**request, 'controls': {'weak': {'acting': False}}})['result']
d = decay['decays']
samples = []
for periods in (0, 1, 2, 4):
    index = periods * 60
    parent = 1000 * d['population_fractions'][index][0]
    expected = 1000 * 2**(-periods)
    assert math.isclose(parent, expected, rel_tol=1e-12)
    samples.append({'half_lives': periods, 'elapsed_s': decay['time_s'][index],
                    'expected_parent_population': parent,
                    'electron_antineutrinos': d['electron_antineutrino_count'][index]})
assert hidden == decay
assert all(row[0] == 1 for row in off['decays']['population_fractions'])
report = {
    'scope': 'Explained examples; complements the executed scientific suite, not integrated-body acceptance.',
    'gravity': gravity, 'electromagnetism': em,
    'strong_mixed_nuclear_process': {'reaction': 'D + T -> He4 + n',
        'Q': dt_result['Q'], 'kinematics': dt_result['kinematics'],
        'note': 'Nuclear binding plus EM barrier; Q alone does not determine reaction rate.'},
    'weak': {'parent': 'C14', 'reaction': 'C14 -> N14 + electron + electron antineutrino',
             'samples': samples, 'visibility_preserves_result': True,
             'acting_off_preserves_parent': True,
             'note': 'Expected populations with the pinned evaluated atomic reference environment.'},
    'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'recheck_manifest_sha256': hashlib.sha256((ROOT / 'evidence/four-forces-recheck-20261023.json').read_bytes()).hexdigest(),
}
destination = ROOT / 'evidence/four-force-examples-20261023.json'
assert not destination.exists(), 'Preserve the prior example receipt; use a new dated artifact.'
destination.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')
print(json.dumps({'written': str(destination), 'decay_samples': samples}, ensure_ascii=False))
