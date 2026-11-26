"""Five JPL epoch clones, independent SI integration and checkpoint semantics."""
from pathlib import Path
import copy
import json
import math
import sys
import tempfile
import numpy as np
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'app'))
from atlas import states
from atlas_import import prepare, experiment_subset, digest, gm_data
from physics import PHYSICAL_SCALE as scale
from session import Session

epochs = ['1950-01-01T00:00:00', '2000-01-01T12:00:00', '2026-10-11T12:00:00',
          '2030-01-01T00:00:00', '2050-01-01T00:00:00']
results = []; initial_2026 = None
for utc in epochs:
    source = states(utc=utc); initial = prepare(experiment_subset(source))
    source_snapshot = copy.deepcopy(source)
    if utc.startswith('2026'):
        initial_2026 = initial
    with tempfile.TemporaryDirectory() as folder:
        session = Session(folder); session.import_atlas(initial)
        current = session.state()
        assert current['time'] == 0 and len(current['bodies']) == 3
        assert current['contract']['epoch'] == source['epoch']
        assert all(b['id'].startswith('exp:' + initial['branch_id']) for b in current['bodies'])
        max_p = max(abs(v * scale['length_unit_m'] + c - x)
                    for b in initial['bodies'] for v, c, x in zip(b['position'], initial['initial_ssb_origin_m'], b['source_position_m']))
        max_v = max(abs(v * scale['velocity_unit_m_s'] + c - x)
                    for b in initial['bodies'] for v, c, x in zip(b['velocity'], initial['inertial_origin_velocity_m_s'], b['source_velocity_m_s']))
        assert max_p <= .001 and max_v <= 1e-8
        assert math.isclose(initial['bodies'][0]['mass'], 1.0000000003108479, rel_tol=1e-14)
        assert initial['bodies'][1]['source_GM']['value'] == 398600.435544 * 1e9
        assert initial['bodies'][2]['source_GM']['value'] == 4902.800104 * 1e9
        total = math.fsum(b['mass'] for b in initial['bodies'])
        com = [math.fsum(b['mass'] * b['position'][k] for b in initial['bodies']) / total for k in range(3)]
        drift = [math.fsum(b['mass'] * b['velocity'][k] for b in initial['bodies']) / total for k in range(3)]
        assert max(map(abs, com)) < 1e-12 and max(map(abs, drift)) < 1e-12
        assert source == source_snapshot
        results.append({'utc': utc, 'inverse_position_max_error_m': max_p, 'inverse_velocity_max_error_m_s': max_v,
                        'initial_barycenter_canonical': com, 'initial_barycenter_velocity_canonical': drift})

# Accelerations in SI compared with a symmetric REBOUND velocity difference.
positions = np.array([b['position'] for b in initial_2026['bodies']]) * scale['length_unit_m']
velocities = np.array([b['velocity'] for b in initial_2026['bodies']]) * scale['velocity_unit_m_s']
gm = np.array([b['source_GM']['value'] for b in initial_2026['bodies']])
def acceleration(pos):
    result = np.zeros((3, 3))
    for i in range(3):
        for j in range(3):
            if i != j:
                delta = pos[j] - pos[i]
                result[i] += gm[j] * delta / np.linalg.norm(delta)**3
    return result
def equations(t, state):
    return np.concatenate((state[9:], acceleration(state[:9].reshape(3, 3)).ravel()))

with tempfile.TemporaryDirectory() as folder:
    session = Session(folder); session.import_atlas(initial_2026)
    forward = session.sim.copy(); backward = session.sim.copy()
    forward.integrate(1 / scale['time_unit_s']); backward.integrate(-1 / scale['time_unit_s'])
    vf = np.array([[p.vx, p.vy, p.vz] for p in forward.particles]) * scale['velocity_unit_m_s']
    vb = np.array([[p.vx, p.vy, p.vz] for p in backward.particles]) * scale['velocity_unit_m_s']
    a_reference = acceleration(positions); a_rebound = (vf - vb) / 2
    accel_max = float(np.max(np.abs(a_rebound - a_reference)))
    assert accel_max < 1e-10
    reference = solve_ivp(equations, [0, 86400], np.concatenate((positions.ravel(), velocities.ravel())),
                          method='DOP853', rtol=2e-13, atol=np.array([.001]*9 + [1e-8]*9), max_step=600)
    assert reference.success
    session.sim.integrate(86400 / scale['time_unit_s'])
    evolved = session.state(); actual = np.array([b['position'] for b in evolved['bodies']]) * scale['length_unit_m']
    independent_error = float(np.max(np.abs(actual - reference.y[:9, -1].reshape(3, 3))))
    assert independent_error <= 10
    assert evolved['atlas_initial'] == initial_2026
    assert evolved['energy_error'] < 1e-9
    assert evolved['contract']['excluded_influences']
    original = session.state()
    # These invalid inputs must not mutate the existing integrated session.
    invalid = []
    corrupt = copy.deepcopy(initial_2026); corrupt['bodies'][1]['mass'] *= 2; invalid.append(corrupt)
    for change in ('GM', 'scale', 'ids', 'frame', 'epoch', 'render_matrix', 'reflected_matrix', 'malformed_observer'):
        broken = copy.deepcopy(initial_2026)
        if change == 'GM':
            del broken['bodies'][0]['source_GM']
        elif change == 'scale':
            broken['physical_scale']['length_unit_m'] *= 2
        elif change == 'ids':
            broken['bodies'][0]['reference_id'] = 'sol:naif:0'
        elif change == 'frame':
            broken['contract']['frame'] = 'GALACTIC'
        elif change == 'epoch':
            broken['contract']['epoch']['et_tdb_s'] += 1000
        elif change == 'render_matrix':
            broken['j2000_to_render_frame'][0][0] *= 2
        elif change == 'reflected_matrix':
            broken['j2000_to_render_frame'][0] = [-v for v in broken['j2000_to_render_frame'][0]]
        else:
            broken['source']['observer'] = 'camera'
        broken['initial_state_sha256'] = digest({k: v for k, v in broken.items() if k != 'initial_state_sha256'})
        invalid.append(broken)
    for broken in invalid:
        try:
            session.import_atlas(broken)
        except (ValueError, KeyError):
            pass
        else:
            raise AssertionError('Incompatible copy was accepted')
        assert session.state() == original
    try:
        session.set_mass('p0', 2)
    except ValueError:
        pass
    else:
        raise AssertionError('Fixture identifier edited an imported body')
    central_id = evolved['bodies'][0]['id']
    event = session.set_mass(central_id, 2)
    assert event['body'] == central_id and session.state()['bodies'][0]['mass'] == 2
    assert session.state()['atlas_initial'] == initial_2026
    saved = session.save(); checkpoint = session.state()
    manifest_file = Path(folder) / 'latest.json'; manifest = json.loads(manifest_file.read_text())
    assert isinstance(saved['sha256'], str) and saved['sha256'] == manifest['sha256']
    assert manifest['schema'] == 3 and manifest['atlas_initial'] == initial_2026
    session.sim.integrate(90000 / scale['time_unit_s']); session.load()
    loaded = session.state()
    assert loaded['bodies'] == checkpoint['bodies'] and loaded['time'] == checkpoint['time']
    assert loaded['atlas_initial'] == checkpoint['atlas_initial']
    assert loaded['restoration']['status'] == 'same_generation'
    # Corrupted metadata and a resealed incompatible contract both refuse load.
    broken = copy.deepcopy(manifest); broken['atlas_initial']['source']['frame'] = 'GALACTIC'
    manifest_file.write_text(json.dumps(broken))
    before = session.state()
    try:
        session.load()
    except ValueError:
        pass
    else:
        raise AssertionError('Corrupt checkpoint metadata accepted')
    assert session.state() == before
    changed = copy.deepcopy(manifest); changed['saved_generation']['runtime']['python'] = 'different'
    changed['manifest_sha256'] = digest({k: v for k, v in changed.items() if k != 'manifest_sha256'})
    manifest_file.write_text(json.dumps(changed)); session.load()
    assert session.state()['restoration']['status'] == 'changed_generation'
    assert session.state()['bodies'] == checkpoint['bodies']

report = {'epoch_clones': results, 'GM_from_DE442_comments': gm_data(),
          'SI_acceleration_max_difference_m_s2': accel_max,
          'independent_DOP853_24h_max_position_difference_m': independent_error,
          'energy_relative_error_24h': evolved['energy_error'], 'invalid_states_rejected_without_mutation': len(invalid),
          'namespace_specific_mass_edit': True, 'source_not_changed_by_intervention': True,
          'checkpoint_exact_bodies_and_source': True, 'checkpoint_corruption_refused': True,
          'changed_generation_reported': True,
          'scope': 'Reduced Newtonian Sun/Earth/Moon clone; agreement between integrators is not JPL accuracy or long-term agreement with excluded forces.'}
(ROOT / 'evidence/atlas-import-check.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
