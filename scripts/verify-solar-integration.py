"""IS-1/2 candidate checks; freeze inputs and apply the predeclared 30-day limits."""
from pathlib import Path
import argparse
import copy
import datetime as dt
import hashlib
import json
import math
import platform
import subprocess
import sys
import time
import traceback
import zipfile

import numpy as np
import rebound
import scipy
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is12-solar-product/app'
sys.path.insert(0, str(APP))
from solar_catalog import states
from solar_import import prepare, validate
from solar_contract import sha, digest
from physics import PHYSICAL_SCALE as U
from session import Session

LIMITS = {'position_component_m': 10., 'velocity_component_m_s': 1e-5,
          'refinement_position_component_m': 1., 'relative_energy_drift': 1e-9,
          'normalized_linear_momentum_drift': 1e-10, 'normalized_angular_momentum_drift': 1e-10,
          'inverse_position_m': .001, 'inverse_velocity_m_s': 1e-8,
          'acceleration_component_m_s2': 1e-10}


def phases(sim):
    return np.array([[p.x, p.y, p.z, p.vx, p.vy, p.vz] for p in sim.particles])


def balances(series, masses, seconds):
    r, v = series[:, :, :3], series[:, :, 3:]
    energy = .5 * np.sum(masses[None, :] * np.sum(v*v, axis=2), axis=1)
    for i in range(len(masses)):
        for j in range(i + 1, len(masses)):
            energy -= masses[i] * masses[j] / np.linalg.norm(r[:, i] - r[:, j], axis=1)
    momentum = np.sum(masses[None, :, None] * v, axis=1)
    angular = np.sum(masses[None, :, None] * np.cross(r, v), axis=1)
    pscale = float(np.sum(masses * np.linalg.norm(v[0], axis=1)))
    lscale = float(np.sum(masses * np.linalg.norm(np.cross(r[0], v[0]), axis=1)))
    center = np.sum(masses[None, :, None] * r, axis=1) / masses.sum()
    center_velocity = np.sum(masses[None, :, None] * v, axis=1) / masses.sum()
    expected_center = center[0] + seconds[:, None] / U['time_unit_s'] * center_velocity[0]
    return {'energy_normalization': 'initial nonzero total canonical kinetic plus pair potential energy',
            'momentum_normalization': 'sum_i(m_i*norm(v_i)) at t0, canonical, same inertial origin',
            'angular_normalization': 'sum_i(m_i*norm(r_i cross v_i)) at t0, canonical, same inertial origin',
            'momentum_scale_canonical': pscale, 'angular_scale_canonical': lscale,
            'relative_energy_drift': float(np.max(np.abs((energy - energy[0]) / energy[0]))),
            'normalized_linear_momentum_drift': float(np.max(np.linalg.norm(momentum - momentum[0], axis=1)) / pscale),
            'normalized_angular_momentum_drift': float(np.max(np.linalg.norm(angular - angular[0], axis=1)) / lscale),
            'barycenter_inertial_drift_m': float(np.max(np.linalg.norm(center - expected_center, axis=1)) * U['length_unit_m'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Use a unique lowercase/digit/hyphen label.')
    folder = ROOT / ('output/is12-solar-check-' + args.label)
    receipt = ROOT / ('evidence/is12-solar-check-' + args.label + '.json')
    if receipt.exists():
        raise FileExistsError(receipt)
    folder.mkdir(exist_ok=False)
    fixture_path = ROOT / 'output/solar-integration-staging/four-body-initial-si.json'
    contract_path = ROOT / 'IS-2-VALIDACAO-PREVIA.md'
    before = json.loads((ROOT / 'evidence/is12-solar-candidate-prepared-20261023.json').read_text())
    installed = {p: sha(ROOT / p) for p in before['base_files_sha256']}
    owner = ROOT / 'user/sessions/latest.json'
    owner_before = sha(owner) if owner.exists() else None
    session_pointer = ROOT / 'output/session.json'
    session_before = sha(session_pointer) if session_pointer.exists() else None
    paths = sorted(p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    paths += [Path(__file__).resolve(), fixture_path, contract_path]
    sources = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}
    archive = folder / 'executed-sources-and-contract.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            z.write(p, p.relative_to(ROOT).as_posix())
    report = {'schema': 1, 'label': args.label, 'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'runtime': {'python': platform.python_version(), 'numpy': np.__version__,
                          'scipy': scipy.__version__, 'rebound': rebound.__version__},
              'source_sha256': sources, 'source_archive': archive.relative_to(ROOT).as_posix(),
              'source_archive_sha256': sha(archive), 'limits_before_execution': LIMITS,
              'recipe_before_execution': {'days': 30, 'sample_interval_s': 21600,
                  'IAS15_epsilon': 1e-9, 'IAS15_refined_epsilon': 1e-12,
                  'IAS15_refinement_intermediate_output_s': 10800,
                  'DOP853_rtol': 2e-13, 'DOP853_position_atol_m': .001,
                  'DOP853_velocity_atol_m_s': 1e-9, 'DOP853_max_step_s': 3600},
              'checks': {}, 'completed': False, 'accepted': False,
              'scope': 'Isolated candidate registry, import, persistence and reduced Newtonian integration. No native UI, rendering performance or four-force coupling acceptance.'}

    def persist():
        receipt.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')

    persist()  # The recipe and input/source hashes exist before propagation.
    try:
        fixture = json.loads(fixture_path.read_text(encoding='utf-8'))
        catalog = states(fixture['epoch']['utc'])
        initial = prepare(catalog)
        (folder / 'catalog.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding='utf-8')
        (folder / 'initial.json').write_text(json.dumps(initial, indent=2, ensure_ascii=False), encoding='utf-8')
        for actual, expected in zip(catalog['bodies'], fixture['bodies']):
            assert actual['id'] == expected['id'] and actual['GM']['value'] == expected['GM_m3_s2']
            assert actual['position_m'] == expected['position_m'] and actual['velocity_m_s'] == expected['velocity_m_s']
        assert initial['initial_ssb_origin_m'] == fixture['subset_barycenter_SSB_position_m']
        assert initial['inertial_origin_velocity_m_s'] == fixture['subset_barycenter_SSB_velocity_m_s']
        report['checks']['initial_fixture_bit_identical'] = True
        inverse_p = max(abs(x * U['length_unit_m'] + c - y) for b in initial['bodies']
                        for x, c, y in zip(b['position'], initial['initial_ssb_origin_m'], b['source_position_m']))
        inverse_v = max(abs(x * U['velocity_unit_m_s'] + c - y) for b in initial['bodies']
                        for x, c, y in zip(b['velocity'], initial['inertial_origin_velocity_m_s'], b['source_velocity_m_s']))
        assert inverse_p <= LIMITS['inverse_position_m'] and inverse_v <= LIMITS['inverse_velocity_m_s']
        report['checks']['round_trip'] = {'position_max_m': inverse_p, 'velocity_max_m_s': inverse_v}

        session = Session(folder / 'sessions')
        session.import_atlas(initial)
        checkpoint = session.state()
        refusals = []
        for case in ['unsealed', 'GM599_as_system5', 'negative_GM', 'bool_GM', 'NaN', 'infinite_velocity',
                     'duplicate_id', 'barycenter_as_planet', 'wrong_frame', 'wrong_epoch', 'wrong_units',
                     'missing_provider', 'mislabelled_capability', 'modified_canonical_position', 'bad_origin', 'reflection', 'bool_schema',
                     'bool_solver_G', 'invalid_UTC_date']:
            bad = copy.deepcopy(initial)
            if case == 'unsealed': bad['bodies'][0]['mass'] *= 2
            elif case == 'GM599_as_system5': bad['reference_catalog']['bodies'][3]['GM']['value'] = 126712764.1e9
            elif case == 'negative_GM': bad['reference_catalog']['bodies'][0]['GM']['value'] = -1
            elif case == 'bool_GM': bad['reference_catalog']['bodies'][0]['GM']['value'] = True
            elif case == 'NaN': bad['reference_catalog']['bodies'][0]['position_m'][0] = float('nan')
            elif case == 'infinite_velocity': bad['reference_catalog']['bodies'][0]['velocity_m_s'][0] = float('inf')
            elif case == 'duplicate_id': bad['reference_catalog']['bodies'][3] = copy.deepcopy(bad['reference_catalog']['bodies'][0])
            elif case == 'barycenter_as_planet': bad['reference_catalog']['bodies'][3]['entity_kind'] = 'system_barycenter'
            elif case == 'wrong_frame': bad['contract']['frame'] = 'GALACTIC'
            elif case == 'wrong_epoch': bad['contract']['epoch']['et_tdb_s'] += 1
            elif case == 'wrong_units': bad['physical_scale']['time_unit_s'] *= 2
            elif case == 'missing_provider': del bad['reference_catalog']['bodies'][3]['state_provider']
            elif case == 'mislabelled_capability': bad['reference_catalog']['bodies'][3]['capabilities']['magnetism']['status'] = 'integrated_evolving'
            elif case == 'modified_canonical_position': bad['bodies'][3]['position'][0] += 1
            elif case == 'bad_origin': bad['initial_ssb_origin_m'][0] += 1
            elif case == 'reflection': bad['reference_catalog']['j2000_to_render_frame'][0] = [-v for v in bad['reference_catalog']['j2000_to_render_frame'][0]]
            elif case == 'bool_schema': bad['schema'] = True
            elif case == 'bool_solver_G': bad['contract']['units']['G'] = True
            elif case == 'invalid_UTC_date': bad['reference_catalog']['epoch']['utc'] = '2026-02-31T12:00:00.000Z'
            if case not in ('unsealed', 'NaN', 'infinite_velocity'):
                bad['initial_state_sha256'] = digest({k: v for k, v in bad.items() if k != 'initial_state_sha256'})
            try:
                session.import_atlas(bad)
            except (ValueError, TypeError, KeyError):
                pass
            else:
                raise AssertionError('Invalid input accepted: ' + case)
            assert session.state() == checkpoint, case
            assert not (folder / 'sessions/latest.json').exists()
            refusals.append(case)
        report['checks']['transactional_refusals'] = refusals

        readings = []
        for body, expected in zip(initial['bodies'], fixture['bodies']):
            reading = session.solar_reading({'system_id': session.system_id, 'edit_token': session.edit_token,
                'revision': session.revision, 'expected_time': session.sim.t, 'frame': session.contract()['frame'], 'body_id': body['id']})
            error = max(abs(a-b) for a, b in zip(reading['acceleration_m_s2'], expected['initial_acceleration_m_s2']))
            assert error < 1e-12 and len(reading['sources']) == 3
            assert body['id'] not in [x['id'] for x in reading['sources']]
            assert session.state() == checkpoint
            readings.append({'body_id': body['reference_id'], 'max_acceleration_error_m_s2': error, 'self_field_omitted': True})
        report['checks']['passive_body_center_readings'] = readings

        # Compare every directional pair with a symmetric REBOUND velocity difference.
        pair_errors = []
        for i in range(4):
            for j in range(i + 1, 4):
                pair = rebound.Simulation(); pair.G = 1; pair.integrator = 'ias15'; pair.integrator.epsilon = 1e-9
                for index in (i, j):
                    b = initial['bodies'][index]
                    pair.add(m=b['mass'], x=b['position'][0], y=b['position'][1], z=b['position'][2],
                             vx=b['velocity'][0], vy=b['velocity'][1], vz=b['velocity'][2])
                f, b = pair.copy(), pair.copy()
                f.integrate(1 / U['time_unit_s']); b.integrate(-1 / U['time_unit_s'])
                actual = (phases(f)[:, 3:] - phases(b)[:, 3:]) * U['velocity_unit_m_s'] / 2
                for local, (a, source) in enumerate([(i, j), (j, i)]):
                    delta = np.array(fixture['bodies'][source]['position_m']) - fixture['bodies'][a]['position_m']
                    expected = fixture['bodies'][source]['GM_m3_s2'] * delta / np.linalg.norm(delta)**3
                    error = float(np.max(np.abs(actual[local] - expected)))
                    assert error < LIMITS['acceleration_component_m_s2'], (i, j, error)
                    pair_errors.append({'target': initial['bodies'][a]['reference_id'],
                                        'source': initial['bodies'][source]['reference_id'], 'max_error_m_s2': error})
        report['checks']['all_reciprocal_source_accelerations'] = pair_errors
        persist()

        seconds = np.arange(0, 30 * 86400 + 1, 21600, dtype=float)
        start = time.perf_counter()
        production, refined = session.sim.copy(), session.sim.copy()
        refined.integrator.epsilon = 1e-12
        series, fine = [], []
        for t in seconds:
            production.integrate(t / U['time_unit_s'])
            if t:
                refined.integrate((t - 10800) / U['time_unit_s'])
            refined.integrate(t / U['time_unit_s'])
            series.append(phases(production)); fine.append(phases(refined))
        series, fine = np.array(series), np.array(fine)
        rebound_wall = time.perf_counter() - start

        # Independent SI ODE: no product acceleration evaluator or REBOUND derivative.
        gm = np.array([b['GM_m3_s2'] for b in fixture['bodies']])
        positions = np.array([b['position_m'] for b in fixture['bodies']]) - initial['initial_ssb_origin_m']
        velocities = np.array([b['velocity_m_s'] for b in fixture['bodies']]) - initial['inertial_origin_velocity_m_s']
        def equations(t, phase):
            position = phase[:12].reshape(4, 3)
            acceleration = np.zeros((4, 3))
            for i in range(4):
                for j in range(4):
                    if i != j:
                        delta = position[j] - position[i]
                        acceleration[i] += gm[j] * delta / float(np.dot(delta, delta))**1.5
            return np.concatenate((phase[12:], acceleration.ravel()))
        start = time.perf_counter()
        reference = solve_ivp(equations, (0, seconds[-1]), np.concatenate((positions.ravel(), velocities.ravel())),
                              method='DOP853', rtol=2e-13, atol=np.array([.001]*12 + [1e-9]*12),
                              max_step=3600, dense_output=True)
        assert reference.success and reference.t[-1] == seconds[-1], reference.message
        sampled = reference.sol(seconds)
        independent = np.concatenate((sampled[:12].T.reshape(-1, 4, 3) / U['length_unit_m'],
                                      sampled[12:].T.reshape(-1, 4, 3) / U['velocity_unit_m_s']), axis=2)
        dop_wall = time.perf_counter() - start
        pdiff = np.abs(series[:, :, :3] - independent[:, :, :3]) * U['length_unit_m']
        vdiff = np.abs(series[:, :, 3:] - independent[:, :, 3:]) * U['velocity_unit_m_s']
        refinements = np.abs(series[:, :, :3] - fine[:, :, :3]) * U['length_unit_m']
        masses = np.array([b['mass'] for b in initial['bodies']])
        report['propagation'] = {
            'samples': len(seconds), 'horizon_days': 30,
            'position_component_max_m': float(pdiff.max()), 'velocity_component_max_m_s': float(vdiff.max()),
            'refinement_position_component_max_m': float(refinements.max()),
            'max_position_error_sample_body_component': list(map(int, np.unravel_index(pdiff.argmax(), pdiff.shape))),
            'per_body_position_max_m': {b['reference_id']: float(pdiff[:, i].max()) for i, b in enumerate(initial['bodies'])},
            'production_balances': balances(series, masses, seconds),
            'refined_balances': balances(fine, masses, seconds),
            'independent_balances': balances(independent, masses, seconds),
            'DOP853': {'nfev': reference.nfev, 'accepted_steps': len(reference.t)-1,
                       'largest_step_s': float(np.diff(reference.t).max()), 'wall_s': dop_wall},
            'IAS15': {'production_and_refined_wall_s': rebound_wall,
                      'production_steps': production.steps_done, 'refined_steps': refined.steps_done},
        }
        output = {'seconds': seconds.tolist(), 'initial': series[0].tolist(), 'final': series[-1].tolist(),
                  'canonical_IAS15': series.tolist(), 'canonical_IAS15_refined': fine.tolist(),
                  'canonical_DOP853': independent.tolist(),
                  'absolute_position_component_errors_m': pdiff.tolist(), 'absolute_velocity_component_errors_m_s': vdiff.tolist()}
        series_path = folder / '30-day-series.json'
        series_path.write_text(json.dumps(output, allow_nan=False), encoding='utf-8')
        report['propagation']['series_file'] = series_path.relative_to(ROOT).as_posix()
        report['propagation']['series_sha256'] = sha(series_path)
        persist()  # Preserve measurements even when a predeclared numerical limit refuses.
        assert pdiff.max() <= LIMITS['position_component_m']
        assert vdiff.max() <= LIMITS['velocity_component_m_s']
        assert refinements.max() <= LIMITS['refinement_position_component_m']
        for name in ['production_balances', 'refined_balances', 'independent_balances']:
            for key in ['relative_energy_drift', 'normalized_linear_momentum_drift', 'normalized_angular_momentum_drift']:
                assert report['propagation'][name][key] <= LIMITS[key], (name, key, report['propagation'][name][key])

        session.sim = production
        session.save(); saved = session.state()
        session.integrate(31 * 86400 / U['time_unit_s']); session.load()
        loaded = session.state()
        assert loaded['bodies'] == saved['bodies'] and loaded['time'] == saved['time']
        assert loaded['atlas_initial'] == initial and loaded['restoration']['status'] == 'same_generation'
        def guard():
            current = session.state()
            return {**{k: current[k] for k in ['system_id', 'edit_token', 'revision']},
                    'expected_time': current['time'], 'frame': current['contract']['frame']}
        first = session.create_branch({**guard(), 'name': 'quatro centros — referência30dias'})
        session.integrate(31 * 86400 / U['time_unit_s'])
        session.load_branch({**guard(), 'branch_id': first['id']})
        assert session.state()['bodies'] == saved['bodies'] and session.atlas_initial == initial
        session.restart_seed()
        assert phases(session.sim).tolist() == series[0].tolist() and session.atlas_initial == initial
        report['checks']['exact_checkpoint_branch_restart'] = True

        # Execute the existing three-body suite with only app and output paths redirected.
        legacy_source = (ROOT / 'scripts/verify-atlas-import.py').read_text(encoding='utf-8')
        redirected = legacy_source.replace("sys.path.insert(0, str(ROOT / 'app'))", "sys.path.insert(0, str(ROOT / 'output/is12-solar-product/app'))")
        redirected = redirected.replace("ROOT = Path(__file__).resolve().parents[1]", 'ROOT = Path(' + repr(str(ROOT)) + ')')
        legacy_receipt = folder / 'legacy-atlas-import-check.json'
        redirected = redirected.replace("ROOT / 'evidence/atlas-import-check.json'", 'Path(' + repr(str(legacy_receipt)) + ')')
        run_path = folder / 'verify-legacy-atlas-import-redirected.py'
        run_path.write_text(redirected, encoding='utf-8')
        with (folder / 'legacy-atlas-import.log').open('w', encoding='utf-8') as log:
            process = subprocess.run([sys.executable, '-Xutf8', str(run_path)], cwd=ROOT,
                                     stdout=log, stderr=subprocess.STDOUT, timeout=300)
        assert process.returncode == 0, 'Legacy three-body regression failed; inspect preserved log.'
        report['checks']['legacy_three_body_suite'] = {'passed': True,
            'original_script_sha256': sha(ROOT / 'scripts/verify-atlas-import.py'),
            'redirected_script_sha256': sha(run_path), 'receipt_sha256': sha(legacy_receipt)}
        report['completed'] = True
    except Exception:
        report['failure'] = traceback.format_exc()
    finally:
        report['installed_preserved'] = all(sha(ROOT / p) == value for p, value in installed.items())
        report['owner_pointer_preserved'] = (sha(owner) if owner.exists() else None) == owner_before
        report['session_pointer_preserved'] = (sha(session_pointer) if session_pointer.exists() else None) == session_before
        report['source_unchanged'] = all(sha(ROOT / p) == value for p, value in sources.items())
        report['accepted'] = report['completed'] and all(report[k] for k in
            ['installed_preserved', 'owner_pointer_preserved', 'session_pointer_preserved', 'source_unchanged'])
        report['finished_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
        persist()
    print(json.dumps({k: report.get(k) for k in ['completed', 'accepted', 'propagation', 'failure']}, ensure_ascii=False), flush=True)
    return 0 if report['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
